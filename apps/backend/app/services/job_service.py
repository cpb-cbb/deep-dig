from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import AppError
from app.models import Job, JobItem, User, UserSettings
from app.schemas import JobCreate
from app.services.quota import reserve_quota
from app.services.workflow_registry import get_workflow


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def ensure_user(db: AsyncSession, user_id, email: str | None) -> User:
    user = await db.get(User, user_id)
    if user is None:
        user = User(id=user_id, email=email, monthly_quota=settings.free_monthly_quota)
        user.settings = UserSettings(user_id=user_id)
        db.add(user)
        await db.flush()
    if user.is_banned:
        raise AppError(403, "USER_BANNED", "This account is banned", {"reason": user.ban_reason})
    return user


async def create_job(db: AsyncSession, user: User, payload: JobCreate, client_version: str | None) -> Job:
    get_workflow(payload.workflow_id)
    if len(payload.items) > settings.free_batch_limit and user.plan == "free":
        raise AppError(400, "BATCH_LIMIT_EXCEEDED", "Batch size exceeds plan limit")
    for item in payload.items:
        if len(item.text) > settings.max_text_chars:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "PDF text exceeds maximum length")

    await reserve_quota(db, user, len(payload.items))
    store_raw_text = bool(user.settings and user.settings.store_raw_text)
    job = Job(
        user_id=user.id,
        workflow_id=payload.workflow_id,
        status="pending",
        total_items=len(payload.items),
        config=payload.config,
        client_version=client_version,
    )
    db.add(job)
    await db.flush()
    for index, item in enumerate(payload.items):
        db.add(
            JobItem(
                job_id=job.id,
                ordinal=index,
                file_name=item.file_name,
                file_hash=item.file_hash,
                text_length=len(item.text),
                raw_text=item.text if store_raw_text else None,
            )
        )
    await db.commit()

    redis = await create_pool(_redis_settings())
    try:
        await redis.enqueue_job("extract_job", str(job.id), [item.text for item in payload.items])
    finally:
        await redis.close()
    return job


async def list_jobs(db: AsyncSession, user_id) -> list[Job]:
    result = await db.scalars(select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(50))
    return list(result)


async def get_owned_job(db: AsyncSession, user_id, job_id: UUID) -> Job:
    job = await db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id).options(selectinload(Job.items)))
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    return job


async def cancel_job(db: AsyncSession, user_id, job_id: UUID) -> Job:
    job = await get_owned_job(db, user_id, job_id)
    if job.status in {"completed", "failed", "cancelled"}:
        return job
    job.status = "cancelled"
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    redis = await create_pool(_redis_settings())
    try:
        await redis.set(f"job:{job.id}:cancelled", "1")
        await redis.publish(f"job:{job.id}:events", '{"event":"job_done","data":{"status":"cancelled"}}')
    finally:
        await redis.close()
    return job
