from __future__ import annotations

import datetime as dt
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase


async def write_audit_log(
    db: AsyncIOMotorDatabase,
    path: str,
    method: str,
    user: Optional[str],
    status: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    doc: Dict[str, Any] = {
        "path": path,
        "method": method,
        "user": user,
        "status": status,
        "createdAt": dt.datetime.utcnow(),
    }
    if extra:
        doc.update(extra)
    await db.get_collection("audit_logs").insert_one(doc)


async def list_audit_logs(
    db: AsyncIOMotorDatabase,
    user: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if user:
        q["user"] = user
    cursor = (
        db.get_collection("audit_logs")
        .find(q)
        .sort("createdAt", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    return [doc async for doc in cursor]


