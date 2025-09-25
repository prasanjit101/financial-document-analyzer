from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from db import init_db, get_db, close_db
from redis_utils import (
    get_redis_client,
    QUEUE_KEY,
    JOB_KEY_PREFIX,
    update_job,
    get_job_status,
)
from task import analyze_financial_document as analyze_financial_document_task
from crewai import Crew, Process


logger = logging.getLogger(__name__)


# -----------------------------
# Crew runner (blocking, run in thread)
# -----------------------------
def _run_crew_sync(query: str, file_path: str) -> str:
    """Run the CrewAI pipeline synchronously for the given query and file path."""
    from agents import financial_analyst

    try:
        financial_crew = Crew(
            agents=[financial_analyst],
            tasks=[analyze_financial_document_task],
            process=Process.sequential,
        )
        result = financial_crew.kickoff({"query": query, "file_path": file_path})
    except Exception as e:
        logger.exception("Error occurred while running CrewAI pipeline", exc_info=e)
        result = {"error": str(e)}
    return str(result)


# -----------------------------
# Job processing
# -----------------------------
async def process_job(job_id: str) -> None:
    """Process a single job by ID pulled from Redis."""
    client = get_redis_client()
    if client is None:
        return
    job_key = JOB_KEY_PREFIX + job_id
    try:
        raw = client.hgetall(job_key)
        if not raw:
            return
        file_path = raw.get("file_path")
        query = raw.get("query") or "Analyze this financial document for investment insights"
        user_id = raw.get("user_id") or "unknown"
        document_id = raw.get("document_id")
        if not file_path or not os.path.exists(file_path):
            update_job(job_id, status="failed", error="File not found")
            return

        update_job(job_id, status="processing", progress=10)

        # Run blocking analysis in a worker thread
        try:
            response = await asyncio.to_thread(_run_crew_sync, query, file_path)
            if "error" in response:
                update_job(job_id, status="failed", error=response)
                return
        except Exception as e:
            update_job(job_id, status="failed", error=str(e))
            return

        update_job(job_id, progress=70)

        # Persist analysis
        db = get_db()
        from repositories import analyses as analyses_repo
        analysis = await analyses_repo.create_analysis(
            db=db,
            document_id=document_id or "",
            user_id=user_id,
            query=query,
            summary=str(response),
        )

        update_job(job_id, status="completed", progress=100, analysis_id=str(analysis.get("_id")))
    except Exception as e:
        logger.exception("Worker failed processing job %s", job_id)
        update_job(job_id, status="failed", error=str(e))


# -----------------------------
# Background worker loop managed by FastAPI lifespan
# -----------------------------
_worker_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def worker_loop(stop_event: asyncio.Event) -> None:
    """Continuously pull jobs from Redis queue and process until stopped."""
    client = get_redis_client()
    if client is None:
        logger.error("Redis is required for worker. Exiting worker loop.")
        return
    logger.info("Worker started. Listening on %s", QUEUE_KEY)
    while not stop_event.is_set():
        try:
            # BRPOP returns (key, job_id) when available
            item = client.blpop(QUEUE_KEY, timeout=5)
            if not item:
                await asyncio.sleep(0.2)
                continue
            _, job_id = item
            await process_job(job_id)
        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(1)
    logger.info("Worker loop received stop signal; exiting.")


def start_worker() -> None:
    global _worker_task, _stop_event
    if _worker_task and not _worker_task.done():
        return
    _stop_event = asyncio.Event()
    _worker_task = asyncio.create_task(worker_loop(_stop_event))


async def stop_worker() -> None:
    global _worker_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _worker_task is not None:
        try:
            await _worker_task
        except Exception:
            pass
    _worker_task = None
    _stop_event = None


# -----------------------------
# FastAPI application
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and any third-party SDKs
    await init_db(app)
    try:
        try:
            # Optional: initialize pylangdb crews if available
            from pylangdb.crewai import init as langdb_init  # type: ignore
            langdb_init()
        except Exception:
            pass
        start_worker()
        yield
    finally:
        await stop_worker()
        await close_db(app)


app = FastAPI(title="PDF Worker Service", lifespan=lifespan, debug=settings.APP_ENV == "dev", version="0.1.0")


@app.get("/")
async def health() -> dict:
    """Basic health endpoint."""
    client_ok = get_redis_client() is not None
    worker_running = bool(_worker_task and not _worker_task.done())
    return {
        "status": "ok",
        "redis": client_ok,
        "worker_running": worker_running,
    }


@app.get("/status")
async def status() -> dict:
    """Service status with simple diagnostics."""
    client = get_redis_client()
    ping = False
    try:
        if client:
            client.ping()
            ping = True
    except Exception:
        ping = False
    return {
        "redis_ping": ping,
        "queue": QUEUE_KEY,
        "worker_task_state": ("running" if _worker_task and not _worker_task.done() else "stopped"),
    }


@app.post("/control/start")
async def control_start() -> JSONResponse:
    """Start the background worker if not already running."""
    if _worker_task and not _worker_task.done():
        return JSONResponse({"status": "already-running"})
    start_worker()
    return JSONResponse({"status": "started"})


@app.post("/control/stop")
async def control_stop() -> JSONResponse:
    """Stop the background worker gracefully."""
    await stop_worker()
    return JSONResponse({"status": "stopped"})


@app.get("/jobs/{job_id}")
async def job_status(job_id: str) -> JSONResponse:
    """Fetch job status directly from Redis (helper endpoint)."""
    meta = get_job_status(job_id)
    if not meta:
        return JSONResponse(status_code=404, content={"detail": "Job not found"})
    return JSONResponse(content=meta)


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO if settings.APP_ENV == "dev" else logging.WARNING)
    uvicorn.run("worker_pdf:app", host=settings.API_HOST, port=settings.API_PORT + 1, reload=True)


