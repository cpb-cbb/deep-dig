from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Protocol

from markitdown import MarkItDown
from pypdf import PdfReader

from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.quality import assess_markdown_quality
from deep_dig_mcp.schemas import ParsedDocument
from deep_dig_mcp.security import config_fingerprint, document_id_for, sha256_file


class DocumentParser(Protocol):
    name: str
    parser_version: str
    supported_extensions: set[str]

    def parse(
        self,
        path: Path,
        *,
        file_hash: str | None = None,
        config: dict[str, Any] | None = None,
        display_name: str | None = None,
    ) -> ParsedDocument: ...


class MarkItDownParser:
    name = "markitdown"
    supported_extensions = {".pdf"}

    def __init__(self, converter: MarkItDown | None = None) -> None:
        self._converter = converter or MarkItDown(enable_plugins=False)
        try:
            self.parser_version = version("markitdown")
        except PackageNotFoundError:
            self.parser_version = "unknown"

    def parse(
        self,
        path: Path,
        *,
        file_hash: str | None = None,
        config: dict[str, Any] | None = None,
        display_name: str | None = None,
    ) -> ParsedDocument:
        parser_config = config or {}
        if path.suffix.lower() not in self.supported_extensions:
            raise DeepDigMcpError("UNSUPPORTED_FORMAT", f"Unsupported format: {path.suffix}")
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise DeepDigMcpError("INVALID_PDF", "The file does not have a valid PDF header")

        try:
            converted = self._converter.convert_local(str(path))
            markdown = converted.text_content or ""
        except DeepDigMcpError:
            raise
        except Exception as exc:
            raise DeepDigMcpError(
                "PARSE_FAILED",
                f"MarkItDown could not parse {display_name or path.name}: {exc}",
            ) from exc

        page_count = _pdf_page_count(path)
        warnings, needs_ocr = assess_markdown_quality(
            markdown,
            page_count=page_count,
            min_text_chars=int(parser_config.get("min_text_chars", 200)),
            min_chars_per_page=int(parser_config.get("min_chars_per_page", 50)),
        )
        resolved_hash = file_hash or sha256_file(path)
        parser_config_hash = config_fingerprint(parser_config)
        document_id = document_id_for(
            resolved_hash,
            self.name,
            self.parser_version,
            parser_config_hash,
        )
        return ParsedDocument(
            document_id=document_id,
            file_name=display_name or path.name,
            file_hash=resolved_hash,
            markdown=markdown,
            text_length=len(markdown),
            parser=self.name,
            parser_version=self.parser_version,
            parser_config_hash=parser_config_hash,
            warnings=warnings,
            needs_ocr=needs_ocr,
            page_count=page_count,
        )


def _pdf_page_count(path: Path) -> int | None:
    try:
        return len(PdfReader(path, strict=False).pages)
    except Exception:
        return None
