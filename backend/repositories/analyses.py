from __future__ import annotations

import datetime as dt
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


async def create_analysis(
    db: AsyncIOMotorDatabase,
    document_id: str,
    user_id: str,
    query: str,
    summary: str,
) -> Dict[str, Any]:
    doc = {
        "documentId": document_id,
        "userId": user_id,
        "query": query,
        "summary": summary,
        "createdAt": dt.datetime.utcnow(),
    }
    res = await db.get_collection("analyses").insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def list_analyses(
    db: AsyncIOMotorDatabase,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if document_id:
        q["documentId"] = document_id
    if user_id:
        q["userId"] = user_id

    cursor = (
        db.get_collection("analyses")
        .find(q)
        .sort("createdAt", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    return [doc async for doc in cursor]


async def get_analysis(db: AsyncIOMotorDatabase, analysis_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(analysis_id)
    except Exception:
        return None
    return await db.get_collection("analyses").find_one({"_id": oid})


