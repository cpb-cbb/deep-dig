# Deep Dig

[简体中文](README.zh-CN.md)

Deep Dig is an open-source, schema-driven AI document extraction tool. It parses PDFs on the
backend, runs versioned extraction workflows, and exports traceable structured results as Excel
workbooks.

## Features

- Upload PDF documents and convert them to Markdown with `markitdown`.
- Choose built-in material-property, custom-record, or entity-relationship workflows.
- Define typed custom fields or domain entity and relationship vocabularies from the UI.
- Keep workflow versions, schema hashes, and immutable job snapshots for reproducible resumes.
- Queue one extraction item per document with PostgreSQL, Redis, and ARQ workers.
- Create multiple accounts with isolated jobs, schemas, model settings, and encrypted API keys.
- Support Anthropic, OpenRouter, and OpenAI-compatible providers, plus a zero-cost fake provider
  for local development.
- Configure provider, Base URL, model, API key, and temperature from the authenticated settings
  panel, or keep using backend environment variables.
- Track task status, retries, and failures, and export completed jobs to `.xlsx`.
- Requeue unfinished documents after a worker, queue, or service interruption.
- Run without built-in plans, extraction quotas, or per-user task throttles.
- Keep provider credentials on the backend; they are never sent to the browser client.

## Architecture

```text
PDF
  -> React/Vite browser UI
  -> FastAPI PDF parser (markitdown)
  -> PostgreSQL job records + Redis queue
  -> ARQ worker
  -> configured LLM provider
  -> versioned workflow + normalized result envelope
  -> Excel export
```

## Repository layout

| Path | Description |
| --- | --- |
| `apps/backend` | FastAPI API, PDF parser, ARQ worker, SQLAlchemy models, and Alembic migrations |
| `apps/desktop` | Main React + Vite browser UI; the historical directory name is `desktop` |
| `apps/web` | Separate React + Vite marketing site |
| `packages/workflows` | Server-owned extraction workflow definitions |
| `packages/shared-types` | Generated TypeScript API types |
| `infra` | Deployment and database assets |
| `docs` | Architecture, API, development, and runbook documentation |

## Requirements

- Node.js and pnpm 9
- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL
- Redis

The repository declares `pnpm@9.15.0` as its package manager.

## Quick start

### 1. Install dependencies

```bash
git clone <your-repository-url>
cd deep-dig
pnpm install

cd apps/backend
uv sync
cp .env.example .env
```

### 2. Configure the backend

Create the PostgreSQL database, then edit `apps/backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/deep_dig
REDIS_URL=redis://localhost:6379/0
AUTH_SECRET=replace-with-a-long-random-secret

LLM_COMPAT_BASE_URL=https://api.openai.com/v1
LLM_COMPAT_API_KEY=replace-with-your-api-key
LLM_COMPAT_MODEL=gpt-4o-mini
```

`AUTH_SECRET` signs login tokens and encrypts per-user API keys. Generate a stable random value and
do not change it after users save provider settings. OpenAI-compatible services such as DeepSeek
or a local gateway can be used by replacing the URL and model.

Apply the database migrations and create the frontend environment file:

```bash
uv run alembic upgrade head
cd ../..
cp apps/desktop/.env.example apps/desktop/.env
```

Do not use sample secrets in a public deployment.

### 3. Start the complete local stack

From the repository root:

```bash
pnpm dev:start
```

This starts Redis, the FastAPI API, the ARQ worker, and the main Web UI. It does not start
PostgreSQL, so PostgreSQL must already be available.

Open the main UI at:

```text
http://127.0.0.1:5173
```

Local service endpoints:

- Web UI: `http://127.0.0.1:5173`
- API: `http://127.0.0.1:8001`
- API docs: `http://127.0.0.1:8001/docs`
- Redis: `127.0.0.1:6379`

Choose **Create account** on the main page. Each account has its own jobs, recent schemas, user
settings, and encrypted LLM credentials. To close public registration after creating the desired
accounts, add `REGISTRATION_ENABLED=false` to `apps/backend/.env` and restart the API.

When upgrading an older single-user installation, keep its existing `LOCAL_AUTH_PASSWORD` for the
first `admin` login. That successful login migrates the legacy user and existing jobs to a hashed
database account; the environment password can then be removed.

## Development commands

```bash
# Complete local stack using apps/backend/.env
pnpm dev:start

# Service management
pnpm dev:status
pnpm dev:stop
pnpm dev:restart
pnpm dev:logs api
pnpm dev:logs worker

# Run only the main Web UI
pnpm dev:desktop

# Run the marketing site
pnpm dev:web
```

The marketing site runs on `http://127.0.0.1:5174`.

To run services manually, use separate terminals:

```bash
# Terminal 1: API
cd apps/backend
uv run uvicorn app.main:app --reload --port 8001

# Terminal 2: worker
cd apps/backend
uv run arq app.workers.arq_worker.WorkerSettings

# Terminal 3: main Web UI
cd apps/desktop
pnpm dev
```

## LLM provider modes

| Mode | Behavior |
| --- | --- |
| `fake` | Returns deterministic demo results; no external API call or cost |
| `auto` | Uses the first configured compatible provider |
| `openrouter` | Uses the OpenRouter API |
| `anthropic` | Uses the Anthropic API |
| `openai_compatible` | Uses an OpenAI-compatible `/chat/completions` endpoint |

The optional fake provider remains available for automated tests and offline development, but the
normal startup path uses the real OpenAI-compatible provider configured in `.env`.

The main UI also has a **Settings** panel. Environment mode reads the variables above. Custom
mode stores an instance-local override; API keys are encrypted on the backend using a key derived
from `AUTH_SECRET` and are never returned to the browser.

## Data and privacy

- Uploaded PDF bytes are processed transiently by the backend and are not persisted by the
  application workflow.
- Persistent PDF parsing cache is disabled by default. When explicitly enabled with
  `PARSED_CACHE_ENABLED=true`, it stores only content-hashed parsed text and never uploader file
  names.
- Parsed text is present temporarily in the Redis queue and PostgreSQL while a job is unfinished,
  allowing its remaining documents to be requeued after an interruption. It is cleared when each
  item reaches a terminal state unless `user_settings.store_raw_text` is enabled.
- Job metadata, extraction results, file names, and hashes are stored according to the configured
  workflow and user settings.
- Provider credentials and extraction prompts stay on the backend.

## Quality checks

```bash
# Backend formatting, linting, and tests + desktop build
pnpm check

# Individual builds
pnpm build:desktop
pnpm build:web

# Backend tests
cd apps/backend
uv run pytest
```

After changing API routes or schemas, regenerate the OpenAPI contract and shared TypeScript
types:

```bash
pnpm generate:api
```

## Documentation

- [Architecture](docs/architecture.md)
- [Backend development](docs/backend-development.md)
- [Desktop Web UI development](docs/desktop-development.md)
- [API reference](docs/api-reference.md)
- [Development runbook](docs/runbooks/development.md)
- [Roadmap](docs/roadmap.md)

## Contributing and security

Pull requests and issue reports are welcome. Please do not commit:

- `.env` files or API keys
- PDF papers, parsed caches, or generated result files
- Database dumps, Redis snapshots, or deployment credentials

Before publishing this repository, review deployment documents for private hosts, internal paths,
and operational credentials. In particular, audit `docs/runbooks/web-deployment.md` before making
the repository public.

## License

Deep Dig is released under the [MIT License](LICENSE).
