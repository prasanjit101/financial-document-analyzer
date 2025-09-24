from __future__ import annotations

import datetime as dt
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


async def get_by_username(db: AsyncIOMotorDatabase, username: str) -> Optional[Dict[str, Any]]:
    return await db.get_collection("users").find_one({"username": username})


async def create_user(db: AsyncIOMotorDatabase, username: str, password: str, full_name: Optional[str], role: str) -> Dict[str, Any]:
    doc = {
        "username": username,
        "passwordHash": hash_password(password),
        "full_name": full_name,
        "role": role,
        "createdAt": dt.datetime.utcnow(),
    }
    res = await db.get_collection("users").insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


async def get_by_id(db: AsyncIOMotorDatabase, user_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None
    return await db.get_collection("users").find_one({"_id": oid})


