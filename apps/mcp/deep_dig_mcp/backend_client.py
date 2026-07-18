from __future__ import annotations

from typing import Any

import httpx

from deep_dig_mcp.errors import BackendApiError


class DeepDigBackendClient:
    def __init__(
        self,
        *,
        base_url: str,
        token: str | None,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout_seconds
        self._transport = transport

    async def submit_job(
        self,
        *,
        file_name: str,
        file_hash: str,
        markdown: str,
        properties: list[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/jobs",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "workflow_id": "material_extraction",
                "config": {"properties": properties},
                "items": [
                    {
                        "file_name": file_name,
                        "file_hash": file_hash,
                        "text": markdown,
                    }
                ],
            },
        )

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/jobs/{job_id}")

    async def get_job_items(self, job_id: str) -> list[dict[str, Any]]:
        result = await self._request_json("GET", f"/jobs/{job_id}/items")
        if not isinstance(result, list):
            raise BackendApiError("INVALID_BACKEND_RESPONSE", "Backend returned invalid job items")
        return result

    async def export_xlsx(self, job_id: str) -> bytes:
        response = await self._request("GET", f"/jobs/{job_id}/export.xlsx")
        return response.content

    async def _request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        response = await self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise BackendApiError(
                "INVALID_BACKEND_RESPONSE",
                "Backend returned a non-JSON response",
            ) from exc

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self._token:
            raise BackendApiError(
                "API_TOKEN_REQUIRED",
                "DEEP_DIG_API_TOKEN is required for extraction and export operations.",
            )
        headers = {
            "Authorization": f"Bearer {self._token}",
            "X-Client-Version": "deep-dig-mcp/0.1.0",
            **kwargs.pop("headers", {}),
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise BackendApiError(
                "BACKEND_UNREACHABLE",
                f"Cannot reach the Deep Dig backend at {self.base_url}: {exc}",
            ) from exc
        if response.is_success:
            return response
        raise _response_error(response)


def _response_error(response: httpx.Response) -> BackendApiError:
    try:
        problem = response.json()
    except ValueError:
        problem = {}
    if isinstance(problem, dict):
        code = str(problem.get("code") or f"BACKEND_HTTP_{response.status_code}")
        message = str(problem.get("message") or response.reason_phrase or "Backend request failed")
        detail = problem.get("detail") if isinstance(problem.get("detail"), dict) else {}
    else:
        code = f"BACKEND_HTTP_{response.status_code}"
        message = response.reason_phrase or "Backend request failed"
        detail = {}
    return BackendApiError(code, message, detail={"status": response.status_code, **detail})
