from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.errors import AppError
from app.models import Job, JobItem
from app.schemas import JobCreate, JobCreateItem
from app.services import job_service
from app.services.llm_config import environment_llm_config
from app.workers import arq_worker


class FakeRedis:
    def __init__(self, failing_text: str | None = None):
        self.calls: list[tuple[str, tuple, dict]] = []
        self.failing_text = failing_text
        self.closed = False

    async def enqueue_job(self, function: str, *args, **kwargs):
        self.calls.append((function, args, kwargs))
        if self.failing_text is not None and args[-1] == self.failing_text:
            raise ConnectionError("queue unavailable")
        return object()

    async def close(self):
        self.closed = True

    async def get(self, _key: str):
        return None


def make_job_with_items(count: int) -> tuple[Job, list[tuple[JobItem, str]]]:
    job_id = uuid4()
    job = Job(
        id=job_id,
        user_id=uuid4(),
        workflow_id="material_extraction",
        status="pending",
        total_items=count,
        completed_items=0,
        failed_items=0,
        config={},
    )
    items = [
        (
            JobItem(
                id=uuid4(),
                job_id=job_id,
                ordinal=index,
                file_name=f"paper-{index}.pdf",
                file_hash=f"hash-{index:08d}",
                text_length=10,
                status="pending",
            ),
            f"text-{index}",
        )
        for index in range(count)
    ]
    return job, items


def make_job_payload() -> JobCreate:
    return JobCreate(
        workflow_id="material_extraction",
        config={"properties": ["surface area"]},
        items=[JobCreateItem(file_name="paper.pdf", file_hash="hash-00000001", text="text")],
    )


def test_job_payload_accepts_registry_workflow_ids_for_service_validation():
    payload = JobCreate(
        workflow_id="custom_record_extraction",
        config={"fields": []},
        items=[JobCreateItem(file_name="paper.pdf", file_hash="hash-00000001", text="text")],
    )

    assert payload.workflow_id == "custom_record_extraction"


@pytest.mark.asyncio
async def test_create_job_reuses_matching_idempotency_key_without_enqueuing(monkeypatch):
    user_id = uuid4()
    user = job_service.User(id=user_id, email="user@example.com")
    existing = Job(
        id=uuid4(),
        user_id=user_id,
        workflow_id="material_extraction",
        status="pending",
        total_items=1,
        completed_items=0,
        failed_items=0,
        config={},
        idempotency_key="idempotency-key-0001",
    )
    db = AsyncMock()
    db.scalar = AsyncMock(side_effect=[user, existing])
    enqueue = AsyncMock()
    monkeypatch.setattr(job_service, "_enqueue_item_jobs", enqueue)

    job, queued_items, reused = await job_service.create_job(
        db,
        user,
        make_job_payload(),
        "desktop-test",
        "idempotency-key-0001",
    )

    assert job is existing
    assert queued_items == 0
    assert reused is True
    enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_enqueue_item_jobs_creates_one_queue_job_per_document(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(job_service, "create_pool", AsyncMock(return_value=redis))
    job, items = make_job_with_items(3)

    errors = await job_service._enqueue_item_jobs(job, items)

    assert errors == {}
    assert len(redis.calls) == 3
    assert redis.closed is True
    for (function, args, kwargs), (item, text) in zip(redis.calls, items, strict=True):
        assert function == "extract_item"
        assert args == (str(job.id), str(item.id), text)
        assert kwargs["_job_id"] == f"extract-item-{item.id}"


@pytest.mark.asyncio
async def test_enqueue_item_jobs_isolates_one_enqueue_failure(monkeypatch):
    redis = FakeRedis(failing_text="text-1")
    monkeypatch.setattr(job_service, "create_pool", AsyncMock(return_value=redis))
    job, items = make_job_with_items(3)

    errors = await job_service._enqueue_item_jobs(job, items)

    assert set(errors) == {items[1][0].id}
    assert len(redis.calls) == 3


@pytest.mark.asyncio
async def test_resume_job_requeues_only_unfinished_items_with_new_queue_ids(monkeypatch):
    job, item_pairs = make_job_with_items(3)
    job.status = "running"
    job.completed_items = 1
    job.items = [pair[0] for pair in item_pairs]
    job.items[0].status = "done"
    job.items[0].raw_text = None
    job.items[1].status = "running"
    job.items[1].claim_token = "old-worker-claim"
    job.items[1].raw_text = item_pairs[1][1]
    job.items[2].raw_text = item_pairs[2][1]
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=job)
    enqueue = AsyncMock(return_value={})
    monkeypatch.setattr(job_service, "_enqueue_item_jobs", enqueue)

    resumed, queued, unavailable = await job_service.resume_job(db, job.user_id, job.id)

    assert resumed is job
    assert queued == 2
    assert unavailable == 0
    assert job.status == "pending"
    assert job.completed_items == 1
    assert job.items[1].status == "pending"
    assert job.items[1].claim_token is None
    enqueue.assert_awaited_once()
    assert enqueue.await_args.kwargs["resumed"] is True


@pytest.mark.asyncio
async def test_resumed_queue_jobs_get_fresh_ids(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(job_service, "create_pool", AsyncMock(return_value=redis))
    job, items = make_job_with_items(2)

    errors = await job_service._enqueue_item_jobs(job, items, resumed=True)

    assert errors == {}
    queue_ids = [call[2]["_job_id"] for call in redis.calls]
    assert all("-resume-" in value for value in queue_ids)
    assert len(set(queue_ids)) == 2


@pytest.mark.asyncio
async def test_transient_extraction_error_is_retried(monkeypatch):
    redis = FakeRedis()
    run = AsyncMock(
        side_effect=[
            AppError(429, "LLM_RATE_LIMITED", "retry later"),
            {"parsed_result": {"success": True}, "raw_results": {}},
        ]
    )
    monkeypatch.setattr(arq_worker, "run_workflow", run)
    monkeypatch.setattr(arq_worker, "get_workflow", lambda _workflow_id: {"steps": []})
    monkeypatch.setattr(arq_worker.settings, "item_max_tries", 2)
    monkeypatch.setattr(arq_worker.settings, "item_retry_base_seconds", 0)

    result = await arq_worker._run_with_retries(
        redis,
        uuid4(),
        "material_extraction",
        {},
        "document",
        environment_llm_config("fake"),
    )

    assert result["parsed_result"]["success"] is True
    assert run.await_count == 2


@pytest.mark.asyncio
async def test_unsuccessful_parsed_result_marks_only_that_item_failed(monkeypatch):
    job_id = uuid4()
    item_id = uuid4()
    finish = AsyncMock()
    monkeypatch.setattr(
        arq_worker,
        "_claim_item",
        AsyncMock(
            return_value=(
                "material_extraction",
                {},
                environment_llm_config("fake"),
                "claim-token",
            )
        ),
    )
    monkeypatch.setattr(
        arq_worker,
        "_run_with_retries",
        AsyncMock(
            return_value={
                "raw_results": {"extract_property_table": {}},
                "parsed_result": {"success": False, "samples": [], "error": "No samples"},
            }
        ),
    )
    monkeypatch.setattr(arq_worker, "_finish_item", finish)

    await arq_worker.extract_item({"redis": FakeRedis()}, str(job_id), str(item_id), "text")

    finish.assert_awaited_once()
    assert finish.await_args.kwargs["status"] == "failed"
    assert finish.await_args.kwargs["claim_token"] == "claim-token"
    assert finish.await_args.kwargs["error_code"] == "RESULT_FORMAT_ERROR"
    assert finish.await_args.kwargs["duration_ms"] >= 0
