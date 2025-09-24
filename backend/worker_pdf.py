from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Optional

from config import settings
from db import init_db, get_db, close_db
from redis_utils import get_redis_client, QUEUE_KEY, JOB_KEY_PREFIX, update_job
from task import analyze_financial_document as analyze_financial_document_task
from crewai import Crew, Process


logger = logging.getLogger(__name__)


def _run_crew_sync(query: str, file_path: str) -> str:
    from agents import financial_analyst

    financial_crew = Crew(
        agents=[financial_analyst],
        tasks=[analyze_financial_document_task],
        process=Process.sequential,
    )
    result = financial_crew.kickoff({"query": query, "file_path": file_path})
    return str(result)


async def process_job(job_id: str) -> None:
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


async def worker_loop() -> None:
    app = None
    await init_db(app)
    try:
        client = get_redis_client()
        if client is None:
            logger.error("Redis is required for worker. Exiting.")
            return
        logger.info("Worker started. Listening on %s", QUEUE_KEY)
        while True:
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
    finally:
        await close_db(app)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()


