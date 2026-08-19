from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import AppError
from app.models import Job, JobItem, User, UserSettings
from app.schemas import JobCreate
from app.services.workflow_registry import (
    get_workflow,
    validate_workflow_config,
    workflow_schema_hash,
    workflow_snapshot,
)


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def ensure_user(db: AsyncSession, user_id, email: str | None) -> User:
    user = await db.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.settings))
    )
    if user is None:
        user = User(id=user_id, email=email)
        user.settings = UserSettings(user_id=user_id)
        db.add(user)
        await db.flush()
    return user


async def create_job(
    db: AsyncSession,
    user: User,
    payload: JobCreate,
    client_version: str | None,
    idempotency_key: str | None = None,
) -> tuple[Job, int, bool]:
    for item in payload.items:
        if len(item.text) > settings.max_text_chars:
            raise AppError(413, "PAYLOAD_TOO_LARGE", "PDF text exceeds maximum length")

    # Serialize task creation per user so idempotency checks stay authoritative
    # when the same client retries concurrently.
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

    workflow = get_workflow(payload.workflow_id)
    normalized_config = validate_workflow_config(workflow, payload.config)

    job = Job(
        user_id=locked_user.id,
        workflow_id=payload.workflow_id,
        workflow_version=workflow["version"],
        workflow_schema_hash=workflow_schema_hash(workflow),
        workflow_snapshot=workflow_snapshot(workflow),
        status="pending",
        total_items=len(payload.items),
        config=normalized_config,
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
            # Active jobs retain source text so unfinished items can be requeued
            # after a worker or Redis restart. Workers clear it at terminal state
            # unless the user explicitly enabled long-term raw text storage.
            raw_text=item_payload.text,
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


async def _enqueue_item_jobs(
    job: Job,
    items: list[tuple[JobItem, str]],
    *,
    resumed: bool = False,
) -> dict[UUID, Exception]:
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
                _job_id=(
                    f"extract-item-{item.id}-resume-{uuid4()}"
                    if resumed
                    else f"extract-item-{item.id}"
                ),
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
    for item in items:
        error = errors[item.id]
        item.status = "pending"
        item.error_code = "QUEUE_ENQUEUE_FAILED"
        item.error_message = str(error) or error.__class__.__name__
        item.finished_at = None
    await db.commit()


async def resume_job(db: AsyncSession, user_id, job_id: UUID) -> tuple[Job, int, int]:
    job = await db.scalar(
        select(Job)
        .where(Job.id == job_id, Job.user_id == user_id)
        .options(selectinload(Job.items), selectinload(Job.user).selectinload(User.settings))
        .with_for_update()
    )
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    if job.status in {"completed", "cancelled"}:
        raise AppError(409, "JOB_NOT_RESUMABLE", "Only unfinished jobs can be continued")

    resumable: list[tuple[JobItem, str]] = []
    unavailable = 0
    for item in job.items:
        if item.status not in {"pending", "running"}:
            continue
        if not item.raw_text:
            unavailable += 1
            continue
        item.status = "pending"
        item.claim_token = None
        item.claimed_at = None
        item.error_code = None
        item.error_message = None
        item.finished_at = None
        resumable.append((item, item.raw_text))

    if not resumable:
        return job, 0, unavailable

    job.status = "pending"
    job.finished_at = None
    job.completed_items = sum(item.status == "done" for item in job.items)
    job.failed_items = sum(item.status == "failed" for item in job.items)
    await db.commit()

    errors = await _enqueue_item_jobs(job, resumable, resumed=True)
    if errors:
        await _record_enqueue_failures(db, job.id, errors)
    await db.refresh(job)
    return job, len(resumable) - len(errors), unavailable


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
        .options(selectinload(Job.items), selectinload(Job.user).selectinload(User.settings))
        .with_for_update()
    )
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", "Job not found")
    if job.status in {"completed", "failed", "cancelled"}:
        return job
    now = datetime.now(timezone.utc)
    store_raw_text = bool(job.user.settings.store_raw_text) if job.user.settings else False
    job.status = "cancelled"
    job.finished_at = now
    for item in job.items:
        if item.status != "pending":
            continue
        item.status = "cancelled"
        item.error_code = "JOB_CANCELLED"
        item.error_message = "Task was cancelled before extraction started"
        item.finished_at = now
        if not store_raw_text:
            item.raw_text = None
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
