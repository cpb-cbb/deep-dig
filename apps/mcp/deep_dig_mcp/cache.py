from __future__ import annotations

import json
import tempfile
from pathlib import Path

from deep_dig_mcp.quality import chunk_markdown
from deep_dig_mcp.schemas import ParsedDocument
from deep_dig_mcp.security import validate_document_id


class DocumentCache:
    def __init__(self, root: Path, *, chunk_chars: int) -> None:
        self.root = root
        self.chunk_chars = chunk_chars

    def load(self, document_id: str) -> ParsedDocument | None:
        key = validate_document_id(document_id)
        directory = self.root / key
        metadata_path = directory / "result.json"
        markdown_path = directory / "document.md"
        if not metadata_path.is_file() or not markdown_path.is_file():
            return None
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            payload["markdown"] = markdown_path.read_text(encoding="utf-8")
            payload["markdownPath"] = str(markdown_path)
            payload["cached"] = True
            return ParsedDocument.model_validate(payload)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def save(self, document: ParsedDocument) -> ParsedDocument:
        directory = self.root / validate_document_id(document.document_id)
        chunks_dir = directory / "chunks"
        directory.mkdir(parents=True, exist_ok=True)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = directory / "document.md"
        _atomic_write_text(markdown_path, document.markdown)

        chunk_paths: list[str] = []
        for index, chunk in enumerate(chunk_markdown(document.markdown, self.chunk_chars), start=1):
            chunk_path = chunks_dir / f"{index:04d}.md"
            _atomic_write_text(chunk_path, chunk)
            chunk_paths.append(str(chunk_path))

        saved = document.model_copy(
            update={
                "markdown_path": str(markdown_path),
                "chunk_paths": chunk_paths,
                "cached": False,
            }
        )
        payload = saved.model_dump(mode="json", by_alias=True, exclude={"markdown"})
        _atomic_write_text(
            directory / "result.json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        )
        return saved

    def get_required(self, document_id: str) -> ParsedDocument:
        document = self.load(document_id)
        if document is None:
            from deep_dig_mcp.errors import DeepDigMcpError

            raise DeepDigMcpError(
                "DOCUMENT_NOT_CACHED",
                "The parsed document is not available in the local cache; parse it again first.",
            )
        return document


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)
