# Deep Dig

Deep Dig is a desktop-first AI extraction tool for materials science papers. PDFs stay local: the desktop client parses text locally, then sends text to the backend for authenticated, quota-aware workflow execution.

## Workspace

```text
apps/backend        FastAPI API, arq worker, SQLAlchemy models, Alembic migrations
apps/desktop        Tauri 2 + React shell for the desktop client
apps/web            Placeholder for the marketing/docs site
packages/workflows  Versioned workflow definitions consumed by the backend
packages/shared-types Generated TypeScript API types
infra               Supabase/Fly deployment assets and SQL policies
docs                ADRs and runbooks
```

## Backend quick start

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

For local development before Supabase/LLM credentials are ready, set:

```env
DEV_AUTH_ENABLED=true
LLM_PROVIDER=fake
```

Then use `Authorization: Bearer dev` for protected API calls.

## Desktop quick start

```bash
pnpm install
cd apps/desktop
uv sync
pnpm tauri dev
```

## MVP boundaries

- No BYO LLM key in the client.
- No PDF upload. Only parsed text, file name, and file hash are submitted.
- Stripe billing is deferred; plan/quota fields are present for compatibility.
- Raw text is not persisted unless `user_settings.store_raw_text` is true.
