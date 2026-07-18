# Deep Dig API Reference

Local base URL: `http://127.0.0.1:8001`. FastAPI serves interactive documentation at `/docs`,
ReDoc at `/redoc`, and the machine-readable schema at `/openapi.json`.

## Authentication and headers

All `/me` and `/jobs` endpoints require `Authorization: Bearer <supabase-access-token>`. When
`DEV_AUTH_ENABLED=true`, local clients may use `Bearer dev`; never enable this in staging or
production. First-party clients also send `X-Client-Version`.

`POST /jobs` should send a stable `Idempotency-Key` of 16–128 characters and reuse it when
retrying the same logical submission. Every response includes `X-App-Version`. Rate-limited
responses include `Retry-After` when known.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/healthz` | No | Liveness response |
| `GET` | `/version` | No | Application version and environment |
| `GET` | `/workflows` | No | List the single supported material workflow |
| `GET` | `/workflows/material_extraction` | No | Get workflow display metadata |
| `GET` | `/me` | Yes | Account, plan, quota, and settings |
| `PATCH` | `/me` | Yes | Update display name or user settings |
| `POST` | `/jobs` | Yes | Validate and queue a document batch |
| `GET` | `/jobs` | Yes | List recent jobs owned by the caller |
| `GET` | `/jobs/{job_id}` | Yes | Read one owned job |
| `GET` | `/jobs/{job_id}/items` | Yes | Read per-document results |
| `POST` | `/jobs/{job_id}/cancel` | Yes | Cancel pending or running work |
| `GET` | `/jobs/{job_id}/export.xlsx` | Yes | Download a terminal job workbook |
| `GET` | `/jobs/{job_id}/events` | Yes | Optional server-sent progress stream |

## Create a job

```http
POST /jobs
Authorization: Bearer dev
Content-Type: application/json
Idempotency-Key: 018f47aa-4ab8-7cb2-a773-9237d7a450c2

{
  "workflow_id": "material_extraction",
  "config": {
    "properties": [
      "BET surface area",
      "total pore volume",
      "specific capacitance"
    ]
  },
  "items": [
    {
      "file_name": "paper.pdf",
      "file_hash": "sha256:0123456789abcdef",
      "text": "# Locally parsed paper text..."
    }
  ]
}
```

Successful response:

```json
{
  "job_id": "31e16b77-e74a-4cd8-b09e-83b77c9cc2b4",
  "queued_items": 1,
  "estimated_seconds": 30,
  "reused": false
}
```

Only `material_extraction` is accepted. `config.properties` contains 1–100 names, each at most
200 characters. Batch and text-size limits may be lower depending on plan and backend settings.

## States and results

Job states are `pending`, `running`, `completed`, `failed`, and `cancelled`. Item states are
`pending`, `running`, `done`, `failed`, and `cancelled`. A completed parent job may contain failed
items; use its counters and item list for the exact outcome.

Normalized successful item results contain `samples[].name`, sample-level `properties`, and
`measurements` split into test `conditions` and measured `performance`. Every property object has
`value`, `unit`, `remark`, `source`, and `method` fields.

## Errors

Application errors use a stable envelope:

```json
{
  "code": "CONCURRENT_JOB_LIMIT",
  "message": "Finish or cancel the active task before starting another one",
  "detail": { "limit": 1 }
}
```

Common codes include `AUTH_REQUIRED`, `AUTH_INVALID`, `WORKFLOW_NOT_FOUND`,
`BATCH_LIMIT_EXCEEDED`, `PAYLOAD_TOO_LARGE`, `CONCURRENT_JOB_LIMIT`, `QUOTA_EXCEEDED`,
`RATE_LIMITED`, `JOB_NOT_FOUND`, `EXPORT_TOO_LARGE`, `LLM_NOT_CONFIGURED`, and
`LLM_RATE_LIMITED`. Request-model violations use FastAPI's standard HTTP 422 response.

The generated `apps/backend/openapi.json` is authoritative for exact field types.

## Hosted MCP exposure

The backend API contract is broader than the public MCP contract. In particular,
`GET /jobs/{job_id}/items` and its `parsed_result` field are for trusted first-party server use and
must not be mirrored by MCP tools. The MCP exposes submission acknowledgement, safe job status, and
the exported workbook only.
