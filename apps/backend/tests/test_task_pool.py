from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.errors import AppError
from app.models import Job, JobItem
from app.services import job_service
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
        redis, uuid4(), "material_extraction", {}, "document"
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
        AsyncMock(return_value=("material_extraction", {})),
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
    assert finish.await_args.kwargs["error_code"] == "RESULT_FORMAT_ERROR"
    assert finish.await_args.kwargs["duration_ms"] >= 0
