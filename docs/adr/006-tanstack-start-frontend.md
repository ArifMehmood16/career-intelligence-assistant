# ADR 006 — The Lovable TanStack Start app is the shipped frontend

- Status: accepted
- Date: 2026-09-18
- Supersedes the "React + Vite SPA" row in the original stack table.

## Context

The frontend was designed in Lovable from `docs/frontend-brief.md`. The plan assumed
the output would be treated as a design source and ported into a plain Vite SPA.

Lovable produced a TanStack Start application: file-based routes, SSR, a Nitro server
entry, react-query, Tailwind v4 and shadcn primitives, under strict TypeScript.

Porting it to a Vite SPA would mean rewriting the routing, the data layer and the
server entry to keep exactly the same pixels — days of work whose only output is a
different way of getting to the same screen. The design is what was wanted; the
framework underneath it is not the part being judged.

## Decision

Ship the TanStack Start application.

- The design system, component composition and screen layouts are fixed. They are the
  deliverable from Lovable.
- Everything else in `frontend/` is ordinary source code in this repository, held to
  the same standard as the backend: strict types, tests at behaviour boundaries, no
  untested component states.
- The Start server is used deliberately, not merely tolerated: it proxies `/api/**` to
  FastAPI, so the browser never holds an API URL and this repository contains no CORS
  configuration.
- SSR is left on but no data fetching moves into route loaders. Data is fetched in the
  browser through react-query. Rendering the shell on the server is free; splitting the
  data layer across two execution contexts is not.

## Consequences

- The deployment story gains a Node process. `compose.yaml` runs three containers —
  Postgres, FastAPI, the Start server — instead of two plus a static bundle. Nitro's
  build target must be set to `node-server`; the Lovable default is Cloudflare.
- The frontend differs from the other repositories in this portfolio, which ship a
  Vite SPA. That is a defensible difference and gets one line in the README rather
  than an apology.
- The SSE answer stream and multipart uploads now pass through a Node proxy. That is
  the one genuine technical risk in the decision, so it is spiked at the start of
  Phase 12 before anything depends on it, with a direct-origin-plus-CORS fallback.
  **Spike result (2026-09-18):** pass — see `frontend/src/server/api-proxy.test.ts`
  and PLAN 12.1. No CORS fallback required.
- `bun` becomes the frontend package manager, since Lovable maintains `bun.lock`.
- Lovable stays connected to the branch, so the design can be revised there later.
  The re-sync rules are in `docs/frontend-integration.md`.

## Alternatives considered

- **Port to a Vite SPA.** Matches the plan and the sibling repositories, one less
  process to run. Rejected: significant work with no user-visible or reviewer-visible
  gain, and it would put the frontend out of sync with Lovable permanently.
- **Keep TanStack Start but disable SSR.** Removes a class of hydration bugs. Rejected
  as premature — nothing in this product needs SSR off, and the server is wanted for
  the proxy regardless.
