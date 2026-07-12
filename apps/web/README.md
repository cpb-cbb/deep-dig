# Deep Dig Marketing Site

Public product site for the Deep Dig material-science extraction desktop application. It is a
static vinext application hosted through Codex Sites; it has no database or application-owned
authentication.

## Development

Requires Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Before merging a change:

```bash
npm run build
npm run lint
```

Product claims must match the current desktop and API behavior. Deep Dig currently accepts PDF
documents, parses them locally, runs only `material_extraction`, and exports results as Excel.
