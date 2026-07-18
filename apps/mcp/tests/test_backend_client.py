from __future__ import annotations

import json

import httpx
import pytest

from deep_dig_mcp.backend_client import DeepDigBackendClient


@pytest.mark.asyncio
async def test_backend_submission_matches_existing_jobs_api() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["auth"] = request.headers["authorization"]
        captured["idempotency"] = request.headers["idempotency-key"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "job_id": "12345678-1234-5678-1234-567812345678",
                "queued_items": 1,
                "estimated_seconds": 30,
                "reused": False,
            },
        )

    client = DeepDigBackendClient(
        base_url="https://api.example.test",
        token="secret-token",
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    await client.submit_job(
        file_name="paper.pdf",
        file_hash="sha256:abc",
        markdown="# Paper",
        properties=["strength"],
        idempotency_key="a" * 64,
    )
    assert captured["path"] == "/jobs"
    assert captured["auth"] == "Bearer secret-token"
    assert captured["payload"]["workflow_id"] == "material_extraction"
    assert captured["payload"]["items"][0]["text"] == "# Paper"
