from __future__ import annotations

import json
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthUser, verify_supabase_jwt
from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.schemas import JobCreate, JobCreateOut, JobItemOut, JobOut
from app.services.exporter import (
    XLSX_MEDIA_TYPE,
    ExportTooLargeError,
    build_job_xlsx,
    export_filename,
)
from app.services.job_service import cancel_job, create_job, ensure_user, get_owned_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


def job_out(job) -> JobOut:
    return JobOut.model_validate(job, from_attributes=True)


@router.post("", response_model=JobCreateOut)
async def post_job(
    payload: JobCreate,
    auth: AuthUser = Depends(verify_supabase_jwt),
    db: AsyncSession = Depends(get_db),
    x_client_version: str | None = Header(default=None),
) -> JobCreateOut:
    user = await ensure_user(db, auth.id, auth.email)
    job, queued_items = await create_job(db, user, payload, x_client_version)
    return JobCreateOut(
        job_id=job.id, queued_items=queued_items, estimated_seconds=queued_items * 30
    )


@router.get("", response_model=list[JobOut])
async def get_jobs(
    auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> list[JobOut]:
    return [job_out(job) for job in await list_jobs(db, auth.id)]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> JobOut:
    return job_out(await get_owned_job(db, auth.id, job_id))


@router.get("/{job_id}/items", response_model=list[JobItemOut])
async def get_job_items(
    job_id: UUID, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> list[JobItemOut]:
    job = await get_owned_job(db, auth.id, job_id)
    return [
        JobItemOut.model_validate(item, from_attributes=True)
        for item in sorted(job.items, key=lambda item: item.ordinal)
    ]


@router.get(
    "/{job_id}/export.xlsx",
    response_class=Response,
    responses={
        200: {
            "content": {XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
            "description": "Excel workbook export",
        }
    },
)
async def export_job_xlsx(
    job_id: UUID, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> Response:
    job = await get_owned_job(db, auth.id, job_id)
    try:
        content = build_job_xlsx(job)
    except ExportTooLargeError as exc:
        raise AppError(422, "EXPORT_TOO_LARGE", str(exc)) from exc
    return Response(
        content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{export_filename(job)}"'},
    )


@router.post("/{job_id}/cancel", response_model=JobOut)
async def post_cancel(
    job_id: UUID, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> JobOut:
    return job_out(await cancel_job(db, auth.id, job_id))


@router.get("/{job_id}/events")
async def job_events(
    job_id: UUID, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    await get_owned_job(db, auth.id, job_id)

    async def stream():
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        channel = f"job:{job_id}:events"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                payload = json.loads(message["data"])
                event = payload.get("event", "progress")
                data = json.dumps(payload.get("data", {}))
                yield f"event: {event}\ndata: {data}\n\n"
        finally:
            await pubsub.unsubscribe(channel)
            await redis.close()

    return StreamingResponse(stream(), media_type="text/event-stream")
