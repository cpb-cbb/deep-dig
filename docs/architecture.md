# Architecture

Deep Dig is a materials-science extraction system. It supports one workflow:
`material_extraction` (Material Science Data Extraction).

```text
PDF files
  -> browser web app (React/Vite)
  -> backend PDF-to-Markdown parser (markitdown, hash-cached)
  -> authenticated FastAPI job API
  -> PostgreSQL job/item records + Redis queue
  -> ARQ worker -> configured LLM provider
  -> normalized result -> Excel export
```

## Trust boundaries

- The web app uploads PDFs to the backend, which parses them with `markitdown`. Uploaded PDF
  bytes are not persisted; only parsed Markdown, file metadata, and requested property names are
  stored, and raw parsed text only when `user_settings.store_raw_text` is enabled.
- Provider credentials and prompts remain on the backend.
- Queue payloads necessarily contain the parsed text while a task is waiting to run.
- Authentication is a single local account (`LOCAL_AUTH_USERNAME` / `LOCAL_AUTH_PASSWORD`) that
  issues signed JWTs from `POST /auth/login`. There is no Supabase and no development bypass.

## Source layout

| Path | Responsibility |
| --- | --- |
| `apps/backend/app/routers` | HTTP boundary, authentication, rate limits, response models |
| `apps/backend/app/services` | Jobs, extraction, PDF parsing, normalization, quota, and export logic |
| `apps/backend/app/workers` | Per-document ARQ execution and retry lifecycle |
| `apps/backend/migrations` | PostgreSQL schema history |
| `apps/desktop/src` | React web UI, API client, domain types |
| `packages/workflows/definitions` | Server-owned active workflow prompt definition |
| `packages/shared-types` | Generated OpenAPI TypeScript contract |
| `infra/supabase` | Row-level security policies (legacy) |
| `docs` | Architecture, API, development, ADR, and roadmap documents |

## Job lifecycle

1. `POST /jobs` validates the material extraction request and reserves quota.
2. One `JobItem` and one ARQ task are created per document.
3. Workers claim items transactionally. A batch can therefore use all available worker slots.
4. Transient LLM failures use bounded exponential retries; permanent failures affect only the
   current document.
5. The parent job completes when every item is terminal. Clients poll the job endpoints or use
   the optional server-sent events endpoint.
6. A terminal job can be exported as an `.xlsx` workbook.

## Extension rules

- Treat `material_extraction` as a durable database/API identifier; change its prompt version
  rather than renaming historical jobs.
- Update the workflow JSON and normalization tests together when the provider output shape changes.
- After changing routes or schemas, regenerate `openapi.json` and shared TypeScript types.
- Add database changes only through a new Alembic migration.
