# ADR 0001: New monorepo for Deep Dig

## Decision

Create Deep Dig as a clean monorepo instead of incrementally mutating the existing `matextract-ai` prototype.

## Rationale

The prototype mixes browser-only LLM calls, prompt endpoints, and demo-oriented UI. The product architecture requires a new trust boundary: the backend owns prompts, quota, jobs, and LLM provider credentials, while the desktop client parses PDFs locally and submits only text.

## Consequences

- Existing prompt and processor ideas may be copied conceptually, but implementation starts clean.
- API contracts are generated from FastAPI OpenAPI.
- Desktop, backend, workflows, infrastructure, and docs evolve in one repository.
