# Development Runbook

## Backend

1. Copy `apps/backend/.env.example` to `apps/backend/.env`.
2. Start Postgres and Redis locally or point the env vars to managed services.
3. Run migrations with `uv run alembic upgrade head`.
4. Start API with `uv run uvicorn app.main:app --reload --port 8000`.
5. Start worker with `uv run arq app.workers.arq_worker.WorkerSettings`.

## Contracts

After backend route changes, export OpenAPI and regenerate TypeScript types:

```bash
cd apps/backend
uv run python -m app.scripts.export_openapi
cd ../..
pnpm generate:types
```
