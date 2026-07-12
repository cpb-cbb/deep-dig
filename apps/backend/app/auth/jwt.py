from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import httpx
from fastapi import Depends, Header
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings
from app.errors import AppError


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str | None
    role: str | None = None


@lru_cache(maxsize=1)
def _jwks_cache_marker() -> str:
    return "jwks"


async def get_jwks() -> dict:
    _jwks_cache_marker()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(str(settings.supabase_jwks_url))
        response.raise_for_status()
        return response.json()


async def verify_supabase_jwt(authorization: str | None = Header(default=None)) -> AuthUser:
    if settings.dev_auth_enabled and authorization == "Bearer dev":
        return AuthUser(
            id=settings.dev_auth_user_id, email=settings.dev_auth_email, role="authenticated"
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(401, "AUTH_REQUIRED", "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwks = await get_jwks()
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_at_hash": False},
        )
        return AuthUser(id=UUID(claims["sub"]), email=claims.get("email"), role=claims.get("role"))
    except (JWTError, KeyError, ValueError) as exc:
        raise AppError(401, "AUTH_INVALID", "Invalid bearer token") from exc


CurrentUser = Depends(verify_supabase_jwt)
