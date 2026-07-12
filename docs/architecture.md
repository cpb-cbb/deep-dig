# Architecture

Deep Dig is a desktop-first materials-science extraction system. It supports one workflow:
`material_extraction` (Material Science Data Extraction).

```text
PDF files
  -> Tauri desktop client
  -> local Python PDF-to-Markdown parser
  -> authenticated FastAPI job API
  -> PostgreSQL job/item records + Redis queue
  -> ARQ worker -> configured LLM provider
  -> normalized result -> Excel export
```

## Trust boundaries

- The desktop client reads PDFs and parses them locally. Original PDF bytes are never submitted
  to the API.
- The API receives parsed Markdown, file metadata, and requested property names.
- Provider credentials and prompts remain on the backend.
- Raw parsed text is persisted only when `user_settings.store_raw_text` is enabled. Queue payloads
  necessarily contain the text while a task is waiting to run.
- Authentication uses Supabase JWTs in deployed environments and an explicit development token
  only when `DEV_AUTH_ENABLED=true`.

## Source layout

| Path | Responsibility |
| --- | --- |
| `apps/backend/app/routers` | HTTP boundary, authentication, rate limits, response models |
| `apps/backend/app/services` | Jobs, extraction, normalization, quota, and export logic |
| `apps/backend/app/workers` | Per-document ARQ execution and retry lifecycle |
| `apps/backend/migrations` | PostgreSQL schema history |
| `apps/desktop/src` | React UI, API client, domain types, native command wrappers |
| `apps/desktop/src-tauri` | Native filesystem and parser process bridge |
| `apps/desktop/desktop_parser` | Local PDF-to-Markdown Python package |
| `packages/workflows/definitions` | Server-owned active workflow prompt definition |
| `packages/shared-types` | Generated OpenAPI TypeScript contract |
| `infra/supabase` | Row-level security policies |
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
