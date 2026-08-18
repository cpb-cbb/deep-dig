(base) caopengbo@192 deep-dig % pnpm dev:start

> deep-dig@0.1.0 dev:start /Users/caopengbo/Documents/code/deep-dig
> scripts/deep-dig-dev.sh start

redis already available on 127.0.0.1:6379
api already running (pid 37699)
worker already running (pid 37706)
Starting desktop...
desktop pid 42444
redis: running (pid 37691)
api: running (pid 37699)
worker: running (pid 37706)
desktop: running (pid 42444)
api port: open at http://127.0.0.1:8001
redis port: open at 127.0.0.1:6379
(base) caopengbo@192 deep-dig %

# Deep Dig

Deep Dig is a desktop-first AI extraction tool for materials-science papers. The desktop parses
PDFs locally and sends only parsed text to an authenticated, quota-aware backend. The product
supports one focused workflow: **Material Science Data Extraction** (`material_extraction`).

## Workspace

```text
apps/backend        FastAPI API, arq worker, SQLAlchemy models, Alembic migrations
apps/desktop        React + Vite web app (replaces the former Tauri client)
apps/web            Marketing site
packages/workflows  Server-owned material extraction workflow definition
packages/shared-types Generated TypeScript API types
infra               Supabase/Fly deployment assets and SQL policies
docs                ADRs and runbooks
```

## Quick start

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8001
```

For local development, copy `apps/backend/.env.example` to `apps/backend/.env` and set
`AUTH_SECRET` and `LOCAL_AUTH_PASSWORD`. To use a fake LLM instead of a real provider, set
`LLM_PROVIDER=fake`.

```bash
pnpm install
cd apps/desktop
cp .env.example .env
pnpm dev
```

Or run the complete local stack from the repository root:

```bash
pnpm dev:start -- --llm fake
```

The web app signs in with the `LOCAL_AUTH_USERNAME`/`LOCAL_AUTH_PASSWORD` account and uploads
PDFs to the backend for server-side parsing. See [Desktop development](docs/desktop-development.md)
for details.

## Documentation

- [Architecture](docs/architecture.md)
- [Backend development](docs/backend-development.md)
- [Desktop development](docs/desktop-development.md)
- [API reference](docs/api-reference.md)
- [Development runbook](docs/runbooks/development.md)
- [Web deployment runbook](docs/runbooks/web-deployment.md)
- [Roadmap](docs/roadmap.md)

## MVP boundaries

- No BYO LLM key in the client.
- PDFs are uploaded transiently for server-side parsing and are not persisted; only parsed
  text, file name, and file hash are stored on jobs.
- Billing is deferred; plan/quota fields are present for compatibility.
- Raw text is not persisted unless `user_settings.store_raw_text` is true.
