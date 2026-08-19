# Backend Development

## Prerequisites and setup

- Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), PostgreSQL, and Redis

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run alembic upgrade head
```

For a self-contained local workflow, set `LLM_PROVIDER=fake` in `.env`. Start the API and worker
in separate terminals:

```bash
uv run uvicorn app.main:app --reload --port 8001
uv run arq app.workers.arq_worker.WorkerSettings
```

From the repository root, the process helper starts Redis, API, worker, and desktop together:

```bash
pnpm dev:start -- --llm fake
pnpm dev:status
pnpm dev:stop
```

Logs are written under `.dev/logs/` and are intentionally ignored by Git.

## Quality checks

```bash
cd apps/backend
uv run ruff format --check app tests
uv run ruff check app tests
uv run pytest
```

Tests use isolated service objects and do not require live PostgreSQL, Redis, or an LLM provider.
When changing job creation or worker state transitions, include a focused regression test.

## Workflow definitions

Built-in workflows live in `packages/workflows/definitions/*.json`. Every definition declares a
stable `id`, semantic `version`, `domain`, `task_type`, `result_type`, `config_schema`, public
`output_schema`, `ui_schema`, and server-only execution steps. The registry loads every definition
and rejects duplicate IDs or malformed metadata.

`POST /jobs` validates configuration against the selected definition and stores the version,
schema hash, and full workflow snapshot. Workers always execute the stored snapshot; never mutate
a released definition without increasing its version. Add processor and export regression tests
for every new `result_type`.

## Configuration

Use `apps/backend/.env.example` as the authoritative list. Important groups are:

- Runtime: `ENV`, `APP_VERSION`, `DATABASE_URL`, `REDIS_URL`
- Authentication: `AUTH_SECRET`, `LOCAL_AUTH_*`
- Provider: `LLM_PROVIDER` and the selected provider's key/model/base URL
- Generation: `LLM_TEMPERATURE`
- Capacity: `UPLOAD_MAX_BYTES`, `MAX_TEXT_CHARS`, `WORKER_MAX_JOBS`
- Privacy: `PARSED_CACHE_ENABLED`, `PARSED_CACHE_DIR`
- Reliability: `ITEM_JOB_TIMEOUT_SECONDS`, `ITEM_MAX_TRIES`, retry and queue expiry values
- Observability: `SENTRY_DSN`

Never commit `.env`, provider keys, database snapshots, parsed papers, or generated result files.
Authenticated users can override provider settings from the main UI. Overrides are stored in
`user_settings`; API keys are encrypted using a key derived from `AUTH_SECRET`. Changing
`AUTH_SECRET` requires saving custom API keys again.

## Database and migrations

```bash
cd apps/backend
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
uv run alembic downgrade -1  # local rollback only
```

Review generated migrations before applying them. Production deploys must run migrations before
new API processes accept traffic.

## API contract generation

```bash
cd apps/backend
uv run python -m app.scripts.export_openapi
cd ../..
pnpm generate:types
```

Commit both `apps/backend/openapi.json` and `packages/shared-types/src/openapi.d.ts` with schema
changes. Interactive docs are available at `/docs` and `/redoc` while the API is running.

## Production notes

- Set `ENV=production` and use strong values for `AUTH_SECRET` and `LOCAL_AUTH_PASSWORD`.
- Run API and worker as separate processes so they can scale independently.
- Keep total worker concurrency within the selected LLM provider's rate limits.
- Configure CORS deliberately before serving another browser origin.
- Monitor queue latency, item failure codes, provider 429s, and daily spend.
