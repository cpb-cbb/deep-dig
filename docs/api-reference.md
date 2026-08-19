# Deep Dig API Reference

Local base URL: `http://127.0.0.1:8001`. FastAPI serves interactive documentation at `/docs`,
ReDoc at `/redoc`, and the machine-readable schema at `/openapi.json`.

## Authentication and headers

All `/me`, `/files`, and `/jobs` endpoints require a bearer token returned by
`POST /auth/login`. Desktop requests also send `X-Client-Version`.

`POST /jobs` should send a stable `Idempotency-Key` of 16–128 characters and reuse it when
retrying the same logical submission. Every response includes `X-App-Version`.

## Endpoints

| Method    | Path                               | Auth | Purpose                                     |
| --------- | ---------------------------------- | ---- | ------------------------------------------- |
| `GET`   | `/healthz`                       | No   | Liveness response                           |
| `GET`   | `/version`                       | No   | Application version and environment         |
| `GET`   | `/workflows`                     | No   | List public workflow schemas and UI metadata |
| `GET`   | `/workflows/{workflow_id}`       | No   | Get one public workflow definition           |
| `GET`   | `/me`                            | Yes  | Account and settings                        |
| `PATCH` | `/me`                            | Yes  | Update display name or user settings        |
| `GET`   | `/me/llm-settings`               | Yes  | Read effective provider settings            |
| `PATCH` | `/me/llm-settings`               | Yes  | Use environment or encrypted custom settings |
| `POST`  | `/jobs`                          | Yes  | Validate and queue a document batch         |
| `GET`   | `/jobs`                          | Yes  | List recent jobs owned by the caller        |
| `GET`   | `/jobs/{job_id}`                 | Yes  | Read one owned job                          |
| `GET`   | `/jobs/{job_id}/items`           | Yes  | Read per-document results                   |
| `POST`  | `/jobs/{job_id}/cancel`          | Yes  | Cancel pending or running work              |
| `POST`  | `/jobs/{job_id}/resume`          | Yes  | Requeue unfinished documents                |
| `GET`   | `/jobs/{job_id}/export.xlsx`     | Yes  | Download a terminal job workbook            |
| `GET`   | `/jobs/{job_id}/events`          | Yes  | Optional server-sent progress stream        |

## Create a job

```http
POST /jobs
Authorization: Bearer <access-token>
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

The initial built-ins are `material_extraction`, `custom_record_extraction`, and
`entity_relation_extraction`. Retrieve `config_schema` and `ui_schema` from `/workflows`; invalid
configuration returns `INVALID_WORKFLOW_CONFIG`. The backend enforces the configured per-document
text-size safety limit but has no plan, extraction quota, or per-user batch/concurrency restriction.

Custom records use typed field definitions:

```json
{
  "workflow_id": "custom_record_extraction",
  "config": {
    "fields": [
      {
        "key": "effective_date",
        "label": "Effective date",
        "type": "date",
        "description": "Date the agreement takes effect"
      }
    ]
  },
  "items": [
    {"file_name": "contract.pdf", "file_hash": "sha256:...", "text": "..."}
  ]
}
```

Entity extraction accepts `entity_types` and optional `relation_types` arrays. Stable custom field
keys begin with a letter and contain only letters, numbers, and underscores.

## States and results

Job states are `pending`, `running`, `completed`, `failed`, and `cancelled`. Item states are
`pending`, `running`, `done`, `failed`, and `cancelled`. A completed parent job may contain failed
items; use its counters and item list for the exact outcome.

New normalized results use a common envelope:

```json
{
  "success": true,
  "schema_version": "1.0",
  "workflow_id": "custom_record_extraction",
  "workflow_version": "1.0.0",
  "result_type": "records",
  "data": {"fields": [], "records": []},
  "evidence": [],
  "warnings": [],
  "validation": {"valid": true, "errors": []},
  "error": null
}
```

`material_property_table` data contains samples, properties, and measurements; `records` contains
typed values and per-field evidence; `entity_relation` contains typed entities and relations.
Legacy material results created before the envelope remain readable and exportable.

## Errors

Application errors use a stable envelope:

```json
{
  "code": "JOB_NOT_FOUND",
  "message": "Job not found",
  "detail": {}
}
```

Common codes include `AUTH_REQUIRED`, `AUTH_INVALID`, `WORKFLOW_NOT_FOUND`,
`INVALID_WORKFLOW_CONFIG`,
`PAYLOAD_TOO_LARGE`, `JOB_NOT_FOUND`, `EXPORT_TOO_LARGE`, `LLM_NOT_CONFIGURED`, and
`LLM_RATE_LIMITED`. Request-model violations use FastAPI's standard HTTP 422 response.

## Provider settings

Environment mode clears database overrides and makes new work items use backend environment
variables:

```json
{ "mode": "environment" }
```

Custom mode accepts `provider`, `base_url`, `model`, `temperature`, and an optional `api_key`.
The API key is encrypted at rest and responses expose only `api_key_configured`; they never return
the key. Worker processes load the effective settings whenever they claim a new document.

## Resume an interrupted job

`POST /jobs/{job_id}/resume` resets and requeues every unfinished item with retained source text.
Claim tokens fence previous Worker attempts, so late results from a superseded claim are ignored.
The response reports `queued_items` and `unavailable_items`; the latter is only expected for legacy
jobs created before resumable source retention was introduced.

The generated `apps/backend/openapi.json` is authoritative for exact field types.
