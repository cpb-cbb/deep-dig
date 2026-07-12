# Desktop Development

The desktop application combines a React/Vite UI, a Tauri 2 native shell, and a small Python
package that converts PDF files to Markdown locally.

## Prerequisites and setup

- Node.js, pnpm 9, the Rust toolchain required by Tauri 2, Python 3.12+, and `uv`

```bash
pnpm install
cd apps/desktop
cp .env.example .env
uv sync
pnpm tauri dev
```

Set `VITE_API_BASE_URL` when the backend is not running at `http://127.0.0.1:8001`. For local
development auth, leave both Supabase values empty and ensure the backend has
`DEV_AUTH_ENABLED=true`.

## Build checks

```bash
cd apps/desktop
pnpm build       # TypeScript + web asset production build
pnpm tauri build # native installers/bundles
```

`pnpm build` is the fast contract and UI check. Run the native build before a release because it
also verifies Rust, Tauri capabilities, icons, and platform packaging.

## Local parsing flow

1. React opens Tauri's native file and folder dialogs.
2. Rust hashes the PDF and checks `<selected-dir>/deep-dig-parsed/<prefix>/<hash>.json`.
3. On a cache miss, Rust runs `uv run python -m desktop_parser.parse_pdf`.
4. Python uses `pymupdf4llm` and returns JSON on stdout.
5. Rust persists that JSON; React submits only the parsed text and metadata to the API.

The parser can be tested independently:

```bash
cd apps/desktop
uv run python -m desktop_parser.parse_pdf /absolute/path/to/paper.pdf
```

Keep stdout machine-readable. Send diagnostics to stderr if logging is added.

## Frontend structure

- `src/App.tsx`: application orchestration and UI composition
- `src/domain.ts`: workflow constants, API view types, and pure presentation helpers
- `src/api.ts`: authenticated fetch/download boundary and normalized connection errors
- `src/native.ts`: typed wrappers for Tauri commands and dialogs
- `src/styles.css`: application styles

The extraction mode is intentionally not user-selectable. The desktop always submits
`material_extraction`; requested property names are the user-controlled extraction configuration.

## Release checklist

1. Update matching versions in root/package metadata, backend settings, desktop package, Cargo,
   and Tauri configuration.
2. Regenerate the OpenAPI contract if request or response models changed.
3. Run backend tests, Ruff checks, `pnpm build`, and `cargo check`.
4. Test PDF selection, cache reuse, authentication, cancellation, polling, and Excel export against
   a release-like backend.
5. Build and smoke-test signed artifacts on every target platform.
