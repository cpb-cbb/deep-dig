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

`pnpm tauri dev` builds a self-contained parser sidecar on the first run. Later runs reuse it until
the parser source, Python project metadata, or lockfile changes.

Set `VITE_API_BASE_URL` when the backend is not running at `http://127.0.0.1:8001`. For local
development auth, leave both Supabase values empty and ensure the backend has
`DEV_AUTH_ENABLED=true`.

## Build checks

```bash
cd apps/desktop
pnpm build       # TypeScript + web asset production build
pnpm build:native # parser sidecar + native installers/bundles
```

`pnpm build` is the fast contract and UI check. Run the native build before a release because it
also verifies Rust, Tauri capabilities, icons, and platform packaging.

## Local parsing flow

1. React opens Tauri's native file and folder dialogs.
2. Rust hashes the PDF and checks `<selected-dir>/deep-dig-parsed/<prefix>/<hash>.json`.
3. On a cache miss, Rust runs the bundled `deep-dig-parser` sidecar.
4. The sidecar uses `markitdown` and returns JSON on stdout.
5. Rust persists that JSON; React submits only the parsed text and metadata to the API.

The parser can be tested independently:

```bash
cd apps/desktop
uv run python -m desktop_parser.parse_pdf /absolute/path/to/paper.pdf
```

Keep stdout machine-readable. Send diagnostics to stderr if logging is added.

## Native installers

The sidecar is generated with PyInstaller and named using Tauri's target-triple convention:

```text
src-tauri/binaries/deep-dig-parser-aarch64-apple-darwin
src-tauri/binaries/deep-dig-parser-x86_64-apple-darwin
src-tauri/binaries/deep-dig-parser-x86_64-pc-windows-msvc.exe
```

Generated binaries and Tauri build output are ignored by Git. Build each target on its matching
operating system because PyInstaller does not cross-compile:

```bash
# macOS host: produces .app and .dmg
pnpm build:native

# Windows x64 host: produces .msi and NSIS setup .exe
pnpm build:native
```

The GitHub Actions workflow `.github/workflows/desktop-release.yml` builds Apple Silicon macOS,
Intel macOS, and Windows x64 artifacts. Run it manually for test artifacts or push a `v*` tag to
create a draft GitHub release.

Configure these GitHub Actions values before a production build:

- Variables: `DESKTOP_API_BASE_URL`, `DESKTOP_SUPABASE_URL`
- Secret: `DESKTOP_SUPABASE_ANON_KEY`
- Apple signing/notarization secrets: `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`,
  `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`

Unsigned builds are suitable for internal smoke testing. Public macOS distribution should be
Developer ID signed and notarized. Public Windows distribution should also use an Authenticode
certificate to avoid reputation warnings.

`markitdown` is distributed under the MIT license. Review the licenses of its PDF dependencies
before publishing an installer.

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
6. Confirm PyMuPDF/PyMuPDF4LLM distribution licensing for the release model.
