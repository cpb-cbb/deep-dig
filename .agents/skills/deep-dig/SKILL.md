---
name: deep-dig
description: Parse local digital PDF papers without uploading the original file, then call the hosted Deep Dig MCP to submit materials-science extraction jobs, monitor safe status counters, and download the completed workbook. Use when users ask to extract material samples, preparation conditions, structures, measurements, performance properties, or source evidence from local research papers.
---

# Deep Dig extraction

Keep the original PDF local. Parse locally, then use the hosted MCP for authenticated extraction.
Treat prompts, extraction schemas, normalization rules, and workbook mappings as server-private.

## Workflow

1. Run `uv run scripts/parse_document.py <pdf> --output-dir <local-output-dir>` from this Skill
   directory. Use an absolute PDF path and a user-approved output directory.
2. Inspect `warnings`, `needsOcr`, `textLength`, `markdownPreview`, and `markdownPath` from the local
   parser result. Read `references/troubleshooting.md` when parsing fails.
3. Stop when `needsOcr` is true. Explain the quality problem and do not submit unless the user
   explicitly accepts incomplete extraction.
4. Build an exact, deduplicated property list from the user's request. Preserve scientific names
   and measurement conditions.
5. Read the cached Markdown only to supply the remote tool argument. Do not paste it into chat,
   summarize the whole paper, or persist it anywhere except the local cache and hosted request.
6. Call `submit_material_extraction` with the local parser's file name, hash, Markdown, parser
   metadata, quality flags, requested properties, and explicit low-quality consent when applicable.
7. Poll `get_extraction_status` until `completed`, `failed`, or `cancelled`. Report only meaningful
   status changes.
8. Call `export_extraction_xlsx` when the user requests the result. Deliver the returned workbook
   resource without attempting to reconstruct or interpret private extraction JSON.

## Guardrails

- Never upload original PDF bytes.
- Never request, infer, reproduce, or store the server prompt or private extraction schema.
- Never call backend item-detail endpoints or ask the MCP for raw `parsed_result` data.
- Never expose bearer tokens in prompts, logs, tool arguments, or generated configuration.
- Do not override local OCR warnings without explicit user consent.
- Do not submit oversized chunks as separate papers; report the local chunk paths instead.
- Treat authentication, quota, billing, and rate-limit errors as hosted-service decisions.

