from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from conftest import FakeBackend, FakeParser
from deep_dig_mcp import server
from deep_dig_mcp.service import DeepDigService
from deep_dig_mcp.settings import Settings
from deep_dig_mcp.web import create_app


def test_mcp_parse_tool_returns_structured_result(
    runtime_settings: Settings,
    digital_pdf: Path,
) -> None:
    service = DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend())
    previous = server._service
    server._service = service
    try:
        result = server.parse_document(str(digital_pdf))
    finally:
        server._service = previous
    assert result["ok"] is True
    assert result["document"]["documentId"]
    assert "markdown" not in result["document"]


def test_web_upload_parses_and_deletes_temporary_pdf(runtime_settings: Settings) -> None:
    service = DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend())
    client = TestClient(create_app(service))
    response = client.post(
        "/api/documents/parse",
        files={"document": ("paper.pdf", b"%PDF-1.4\nfixture", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["document"]["fileName"] == "paper.pdf"
    assert list(runtime_settings.upload_dir.iterdir()) == []


def test_web_ui_is_available(runtime_settings: Settings) -> None:
    client = TestClient(
        create_app(DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend()))
    )
    response = client.get("/")
    assert response.status_code == 200
    assert "DEEP DIG" in response.text
    assert "/static/app.js" in response.text
