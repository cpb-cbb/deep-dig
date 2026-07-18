from __future__ import annotations

import pytest

from conftest import FakeBackend
from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.gateway import DeepDigGateway
from deep_dig_mcp.settings import Settings


@pytest.mark.asyncio
async def test_gateway_submits_markdown_with_caller_identity(
    runtime_settings: Settings,
) -> None:
    backend = FakeBackend()
    tokens: list[str] = []

    def client_factory(token: str) -> FakeBackend:
        tokens.append(token)
        return backend

    gateway = DeepDigGateway(runtime_settings, client_factory=client_factory)
    result = await gateway.submit_material_extraction(
        access_token="user-token",
        file_name="paper.pdf",
        file_hash="sha256:" + "a" * 64,
        markdown="# Paper\n\nLocally parsed text.",
        properties=[" tensile strength ", "tensile strength", "elongation"],
    )
    assert result.queued_items == 1
    assert tokens == ["user-token"]
    assert backend.submissions[0]["properties"] == ["tensile strength", "elongation"]
    assert backend.submissions[0]["markdown"] == "# Paper\n\nLocally parsed text."


@pytest.mark.asyncio
async def test_gateway_status_omits_item_results(runtime_settings: Settings) -> None:
    backend = FakeBackend()
    gateway = DeepDigGateway(runtime_settings, client_factory=lambda _token: backend)
    status = await gateway.get_extraction_status(
        access_token="user-token",
        job_id="12345678-1234-5678-1234-567812345678",
    )
    payload = status.model_dump(mode="json", by_alias=True)
    assert payload["status"] == "completed"
    assert "items" not in payload
    assert "parsedResult" not in payload


@pytest.mark.asyncio
async def test_gateway_requires_explicit_low_quality_consent(runtime_settings: Settings) -> None:
    gateway = DeepDigGateway(runtime_settings, client_factory=lambda _token: FakeBackend())
    with pytest.raises(DeepDigMcpError) as error:
        await gateway.submit_material_extraction(
            access_token="user-token",
            file_name="paper.pdf",
            file_hash="sha256:" + "b" * 64,
            markdown="short text",
            properties=["composition"],
            needs_ocr=True,
            warnings=["OCR may be required"],
        )
    assert error.value.code == "OCR_REQUIRED"


@pytest.mark.asyncio
async def test_gateway_exports_binary_workbook(runtime_settings: Settings) -> None:
    gateway = DeepDigGateway(runtime_settings, client_factory=lambda _token: FakeBackend())
    content = await gateway.export_extraction_xlsx(
        access_token="user-token",
        job_id="12345678-1234-5678-1234-567812345678",
    )
    assert content.startswith(b"PK")
