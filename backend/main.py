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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan to manage startup and shutdown."""
    await init_db(app)
    logger.info("Application startup complete")
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
    from services.analysis import analysis_router
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(analysis_router)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)