# Development Runbook

## Backend

1. Copy `apps/backend/.env.example` to `apps/backend/.env`.
2. Start Postgres and Redis locally or point the env vars to managed services.
3. Run migrations with `uv run alembic upgrade head`.
4. Start API with `uv run uvicorn app.main:app --reload --port 8000`.
5. Start worker with `uv run arq app.workers.arq_worker.WorkerSettings`.

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
uv run deep-dig-parse-pdf /absolute/path/to/input.pdf
```

The command prints JSON with `fileName`, `fileHash`, `text`, `textFormat`, and
`textLength`. The `text` field remains compatible with the existing `/jobs`
payload and contains Markdown.

The Tauri desktop UI uses the same parser through the `parse_pdf_to_markdown`
native command. During development, run the app from `apps/desktop` so the
native command can execute `uv run deep-dig-parse-pdf` in that directory:

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
