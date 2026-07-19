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
apps/desktop        Tauri 2 + React shell for the desktop client
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

For local development before Supabase/LLM credentials are ready, set:

```env
DEV_AUTH_ENABLED=true
LLM_PROVIDER=fake
```

Then use `Authorization: Bearer dev` for protected API calls.

```bash
pnpm install
cd apps/desktop
cp .env.example .env
uv sync
pnpm tauri dev
```

Or run the complete local stack from the repository root:

```bash
pnpm dev:start -- --auth dev --llm fake
```

Build a self-contained installer for the current desktop platform:

```bash
pnpm build:desktop:native
```

The installer bundles the local PDF parser; end users do not need Python or `uv`. See
[Desktop development](docs/desktop-development.md) for macOS/Windows release and signing details.

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
- No PDF upload. Only parsed text, file name, and file hash are submitted.
- Billing is deferred; plan/quota fields are present for compatibility.
- Raw text is not persisted unless `user_settings.store_raw_text` is true.
