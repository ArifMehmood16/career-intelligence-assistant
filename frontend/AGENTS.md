# Frontend agent notes

Applies to `frontend/`, on top of the repository root `AGENTS.md`, which still governs
the working protocol, TDD commit rhythm, SonarQube rules and security rules.
`frontend/CLAUDE.md` imports this file.

- This is the shipped TanStack Start (React 19) app, designed in Lovable
  ([ADR 006](../docs/adr/006-tanstack-start-frontend.md)). Lovable owns how it looks;
  the repository owns what it does
  ([docs/frontend-integration.md](../docs/frontend-integration.md)).
- Packages are managed with `bun` only (`bun.lock`). Do not add npm or yarn lockfiles.
- Routing is file-based under `src/routes/`. Read `src/routes/README.md` before adding
  a route, and never edit `routeTree.gen.ts` by hand.
- The design tokens in `src/styles.css` are fixed and guarded by the ESLint rule in
  `eslint/design-tokens.mjs`. No new tokens or visual patterns without a note in
  `docs/engineering-journal.md`.
- Presentational components take props and fetch nothing; containers fetch. Every
  state is reachable from props alone and appears in `/dev/states` with a test.
- All HTTP goes through `src/api/client.ts` and the same-origin `/api/**` proxy. No API
  URL, key or server variable in browser code, and never a `VITE_*` variable for the
  backend address. `src/api/__fixtures__/` is for tests and `/dev/states` only.
- Render excerpts and generated text as escaped text. Never use
  `dangerouslySetInnerHTML`.
- An incomplete analysis never shows `/100`, a band or a ranking position. Loading,
  failed, incomplete, unscored and valid-zero states stay visually and semantically
  distinct.
- Before each commit: `bun run lint`, `bun run typecheck` and the focused Vitest file
  (`bunx vitest run <file>`); `bun run test` before the checkpoint.
- Do not introduce third-party editor telemetry, analytics trackers or vendor branding.
