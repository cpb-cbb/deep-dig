# Architecture

Deep Dig is a local-first materials-science extraction system with one workflow:
`material_extraction`.

```text
PDF under /workspace                   Browser upload to local container
        |                                           |
        v                                           v
AI client -> stdio MCP                  Web UI on 127.0.0.1
        |                                           |
        +--------------- shared service ------------+
                            |
                 MarkItDown PDF conversion
                 hash + versioned file cache
                 quality / suspected-scan checks
                 bounded Markdown chunks
                            |
             authenticated existing /jobs API
                            |
         PostgreSQL + Redis -> ARQ worker -> LLM
                            |
            normalized samples -> Excel export
```

## Trust boundaries

- The original document is read only inside the local container. MCP input is restricted to
  `/workspace`; browser uploads use a temporary local file that is deleted after parsing.
- `/output` is the only persistent writable mount. It contains Markdown, cache metadata, chunks,
  and exported workbooks.
- MCP responses return a `documentId`, metadata, warnings, paths, and a bounded preview rather than
  the full Markdown. Follow-up tools resolve the cached content internally.
- The backend receives parsed Markdown, file metadata, and requested property names. It never
  receives original PDF bytes.
- The API token is supplied through the process environment and is never serialized into cache or
  returned by tools.
- The container runs as a non-root user with a read-only root filesystem, dropped Linux
  capabilities, and `no-new-privileges` in the supported run configurations.

## Source layout

| Path | Responsibility |
| --- | --- |
| `apps/mcp/deep_dig_mcp/parser.py` | `DocumentParser` interface and MarkItDown adapter |
| `apps/mcp/deep_dig_mcp/cache.py` | Atomic Markdown, metadata, and chunk persistence |
| `apps/mcp/deep_dig_mcp/quality.py` | Low text and page-density checks; bounded chunking |
| `apps/mcp/deep_dig_mcp/security.py` | Hashing, cache identity, input/output path boundaries |
| `apps/mcp/deep_dig_mcp/service.py` | Shared parse, submit, poll, and export application service |
| `apps/mcp/deep_dig_mcp/server.py` | Official Python MCP SDK stdio boundary |
| `apps/mcp/deep_dig_mcp/web.py` | Local FastAPI Web UI boundary |
| `apps/backend/app/routers` | Existing HTTP API, authentication, rate limits, responses |
| `apps/backend/app/services` | Existing jobs, extraction, normalization, quota, export |
| `.agents/skills/deep-dig` | AI workflow orchestration and result interpretation |

## Parse lifecycle

1. Resolve the path and reject files outside the allowed mount, unsupported formats, empty files,
   oversized files, and symlink escapes.
2. Hash the original bytes with SHA-256.
3. Build a cache identity from file hash, parser name, parser version, and canonical configuration.
4. Return the cached result when both metadata and Markdown are valid.
5. Convert the PDF with MarkItDown and count PDF pages with pypdf.
6. Mark empty, unusually short, or low-density text as `needsOcr` and attach warnings.
7. Atomically persist full Markdown, metadata, and bounded chunks beneath `/output/cache/<id>`.

## Extraction lifecycle

1. `submit_material_extraction` resolves cached Markdown by `documentId` and validates properties.
2. Suspected scans require explicit low-quality consent. Empty Markdown is never submitted.
3. Text above the current backend `200_000` character limit returns a structured local error and
   chunk paths; chunks are not treated as independent papers.
4. The existing `POST /jobs` endpoint reserves quota and queues one item.
5. `get_extraction` combines `GET /jobs/{id}` and `GET /jobs/{id}/items`.
6. `export_extraction_xlsx` downloads the existing backend workbook into `/output`.

## Extension rules

- Add future converters behind `DocumentParser`; keep MCP and Web contracts stable.
- Include every parser behavior change in the parser configuration fingerprint or version.
- Keep `material_extraction` as a durable backend workflow identifier.
- Do not add automatic chunk submission until sample reconciliation and deduplication have an
  explicit design and tests.

