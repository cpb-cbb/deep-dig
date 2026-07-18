from __future__ import annotations

from pathlib import Path

import pytest

from conftest import FakeBackend, FakeParser
from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.service import DeepDigService
from deep_dig_mcp.settings import Settings


def test_parse_caches_markdown_and_chunks(
    runtime_settings: Settings,
    digital_pdf: Path,
) -> None:
    parser = FakeParser()
    service = DeepDigService(runtime_settings, parser=parser, backend=FakeBackend())
    first = service.parse_document(str(digital_pdf))
    second = service.parse_document(str(digital_pdf))
    assert first.cached is False
    assert second.cached is True
    assert parser.calls == 1
    assert Path(first.markdown_path).is_file()
    assert len(first.chunk_paths) > 1
    assert all(Path(path).is_file() for path in first.chunk_paths)


def test_parser_config_change_invalidates_cache(
    runtime_settings: Settings,
    digital_pdf: Path,
) -> None:
    first_service = DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend())
    first = first_service.parse_document(str(digital_pdf))
    changed = runtime_settings.model_copy(update={"min_text_chars": 999})
    second_service = DeepDigService(changed, parser=FakeParser(), backend=FakeBackend())
    second = second_service.parse_document(str(digital_pdf))
    assert first.document_id != second.document_id
    assert second.cached is False


@pytest.mark.asyncio
async def test_submit_uses_cached_markdown_not_tool_preview(
    runtime_settings: Settings,
    digital_pdf: Path,
) -> None:
    backend = FakeBackend()
    parser = FakeParser(markdown="complete markdown " * 40)
    service = DeepDigService(runtime_settings, parser=parser, backend=backend)
    parsed = service.parse_document(str(digital_pdf))
    submission = await service.submit_material_extraction(
        parsed.document_id,
        [" tensile strength ", "tensile strength", "elongation"],
    )
    assert submission.queued_items == 1
    assert backend.submissions[0]["markdown"] == parser.markdown
    assert backend.submissions[0]["properties"] == ["tensile strength", "elongation"]


@pytest.mark.asyncio
async def test_low_quality_submission_requires_explicit_override(
    runtime_settings: Settings,
    digital_pdf: Path,
) -> None:
    service = DeepDigService(
        runtime_settings,
        parser=FakeParser(markdown="tiny"),
        backend=FakeBackend(),
    )
    parsed = service.parse_document(str(digital_pdf))
    with pytest.raises(DeepDigMcpError) as error:
        await service.submit_material_extraction(parsed.document_id, ["composition"])
    assert error.value.code == "OCR_REQUIRED"


@pytest.mark.asyncio
async def test_export_is_written_only_to_output(
    runtime_settings: Settings,
) -> None:
    service = DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend())
    job_id = "12345678-1234-5678-1234-567812345678"
    path = await service.export_extraction_xlsx(job_id, "result")
    assert Path(path).parent == runtime_settings.output_dir
    assert Path(path).read_bytes().startswith(b"PK")

    with pytest.raises(DeepDigMcpError):
        await service.export_extraction_xlsx(job_id, "../outside")
