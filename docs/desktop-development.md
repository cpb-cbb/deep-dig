# Desktop Development

The app is now a pure browser web app (React + Vite) living under `apps/desktop`. The former
Tauri native shell and local Python parser have been removed; PDF parsing happens on the backend.

## Prerequisites and setup

- Node.js, pnpm 9

```bash
pnpm install
cd apps/desktop
cp .env.example .env
pnpm dev
```

Set `VITE_API_BASE_URL` when the backend is not running at `http://127.0.0.1:8001`.

Authentication uses database-backed accounts. The UI can register through `POST /auth/register`
and sign in through `POST /auth/login`; every protected request requires the returned token.
Jobs, recent schemas, user settings, and encrypted provider credentials are isolated by user ID.

## Build checks

```bash
cd apps/desktop
pnpm build       # TypeScript + web asset production build
```

`pnpm build` is the fast contract and UI check.

## PDF parsing flow

1. The UI lets the user select PDFs with a browser file picker (`src/files.ts`).
2. The PDFs are uploaded to the backend `POST /files/parse`.
3. The backend parses each file with `markitdown`. Persistent caching is disabled by default.
   When `PARSED_CACHE_ENABLED=true`, parsed text is cached by content hash under
   `PARSED_CACHE_DIR`; uploader file names are never cached.
4. The UI keeps only the parsed Markdown text and submits it to `POST /jobs`.

The parsed text is held in the browser; the uploaded PDF bytes are not persisted. With the
default cache setting, parsed text is not persisted by the parser either.

## Frontend structure

- `src/App.tsx`: application orchestration and UI composition
- `src/domain.ts`: workflow metadata, API view types, and pure presentation helpers
- `src/api.ts`: authenticated fetch/upload/download boundary and normalized connection errors
- `src/files.ts`: browser file picker and upload-to-parse helper
- `src/styles.css`: application styles

The header **Settings** panel switches between backend environment variables and an encrypted
database override for provider, Base URL, model, API key, and temperature. Active tasks expose a
**Continue** action that requeues unfinished documents after an interruption.

The app loads public workflow metadata from `GET /workflows`. `ui_schema.controls` drives the
configuration surface: tag-list controls collect material properties or entity vocabularies, and
the field builder creates typed custom-record schemas. Prompts and provider credentials remain
server-only. Job cards and reports resolve names and result counts by workflow/result type.

## Release checklist

1. Update matching versions in root/package metadata and backend settings.
2. Regenerate the OpenAPI contract if request or response models changed.
3. Run backend tests, Ruff checks, and `pnpm build`.
4. Test registration, login, account isolation, PDF selection, cache reuse, cancellation, polling,
   and Excel export against a
   release-like backend.
