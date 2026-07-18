from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from deep_dig_mcp.schemas import ParsedDocument
from deep_dig_mcp.security import config_fingerprint, document_id_for, sha256_file
from deep_dig_mcp.settings import Settings


class FakeParser:
    name = "markitdown"
    parser_version = "test-1.0"
    supported_extensions = {".pdf"}

    def __init__(self, markdown: str = "# Paper\n\n" + "Useful scientific text. " * 20) -> None:
        self.markdown = markdown
        self.calls = 0

    def parse(
        self,
        path: Path,
        *,
        file_hash: str | None = None,
        config: dict[str, Any] | None = None,
        display_name: str | None = None,
    ) -> ParsedDocument:
        self.calls += 1
        resolved_hash = file_hash or sha256_file(path)
        parser_config_hash = config_fingerprint(config or {})
        return ParsedDocument(
            document_id=document_id_for(
                resolved_hash,
                self.name,
                self.parser_version,
                parser_config_hash,
            ),
            file_name=display_name or path.name,
            file_hash=resolved_hash,
            markdown=self.markdown,
            text_length=len(self.markdown),
            parser=self.name,
            parser_version=self.parser_version,
            parser_config_hash=parser_config_hash,
            needs_ocr=len(self.markdown.strip()) < 20,
            warnings=["Low text"] if len(self.markdown.strip()) < 20 else [],
            page_count=1,
        )


class FakeBackend:
    def __init__(self) -> None:
        self.submissions: list[dict[str, Any]] = []

    async def submit_job(self, **kwargs: Any) -> dict[str, Any]:
        self.submissions.append(kwargs)
        return {
            "job_id": "12345678-1234-5678-1234-567812345678",
            "queued_items": 1,
            "estimated_seconds": 30,
            "reused": False,
        }

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return {
            "id": job_id,
            "status": "completed",
            "total_items": 1,
            "completed_items": 1,
            "failed_items": 0,
        }

    async def get_job_items(self, _job_id: str) -> list[dict[str, Any]]:
        return [{"status": "completed", "parsed_result": {"success": True, "samples": []}}]

    async def export_xlsx(self, _job_id: str) -> bytes:
        return b"PK\x03\x04fake-xlsx"


@pytest.fixture
def runtime_settings(tmp_path: Path) -> Settings:
    workspace = tmp_path / "workspace"
    output = tmp_path / "output"
    workspace.mkdir()
    output.mkdir()
    return Settings(
        _env_file=None,
        workspace_dir=workspace,
        output_dir=output,
        api_token="test-token",
        markdown_chunk_chars=120,
    )


@pytest.fixture
def digital_pdf(runtime_settings: Settings) -> Path:
    path = runtime_settings.workspace_dir / "paper.pdf"
    path.write_bytes(b"%PDF-1.4\nfixture")
    return path
