# Frontend integration

How the Lovable design becomes the shipped frontend, and how it talks to the API.

[frontend-brief.md](frontend-brief.md) is the brief that produced it. This file takes
over from the moment the generated app landed in `frontend/`.

## The decision

**Keep what Lovable shipped.** The frontend is a TanStack Start application — file
routes, SSR, react-query, Nitro server, Tailwind v4, shadcn primitives — and that is
the frontend that ships. It is not ported to a plain Vite SPA.

Recorded in [adr/006-tanstack-start-frontend.md](adr/006-tanstack-start-frontend.md).

What this buys, and what it costs, is in the ADR. The practical consequence: there is
a Node server in front of the React app, and that server is useful — it is where the
API proxy lives, so the browser never holds an API URL and there is no CORS
configuration anywhere in this repository.

## What is fixed, and what is open

**Fixed — changing it needs a reason and a note in the engineering journal:**

- Every design token in `src/styles.css`, light and dark. Colour, radius, spacing,
  type scale.
- The visual language: flat surfaces, 6px radius, status never carried by colour
  alone, accent reserved for the active provider badge, focus rings and primary
  buttons. No gradients, shadows over 2px, emoji or hero sections.
- The component composition and layout of the screens that exist: app shell,
  workspace, role detail, ask, settings.
- The container / presentational split. Presentational components take props and
  fetch nothing; every state is reachable by passing props alone.

**Open — expected to change:**

- `src/api/client.ts`. Real HTTP client with multipart uploads, `getJob`, and
  `reanalyseRole` (Phase 12.3–12.7). Remaining: SSE stream helper.
- `src/api/__fixtures__/`. Test and `/dev/states` gallery data only; no component
  imports (Phase 12.4).
- `src/types/index.ts`. Additive types landed (Phase 12.5); keep existing shapes stable.
- New routes and components for the features that have no screen yet: gaps, prepare,
  letter, ranking, compare.
- Everything absent: byte-level upload progress bar, full error-code map across
  screens, accessibility fixes, full component coverage.

## What is missing from the Lovable output

Named, so none of it is discovered late:

| Missing | Added in |
|---|---|
| Any test tooling — no Vitest, no Testing Library, no Playwright | Phase 1 |
| A real HTTP client and error handling | Phase 12 |
| The API proxy route | Phase 12 |
| Polling for the analysis job | Phase 12 |
| Streaming answers — the chat renders a stream it never receives | Phase 12 |
| PostgreSQL-backed chat history, idempotent retries and delete-history | Phase 12 |
| Supporting cover-letter upload/list/delete and the “not score evidence” notice | Phase 12 |
| Screens for gaps, prepare, letter, ranking, compare | Phase 13 |
| `src/routes/dev.states.tsx` — a stub heading, no gallery | Phase 13 |
| Two lockfiles: `bun.lock` and `package-lock.json` | Phase 1 — keep `bun.lock`, delete the other |
| Empty `src/app/components/` and `src/app/lib/` from the old skeleton | Phase 1 — delete |
| Nitro's default build target is Cloudflare; this deploys as a container | Phase 16 — `node-server` preset |

## The API proxy

One mechanism, identical in development and production: a catch-all server route at
`src/routes/api.$.ts` forwards `/api/**` to the backend.

```text
browser ──/api/roles──> Start server (Nitro) ──> FastAPI /api/roles
```

- The browser has no API base URL, no CORS preflight, no second origin.
- `API_BASE_URL` is a **server** environment variable. It is never a `VITE_*` value,
  because anything prefixed `VITE_` is compiled into browser code.
- The route forwards method, headers, body and the workspace cookie unchanged, and
  returns the upstream response including its stream. Streaming answers and multipart
  uploads both pass through it.
- Non-`GET` requests are rejected unless the `Origin` header matches the app's own
  origin. The CSRF middleware in `src/start.ts` covers server functions only, not
  this route, so the check is written here explicitly.
- Hop-by-hop headers are stripped. Nothing else is rewritten.

Two things get verified by a spike at the start of Phase 12, before anything is built
on them: that a `text/event-stream` response survives the proxy unbuffered, and that a
multipart upload of `MAX_UPLOAD_BYTES` streams rather than buffering in the Node
process. If either fails, the fallback is a direct browser-to-API origin with CORS,
and the ADR gets a follow-up entry — this is the one assumption in the frontend plan
worth testing early.

## Replacing the fixture client

`src/api/client.ts` keeps its exported function names and signatures wherever the
existing screens use them, so the swap touches one file:

```ts
// before: delay(clone(rolesFixture))
// after:  get<Role[]>("/api/roles")
export function getRoles(): Promise<Role[]> { ... }
```

The new client adds, in the same file:

- a single `request()` that sets `Accept`, parses the error envelope from
  [api-contract.md](api-contract.md), and throws a typed `ApiError` carrying `code`
  and `correlationId`;
- runtime validation of every response with the zod schemas that mirror
  `src/types/index.ts` — the frontend does not trust the API's shape merely because
  TypeScript says so;
- `postMessageStream()` for the SSE answer stream;
- a stable `clientRequestId` per user send, reused on network retry, plus
  `getMessages()` and `deleteMessages()` for PostgreSQL-backed history;
- `getCoverLetters()`, `uploadCoverLetter()` and `deleteCoverLetter()` for supporting
  documents, kept separate from role-generated cover-letter versions;
- `getJob()` for analysis polling.

react-query is already installed and already wraps the app. Query keys are namespaced
per resource, mutations invalidate the queries they affect, and the analysis job query
polls while the job is live and stops on a terminal state. Chat history is server
state: page reload reads it from PostgreSQL rather than treating the browser cache as
the source of truth.

Fixtures move to `src/api/__fixtures__/` and are used by component tests and by the
`/dev/states` gallery. **No component imports a fixture.** That rule was in the brief
and it survives the handover.

## Testing, added in Phase 1

| Layer | Tool | What it covers |
|---|---|---|
| Component | Vitest + Testing Library + jsdom | Every state of every presentational component, driven by props |
| Client | Vitest | The API client against recorded responses, including every error code |
| Type check | `tsc --noEmit` | Strict, with the settings already in `tsconfig.json` |
| Lint | ESLint | The config Lovable shipped, plus a rule banning fixture imports outside tests |
| End to end | Playwright | The walkthrough in [features.md](features.md), against a running stack |

`bun` is the package manager — `bun.lock` is committed and Lovable regenerates it.
`package-lock.json` is deleted so there is one source of truth.

The `/dev/states` route becomes the state gallery: every component state rendered from
props on one page. It is how a reviewer sees the empty, loading, error and
insufficient-evidence states without simulating them, and it is the Playwright
screenshot target.

## Keeping the design honest

The risk in an AI-designed frontend is drift: a hex value, a shadow, a pill button
creeping in over a hundred small edits until it looks like something else.

- Component styling uses semantic classes only — `bg-surface`,
  `text-muted-foreground`, `border-border`. No hex, no inline styles, no `bg-gray-100`.
- An ESLint rule fails the build on a hex colour or a raw Tailwind palette class in
  `src/components/**`.
- Any change to `src/styles.css` is called out in the task report. There is no reason
  to touch that file while adding a feature.

## If Lovable regenerates

The project stays connected to Lovable, so the design can be revised there. When it
is:

1. Pull the branch Lovable pushed. Never force-push over it — that rewrites history on
   Lovable's side.
2. Diff `src/components/**` and `src/styles.css`. Take those.
3. Diff `src/api/**`, `src/routes/**` and anything under test. **Do not take those** —
   Lovable regenerates the fixture client and will overwrite the real one.
4. Run `tsc`, the component tests and the Playwright walkthrough. A design revision
   that breaks a test is a design revision that changed behaviour, and that gets
   resolved deliberately rather than absorbed.

The working rule: Lovable owns how it looks, this repository owns what it does.
