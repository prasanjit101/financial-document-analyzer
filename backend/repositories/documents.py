from __future__ import annotations

import datetime as dt
from typing import Optional, Dict, Any, List

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


async def create_document(
    db: AsyncIOMotorDatabase,
    filename: str,
    path: str,
    size: int,
    mime: Optional[str],
    uploaded_by: str,
) -> Dict[str, Any]:
    doc = {
        "filename": filename,
        "path": path,
        "size": size,
        "mime": mime,
        "uploadedBy": uploaded_by,
        "createdAt": dt.datetime.utcnow(),
    }
    res = await db.get_collection("documents").insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def get_document(db: AsyncIOMotorDatabase, document_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(document_id)
    except Exception:
        return None
    return await db.get_collection("documents").find_one({"_id": oid})


async def list_documents(
    db: AsyncIOMotorDatabase,
    uploaded_by: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    q = {"uploadedBy": uploaded_by} if uploaded_by else {}
    cursor = (
        db.get_collection("documents")
        .find(q)
        .sort("createdAt", -1)
        .skip(max(skip, 0))
        .limit(max(min(limit, 100), 1))
    )
    return [doc async for doc in cursor]


async def delete_document(db: AsyncIOMotorDatabase, document_id: str) -> bool:
    try:
        oid = ObjectId(document_id)
    except Exception:
        return False
    res = await db.get_collection("documents").delete_one({"_id": oid})
    return res.deleted_count == 1


