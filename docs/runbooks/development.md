# Development Runbook

## Backend

1. Copy `apps/backend/.env.example` to `apps/backend/.env`.
2. Start Postgres and Redis locally or point the env vars to managed services.
3. Run migrations with `uv run alembic upgrade head`.
4. Start API with `uv run uvicorn app.main:app --reload --port 8001`.
5. Start worker with `uv run arq app.workers.arq_worker.WorkerSettings`.

Each submitted document is queued as an independent `extract_item` job. A worker
immediately takes another document when one of its execution slots becomes free,
including documents belonging to the same parent task. Run more worker processes
or replicas to increase capacity; Redis distributes item jobs across them.

Worker concurrency and retry behavior can be tuned with:

```env
WORKER_MAX_JOBS=auto
ITEM_JOB_TIMEOUT_SECONDS=600
ITEM_MAX_TRIES=3
ITEM_RETRY_BASE_SECONDS=2
ITEM_QUEUE_EXPIRY_SECONDS=604800
```

Effective extraction concurrency is approximately the number of worker replicas
multiplied by the resolved `WORKER_MAX_JOBS`. Auto mode uses 1–8 slots based on available CPU;
keep total concurrency within the LLM provider's rate limits.

### Capacity and self-hosting

The application has no built-in plans, extraction quotas, per-user concurrency
gates, or request-rate limits. Instance owners control capacity through worker
concurrency and these technical safety settings:

```env
UPLOAD_MAX_BYTES=50000000
MAX_TEXT_CHARS=200000
WORKER_MAX_JOBS=auto
```

If an instance is exposed to untrusted public traffic, configure any desired
request throttling at the reverse proxy or deployment platform.

Desktop task submissions send an `Idempotency-Key`. API clients should reuse the
same key when retrying the same logical submission; keys are unique per user.
Apply every Alembic migration before deploying a backend that accepts these
requests.

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

The authenticated UI can override provider, Base URL, model, API key, and temperature without a
restart. The API key is encrypted in PostgreSQL using `AUTH_SECRET`; environment variables remain
active when no override is saved.

## Web UI and PDF Parsing

The web UI is a React/Vite app under `apps/desktop` (no native shell). Run it in
development with:

```bash
cd apps/desktop
pnpm dev
```

The app creates database accounts through `POST /auth/register`, signs in through
`POST /auth/login`, and
uploads PDFs to `POST /files/parse`. The backend parses them with `markitdown`
server-side and returns the Markdown text, which the UI then submits as the job
payload. Persistent parsing cache is disabled by default; opt in with
`PARSED_CACHE_ENABLED=true`. Cached entries contain parsed text only, keyed by
content hash, and never uploader file names. A full local stack (Redis, API,
worker, Vite) can be started from the repository root with `pnpm dev:start`.

If a Worker, Redis queue, or full service stack is interrupted, open the active task and choose
**Continue**. The backend requeues unfinished items from their temporarily retained source text.
Completed and failed items are not repeated.

## Contracts

After backend route changes, export OpenAPI and regenerate TypeScript types:

```bash
cd apps/backend
uv run python -m app.scripts.export_openapi
cd ../..
pnpm generate:types
```
