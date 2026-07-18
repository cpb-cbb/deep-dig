from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable
from uuid import UUID

from deep_dig_mcp.backend_client import DeepDigBackendClient
from deep_dig_mcp.cache import DocumentCache
from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.parser import DocumentParser, MarkItDownParser
from deep_dig_mcp.schemas import (
    ExtractionSubmission,
    ParsedDocument,
    ParseDocumentResult,
    ParserInfo,
    SafeJobStatus,
)
from deep_dig_mcp.security import (
    config_fingerprint,
    document_id_for,
    resolve_input_document,
    safe_output_path,
    sha256_file,
)
from deep_dig_mcp.settings import Settings


class DeepDigService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        parser: DocumentParser | None = None,
        backend: DeepDigBackendClient | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.parser = parser or _build_parser(self.settings.parser)
        self.cache = DocumentCache(
            self.settings.cache_dir,
            chunk_chars=self.settings.markdown_chunk_chars,
        )
        token = (
            self.settings.api_token.get_secret_value()
            if self.settings.api_token is not None
            else None
        )
        self.backend = backend or DeepDigBackendClient(
            base_url=self.settings.api_base_url,
            token=token,
            timeout_seconds=self.settings.request_timeout_seconds,
        )

    def parse_document(
        self,
        path: str | Path,
        *,
        allowed_roots: Iterable[Path] | None = None,
        display_name: str | None = None,
    ) -> ParseDocumentResult:
        roots = list(allowed_roots or [self.settings.workspace_dir])
        resolved = resolve_input_document(
            path,
            allowed_roots=roots,
            allowed_extensions=self.parser.supported_extensions,
            max_file_bytes=self.settings.max_file_bytes,
        )
        file_hash = sha256_file(resolved)
        parser_config = self._parser_config()
        parser_config_hash = config_fingerprint(parser_config)
        document_id = document_id_for(
            file_hash,
            self.parser.name,
            self.parser.parser_version,
            parser_config_hash,
        )
        cached = self.cache.load(document_id)
        if cached is not None:
            if display_name:
                cached = cached.model_copy(update={"file_name": display_name})
            return self._tool_result(cached)

        parsed = self.parser.parse(
            resolved,
            file_hash=file_hash,
            config=parser_config,
            display_name=display_name,
        )
        saved = self.cache.save(parsed)
        return self._tool_result(saved)

    async def submit_material_extraction(
        self,
        document_id: str,
        properties: list[str],
        *,
        allow_low_quality: bool = False,
    ) -> ExtractionSubmission:
        document = self.cache.get_required(document_id)
        if not document.markdown.strip():
            raise DeepDigMcpError(
                "EMPTY_MARKDOWN",
                "No text was extracted. A blank document cannot be submitted to the backend.",
                detail={"warnings": document.warnings},
            )
        if document.needs_ocr and not allow_low_quality:
            raise DeepDigMcpError(
                "OCR_REQUIRED",
                "The parsed document appears to require OCR. Review warnings or explicitly allow "
                "low-quality submission.",
                detail={"warnings": document.warnings},
            )
        if document.text_length > self.settings.backend_max_text_chars:
            raise DeepDigMcpError(
                "DOCUMENT_TOO_LONG_FOR_BACKEND",
                "Parsed Markdown exceeds the current backend per-document limit.",
                detail={
                    "textLength": document.text_length,
                    "limit": self.settings.backend_max_text_chars,
                    "chunkPaths": document.chunk_paths,
                },
            )
        normalized_properties = _normalize_properties(properties)
        idempotency_source = "\n".join([document.file_hash, *normalized_properties])
        idempotency_key = hashlib.sha256(idempotency_source.encode("utf-8")).hexdigest()
        result = await self.backend.submit_job(
            file_name=document.file_name,
            file_hash=document.file_hash,
            markdown=document.markdown,
            properties=normalized_properties,
            idempotency_key=idempotency_key,
        )
        return ExtractionSubmission.model_validate(result)

    async def get_extraction_status(self, job_id: str) -> SafeJobStatus:
        normalized_job_id = _validate_job_id(job_id)
        job = await self.backend.get_job(normalized_job_id)
        return SafeJobStatus.model_validate(job)

    async def export_extraction_xlsx(
        self,
        job_id: str,
        output_name: str | None = None,
    ) -> str:
        normalized_job_id = _validate_job_id(job_id)
        destination = safe_output_path(
            self.settings.output_dir,
            output_name or f"deep-dig-{normalized_job_id}",
            ".xlsx",
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = await self.backend.export_xlsx(normalized_job_id)
        destination.write_bytes(content)
        return str(destination)

    def parser_info(self) -> ParserInfo:
        return ParserInfo(
            name=self.parser.name,
            version=self.parser.parser_version,
            supported_formats=sorted(self.parser.supported_extensions),
            ocr_available=False,
            workspace_dir=str(self.settings.workspace_dir),
            output_dir=str(self.settings.output_dir),
            max_file_bytes=self.settings.max_file_bytes,
            backend_max_text_chars=self.settings.backend_max_text_chars,
        )

    def _parser_config(self) -> dict[str, int]:
        return {
            "min_text_chars": self.settings.min_text_chars,
            "min_chars_per_page": self.settings.min_chars_per_page,
            "markdown_chunk_chars": self.settings.markdown_chunk_chars,
        }

    def _tool_result(self, document: ParsedDocument) -> ParseDocumentResult:
        preview = document.markdown[: self.settings.max_preview_chars]
        return ParseDocumentResult(
            document_id=document.document_id,
            file_name=document.file_name,
            file_hash=document.file_hash,
            markdown_path=document.markdown_path,
            chunk_paths=document.chunk_paths,
            markdown_preview=preview,
            preview_truncated=len(preview) < document.text_length,
            text_length=document.text_length,
            parser=document.parser,
            parser_version=document.parser_version,
            cached=document.cached,
            warnings=document.warnings,
            needs_ocr=document.needs_ocr,
            page_count=document.page_count,
        )


def _build_parser(name: str) -> DocumentParser:
    if name == "markitdown":
        return MarkItDownParser()
    raise DeepDigMcpError(
        "UNKNOWN_PARSER",
        f"Unsupported DEEP_DIG_PARSER value: {name}",
        detail={"supportedParsers": ["markitdown"]},
    )


def _normalize_properties(properties: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in properties:
        property_name = value.strip()
        if not property_name or property_name in seen:
            continue
        if len(property_name) > 200:
            raise DeepDigMcpError(
                "INVALID_PROPERTIES",
                "Each property name must contain at most 200 characters.",
            )
        normalized.append(property_name)
        seen.add(property_name)
    if not normalized:
        raise DeepDigMcpError("INVALID_PROPERTIES", "At least one property name is required.")
    if len(normalized) > 100:
        raise DeepDigMcpError("INVALID_PROPERTIES", "At most 100 properties may be requested.")
    return normalized


def _validate_job_id(job_id: str) -> str:
    try:
        return str(UUID(job_id))
    except ValueError as exc:
        raise DeepDigMcpError("INVALID_JOB_ID", "Job ID must be a UUID") from exc
