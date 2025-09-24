from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from config import settings


logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database has not been initialized. Ensure init_db() is called on startup.")
    return _db


async def init_db(app: Optional[FastAPI] = None) -> None:
    global _client, _db
    if _client is not None and _db is not None:
        return

    mongo_uri = settings.MONGODB_URI
    db_name = settings.MONGODB_DB_NAME

    _client = AsyncIOMotorClient(mongo_uri)
    _db = _client[db_name]

    await _ensure_indexes(_db)
    logger.info("MongoDB connected and indexes ensured (db=%s)", db_name)


async def close_db(app: Optional[FastAPI] = None) -> None:
    global _client, _db
    try:
        if _client is not None:
            _client.close()
    finally:
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    # users: unique username, basic createdAt index
    await db.get_collection("users").create_index([("username", ASCENDING)], unique=True, name="uniq_username")
    await db.get_collection("users").create_index([("createdAt", DESCENDING)], name="users_createdAt_desc")

    # documents: uploadedBy and createdAt
    await db.get_collection("documents").create_index([("uploadedBy", ASCENDING)], name="docs_uploadedBy")
    await db.get_collection("documents").create_index([("createdAt", DESCENDING)], name="docs_createdAt_desc")

    # analyses: documentId and createdAt
    await db.get_collection("analyses").create_index([("documentId", ASCENDING)], name="analyses_docId")
    await db.get_collection("analyses").create_index([("createdAt", DESCENDING)], name="analyses_createdAt_desc")

    # audit_logs: user and createdAt
    await db.get_collection("audit_logs").create_index([("user", ASCENDING)], name="audit_user")
    await db.get_collection("audit_logs").create_index([("createdAt", DESCENDING)], name="audit_createdAt_desc")


