from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.models import User


async def reserve_quota(db: AsyncSession, user: User, amount: int) -> None:
    refreshed = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if refreshed is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found")
    if refreshed.used_this_month + amount > refreshed.monthly_quota:
        raise AppError(
            402,
            "QUOTA_EXCEEDED",
            "Monthly extraction quota has been used up",
            {"used": refreshed.used_this_month, "limit": refreshed.monthly_quota},
        )
    refreshed.used_this_month += amount


async def rollback_quota(db: AsyncSession, user_id, amount: int) -> None:
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is not None:
        user.used_this_month = max(0, user.used_this_month - amount)
