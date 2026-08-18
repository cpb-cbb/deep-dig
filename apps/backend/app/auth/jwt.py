from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, Header
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings
from app.errors import AppError

TOKEN_TTL_DAYS = 7


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    email: str | None
    role: str | None = None


def create_access_token(user_id: UUID, email: str | None) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "email": email,
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(claims, settings.auth_secret, algorithm="HS256")


async def verify_auth(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(401, "AUTH_REQUIRED", "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
        return AuthUser(
            id=UUID(claims["sub"]),
            email=claims.get("email"),
            role=claims.get("role"),
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise AppError(401, "AUTH_INVALID", "Invalid bearer token") from exc


CurrentUser = Depends(verify_auth)
