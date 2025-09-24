from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from typing import Optional
import os
import uuid
import logging
import tempfile
import shutil
import asyncio
import pdfplumber

from services.auth import get_current_user, User, rate_limit_dependency
from db import get_db
from repositories import documents as docs_repo
from repositories import analyses as analyses_repo
from repositories import audit_logs as audit_repo
from task import analyze_financial_document as analyze_financial_document_task
from config import settings
from crewai import Crew, Process
from redis_utils import (
    cache_get_json,
    cache_set_json,
    cache_invalidate_by_pattern,
    enqueue_pdf_job,
    get_job_status,
)

router = APIRouter(prefix="/v1/documents", tags=["documents"])

logger = logging.getLogger(__name__)

def run_crew(query: str, file_path: str = "data/sample.pdf"):
    """Run the financial analysis crew."""
    financial_crew = Crew(
        agents=[__import__('agents').financial_analyst],
        tasks=[analyze_financial_document_task],
        process=Process.sequential,
    )
    result = financial_crew.kickoff({'query': query, 'file_path': file_path})
    return result

@router.post("/analyze", dependencies=[Depends(rate_limit_dependency)])
async def analyze_financial_document(
    request: Request,
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    current_user: User = Depends(get_current_user),
):
    """Analyze a financial document and provide investment recommendations."""
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"
    try:
        os.makedirs("data", exist_ok=True)
        # Validate MIME type early
        mime_type = getattr(file, "content_type", None) or ""
        if settings.ALLOWED_UPLOAD_MIME_TYPES and mime_type not in settings.ALLOWED_UPLOAD_MIME_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported file type. Only PDF is allowed.")

        # Stream to a temp file enforcing size limit
        total_bytes = 0
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                        raise HTTPException(status_code=413, detail="File too large. Max 100MB.")
                    tmp.write(chunk)
                tmp.flush()
            finally:
                tmp_path = tmp.name

        # Magic header validation to reject non-PDF masquerading files
        try:
            with open(tmp_path, "rb") as fh:
                header = fh.read(5)
                if not header.startswith(b"%PDF-"):
                    os.unlink(tmp_path)
                    raise HTTPException(status_code=415, detail="Invalid file format. Only PDF is supported.")
        except HTTPException:
            raise
        except Exception:
            os.unlink(tmp_path)
            raise HTTPException(status_code=400, detail="Failed to validate uploaded file.")

        # Move to final path only after size and header validated
        shutil.move(tmp_path, file_path)

        # Preflight PDF: verify readable and not password-protected; basic text presence check
        try:
            with pdfplumber.open(file_path) as pdf:
                # Try first few pages for text to detect scanned images or encryption
                text_found = False
                check_pages = min(len(pdf.pages), 3)
                for i in range(check_pages):
                    try:
                        sample = pdf.pages[i].extract_text() or ""
                        if sample.strip():
                            text_found = True
                            break
                    except Exception:
                        # If any page extraction fails due to encryption/corruption, treat as unreadable
                        raise HTTPException(status_code=422, detail="PDF is corrupted or password-protected.")
                if not text_found:
                    raise HTTPException(status_code=422, detail="Scanned or image-only PDF detected; OCR is not supported.")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=422, detail="Failed to open PDF. It may be corrupted or password-protected.")

        if not query:
            query = "Analyze this financial document for investment insights"
        # Limit prompt size
        query = (query or "").strip()
        if len(query) > settings.MAX_QUERY_CHARS:
            raise HTTPException(status_code=400, detail=f"Query too long. Max {settings.MAX_QUERY_CHARS} characters.")
        db = get_db()
        doc = await docs_repo.create_document(
            db=db,
            filename=file.filename or os.path.basename(file_path),
            path=file_path,
            size=total_bytes,
            mime=mime_type,
            uploaded_by=current_user.username,
        )
        # Enqueue job for background processing
        job_id = str(uuid.uuid4())
        payload = {
            "id": job_id,
            "file_path": file_path,
            "query": query,
            "user_id": current_user.username,
            "document_id": str(doc.get("_id")),
        }
        enq_id = enqueue_pdf_job(payload)
        if not enq_id:
            raise HTTPException(status_code=503, detail="Background queue unavailable. Try again later.")

        try:
            await audit_repo.write_audit_log(
                db=db,
                path="/documents/analyze",
                method="POST",
                user=current_user.username,
                status="queued",
                extra={"documentId": str(doc.get("_id")), "jobId": job_id},
            )
        except Exception:
            logger.exception("Failed to write audit log")
        return {
            "status": "queued",
            "query": query,
            "file_processed": file.filename,
            "documentId": str(doc.get("_id")),
            "jobId": job_id,
        }
    except Exception as e:
        # Mask internal errors while remaining informative
        if isinstance(e, HTTPException):
            raise
        logger.exception("Unhandled error during document analysis")
        raise HTTPException(status_code=500, detail="Error processing financial document.")
    finally:
        pass  # In production, use a storage lifecycle policy

@router.get("")
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    """List all documents uploaded by the current user."""
    # Try cache first
    cache_key = f"docs:list:{current_user.username}:{skip}:{limit}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return {"items": cached}

    db = get_db()
    docs = await docs_repo.list_documents(db=db, uploaded_by=current_user.username, skip=skip, limit=limit)
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])
    # Cache result
    cache_set_json(cache_key, docs, ttl_seconds=settings.CACHE_TTL_DEFAULT_SECONDS)
    return {"items": docs}

@router.get("/{document_id}")
async def get_document(document_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific document by ID if owned by the current user."""
    cache_key = f"docs:get:{document_id}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    db = get_db()
    doc = await docs_repo.get_document(db=db, document_id=document_id)
    if not doc or doc.get("uploadedBy") != current_user.username:
        raise HTTPException(status_code=404, detail="Document not found")
    doc["_id"] = str(doc["_id"])
    cache_set_json(cache_key, doc, ttl_seconds=settings.CACHE_TTL_LONG_SECONDS)
    return doc

@router.delete("/{document_id}")
async def delete_document(document_id: str, current_user: User = Depends(get_current_user)):
    """Delete a document by ID if owned by the current user."""
    db = get_db()
    doc = await docs_repo.get_document(db=db, document_id=document_id)
    if not doc or doc.get("uploadedBy") != current_user.username:
        raise HTTPException(status_code=404, detail="Document not found")
    ok = await docs_repo.delete_document(db=db, document_id=document_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    # Invalidate cache for this user/doc
    cache_invalidate_by_pattern(f"docs:list:{current_user.username}:*")
    cache_invalidate_by_pattern(f"docs:get:{document_id}")
    return {"status": "deleted", "documentId": document_id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, current_user: User = Depends(get_current_user)):
    """Get background job status and result metadata."""
    meta = get_job_status(job_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Job not found")
    # Do not leak other users' metadata; best effort check
    if meta.get("user_id") and meta.get("user_id") != current_user.username:
        raise HTTPException(status_code=404, detail="Job not found")
    return meta
