# Architecture

Deep Dig is a schema-driven document extraction system. Its shared execution engine runs
versioned workflows for material-property tables, user-defined records, and entity relationships.

```text
PDF files
  -> browser web app (React/Vite)
  -> backend PDF-to-Markdown parser (markitdown, optional content cache)
  -> authenticated FastAPI job API
  -> PostgreSQL job/item records + Redis queue
  -> ARQ worker -> immutable workflow snapshot -> configured LLM provider
  -> normalized result envelope -> result-aware Excel export
```

## Trust boundaries

- The web app uploads PDFs to the backend, which parses them with `markitdown`. Uploaded PDF
  bytes are not persisted. The optional persistent parsing cache is disabled by default and,
  when enabled, stores parsed text by content hash without uploader file names. Job records store
  raw parsed text only when `user_settings.store_raw_text` is enabled.
- Provider credentials and prompts remain on the backend.
- Queue payloads and active job items contain parsed text while a task is unfinished so it can be
  requeued after an interruption. Terminal items clear it unless long-term raw text storage is
  enabled.
- Custom provider API keys are encrypted in PostgreSQL with a key derived from `AUTH_SECRET` and
  are never returned through the API. Environment variables remain the default configuration.
- Authentication uses unique database usernames and salted PBKDF2 password hashes. Registration
  and login issue signed JWTs; jobs, schemas, settings, and encrypted provider keys remain scoped
  to the authenticated user ID. There is no Supabase or development authentication bypass.

## Source layout

| Path | Responsibility |
| --- | --- |
| `apps/backend/app/routers` | HTTP boundary, authentication, and response models |
| `apps/backend/app/services` | Jobs, extraction, PDF parsing, normalization, and export logic |
| `apps/backend/app/workers` | Per-document ARQ execution and retry lifecycle |
| `apps/backend/migrations` | PostgreSQL schema history |
| `apps/desktop/src` | React web UI, API client, domain types |
| `packages/workflows/definitions` | Server-owned workflow schemas, UI metadata, and prompts |
| `packages/shared-types` | Generated OpenAPI TypeScript contract |
| `infra/supabase` | Row-level security policies (legacy) |
| `docs` | Architecture, API, development, ADR, and roadmap documents |

## Job lifecycle

1. `POST /jobs` resolves the selected workflow and validates its dynamic configuration.
2. The job stores the workflow version, SHA-256 schema hash, and an immutable definition snapshot.
3. One `JobItem` and one ARQ task are created per document.
4. Workers claim items transactionally and execute the stored snapshot. A batch can therefore use
   all available worker slots without changing behavior after a workflow deployment.
5. Workers fence each claim with a unique token, preventing a superseded worker from overwriting
   a manually resumed item.
6. Transient LLM failures use bounded exponential retries; permanent failures affect only the
   current document.
7. `POST /jobs/{job_id}/resume` requeues unfinished items from their temporarily retained text.
8. The parent job completes when every item is terminal. Clients poll the job endpoints or use
   the optional server-sent events endpoint.
9. A terminal job can be exported as a result-aware `.xlsx` workbook.

## Workflow and result contracts

Workflow metadata separates `domain` from `task_type`: materials science is a domain, while
record extraction and entity-relationship extraction are reusable tasks. Public workflow APIs
expose configuration, output, and UI schemas but never execution prompts.

New item results use a shared envelope containing `schema_version`, workflow identity,
`result_type`, typed `data`, warnings, validation state, and an error field. Payloads remain
result-specific so specialist material measurements are not forced into an overly generic graph.
Exporters and frontend metrics dispatch on `result_type`. Legacy material results without the
envelope remain readable and exportable.

## Extension rules

- Treat every workflow ID as a durable database/API identifier; increase its version when prompts,
  schemas, or result semantics change.
- Update workflow JSON, processor validation, export behavior, and tests together when an output
  shape changes.
- Add a new workflow definition for a new domain preset; add backend code only for a genuinely new
  `result_type`.
- After changing routes or schemas, regenerate `openapi.json` and shared TypeScript types.
- Add database changes only through a new Alembic migration.
