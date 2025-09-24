from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from typing import Optional
import logging
import os
import uuid
import asyncio

from crewai import Crew, Process
from config import settings
from agents import financial_analyst
from auth import get_current_user, User
from db import init_db, close_db, get_db
from repositories import documents as docs_repo
from repositories import analyses as analyses_repo
from repositories import audit_logs as audit_repo
from task import analyze_financial_document as analyze_financial_document_task

app = FastAPI(title="Financial Document Analyzer")

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def _startup() -> None:
    await init_db(app)
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await close_db(app)
    logger.info("Application shutdown complete")

# Routers
try:
    from auth import router as auth_router
    app.include_router(auth_router)
except Exception:
    # Avoid startup failure if auth dependencies are missing in some environments
    pass

def run_crew(query: str, file_path: str="data/sample.pdf"):
    """To run the whole crew"""
    financial_crew = Crew(
        agents=[financial_analyst],
        tasks=[analyze_financial_document_task],
        process=Process.sequential,
    )
    
    # Pass query (and file_path for tools that may use it)
    result = financial_crew.kickoff({'query': query, 'file_path': file_path})
    return result

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Financial Document Analyzer API is running"}

@app.post("/analyze")
async def analyze_financial_document(
    file: UploadFile = File(...),
    query: str = Form(default="Analyze this financial document for investment insights"),
    current_user: User = Depends(get_current_user),
):
    """Analyze financial document and provide comprehensive investment recommendations"""
    
    file_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{file_id}.pdf"
    
    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Validate query
        if query=="" or query is None:
            query = "Analyze this financial document for investment insights"
            
        # Persist document metadata
        db = get_db()
        doc = await docs_repo.create_document(
            db=db,
            filename=file.filename or os.path.basename(file_path),
            path=file_path,
            size=len(content or b""),
            mime=getattr(file, "content_type", None),
            uploaded_by=current_user.username,
        )

        # Process the financial document with all analysts
        response = run_crew(query=query.strip(), file_path=file_path)

        # Persist analysis referencing the document
        analysis = await analyses_repo.create_analysis(
            db=db,
            document_id=str(doc.get("_id")),
            user_id=current_user.username,
            query=query.strip(),
            summary=str(response),
        )

        # Audit log
        try:
            await audit_repo.write_audit_log(
                db=db,
                path="/analyze",
                method="POST",
                user=current_user.username,
                status="success",
                extra={"documentId": str(doc.get("_id")), "analysisId": str(analysis.get("_id"))},
            )
        except Exception:
            logger.exception("Failed to write audit log")
        
        return {
            "status": "success",
            "query": query,
            "analysis": str(response),
            "file_processed": file.filename,
            "documentId": str(doc.get("_id")),
            "analysisId": str(analysis.get("_id")),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing financial document: {str(e)}")
    
    finally:
        # Keep uploaded file for reference. In production, use a storage lifecycle policy.
        pass


@app.get("/documents")
async def list_documents(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    db = get_db()
    docs = await docs_repo.list_documents(db=db, uploaded_by=current_user.username, skip=skip, limit=limit)
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])  # serialize ObjectId
    return {"items": docs}


@app.get("/documents/{document_id}")
async def get_document(document_id: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    doc = await docs_repo.get_document(db=db, document_id=document_id)
    if not doc or doc.get("uploadedBy") != current_user.username:
        raise HTTPException(status_code=404, detail="Document not found")
    doc["_id"] = str(doc["_id"])  # serialize
    return doc


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    doc = await docs_repo.get_document(db=db, document_id=document_id)
    if not doc or doc.get("uploadedBy") != current_user.username:
        raise HTTPException(status_code=404, detail="Document not found")
    ok = await docs_repo.delete_document(db=db, document_id=document_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    # optional: remove file from disk (omitted for now)
    return {"status": "deleted", "documentId": document_id}


@app.get("/analyses")
async def list_analyses(
    documentId: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    db = get_db()
    items = await analyses_repo.list_analyses(
        db=db,
        document_id=documentId,
        user_id=current_user.username,
        skip=skip,
        limit=limit,
    )
    for a in items:
        if "_id" in a:
            a["_id"] = str(a["_id"])  # serialize ObjectId
    return {"items": items}


@app.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    a = await analyses_repo.get_analysis(db=db, analysis_id=analysis_id)
    if not a or a.get("userId") != current_user.username:
        raise HTTPException(status_code=404, detail="Analysis not found")
    a["_id"] = str(a["_id"])  # serialize
    return a

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT, reload=True)