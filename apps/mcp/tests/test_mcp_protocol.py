from __future__ import annotations

import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from deep_dig_mcp.settings import Settings


@pytest.mark.asyncio
async def test_stdio_server_lists_expected_tools(runtime_settings: Settings) -> None:
    environment = {
        **os.environ,
        "DEEP_DIG_WORKSPACE_DIR": str(runtime_settings.workspace_dir),
        "DEEP_DIG_OUTPUT_DIR": str(runtime_settings.output_dir),
        "DEEP_DIG_API_TOKEN": "test-token",
    }
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "deep_dig_mcp.server"],
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {
                "parse_document",
                "submit_material_extraction",
                "get_extraction",
                "export_extraction_xlsx",
                "parser_info",
            }
            result = await session.call_tool("parser_info")
            assert result.isError is False
            assert result.structuredContent["result"]["ok"] is True
