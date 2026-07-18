# Deep Dig

Deep Dig turns local materials-science papers into structured data. The current product direction is
a Dockerized local runtime: MarkItDown parses the original PDF inside the container, an MCP server
lets AI clients orchestrate extraction, and a local Web UI provides the same workflow visually.
Only parsed Markdown is submitted to the existing authenticated Deep Dig backend.

## Architecture

```text
Local PDF
  -> Codex / Claude through Deep Dig Skill + stdio MCP
  -> or local browser through Docker Web UI
  -> shared MarkItDown parser, quality checks, content cache
  -> existing FastAPI /jobs API
  -> ARQ worker + LLM extraction
  -> structured results + Excel
```

## Workspace

```text
apps/mcp            Local parser, stdio MCP server, Web UI, and tests
apps/backend        FastAPI API, ARQ worker, jobs, extraction, and Excel export
.agents/skills      Repository-scoped AI orchestration skill
packages/workflows  Server-owned material extraction workflow definition
infra/docker        Container entrypoint
docs                Architecture, API, and runbooks
```

The old Tauri desktop package has been removed. Local parsing and visual workflows now live in
`apps/mcp`.

## Run the local Web UI

Start the existing backend first, or point the local runtime at a deployed backend. Then run:

```bash
mkdir -p deep-dig-output
export DEEP_DIG_UID="$(id -u)"
export DEEP_DIG_GID="$(id -g)"
export DEEP_DIG_API_BASE_URL="http://host.docker.internal:8001"
export DEEP_DIG_API_TOKEN="dev"
docker compose up --build web
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). The Web UI accepts digital PDFs, displays
the Markdown preview and quality warnings, submits requested properties, polls the job, and exports
Excel.

## Connect Codex to the MCP server

Build the image and print a project-scoped MCP configuration:

```bash
docker build -f Dockerfile.mcp -t deep-dig-mcp:local .
python3 .agents/skills/deep-dig/scripts/configure_mcp.py
```

Copy the generated table into the trusted project's `.codex/config.toml`, set
`DEEP_DIG_API_TOKEN` in the environment, and restart Codex. Invoke `$deep-dig` or ask to extract
materials properties from a local PDF.

The equivalent container contract is:

```bash
docker run --rm -i \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/workspace:ro" \
  -v "$PWD/deep-dig-output:/output" \
  -e DEEP_DIG_API_TOKEN \
  -e DEEP_DIG_API_BASE_URL \
  deep-dig-mcp:local mcp
```

## Local development

```bash
cd apps/mcp
uv sync
uv run deep-dig-web
uv run pytest
uv run ruff check .
uv run python scripts/check_licenses.py
```

Run all maintained checks from the repository root with `pnpm check`.

## First-release boundaries

- Digital PDF only. Scanned documents return `needsOcr: true`; OCR is not silently attempted.
- Original PDF bytes stay local. Only Markdown, metadata, and requested properties reach the backend.
- Cache identity includes file hash, parser name/version, and canonical parser configuration.
- Markdown is saved in bounded chunks for local access, but oversized documents are not submitted as
  unrelated backend items because cross-chunk result merging is not implemented yet.
- The formal MCP image contains MarkItDown/PDFMiner and explicitly rejects PyMuPDF dependencies.

## Documentation

- [Local MCP and Docker](docs/local-mcp.md)
- [Architecture](docs/architecture.md)
- [Backend development](docs/backend-development.md)
- [API reference](docs/api-reference.md)
- [Development runbook](docs/runbooks/development.md)
