from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from markitdown import MarkItDown

from app.config import settings
from app.errors import AppError

CACHE_VERSION = 1


def sha256_hash(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _cache_path(file_hash: str) -> Path:
    digest = file_hash.removeprefix("sha256:")
    return settings.parsed_cache_dir / digest[:2] / f"{digest}.json"


def _cache_payload(markdown: str) -> dict[str, object]:
    return {
        "version": CACHE_VERSION,
        "text": markdown,
        "textFormat": "markdown",
        "textLength": len(markdown),
    }


def _write_cache(path: Path, markdown: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            json.dump(_cache_payload(markdown), tmp, ensure_ascii=False)
            temp_path = Path(tmp.name)
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _read_cache(path: Path, file_name: str, file_hash: str) -> dict[str, object] | None:
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    markdown = cached.get("text") if isinstance(cached, dict) else None
    if not isinstance(markdown, str):
        return None

    # Rewrite older cache entries so uploader-controlled metadata such as the
    # original file name cannot leak to a later upload of the same document.
    if cached != _cache_payload(markdown):
        _write_cache(path, markdown)
    return {
        "fileName": file_name,
        "fileHash": file_hash,
        "text": markdown,
        "textFormat": "markdown",
        "textLength": len(markdown),
        "reused": True,
    }


def parse_pdf_bytes(data: bytes, file_name: str) -> dict[str, object]:
    file_hash = sha256_hash(data)
    cached = _cache_path(file_hash)
    if settings.parsed_cache_enabled and cached.is_file():
        result = _read_cache(cached, file_name, file_hash)
        if result is not None:
            return result

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        markdown = MarkItDown(enable_plugins=False).convert(tmp_path).text_content
    except Exception as exc:
        raise AppError(422, "PDF_PARSE_FAILED", f"Could not parse PDF: {file_name}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    result = {
        "fileName": file_name,
        "fileHash": file_hash,
        "text": markdown,
        "textFormat": "markdown",
        "textLength": len(markdown),
        "reused": False,
    }
    if settings.parsed_cache_enabled:
        _write_cache(cached, markdown)
    return result
