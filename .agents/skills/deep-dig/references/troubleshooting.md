# Deep Dig troubleshooting

Read this reference when local parsing or a hosted MCP operation fails.

| Code or symptom | Action |
| --- | --- |
| Local parser unavailable | Confirm `uv` is installed and run the bundled `scripts/parse_document.py` directly. |
| `DOCUMENT_NOT_FOUND` | Confirm the local path exists and the user authorized access. |
| `UNSUPPORTED_FORMAT` | First release accepts digital PDF only. |
| `INVALID_PDF` or `PARSE_FAILED` | Verify the PDF opens normally and is not encrypted or damaged. |
| `OCR_REQUIRED` | Ask for a digital PDF or explicit permission to submit potentially incomplete text. |
| `DOCUMENT_TOO_LONG_FOR_BACKEND` | Report local Markdown/chunk paths; do not submit chunks as separate papers. |
| Hosted MCP unavailable | Verify the configured Streamable HTTP URL and service health. Do not start Docker. |
| Hosted MCP 401/403 | Ask the user to sign in or refresh the locally configured token; never request the token in chat. |
| Quota, balance, or rate-limit error | Report the hosted message and direct the user to account management. |
| Export unavailable | Confirm the job is terminal and request the workbook again. |

