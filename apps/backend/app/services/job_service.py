from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import AppError
from app.models import Job, JobItem, User, UserSettings
from app.schemas import JobCreate
from app.services.quota import reserve_quota, rollback_quota
from app.services.workflow_registry import get_workflow


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def ensure_user(db: AsyncSession, user_id, email: str | None) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.settings))
    )
    if user is None:
        user = User(id=user_id, email=email, monthly_quota=settings.free_monthly_quota)
        user.settings = UserSettings(user_id=user_id)
        db.add(user)
        await db.flush()
    if user.is_banned:
        raise AppError(403, "USER_BANNED", "This account is banned", {"reason": user.ban_reason})
    return user


async def create_job(
    db: AsyncSession,
    user: User,
    payload: JobCreate,
    client_version: str | None,
    idempotency_key: str | None = None,
) -> tuple[Job, int, bool]:
    get_workflow(payload.workflow_id)
    if len(payload.items) > settings.free_batch_limit and user.plan == "free":
        raise AppError(400, "BATCH_LIMIT_EXCEEDED", "Batch size exceeds plan limit")
    for item in payload.items:
        if len(item.text) > settings.max_text_chars:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "PDF text exceeds maximum length")

    # Serializing task creation per user makes the concurrency and quota checks
    # authoritative even when several modified clients submit at the same time.
    locked_user = await db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked_user is None:
        raise AppError(404, "USER_NOT_FOUND", "User not found")

    if idempotency_key:
        existing_job = await db.scalar(
            select(Job).where(
                Job.user_id == locked_user.id,
                Job.idempotency_key == idempotency_key,
            )
        )
        if existing_job is not None:
            return existing_job, 0, True

    if locked_user.plan == "free" and settings.free_concurrent_jobs > 0:
        active_jobs = await db.scalar(
            select(func.count(Job.id)).where(
                Job.user_id == locked_user.id,
                Job.status.in_({"pending", "running"}),
            )
        )
        if (active_jobs or 0) >= settings.free_concurrent_jobs:
            raise AppError(
                409,
                "CONCURRENT_JOB_LIMIT",
                "Finish or cancel the active task before starting another one",
                {"limit": settings.free_concurrent_jobs},
            )

    await reserve_quota(db, locked_user, len(payload.items))
    store_raw_text = bool(user.settings and user.settings.store_raw_text)
    job = Job(
        user_id=locked_user.id,
        workflow_id=payload.workflow_id,
        status="pending",
        total_items=len(payload.items),
        config=payload.config.model_dump(),
        client_version=client_version,
        idempotency_key=idempotency_key,
    )
    db.add(job)
    await db.flush()
    queued_items: list[tuple[JobItem, str]] = []
    for index, item_payload in enumerate(payload.items):
        item = JobItem(
            job_id=job.id,
            ordinal=index,
            file_name=item_payload.file_name,
            file_hash=item_payload.file_hash,
            text_length=len(item_payload.text),
            raw_text=item_payload.text if store_raw_text else None,
        )
        db.add(item)
        queued_items.append((item, item_payload.text))
    await db.flush()
    await db.commit()

    enqueue_errors = await _enqueue_item_jobs(job, queued_items)
    if enqueue_errors:
        await _record_enqueue_failures(db, job.id, enqueue_errors)
        await db.refresh(job)
    return job, len(queued_items) - len(enqueue_errors), False


async def _enqueue_item_jobs(job: Job, items: list[tuple[JobItem, str]]) -> dict[UUID, Exception]:
    errors: dict[UUID, Exception] = {}
    try:
        redis = await create_pool(_redis_settings())
    except Exception as exc:
        return {item.id: exc for item, _ in items}

    async def enqueue(item: JobItem, text: str) -> tuple[UUID, Exception | None]:
        try:
            await redis.enqueue_job(
                "extract_item",
                str(job.id),
                str(item.id),
                text,
                _job_id=f"extract-item-{item.id}",
                _expires=settings.item_queue_expiry_seconds,
            )
            return item.id, None
        except Exception as exc:
            return item.id, exc

    try:
        # Limit enqueue fan-out so a very large batch does not create thousands of
        # simultaneous Redis pipelines in the API process.
        for start in range(0, len(items), 100):
            chunk = items[start : start + 100]
            results = await asyncio.gather(*(enqueue(item, text) for item, text in chunk))
            errors.update({item_id: error for item_id, error in results if error is not None})
    finally:
        await redis.close()
    return errors


async def _record_enqueue_failures(
    db: AsyncSession, job_id: UUID, errors: dict[UUID, Exception]
) -> None:
    job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None:
        return
    items = list(
        await db.scalars(
            select(JobItem)
            .where(JobItem.job_id == job_id, JobItem.id.in_(errors))
            .with_for_update()
        )
    )
    failed = 0
    now = datetime.now(timezone.utc)
    for item in items:
        if item.status != "pending":
            continue
        error = errors[item.id]
        item.status = "failed"
        item.error_code = "QUEUE_ENQUEUE_FAILED"
        item.error_message = str(error) or error.__class__.__name__
        item.finished_at = now
        failed += 1
    if not failed:
        return
    job.failed_items += failed
    if job.failed_items >= job.total_items:
        job.status = "failed"
        job.finished_at = now
    await rollback_quota(db, job.user_id, failed)
    await db.commit()


async def list_jobs(db: AsyncSession, user_id) -> list[Job]:
    result = await db.scalars(
        select(Job).where(Job.user_id == user_id).order_by(Job.created_at.desc()).limit(50)
    )
    return list(result)


async def get_owned_job(db: AsyncSession, user_id, job_id: UUID) -> Job:
    job = await db.scalar(
        select(Job).where(Job.id == job_id, Job.user_id == user_id).options(selectinload(Job.items))
    )
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    return job


async def cancel_job(db: AsyncSession, user_id, job_id: UUID) -> Job:
    job = await db.scalar(
        select(Job)
        .where(Job.id == job_id, Job.user_id == user_id)
        .options(selectinload(Job.items))
        .with_for_update()
    )
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    if job.status in {"completed", "failed", "cancelled"}:
        return job
    now = datetime.now(timezone.utc)
    job.status = "cancelled"
    job.finished_at = now
    cancelled_items = 0
    for item in job.items:
        if item.status != "pending":
            continue
        item.status = "cancelled"
        item.error_code = "JOB_CANCELLED"
        item.error_message = "Task was cancelled before extraction started"
        item.finished_at = now
        cancelled_items += 1
    if cancelled_items:
        await rollback_quota(db, job.user_id, cancelled_items)
    await db.commit()
    redis = None
    try:
        redis = await create_pool(_redis_settings())
        await redis.set(f"job:{job.id}:cancelled", "1")
        await redis.publish(
            f"job:{job.id}:events", '{"event":"job_done","data":{"status":"cancelled"}}'
        )
    except Exception:
        # The committed database status is authoritative. Queued workers check it
        # before starting even when the live Redis notification is unavailable.
        pass
    finally:
        if redis is not None:
            await redis.close()
    return job
