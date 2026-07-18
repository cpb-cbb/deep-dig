---
name: deep-dig
description: Parse local digital PDF papers with the Dockerized Deep Dig MCP, inspect Markdown quality, submit requested materials-science properties for structured extraction, monitor jobs, interpret results, and export Excel. Use when a user asks to extract material samples, preparation conditions, structures, measurements, performance properties, or source evidence from local research papers without uploading the original PDF.
---

# Deep Dig local extraction

Keep original documents local. Use the Deep Dig MCP tools for parsing and backend operations; do not implement parsing in the skill or upload the PDF to an external service.

## Workflow

1. Call `parser_info` before the first document. If the MCP is unavailable, run `scripts/configure_mcp.py` to print a project configuration, then ask the user to build or pull the image and restart the MCP client.
2. Convert the host path to a container path under `/workspace`. Preserve its path relative to the configured workspace mount. Reject files outside that mount instead of widening container access.
3. Call `parse_document` with the container path.
4. Stop on `ok: false` and follow `references/troubleshooting.md`. Inspect `warnings`, `needsOcr`, `textLength`, `markdownPreview`, and `chunkPaths`.
5. If `needsOcr` is true, explain that first-version OCR is unavailable. Do not submit unless the user explicitly accepts a potentially incomplete result.
6. Build an exact, deduplicated property list from the user's request. Preserve scientific names and measurement conditions. Ask only when a missing choice would materially change the result.
7. Call `submit_material_extraction` with `documentId` and the property list. Never paste the complete Markdown into a prompt or tool argument.
8. Poll `get_extraction` until the job is `completed`, `failed`, or `cancelled`. Report meaningful progress without repeatedly narrating unchanged state.
9. Interpret item results using `references/extraction-schema.md`. Surface per-item errors and source evidence; do not invent missing values.
10. Call `export_extraction_xlsx` only when the user requests a workbook or the requested workflow explicitly ends in Excel.

## Guardrails

- Treat `/workspace` as read-only input and `/output` as the only writable result location.
- Send only cached Markdown, file metadata, requested properties, and job identifiers to the backend.
- Do not expose `DEEP_DIG_API_TOKEN` in prompts, logs, tool results, or generated configuration.
- Do not override `OCR_REQUIRED` with `allow_low_quality=true` without explicit user consent.
- If `DOCUMENT_TOO_LONG_FOR_BACKEND` occurs, report the generated chunk paths. Do not submit chunks as independent papers because the current backend does not merge cross-chunk samples.
- Use the returned `documentId` for every follow-up operation; do not recompute cache identifiers.

