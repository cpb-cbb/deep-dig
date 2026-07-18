# Architecture

Deep Dig separates local document handling from the hosted commercial service.

```text
LOCAL TRUST BOUNDARY                         HOSTED TRUST BOUNDARY

PDF -> Skill -> local parser                 MCP gateway (Streamable HTTP)
              |                               |
              +-- Markdown + metadata ------>+-- authenticate caller
                                              +-- enforce access boundary
                                              +-- submit/poll/export
                                                       |
                                                       v
                                             FastAPI /jobs API
                                                       |
                                          PostgreSQL + Redis + ARQ
                                                       |
                                      private prompt + private schema
                                                       |
                                               result workbook
```

The optional Docker Web UI is a separate visual client. It may reuse local parsing code and call the
same hosted backend, but it is not part of the Skill-to-MCP execution path.

## Trust boundaries

### Local Skill

- Read the original PDF from a user-authorized local path.
- Parse to Markdown, hash the bytes, assess text quality, and cache local artifacts.
- Send only Markdown, file metadata, requested properties, and control identifiers remotely.
- Never package or reconstruct server prompts, private extraction schemas, normalization rules, or
  workbook mappings.

### Hosted MCP

- Run as a Streamable HTTP service reachable by supported AI clients.
- Validate the caller bearer token against the backend and forward that same identity.
- Expose only submission, job status, cancellation if added, and result-file export operations.
- Never return raw `parsed_result`, LLM output JSON, private schema resources, or prompt resources.
- Keep tool descriptions limited to the public product contract.

### Backend

- Own accounts, quota, rate limits, plans, future billing records, jobs, and exports.
- Own provider credentials, prompts, private extraction schemas, validation, retries, normalization,
  and Excel generation.
- Treat the MCP as a user-facing gateway, not as a trusted shared service account.

## Public and private contracts

Public MCP information is intentionally small:

- submission acknowledgement with a job identifier;
- status and progress counters;
- safe user-facing error codes/messages;
- an exported result file.

Private server information includes:

- prompt text and prompt construction;
- LLM response schema and intermediate reasoning fields;
- normalization and reconciliation rules;
- raw per-item `parsed_result` payloads;
- Excel field and sheet mappings.

The backend HTTP API may retain internal endpoints needed by trusted first-party services. The MCP
must not mirror those endpoints blindly.

## Source layout

| Path | Responsibility |
| --- | --- |
| `.agents/skills/deep-dig` | Local parse workflow and remote MCP orchestration; no private schema |
| `apps/mcp/deep_dig_mcp/server.py` | Hosted MCP public tool boundary |
| `apps/mcp/deep_dig_mcp/gateway.py` | Safe submit/status/export service |
| `apps/mcp/deep_dig_mcp/backend_client.py` | Identity-preserving backend HTTP calls |
| `apps/mcp/deep_dig_mcp/parser.py` | Local parser reused by the optional visual runtime |
| `apps/mcp/deep_dig_mcp/web.py` | Optional Docker Web UI boundary |
| `apps/backend/app/routers` | Authenticated backend HTTP API |
| `apps/backend/app/workers` | Private extraction execution |
| `packages/workflows` | Server-only prompts and private definitions |

## Local parse lifecycle

1. Resolve a user-authorized digital PDF path.
2. Hash the original bytes with SHA-256.
3. Convert the PDF to Markdown locally.
4. Detect empty or unusually sparse text and stop for OCR consent when required.
5. Persist local Markdown and bounded chunks using a parser-versioned cache key.
6. Pass Markdown and public metadata to the hosted MCP only after user intent is clear.

## Hosted extraction lifecycle

1. Authenticate the MCP caller and preserve the caller token when invoking the backend.
2. Validate public inputs without revealing the private workflow schema.
3. Submit `material_extraction` to the backend with a stable idempotency key.
4. Return a job identifier and safe status counters only.
5. Keep per-item JSON private.
6. Return the completed workbook as an MCP binary resource.

## Extension rules

- Add billing behind the existing user identity; never introduce a shared MCP backend token.
- Version private prompts and schemas server-side without updating the local Skill.
- Keep the public MCP contract backward compatible and deliberately smaller than the backend API.
- Do not add raw-result tools or schema resources to the MCP.

