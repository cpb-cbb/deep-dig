from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import FakeBackend, FakeParser
from deep_dig_mcp.service import DeepDigService
from deep_dig_mcp.settings import Settings
from deep_dig_mcp.web import create_app


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
    assert "resultJson" not in response.text


def test_web_status_does_not_return_item_results(runtime_settings: Settings) -> None:
    client = TestClient(
        create_app(DeepDigService(runtime_settings, parser=FakeParser(), backend=FakeBackend()))
    )
    response = client.get("/api/extractions/12345678-1234-5678-1234-567812345678")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["status"] == "completed"
    assert "items" not in payload
    assert "parsedResult" not in response.text
