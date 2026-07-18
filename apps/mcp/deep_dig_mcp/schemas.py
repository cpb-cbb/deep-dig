from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ParsedDocument(ApiModel):
    document_id: str
    file_name: str
    file_hash: str
    markdown: str = Field(repr=False)
    markdown_path: str = ""
    chunk_paths: list[str] = Field(default_factory=list)
    text_length: int
    parser: str
    parser_version: str
    parser_config_hash: str
    cached: bool = False
    warnings: list[str] = Field(default_factory=list)
    needs_ocr: bool = False
    page_count: int | None = None


class ParseDocumentResult(ApiModel):
    document_id: str
    file_name: str
    file_hash: str
    markdown_path: str
    chunk_paths: list[str]
    markdown_preview: str
    preview_truncated: bool
    text_length: int
    parser: str
    parser_version: str
    cached: bool
    warnings: list[str]
    needs_ocr: bool
    page_count: int | None


class ParserInfo(ApiModel):
    name: str
    version: str
    supported_formats: list[str]
    ocr_available: bool
    workspace_dir: str
    output_dir: str
    max_file_bytes: int
    backend_max_text_chars: int


class ExtractionSubmission(ApiModel):
    job_id: str
    queued_items: int
    estimated_seconds: int
    reused: bool = False


class ExtractionStatus(ApiModel):
    job: dict[str, Any]
    items: list[dict[str, Any]]
