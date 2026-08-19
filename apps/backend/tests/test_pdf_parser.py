import json
from types import SimpleNamespace

from app.services import pdf_parser


class FakeMarkItDown:
    calls = 0

    def __init__(self, **_kwargs):
        pass

    def convert(self, _path):
        type(self).calls += 1
        return SimpleNamespace(text_content="# Parsed paper")


def test_parsed_cache_is_disabled_by_default(monkeypatch, tmp_path):
    FakeMarkItDown.calls = 0
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_enabled", False)
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_dir", tmp_path / "cache")
    monkeypatch.setattr(pdf_parser, "MarkItDown", FakeMarkItDown)

    result = pdf_parser.parse_pdf_bytes(b"%PDF-test", "paper.pdf")

    assert result["fileName"] == "paper.pdf"
    assert result["reused"] is False
    assert FakeMarkItDown.calls == 1
    assert not (tmp_path / "cache").exists()


def test_enabled_cache_does_not_store_or_reuse_uploader_file_name(monkeypatch, tmp_path):
    FakeMarkItDown.calls = 0
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_enabled", True)
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_dir", tmp_path / "cache")
    monkeypatch.setattr(pdf_parser, "MarkItDown", FakeMarkItDown)

    first = pdf_parser.parse_pdf_bytes(b"%PDF-shared", "private-name.pdf")
    second = pdf_parser.parse_pdf_bytes(b"%PDF-shared", "current-name.pdf")

    cache_path = pdf_parser._cache_path(first["fileHash"])
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "fileName" not in payload
    assert payload == pdf_parser._cache_payload("# Parsed paper")
    assert second["fileName"] == "current-name.pdf"
    assert second["reused"] is True
    assert FakeMarkItDown.calls == 1


def test_legacy_cache_metadata_is_removed_on_read(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_enabled", True)
    monkeypatch.setattr(pdf_parser.settings, "parsed_cache_dir", tmp_path / "cache")
    file_hash = pdf_parser.sha256_hash(b"%PDF-legacy")
    cache_path = pdf_parser._cache_path(file_hash)
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(
        json.dumps(
            {
                "fileName": "previous-user-secret.pdf",
                "fileHash": file_hash,
                "text": "legacy text",
                "textFormat": "markdown",
                "textLength": 11,
                "reused": False,
            }
        ),
        encoding="utf-8",
    )

    result = pdf_parser.parse_pdf_bytes(b"%PDF-legacy", "safe-name.pdf")

    assert result["fileName"] == "safe-name.pdf"
    assert result["reused"] is True
    assert json.loads(cache_path.read_text(encoding="utf-8")) == pdf_parser._cache_payload(
        "legacy text"
    )
