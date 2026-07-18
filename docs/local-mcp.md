# Hosted MCP and local clients

## Responsibility split

The local Skill parses source documents. The hosted MCP never receives a local path and never reads
the original PDF. Docker is an independent visual-client deployment option.

## Public MCP tools

| Tool | Purpose |
| --- | --- |
| `submit_material_extraction(...)` | Submit locally parsed Markdown and requested properties. |
| `get_extraction_status(job_id)` | Return safe job state and progress counters. |
| `export_extraction_xlsx(job_id)` | Return the completed workbook as an MCP binary resource. |

The MCP intentionally has no `parse_document`, `parser_info`, raw item listing, or raw extraction
result tool. It exposes no prompt or schema resources.

## Transport and identity

- Transport: Streamable HTTP at `/mcp`.
- Authentication: bearer token supplied by the client.
- Identity: the MCP validates the token through the backend and forwards it for every operation.
- Authorization, quota, rate limits, plan checks, and future billing remain backend-owned.

The production MCP must never use one shared `DEEP_DIG_API_TOKEN` for all users.

## Environment

| Variable | Default | Description |
| --- | --- | --- |
| `DEEP_DIG_API_BASE_URL` | `http://127.0.0.1:8001` | Deep Dig backend API. |
| `DEEP_DIG_MCP_HOST` | `127.0.0.1` | MCP listen host. |
| `DEEP_DIG_MCP_PORT` | `8002` | MCP listen port. |
| `DEEP_DIG_MCP_PUBLIC_URL` | `http://127.0.0.1:8002/mcp` | Public MCP resource URL. |
| `DEEP_DIG_AUTH_ISSUER_URL` | `http://127.0.0.1:8001` | Token issuer/validation boundary metadata. |
| `DEEP_DIG_REQUEST_TIMEOUT_SECONDS` | `30` | Backend request timeout. |

Docker visual-client variables such as workspace, output directory, and Web port are unrelated to
the hosted MCP transport.

## Skill behavior

The repository Skill uses its bundled local parser script, inspects quality warnings, and invokes
the hosted tools. It contains no private extraction schema and does not interpret raw model JSON.
After submission it reports status changes and requests the workbook when the user asks for the
result.

## Verification

```bash
cd apps/mcp
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/check_licenses.py
```

Verify that the MCP tool list contains exactly the three public tools and no resources containing
prompt or schema content.

