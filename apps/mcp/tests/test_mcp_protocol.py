from __future__ import annotations

import pytest

from deep_dig_mcp.server import build_mcp
from deep_dig_mcp.settings import Settings


@pytest.mark.asyncio
async def test_hosted_server_exposes_only_public_tools(runtime_settings: Settings) -> None:
    mcp = build_mcp(runtime_settings)
    tools = await mcp.list_tools()
    assert {tool.name for tool in tools} == {
        "submit_material_extraction",
        "get_extraction_status",
        "export_extraction_xlsx",
    }
    assert all(tool.outputSchema is None for tool in tools)
    assert await mcp.list_resources() == []
    assert await mcp.list_resource_templates() == []


def test_hosted_server_uses_streamable_http_settings(runtime_settings: Settings) -> None:
    configured = runtime_settings.model_copy(
        update={
            "mcp_host": "0.0.0.0",
            "mcp_port": 9000,
            "mcp_public_url": "https://mcp.example.test/mcp",
            "auth_issuer_url": "https://api.example.test",
        }
    )
    mcp = build_mcp(configured)
    assert mcp.settings.host == "0.0.0.0"
    assert mcp.settings.port == 9000
    assert mcp.settings.streamable_http_path == "/mcp"
    assert mcp.settings.stateless_http is True
