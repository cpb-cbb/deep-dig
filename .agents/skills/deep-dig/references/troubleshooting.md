# Deep Dig troubleshooting

Read this reference when an MCP tool returns `ok: false` or the local server is unavailable.

| Code or symptom | Action |
| --- | --- |
| MCP unavailable | Run `python .agents/skills/deep-dig/scripts/configure_mcp.py`, build `deep-dig-mcp:local`, apply the printed project config, and restart the client. |
| `DOCUMENT_NOT_FOUND` | Confirm the host file is under the mounted workspace and pass its `/workspace/...` path. |
| `PATH_OUTSIDE_ALLOWED_ROOT` | Do not broaden access automatically. Remount the intended input directory explicitly. |
| `UNSUPPORTED_FORMAT` | First release accepts digital PDF only. Convert other formats separately or wait for parser support. |
| `INVALID_PDF` or `PARSE_FAILED` | Verify the file opens normally and is not encrypted or damaged. |
| `OCR_REQUIRED` | Explain that the PDF looks scanned. Ask for a digital version or explicit permission to submit incomplete text. |
| `DOCUMENT_TOO_LONG_FOR_BACKEND` | Report the Markdown and chunk paths. Do not submit chunks independently. |
| `API_TOKEN_REQUIRED` | Ask the user to set `DEEP_DIG_API_TOKEN` in their environment; never ask them to paste it into chat. |
| `BACKEND_UNREACHABLE` | Check `DEEP_DIG_API_BASE_URL`, Docker host routing, and backend health. |
| Backend 401/403 | Refresh the configured API token or verify account access. |
| Export fails | Confirm the job is complete and `/output` is writable by the container user. |

