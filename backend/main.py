from fastapi import FastAPI, HTTPException, Depends, Request
from typing import Optional, Literal
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from config import settings
from services.auth import get_current_user, User
from db import init_db, close_db, get_db
from repositories import analyses as analyses_repo
from redis_utils import cache_get_json, cache_set_json
from pylangdb.crewai import init


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan to manage startup and shutdown."""
    await init_db(app)
    logger.info("Application startup complete")
    init()
    try:
        yield
    finally:
        await close_db(app)
        logger.info("Application shutdown complete")


app = FastAPI(title="Financial Document Analyzer", lifespan=lifespan, debug=settings.APP_ENV == "dev", version="0.1.0")

# Basic logging setup
logging.basicConfig(level=logging.INFO if settings.APP_ENV == "dev" else logging.WARNING)
logger = logging.getLogger(__name__)

# CORS configuration to allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log unhandled rejections in asyncio tasks to help diagnose timeouts
def _handle_asyncio_exception(loop, context):
    msg = context.get("exception") or context.get("message")
    logger.error("Asyncio exception: %s", msg)

try:
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_handle_asyncio_exception)
except Exception:
    pass

# Routers
try:
    from services.auth import router as auth_router
    from services.documents import router as documents_router
    app.include_router(auth_router)
    app.include_router(documents_router)
except Exception:
    # Avoid startup failure if auth dependencies are missing in some environments
    pass

# Global exception handlers for robustness and structured errors
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Financial Document Analyzer API is running"}


@app.get("v1/analyses")
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


@app.get("/v1/analyses/{analysis_id}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)