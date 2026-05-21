from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Job, JobItem
from app.services.extractor import run_workflow
from app.services.quota import rollback_quota
from app.services.workflow_registry import get_workflow


async def extract_job(ctx, job_id: str, texts: list[str]) -> None:
    redis = ctx["redis"]
    async with SessionLocal() as db:
        job = await db.get(Job, UUID(job_id))
        if job is None:
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()
        workflow = get_workflow(job.workflow_id)
        items = list(await db.scalars(select(JobItem).where(JobItem.job_id == job.id).order_by(JobItem.ordinal)))
        for item, text in zip(items, texts, strict=False):
            if await redis.get(f"job:{job.id}:cancelled"):
                job.status = "cancelled"
                break
            item.status = "running"
            await db.commit()
            try:
                result = await run_workflow(workflow, text, job.config)
                item.raw_results = result["raw_results"]
                item.parsed_result = result["parsed_result"]
                item.status = "done"
                item.finished_at = datetime.now(timezone.utc)
                job.completed_items += 1
                await redis.publish(
                    f"job:{job.id}:events",
                    json.dumps({"event": "item_done", "data": {"item_id": str(item.id), "ordinal": item.ordinal, "status": "done"}}),
                )
            except Exception as exc:
                item.status = "failed"
                item.error_code = exc.__class__.__name__
                item.error_message = str(exc)
                item.finished_at = datetime.now(timezone.utc)
                job.failed_items += 1
                await rollback_quota(db, job.user_id, 1)
                await redis.publish(
                    f"job:{job.id}:events",
                    json.dumps({"event": "error", "data": {"item_id": str(item.id), "code": item.error_code, "message": item.error_message}}),
                )
            await db.commit()
            await redis.publish(
                f"job:{job.id}:events",
                json.dumps({"event": "progress", "data": {"completed": job.completed_items, "failed": job.failed_items, "total": job.total_items}}),
            )
        if job.status != "cancelled":
            job.status = "completed" if job.completed_items else "failed"
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await redis.publish(
            f"job:{job.id}:events",
            json.dumps({"event": "job_done", "data": {"status": job.status, "completed": job.completed_items, "failed": job.failed_items}}),
        )


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [extract_job]
