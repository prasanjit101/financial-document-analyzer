from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from config import settings
from db import get_db
from repositories import users as users_repo
import logging

try:
    # Authlib provides a JOSE-compliant JWT API
    from authlib.jose import jwt
except Exception as e:  # pragma: no cover - fail fast with clear error
    raise RuntimeError("authlib is required for JWT functionality. Please install it.")

try:
    import redis
except Exception:
    redis = None  # type: ignore


router = APIRouter(prefix="/v1/auth", tags=["auth"])


class User(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: str  # "admin" or "viewer"
    disabled: bool = False


logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _get_redis_client() -> Optional["redis.Redis"]:
    if redis is None:
        return None
    try:
        return redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


def issue_access_token(subject: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    header = {"alg": settings.JWT_ALGORITHM}
    return jwt.encode(header, payload, settings.JWT_SECRET_KEY).decode()


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        claims = jwt.decode(token, settings.JWT_SECRET_KEY)
        # Ensure standard claims like exp/iat are enforced
        claims.validate()
        return dict(claims)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    data = decode_access_token(token)
    username = data.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    db = get_db()
    raw = await users_repo.get_by_username(db, username)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return User(username=raw.get("username"), full_name=raw.get("full_name"), role=raw.get("role", "viewer"))


def require_role(required: str):
    async def role_dependency(user: User = Depends(get_current_user)) -> User:
        role = (user.role or "").lower()
        if required == "admin" and role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
        # viewer routes accept both admin and viewer; admin is a superset
        if required == "viewer" and role not in ("viewer", "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role required")
        return user

    return role_dependency


def rate_limiter(key_builder: Optional[Any] = None):
    """Minimal Redis-backed rate limiter dependency.

    - Uses a sliding window implemented as a fixed window counter for simplicity.
    - Falls back to no-op if Redis is unavailable.
    """

    async def dependency(request: Request) -> None:
        client = _get_redis_client()
        if client is None:
            return  # no-op when Redis is not available

        # identity key: either user sub (if authenticated) or IP
        identity: str
        auth_header = request.headers.get("authorization") or ""
        token = auth_header.split(" ")[1] if auth_header.lower().startswith("bearer ") else None
        if token:
            try:
                payload = decode_access_token(token)
                identity = str(payload.get("sub"))
            except Exception:
                identity = request.client.host if request.client else "unknown"
        else:
            identity = request.client.host if request.client else "unknown"

        route_key = request.url.path
        key = f"rate:{identity}:{route_key}"
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_requests = settings.RATE_LIMIT_MAX_REQUESTS

        # INCR with TTL for fixed window
        pipe = client.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, window)
        try:
            count, _ = pipe.execute()
        except Exception:
            return

        if isinstance(count, str):
            try:
                count = int(count)
            except Exception:
                count = 0

        if count > max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    return dependency


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    user_record = await users_repo.get_by_username(db, form_data.username)
    if not user_record or not users_repo.verify_password(form_data.password, user_record.get("passwordHash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = issue_access_token(subject=user_record["username"], role=user_record.get("role", "viewer"))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin-only")
async def admin_only(
    _: User = Depends(require_role("admin")),
    __: None = Depends(rate_limiter()),
):
    return {"message": "Hello, Admin!"}


@router.get("/viewer-or-admin")
async def viewer_or_admin(
    user: User = Depends(require_role("viewer")),
    __: None = Depends(rate_limiter()),
):
    return {"message": f"Hello, {user.role.title()}!"}

# Export a rate limiter instance for reuse in other routers
rate_limit_dependency = rate_limiter()


from schemas import UserCreate


@router.post("/register")
async def register(payload: UserCreate):
    """Open registration endpoint. Forces role to 'viewer' for simplicity/security."""
    db = get_db()
    existing = await users_repo.get_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    created = await users_repo.create_user(
        db=db,
        username=payload.username,
        password=payload.password,
        full_name=payload.full_name,
        role="viewer",
    )
    logger.info("User registered: %s", created.get("username"))
    return {
        "username": created.get("username"),
        "full_name": created.get("full_name"),
        "role": created.get("role"),
    }

