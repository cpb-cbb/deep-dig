#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "markitdown[pdf]>=0.1.3",
#   "pypdf>=5.1.0",
# ]
# ///
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from markitdown import MarkItDown
from pypdf import PdfReader


PARSER_NAME = "markitdown"
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_PREVIEW_CHARS = 4_000
CHUNK_CHARS = 50_000
MIN_TEXT_CHARS = 200
MIN_CHARS_PER_PAGE = 50


class ParseError(Exception):
    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def config_fingerprint(config: dict[str, int]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def document_id_for(file_hash: str, parser_version: str, config_hash: str) -> str:
    identity = "\n".join((file_hash, PARSER_NAME, parser_version, config_hash))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def assess_quality(markdown: str, page_count: int | None) -> tuple[list[str], bool]:
    meaningful = re.sub(r"[\s#*_`>|\-]+", "", markdown)
    length = len(meaningful)
    warnings: list[str] = []
    if length == 0:
        warnings.append("No readable text was extracted; the document may be scanned or damaged.")
    elif length < MIN_TEXT_CHARS:
        warnings.append(f"Only {length} meaningful characters were extracted; OCR may be required.")
    if page_count and length / page_count < MIN_CHARS_PER_PAGE:
        warnings.append(
            "Extracted text density is unusually low for the page count; the PDF may be scanned."
        )
    return warnings, bool(warnings)


def chunk_markdown(markdown: str) -> list[str]:
    if not markdown:
        return [""]
    chunks: list[str] = []
    remaining = markdown
    while len(remaining) > CHUNK_CHARS:
        cut = remaining.rfind("\n\n", 0, CHUNK_CHARS + 1)
        cut = CHUNK_CHARS if cut < CHUNK_CHARS // 2 else cut + 2
        chunks.append(remaining[:cut])
        remaining = remaining[cut:]
    chunks.append(remaining)
    return chunks


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def parse_document(path: Path, output_dir: Path) -> dict[str, Any]:
    try:
        source = path.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise ParseError("DOCUMENT_NOT_FOUND", f"Document not found: {path}") from exc
    if not source.is_file():
        raise ParseError("NOT_A_FILE", f"Document is not a regular file: {source}")
    if source.suffix.lower() != ".pdf":
        raise ParseError("UNSUPPORTED_FORMAT", "Only digital PDF files are supported")
    size = source.stat().st_size
    if size <= 0:
        raise ParseError("EMPTY_FILE", "Document is empty")
    if size > MAX_FILE_BYTES:
        raise ParseError(
            "FILE_TOO_LARGE",
            f"Document exceeds the {MAX_FILE_BYTES}-byte local limit",
            {"size": size, "limit": MAX_FILE_BYTES},
        )
    with source.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ParseError("INVALID_PDF", "The file does not have a valid PDF header")

    parser_version = importlib.metadata.version("markitdown")
    config = {
        "min_text_chars": MIN_TEXT_CHARS,
        "min_chars_per_page": MIN_CHARS_PER_PAGE,
        "markdown_chunk_chars": CHUNK_CHARS,
    }
    file_hash = sha256_file(source)
    config_hash = config_fingerprint(config)
    document_id = document_id_for(file_hash, parser_version, config_hash)
    cache_dir = output_dir.expanduser().resolve() / "cache" / document_id
    metadata_path = cache_dir / "result.json"
    markdown_path = cache_dir / "document.md"

    if metadata_path.is_file() and markdown_path.is_file():
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        payload["cached"] = True
        return payload

    try:
        converted = MarkItDown(enable_plugins=False).convert_local(str(source))
        markdown = converted.text_content or ""
    except Exception as exc:
        raise ParseError("PARSE_FAILED", f"MarkItDown could not parse {source.name}: {exc}") from exc

    try:
        page_count: int | None = len(PdfReader(source, strict=False).pages)
    except Exception:
        page_count = None
    warnings, needs_ocr = assess_quality(markdown, page_count)
    atomic_write(markdown_path, markdown)
    chunk_paths: list[str] = []
    for index, chunk in enumerate(chunk_markdown(markdown), start=1):
        chunk_path = cache_dir / "chunks" / f"{index:04d}.md"
        atomic_write(chunk_path, chunk)
        chunk_paths.append(str(chunk_path))

    preview = markdown[:MAX_PREVIEW_CHARS]
    payload = {
        "ok": True,
        "documentId": document_id,
        "fileName": source.name,
        "fileHash": file_hash,
        "markdownPath": str(markdown_path),
        "chunkPaths": chunk_paths,
        "markdownPreview": preview,
        "previewTruncated": len(preview) < len(markdown),
        "textLength": len(markdown),
        "parser": PARSER_NAME,
        "parserVersion": parser_version,
        "cached": False,
        "warnings": warnings,
        "needsOcr": needs_ocr,
        "pageCount": page_count,
    }
    atomic_write(metadata_path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a digital PDF locally for Deep Dig.")
    parser.add_argument("document", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd() / "deep-dig-output")
    args = parser.parse_args()
    try:
        result = parse_document(args.document, args.output_dir)
    except ParseError as exc:
        result = {
            "ok": False,
            "error": {"code": exc.code, "message": exc.message, "detail": exc.detail},
        }
    print(json.dumps(result, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
