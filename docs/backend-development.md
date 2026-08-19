# Backend Development

## Prerequisites and setup

- Python 3.12 or newer, [`uv`](https://docs.astral.sh/uv/), PostgreSQL, and Redis

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run alembic upgrade head
```

Configure a real OpenAI-compatible endpoint in `.env`, then start the API and worker in separate
terminals:

```bash
uv run uvicorn app.main:app --reload --port 8001
uv run arq app.workers.arq_worker.WorkerSettings
```

From the repository root, the process helper starts Redis, API, worker, and desktop together:

```bash
pnpm dev:start
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

Use `apps/backend/.env.example` as the minimal setup template. Advanced settings and their defaults
are defined in `app/config.py`. Important groups are:

- Runtime: `ENV`, `APP_VERSION`, `DATABASE_URL`, `REDIS_URL`
- Authentication: `AUTH_SECRET`, `REGISTRATION_ENABLED`; `LOCAL_AUTH_*` is legacy migration only
- Provider: `LLM_PROVIDER` and the selected provider's key/model/base URL
- Generation: `LLM_TEMPERATURE`
- Capacity: `UPLOAD_MAX_BYTES`, `MAX_TEXT_CHARS`, `WORKER_MAX_JOBS`
- Privacy: `PARSED_CACHE_ENABLED`, `PARSED_CACHE_DIR`
- Reliability: `ITEM_JOB_TIMEOUT_SECONDS`, `ITEM_MAX_TRIES`, retry and queue expiry values
- Observability: `SENTRY_DSN`

Worker concurrency defaults to `WORKER_MAX_JOBS=auto`. Auto mode uses the CPU capacity available to
the process and keeps each worker between 1 and 8 concurrent items. Set an integer from 1 to 128 to
override it, but keep the combined concurrency of all worker processes within the LLM provider's
rate limits.

Never commit `.env`, provider keys, database snapshots, parsed papers, or generated result files.
Authenticated users can override provider settings from the main UI. Overrides are stored in
`user_settings`; API keys are encrypted using a key derived from `AUTH_SECRET`. Changing
`AUTH_SECRET` requires saving custom API keys again.

Registration is enabled by default. After creating the desired users, a public deployment can set
`REGISTRATION_ENABLED=false`. Passwords are stored as salted PBKDF2-SHA256 hashes; plaintext
passwords are never stored. An upgraded single-user instance can keep `LOCAL_AUTH_PASSWORD` until
the first successful legacy `admin` login migrates that account and its existing data.

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

- Set `ENV=production`, use a strong stable `AUTH_SECRET`, and disable registration when open
  account creation is not intended.
- Run API and worker as separate processes so they can scale independently.
- Keep total worker concurrency within the selected LLM provider's rate limits.
- Configure CORS deliberately before serving another browser origin.
- Monitor queue latency, item failure codes, provider 429s, and daily spend.
