# Career Intelligence Assistant — frontend

TanStack Start (React 19) UI for the Career Intelligence Assistant. Agent rules for
this directory are in [AGENTS.md](AGENTS.md).

## Run it

From the repository root, `make run-web` starts the dev server on `WEB_PORT` (default
3000) and loads `API_BASE_URL` from `config/app.env` into the Start server, which
proxies `/api/**` to the FastAPI backend. A plain `bun run dev` here does not load that
file, so the proxy has no backend address. `make run` starts the API and the web app
together.

## Checks

```bash
bun install --frozen-lockfile
bun run lint
bun run typecheck
bun run test
bun run build
```

How the Lovable design became this app, and the proxy details, are in
[docs/frontend-integration.md](../docs/frontend-integration.md).
