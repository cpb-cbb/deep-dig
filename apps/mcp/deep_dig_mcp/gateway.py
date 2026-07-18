from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import UUID

from deep_dig_mcp.backend_client import DeepDigBackendClient
from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.schemas import ExtractionSubmission, SafeJobStatus
from deep_dig_mcp.settings import Settings


BackendClientFactory = Callable[[str], DeepDigBackendClient]


class DeepDigGateway:
    """Public MCP application service; never exposes private extraction JSON."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client_factory: BackendClientFactory | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.client_factory = client_factory or self._build_client

    async def submit_material_extraction(
        self,
        *,
        access_token: str,
        file_name: str,
        file_hash: str,
        markdown: str,
        properties: list[str],
        needs_ocr: bool = False,
        warnings: list[str] | None = None,
        allow_low_quality: bool = False,
    ) -> ExtractionSubmission:
        normalized_name = file_name.strip()
        if not normalized_name or len(normalized_name) > 255:
            raise DeepDigMcpError("INVALID_FILE_NAME", "File name must contain 1-255 characters")
        normalized_hash = _validate_file_hash(file_hash)
        if not markdown.strip():
            raise DeepDigMcpError("EMPTY_MARKDOWN", "Parsed Markdown is empty")
        if needs_ocr and not allow_low_quality:
            raise DeepDigMcpError(
                "OCR_REQUIRED",
                "Local parsing reported that OCR may be required",
                detail={"warnings": warnings or []},
            )
        if len(markdown) > self.settings.backend_max_text_chars:
            raise DeepDigMcpError(
                "DOCUMENT_TOO_LONG_FOR_BACKEND",
                "Parsed Markdown exceeds the hosted per-document limit",
                detail={"textLength": len(markdown), "limit": self.settings.backend_max_text_chars},
            )
        normalized_properties = _normalize_properties(properties)
        idempotency_source = "\n".join([normalized_hash, *normalized_properties])
        idempotency_key = hashlib.sha256(idempotency_source.encode("utf-8")).hexdigest()
        result = await self.client_factory(access_token).submit_job(
            file_name=normalized_name,
            file_hash=normalized_hash,
            markdown=markdown,
            properties=normalized_properties,
            idempotency_key=idempotency_key,
        )
        return ExtractionSubmission.model_validate(result)

    async def get_extraction_status(self, *, access_token: str, job_id: str) -> SafeJobStatus:
        normalized_job_id = _validate_job_id(job_id)
        result = await self.client_factory(access_token).get_job(normalized_job_id)
        return SafeJobStatus.model_validate(result)

    async def export_extraction_xlsx(self, *, access_token: str, job_id: str) -> bytes:
        normalized_job_id = _validate_job_id(job_id)
        return await self.client_factory(access_token).export_xlsx(normalized_job_id)

    def _build_client(self, token: str) -> DeepDigBackendClient:
        return DeepDigBackendClient(
            base_url=self.settings.api_base_url,
            token=token,
            timeout_seconds=self.settings.request_timeout_seconds,
        )


def _normalize_properties(properties: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in properties:
        name = value.strip()
        if not name or name in seen:
            continue
        if len(name) > 200:
            raise DeepDigMcpError(
                "INVALID_PROPERTIES", "Each property name must contain at most 200 characters"
            )
        normalized.append(name)
        seen.add(name)
    if not normalized:
        raise DeepDigMcpError("INVALID_PROPERTIES", "At least one property name is required")
    if len(normalized) > 100:
        raise DeepDigMcpError("INVALID_PROPERTIES", "At most 100 properties may be requested")
    return normalized


def _validate_file_hash(file_hash: str) -> str:
    value = file_hash.strip().lower()
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise DeepDigMcpError("INVALID_FILE_HASH", "File hash must be a SHA-256 value")
    return f"sha256:{digest}"


def _validate_job_id(job_id: str) -> str:
    try:
        return str(UUID(job_id))
    except ValueError as exc:
        raise DeepDigMcpError("INVALID_JOB_ID", "Job ID must be a UUID") from exc
