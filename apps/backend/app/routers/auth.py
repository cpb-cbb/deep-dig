from __future__ import annotations

import asyncio
import hmac
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import create_access_token
from app.auth.passwords import hash_password, normalize_username, verify_password
from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.models import User, UserSettings
from app.schemas import LoginRequest, LoginResponse, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    if not settings.registration_enabled:
        raise AppError(403, "REGISTRATION_DISABLED", "New account registration is disabled")

    username = normalize_username(payload.username)
    existing = await db.scalar(select(User.id).where(User.username == username))
    if existing is not None:
        raise AppError(409, "USERNAME_TAKEN", "Username is already registered")

    user_id = uuid4()
    user = User(
        id=user_id,
        username=username,
        password_hash=await asyncio.to_thread(hash_password, payload.password),
        email=payload.email.strip().lower() if payload.email else None,
    )
    user.settings = UserSettings(user_id=user_id)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(409, "USERNAME_TAKEN", "Username is already registered") from exc
    return _login_response(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    username = normalize_username(payload.username)
    user = await db.scalar(select(User).where(User.username == username))
    if user is not None and await asyncio.to_thread(
        verify_password, payload.password, user.password_hash
    ):
        return _login_response(user)

    legacy_user = await _migrate_legacy_user(db, username, payload.password, user)
    if legacy_user is not None:
        return _login_response(legacy_user)
    raise AppError(401, "AUTH_INVALID", "Invalid username or password")


async def _migrate_legacy_user(
    db: AsyncSession,
    username: str,
    password: str,
    candidate: User | None,
) -> User | None:
    """Move the former single-user env login into the users table on first login."""
    if not settings.local_auth_password:
        return None
    username_ok = hmac.compare_digest(username, normalize_username(settings.local_auth_username))
    password_ok = hmac.compare_digest(password, settings.local_auth_password)
    if not (username_ok and password_ok):
        return None

    user = candidate
    if user is None:
        user = await db.scalar(
            select(User)
            .where(User.id == settings.local_auth_user_id)
            .options(selectinload(User.settings))
        )
    if user is None:
        user = User(
            id=settings.local_auth_user_id,
            email=settings.local_auth_email,
        )
        user.settings = UserSettings(user_id=user.id)
        db.add(user)
    user.username = username
    user.password_hash = await asyncio.to_thread(hash_password, password)
    if user.email is None:
        user.email = settings.local_auth_email
    await db.commit()
    return user


def _login_response(user: User) -> LoginResponse:
    return LoginResponse(access_token=create_access_token(user.id, user.email))
