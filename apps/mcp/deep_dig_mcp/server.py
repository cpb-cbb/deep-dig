from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.service import DeepDigService


mcp = FastMCP(
    "Deep Dig",
    instructions=(
        "Parse local documents before submitting extraction. Inspect warnings and needsOcr. "
        "Use documentId for later tools so full Markdown stays out of model context. Original "
        "documents remain inside the local container; only Markdown is sent to the configured "
        "Deep Dig backend."
    ),
    json_response=True,
)
_service: DeepDigService | None = None


def get_service() -> DeepDigService:
    global _service
    if _service is None:
        _service = DeepDigService()
    return _service


@mcp.tool()
def parse_document(path: str) -> dict[str, Any]:
    """Parse a document under /workspace and cache Markdown under /output."""
    try:
        result = get_service().parse_document(path)
        return {"ok": True, "document": result.model_dump(mode="json", by_alias=True)}
    except DeepDigMcpError as exc:
        return _error_result(exc)


@mcp.tool()
async def submit_material_extraction(
    document_id: str,
    properties: list[str],
    allow_low_quality: bool = False,
) -> dict[str, Any]:
    """Submit cached Markdown and requested material properties to the Deep Dig backend."""
    try:
        result = await get_service().submit_material_extraction(
            document_id,
            properties,
            allow_low_quality=allow_low_quality,
        )
        return {"ok": True, "submission": result.model_dump(mode="json", by_alias=True)}
    except DeepDigMcpError as exc:
        return _error_result(exc)


@mcp.tool()
async def get_extraction(job_id: str) -> dict[str, Any]:
    """Get extraction job status and item results in one call."""
    try:
        result = await get_service().get_extraction(job_id)
        return {"ok": True, "extraction": result.model_dump(mode="json", by_alias=True)}
    except DeepDigMcpError as exc:
        return _error_result(exc)


@mcp.tool()
async def export_extraction_xlsx(
    job_id: str,
    output_name: str | None = None,
) -> dict[str, Any]:
    """Download a completed extraction as XLSX into the mounted /output directory."""
    try:
        output_path = await get_service().export_extraction_xlsx(job_id, output_name)
        return {"ok": True, "outputPath": output_path}
    except DeepDigMcpError as exc:
        return _error_result(exc)


@mcp.tool()
def parser_info() -> dict[str, Any]:
    """Return parser version, supported formats, limits, and OCR capability."""
    try:
        result = get_service().parser_info()
        return {"ok": True, "parser": result.model_dump(mode="json", by_alias=True)}
    except DeepDigMcpError as exc:
        return _error_result(exc)


@mcp.resource("deep-dig://parser-info")
def parser_info_resource() -> str:
    """Machine-readable local parser capabilities."""
    result = parser_info()
    return json.dumps(result, ensure_ascii=False)


def _error_result(exc: DeepDigMcpError) -> dict[str, Any]:
    return {"ok": False, "error": exc.as_dict()}


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
