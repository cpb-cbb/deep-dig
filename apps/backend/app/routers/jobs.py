from __future__ import annotations

import json
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthUser, verify_auth
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
from app.services.ratelimit import (
    JOB_ACTION_IP_RULE,
    JOB_ACTION_USER_RULE,
    JOB_READ_IP_RULE,
    JOB_READ_USER_RULE,
    JOB_SUBMIT_IP_RULE,
    JOB_SUBMIT_USER_RULE,
    check_rate_limits,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def job_out(job) -> JobOut:
    return JobOut.model_validate(job, from_attributes=True)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def _limit_job_requests(request: Request, auth: AuthUser, *, submit: bool) -> None:
    user_rule = JOB_SUBMIT_USER_RULE if submit else JOB_READ_USER_RULE
    ip_rule = JOB_SUBMIT_IP_RULE if submit else JOB_READ_IP_RULE
    await check_rate_limits(
        [
            (str(auth.id), user_rule),
            (_client_ip(request), ip_rule),
        ]
    )


async def _limit_job_actions(request: Request, auth: AuthUser) -> None:
    await check_rate_limits(
        [
            (str(auth.id), JOB_ACTION_USER_RULE),
            (_client_ip(request), JOB_ACTION_IP_RULE),
        ]
    )


@router.post("", response_model=JobCreateOut)
async def post_job(
    payload: JobCreate,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
    x_client_version: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobCreateOut:
    await _limit_job_requests(request, auth, submit=True)
    if idempotency_key is not None and not 16 <= len(idempotency_key) <= 128:
        raise AppError(
            400,
            "INVALID_IDEMPOTENCY_KEY",
            "Idempotency-Key must contain between 16 and 128 characters",
        )
    user = await ensure_user(db, auth.id, auth.email)
    job, queued_items, reused = await create_job(
        db, user, payload, x_client_version, idempotency_key
    )
    return JobCreateOut(
        job_id=job.id,
        queued_items=queued_items,
        estimated_seconds=queued_items * 30,
        reused=reused,
    )


@router.get("", response_model=list[JobOut])
async def get_jobs(
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> list[JobOut]:
    await _limit_job_requests(request, auth, submit=False)
    return [job_out(job) for job in await list_jobs(db, auth.id)]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    await _limit_job_requests(request, auth, submit=False)
    return job_out(await get_owned_job(db, auth.id, job_id))


@router.get("/{job_id}/items", response_model=list[JobItemOut])
async def get_job_items(
    job_id: UUID,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> list[JobItemOut]:
    await _limit_job_requests(request, auth, submit=False)
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
    job_id: UUID,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _limit_job_actions(request, auth)
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
    job_id: UUID,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    await _limit_job_actions(request, auth)
    return job_out(await cancel_job(db, auth.id, job_id))


@router.get("/{job_id}/events")
async def job_events(
    job_id: UUID,
    request: Request,
    auth: AuthUser = Depends(verify_auth),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await _limit_job_requests(request, auth, submit=False)
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
