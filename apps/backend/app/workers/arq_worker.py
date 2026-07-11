from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from arq.connections import RedisSettings
from arq.worker import func
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.errors import AppError
from app.models import Job, JobItem
from app.services.extractor import run_workflow
from app.services.quota import rollback_quota
from app.services.workflow_registry import get_workflow

TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}
TERMINAL_ITEM_STATUSES = {"done", "failed", "cancelled"}


async def extract_item(ctx: dict[str, Any], job_id: str, item_id: str, text: str) -> None:
    """Extract one document so idle ARQ execution slots can take work from the same batch."""
    job_uuid = UUID(job_id)
    item_uuid = UUID(item_id)
    claimed = await _claim_item(job_uuid, item_uuid)
    if claimed is None:
        return

    workflow_id, config = claimed
    try:
        result = await _run_with_retries(ctx["redis"], job_uuid, workflow_id, config, text)
    except asyncio.CancelledError:
        # A graceful worker shutdown lets ARQ redeliver the item. The claim logic
        # accepts a pending/running item, while terminal items remain idempotent.
        await _release_item_claim(job_uuid, item_uuid)
        raise
    except JobCancelledError:
        await _cancel_claimed_item(job_uuid, item_uuid)
        return
    except Exception as exc:
        await _finish_item(
            ctx["redis"],
            job_uuid,
            item_uuid,
            status="failed",
            error_code=_error_code(exc),
            error_message=_error_message(exc),
        )
        return

    parsed_result = result.get("parsed_result")
    if not isinstance(parsed_result, dict) or not parsed_result.get("success", False):
        error_message = (
            str(parsed_result.get("error") or "No samples parsed")
            if isinstance(parsed_result, dict)
            else "Invalid parsed result"
        )
        await _finish_item(
            ctx["redis"],
            job_uuid,
            item_uuid,
            status="failed",
            raw_results=result.get("raw_results"),
            parsed_result=parsed_result,
            error_code="RESULT_FORMAT_ERROR",
            error_message=error_message,
        )
        return

    await _finish_item(
        ctx["redis"],
        job_uuid,
        item_uuid,
        status="done",
        raw_results=result.get("raw_results"),
        parsed_result=parsed_result,
    )


async def _claim_item(job_id: UUID, item_id: UUID) -> tuple[str, dict[str, Any]] | None:
    async with SessionLocal() as db:
        job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            return None
        item = await db.scalar(
            select(JobItem)
            .where(JobItem.id == item_id, JobItem.job_id == job_id)
            .with_for_update()
        )
        if item is None or item.status in TERMINAL_ITEM_STATUSES:
            return None
        if job.status in TERMINAL_JOB_STATUSES:
            if job.status == "cancelled":
                item.status = "cancelled"
                item.error_code = "JOB_CANCELLED"
                item.error_message = "Task was cancelled before extraction started"
                item.finished_at = datetime.now(timezone.utc)
                await rollback_quota(db, job.user_id, 1)
                await db.commit()
            return None

        now = datetime.now(timezone.utc)
        if job.status == "pending":
            job.status = "running"
            job.started_at = job.started_at or now
        item.status = "running"
        item.error_code = None
        item.error_message = None
        await db.commit()
        config = job.config if isinstance(job.config, dict) else {}
        return job.workflow_id, config


async def _release_item_claim(job_id: UUID, item_id: UUID) -> None:
    async with SessionLocal() as db:
        job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            return
        item = await db.scalar(
            select(JobItem)
            .where(JobItem.id == item_id, JobItem.job_id == job_id)
            .with_for_update()
        )
        if item is None or item.status != "running":
            return
        if job.status == "cancelled":
            item.status = "cancelled"
            item.error_code = "JOB_CANCELLED"
            item.error_message = "Task was cancelled during extraction"
            item.finished_at = datetime.now(timezone.utc)
            await rollback_quota(db, job.user_id, 1)
        else:
            item.status = "pending"
        await db.commit()


async def _cancel_claimed_item(job_id: UUID, item_id: UUID) -> None:
    async with SessionLocal() as db:
        job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            return
        item = await db.scalar(
            select(JobItem)
            .where(JobItem.id == item_id, JobItem.job_id == job_id)
            .with_for_update()
        )
        if item is None or item.status in TERMINAL_ITEM_STATUSES:
            return
        item.status = "cancelled"
        item.error_code = "JOB_CANCELLED"
        item.error_message = "Task was cancelled during extraction"
        item.finished_at = datetime.now(timezone.utc)
        await rollback_quota(db, job.user_id, 1)
        await db.commit()


async def _run_with_retries(
    redis: Any,
    job_id: UUID,
    workflow_id: str,
    config: dict[str, Any],
    text: str,
) -> dict[str, Any]:
    workflow = get_workflow(workflow_id)
    for attempt in range(1, settings.item_max_tries + 1):
        if await _is_job_cancelled(redis, job_id):
            raise JobCancelledError("Task was cancelled")
        try:
            return await asyncio.wait_for(
                run_workflow(workflow, text, config),
                timeout=settings.item_job_timeout_seconds,
            )
        except Exception as exc:
            if attempt >= settings.item_max_tries or not _is_transient_error(exc):
                raise
            delay = settings.item_retry_base_seconds * (2 ** (attempt - 1))
            await asyncio.sleep(delay)
    raise RuntimeError("Extraction retry loop exited unexpectedly")


async def _is_job_cancelled(redis: Any, job_id: UUID) -> bool:
    try:
        return bool(await redis.get(f"job:{job_id}:cancelled"))
    except Exception:
        # Workers also verify the parent status when claiming and finishing.
        # A temporary Redis read failure must not turn a document into a failure.
        return False


async def _finish_item(
    redis: Any,
    job_id: UUID,
    item_id: UUID,
    *,
    status: str,
    raw_results: Any = None,
    parsed_result: Any = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    job_done = False
    event_data: dict[str, Any] | None = None
    async with SessionLocal() as db:
        # Always lock the parent before the child. Cancellation uses the same
        # order, preventing deadlocks when many items finish simultaneously.
        job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            return
        item = await db.scalar(
            select(JobItem)
            .where(JobItem.id == item_id, JobItem.job_id == job_id)
            .with_for_update()
        )
        if item is None or item.status in TERMINAL_ITEM_STATUSES:
            return

        now = datetime.now(timezone.utc)
        item.raw_results = raw_results
        item.parsed_result = parsed_result
        item.status = status
        item.error_code = error_code
        item.error_message = error_message
        item.finished_at = now
        if status == "done":
            job.completed_items += 1
        else:
            job.failed_items += 1
            await rollback_quota(db, job.user_id, 1)

        if job.status != "cancelled" and job.completed_items + job.failed_items >= job.total_items:
            job.status = "completed" if job.completed_items else "failed"
            job.finished_at = now
            job_done = True

        event_data = {
            "item_id": str(item.id),
            "ordinal": item.ordinal,
            "status": item.status,
            "completed": job.completed_items,
            "failed": job.failed_items,
            "total": job.total_items,
            "job_status": job.status,
        }
        await db.commit()

    if event_data is None:
        return
    await _safe_publish(
        redis,
        f"job:{job_id}:events",
        "item_done" if status == "done" else "error",
        event_data,
    )
    await _safe_publish(redis, f"job:{job_id}:events", "progress", event_data)
    if job_done:
        await _safe_publish(redis, f"job:{job_id}:events", "job_done", event_data)


async def _safe_publish(redis: Any, channel: str, event: str, data: dict[str, Any]) -> None:
    try:
        await redis.publish(channel, json.dumps({"event": event, "data": data}))
    except Exception:
        # Database state is authoritative; a dropped live update is recovered by
        # the next API refresh and must not cause an already-finished item to retry.
        return


def _is_transient_error(exc: Exception) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    if isinstance(exc, AppError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _error_code(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.code
    if isinstance(exc, asyncio.TimeoutError):
        return "ITEM_TIMEOUT"
    return exc.__class__.__name__


def _error_message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return str(exc) or exc.__class__.__name__


class JobCancelledError(Exception):
    pass


_outer_timeout = (
    settings.item_job_timeout_seconds * settings.item_max_tries
    + int(settings.item_retry_base_seconds * (2**settings.item_max_tries - 1))
    + 30
)


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [
        func(
            extract_item,
            timeout=_outer_timeout,
            max_tries=settings.item_max_tries,
            keep_result=0,
        )
    ]
    max_jobs = settings.worker_max_jobs
    job_timeout = _outer_timeout
    max_tries = settings.item_max_tries
    keep_result = 0
