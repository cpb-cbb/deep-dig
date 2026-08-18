from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from markitdown import MarkItDown

from app.config import settings
from app.errors import AppError


def sha256_hash(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _cache_path(file_hash: str) -> Path:
    digest = file_hash.removeprefix("sha256:")
    return settings.parsed_cache_dir / digest[:2] / f"{digest}.json"


def parse_pdf_bytes(data: bytes, file_name: str) -> dict[str, object]:
    file_hash = sha256_hash(data)
    cached = _cache_path(file_hash)
    if cached.is_file():
        result = json.loads(cached.read_text(encoding="utf-8"))
        result["reused"] = True
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
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result
