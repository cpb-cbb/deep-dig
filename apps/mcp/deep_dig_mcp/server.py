from __future__ import annotations

import base64

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import BlobResourceContents, CallToolResult, EmbeddedResource
from starlette.requests import Request
from starlette.responses import JSONResponse

from deep_dig_mcp.auth import BackendTokenVerifier
from deep_dig_mcp.errors import DeepDigMcpError
from deep_dig_mcp.gateway import DeepDigGateway
from deep_dig_mcp.settings import Settings


XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_settings = Settings()


def build_mcp(
    settings: Settings | None = None,
    *,
    gateway: DeepDigGateway | None = None,
) -> FastMCP:
    runtime = settings or _settings
    runtime_gateway = gateway or DeepDigGateway(runtime)
    verifier = BackendTokenVerifier(runtime)
    server = FastMCP(
        "Deep Dig",
        instructions=(
            "Submit Markdown parsed on the caller's machine, monitor safe job status, and download "
            "the completed workbook. This service does not expose prompts, schemas, or raw "
            "extraction JSON."
        ),
        host=runtime.mcp_host,
        port=runtime.mcp_port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        auth=AuthSettings(
            issuer_url=runtime.auth_issuer_url,
            resource_server_url=runtime.mcp_public_url,
            required_scopes=["deep-dig"],
        ),
        token_verifier=verifier,
    )

    @server.tool(structured_output=False)
    async def submit_material_extraction(
        file_name: str,
        file_hash: str,
        markdown: str,
        properties: list[str],
        needs_ocr: bool = False,
        warnings: list[str] | None = None,
        allow_low_quality: bool = False,
    ) -> str:
        """Submit locally parsed Markdown. Returns only a job acknowledgement, never result JSON."""
        try:
            result = await runtime_gateway.submit_material_extraction(
                access_token=_caller_token(),
                file_name=file_name,
                file_hash=file_hash,
                markdown=markdown,
                properties=properties,
                needs_ocr=needs_ocr,
                warnings=warnings,
                allow_low_quality=allow_low_quality,
            )
        except DeepDigMcpError as exc:
            raise _safe_tool_error(exc) from exc
        return (
            f"job_id={result.job_id} queued_items={result.queued_items} "
            f"estimated_seconds={result.estimated_seconds} reused={str(result.reused).lower()}"
        )

    @server.tool(structured_output=False)
    async def get_extraction_status(job_id: str) -> str:
        """Return safe state and progress counters without item details or extraction JSON."""
        try:
            result = await runtime_gateway.get_extraction_status(
                access_token=_caller_token(), job_id=job_id
            )
        except DeepDigMcpError as exc:
            raise _safe_tool_error(exc) from exc
        return (
            f"job_id={result.id} status={result.status} "
            f"progress={result.completed_items}/{result.total_items} "
            f"failed_items={result.failed_items}"
        )

    @server.tool(structured_output=False)
    async def export_extraction_xlsx(job_id: str) -> CallToolResult:
        """Return the completed Excel workbook as a binary MCP resource."""
        try:
            normalized_job_id = str(job_id).strip()
            content = await runtime_gateway.export_extraction_xlsx(
                access_token=_caller_token(), job_id=normalized_job_id
            )
        except DeepDigMcpError as exc:
            raise _safe_tool_error(exc) from exc
        file_name = f"deep-dig-{normalized_job_id}.xlsx"
        resource = EmbeddedResource(
            type="resource",
            resource=BlobResourceContents(
                uri=f"deep-dig://exports/{file_name}",
                mimeType=XLSX_MEDIA_TYPE,
                blob=base64.b64encode(content).decode("ascii"),
                _meta={"fileName": file_name, "sizeBytes": len(content)},
            ),
        )
        return CallToolResult(content=[resource], isError=False)

    @server.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "deep-dig-mcp"})

    return server


def _caller_token() -> str:
    token = get_access_token()
    if token is None or not token.token:
        raise ToolError("AUTH_REQUIRED: Sign in and configure a user bearer token")
    return token.token


def _safe_tool_error(exc: DeepDigMcpError) -> ToolError:
    return ToolError(f"{exc.code}: {exc.message}")


mcp = build_mcp()


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
