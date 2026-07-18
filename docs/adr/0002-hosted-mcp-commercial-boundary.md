# ADR 0002: Hosted MCP as the commercial boundary

## Decision

Run the Deep Dig MCP as a hosted Streamable HTTP service. Parse original documents locally through
the distributed Skill. Keep Docker as a separate visual-client deployment option.

## Rationale

The hosted MCP is the product entry point for authenticated users and future paid plans. It must
preserve user identity so the backend can apply quota, rate limits, balances, and billing. Local
distribution of prompts or extraction schemas would expose the product's core intellectual
property, so the local Skill contains only parsing and orchestration logic.

## Consequences

- Original PDFs remain local; parsed Markdown crosses the network.
- MCP clients authenticate per user; shared backend service tokens are forbidden.
- The MCP exposes status and result-file export, not raw extraction JSON.
- Prompts, private schemas, normalization, and workbook mappings remain server-only.
- Docker is maintained as an optional visual client and is not required for MCP usage.
