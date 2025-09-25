from fastapi import FastAPI, HTTPException, Depends, Request, APIRouter
from typing import Optional
from config import settings
from services.auth import get_current_user, User
from db import init_db, close_db, get_db
from repositories import analyses as analyses_repo
from redis_utils import cache_get_json, cache_set_json
from pylangdb.crewai import init


analysis_router = APIRouter(prefix="/v1/analyses", tags=["analyses"])


@analysis_router.get("")
async def list_analyses(
    documentId: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
):
    cache_key = f"analyses:list:{current_user.username}:{documentId or ''}:{skip}:{limit}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return {"items": cached}

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
    cache_set_json(cache_key, items, ttl_seconds=settings.CACHE_TTL_DEFAULT_SECONDS)
    return {"items": items}


@analysis_router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, current_user: User = Depends(get_current_user)):
    cache_key = f"analyses:get:{analysis_id}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    db = get_db()
    a = await analyses_repo.get_analysis(db=db, analysis_id=analysis_id)
    if not a or a.get("userId") != current_user.username:
        raise HTTPException(status_code=404, detail="Analysis not found")
    a["_id"] = str(a["_id"])  # serialize
    cache_set_json(cache_key, a, ttl_seconds=settings.CACHE_TTL_LONG_SECONDS)
    return a