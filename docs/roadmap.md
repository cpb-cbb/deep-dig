# Roadmap

## Completed

- Show task queue, progress, and user-selected output locations.
- Support email/password registration, sign-in, password reset, and task management.
- Export completed extraction results as Excel workbooks.
- Establish a local-document/hosted-service trust boundary: original PDFs remain local and only
  parsed Markdown is submitted.

## In progress

- Publish a local parsing Skill and a hosted, per-user authenticated MCP gateway without shipping
  private prompts or extraction schemas.

## Candidate work

- Add an account portal for registration, token management, usage, plans, recharge, and invoices.
- Add billing only when product requirements are defined. The current `plan` and quota fields
  are compatibility placeholders, not a payment implementation.
