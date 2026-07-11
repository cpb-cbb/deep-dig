# Development Runbook

## Backend

1. Copy `apps/backend/.env.example` to `apps/backend/.env`.
2. Start Postgres and Redis locally or point the env vars to managed services.
3. Run migrations with `uv run alembic upgrade head`.
4. Start API with `uv run uvicorn app.main:app --reload --port 8000`.
5. Start worker with `uv run arq app.workers.arq_worker.WorkerSettings`.

Each submitted document is queued as an independent `extract_item` job. A worker
immediately takes another document when one of its execution slots becomes free,
including documents belonging to the same parent task. Run more worker processes
or replicas to increase capacity; Redis distributes item jobs across them.

Worker concurrency and retry behavior can be tuned with:

```env
WORKER_MAX_JOBS=8
ITEM_JOB_TIMEOUT_SECONDS=600
ITEM_MAX_TRIES=3
ITEM_RETRY_BASE_SECONDS=2
ITEM_QUEUE_EXPIRY_SECONDS=604800
```

Effective extraction concurrency is approximately the number of worker replicas
multiplied by `WORKER_MAX_JOBS`. Keep it within the LLM provider's rate limits.

### VS Code debugging

1. Open the repository root in VS Code and install the recommended Python and
   Python Debugger extensions when prompted.
2. Make sure `apps/backend/.env` contains the database, Redis, authentication,
   and LLM settings you want to test.
3. Open **Run and Debug** (`Shift+Command+D` on macOS).
4. Select **Backend: API + Worker** and press `F5`.

The compound debug configuration starts Redis and launches FastAPI plus the ARQ
worker under the debugger. Breakpoints in API code stop the FastAPI debug
session; breakpoints in extraction code such as `extract_item` stop the Worker
debug session. Stopping the compound session stops both Python processes. The
Redis background task can be stopped from **Terminal → Run Task → Terminate
Task** when it is no longer needed.

Use **Backend: FastAPI** or **Backend: Worker** when only one process needs to be
debugged and Redis is already running.

For a platform that provides an OpenAI-compatible API, configure:

```env
LLM_PROVIDER=openai_compatible
LLM_COMPAT_BASE_URL=https://your-provider.example/v1
LLM_COMPAT_API_KEY=your-api-key
LLM_COMPAT_MODEL=your-model-name
```

`LLM_COMPAT_BASE_URL` may be either the `/v1` base URL or the full
`/v1/chat/completions` URL.

## Desktop PDF Parsing

The desktop parser is a local `uv` Python project under `apps/desktop`.
It uses `pymupdf4llm` to convert a user-selected PDF into Markdown before the
text is submitted to the backend.

```bash
cd apps/desktop
uv sync
uv run python -m desktop_parser.parse_pdf /absolute/path/to/input.pdf
```

The command prints JSON with `fileName`, `fileHash`, `text`, `textFormat`, and
`textLength`. The `text` field remains compatible with the existing `/jobs`
payload and contains Markdown.

The Tauri desktop UI uses the same parser through the `parse_pdf_to_markdown`
native command. During development, run the app from `apps/desktop` so the
native command can execute `uv run python -m desktop_parser.parse_pdf` in that
directory:

```bash
cd apps/desktop
uv sync
pnpm tauri dev
```

## Contracts

After backend route changes, export OpenAPI and regenerate TypeScript types:

```bash
cd apps/backend
uv run python -m app.scripts.export_openapi
cd ../..
pnpm generate:types
```
