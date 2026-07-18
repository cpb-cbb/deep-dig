# Local MCP and Docker

## MCP tools

| Tool | Purpose |
| --- | --- |
| `parse_document(path)` | Parse a PDF under `/workspace`, cache Markdown, and return metadata plus a preview. |
| `submit_material_extraction(document_id, properties, allow_low_quality=false)` | Submit cached Markdown to the existing backend. |
| `get_extraction(job_id)` | Return job counters and item results together. |
| `export_extraction_xlsx(job_id, output_name?)` | Save the existing backend export under `/output`. |
| `parser_info()` | Report version, formats, OCR capability, mounts, and size limits. |

Every tool returns `ok`. Expected failures use:

```json
{
  "ok": false,
  "error": {
    "code": "OCR_REQUIRED",
    "message": "...",
    "detail": {}
  }
}
```

`parse_document` intentionally omits full Markdown. It returns a bounded preview, the full local
Markdown path, chunk paths, and a content-addressed `documentId`.

## Environment

| Variable | Default | Description |
| --- | --- | --- |
| `DEEP_DIG_WORKSPACE_DIR` | `/workspace` | Read-only document root. |
| `DEEP_DIG_OUTPUT_DIR` | `/output` | Cache and export root. |
| `DEEP_DIG_API_BASE_URL` | `http://host.docker.internal:8001` | Existing Deep Dig backend. |
| `DEEP_DIG_API_TOKEN` | none | Bearer token required for submit, poll, and export. |
| `DEEP_DIG_MAX_FILE_BYTES` | `104857600` | Maximum local input size. |
| `DEEP_DIG_MARKDOWN_CHUNK_CHARS` | `50000` | Maximum local Markdown chunk size. |
| `DEEP_DIG_BACKEND_MAX_TEXT_CHARS` | `200000` | Mirror of the current `/jobs` item limit. |
| `DEEP_DIG_WEB_PORT` | `8787` | Container Web port. |

## Cache contract

```text
/output/cache/<document-id>/
  result.json
  document.md
  chunks/
    0001.md
    0002.md
```

`document-id` is SHA-256 over the file hash, parser name, parser package version, and canonical
configuration hash. A parser or quality-configuration upgrade therefore cannot reuse stale output.

## Web behavior

The Web UI binds to `127.0.0.1` through Compose. Browser uploads are written only to
`/output/.uploads`, parsed, then deleted in a `finally` block. Persistent PDF copies are not kept.
The UI uses the same service methods and cache as MCP rather than calling the MCP protocol itself.

## Verification

```bash
cd apps/mcp
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv run python scripts/check_licenses.py

cd ../..
docker compose config --quiet
docker build -f Dockerfile.mcp -t deep-dig-mcp:local .
```

The license scanner follows installed production dependencies from `deep-dig-mcp`, reports their
declared licenses, and fails if PyMuPDF/PyMuPDF4LLM or selected strong-copyleft licenses are present.

