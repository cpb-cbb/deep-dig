# Deep Dig

Deep Dig turns materials-science papers into structured workbooks while keeping original documents
on the user's machine. The local Skill parses a PDF to Markdown, then calls the hosted Deep Dig MCP
service. The hosted service owns authentication, quota, billing boundaries, extraction prompts,
private schemas, job execution, and export generation.

## Architecture

```text
User machine                              Deep Dig service
------------                              ----------------
Local PDF
  -> Deep Dig Skill
  -> local MarkItDown parser
  -> Markdown + file metadata ----------> hosted MCP (/mcp)
                                             -> authenticated /jobs API
                                             -> PostgreSQL + Redis + ARQ worker
                                             -> private prompt + private extraction schema
                                             -> Excel/result file
```

The original PDF never leaves the user's machine. The hosted MCP exposes submission, status, and
file export operations; it does not expose the private extraction JSON, prompt, normalization rules,
or workflow schema.

Docker is a separate one-command visual client. It is not required by the Skill or hosted MCP.

## Workspace

```text
apps/backend        FastAPI API, authentication, quota, jobs, workers, and Excel export
apps/mcp            Hosted Streamable HTTP MCP gateway and shared visual-runtime code
.agents/skills      Local parsing and hosted-MCP orchestration skill
packages/workflows  Server-only prompts and private extraction definitions
infra/docker        Entry point for the optional visual client
docs                Architecture, API, and runbooks
```

## Run the backend

```bash
cd apps/backend
uv sync --frozen
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

Run the worker in a second terminal:

```bash
cd apps/backend
uv run arq app.workers.arq_worker.WorkerSettings
```

## Run the hosted MCP gateway locally

```bash
cd apps/mcp
uv sync --frozen
DEEP_DIG_API_BASE_URL=http://127.0.0.1:8001 \
DEEP_DIG_MCP_PUBLIC_URL=http://127.0.0.1:8002/mcp \
uv run python -m deep_dig_mcp.server
```

The Streamable HTTP endpoint is `http://127.0.0.1:8002/mcp`. Clients authenticate with the same
user bearer token accepted by the backend; the MCP validates and forwards the caller identity.

## Configure the local Skill

```bash
python3 .agents/skills/deep-dig/scripts/configure_mcp.py \
  --url https://your-deep-dig-host.example/mcp
```

Apply the printed project MCP configuration, set the named token environment variable locally, and
restart the AI client. The Skill parses PDFs locally before invoking the hosted MCP.

## Optional Docker visual client

```bash
mkdir -p deep-dig-output
export DEEP_DIG_API_BASE_URL="http://host.docker.internal:8001"
export DEEP_DIG_API_TOKEN="dev"
docker compose up --build web
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787). This visual workflow is independent of the
Skill-to-MCP path.

## Product boundaries

- Digital PDF only; first-version OCR is not automatic.
- Original PDF bytes remain local.
- Local Skill packages contain no extraction prompt, private schema, normalization rule, or Excel
  field mapping.
- The hosted MCP returns control-plane status and result files, never raw private extraction JSON.
- Every hosted MCP request is associated with the caller identity so quota, rate limits, plans, and
  future billing can be enforced server-side.

## Documentation

- [Service boundaries and MCP](docs/local-mcp.md)
- [Architecture](docs/architecture.md)
- [Backend development](docs/backend-development.md)
- [API reference](docs/api-reference.md)
- [Development runbook](docs/runbooks/development.md)
