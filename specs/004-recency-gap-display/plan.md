# Implementation Plan: Display published recency gaps

Branch: `fix/phase-19-recency-gap-display` | Date: 2026-10-02 | [Spec](spec.md)
Root: PLAN 19.1, verification under 19.4.

## Summary

Extend the frontend gap enum/type with the existing domain recency category, keeping
JudgeDimension unchanged. Display recency as current percentage weight; retain 0–4
labels for judge gaps. Add a synthetic fixture/regressions and a /dev/states example.
Correct docs/api-contract.md and docs/features.md, which currently omit recency.

## Technical Context

Existing TypeScript/React/TanStack Query/Zod/Bun/Vitest. No new dependency, route,
API/backend/storage change. Existing published data works after refetch. No model
or database write. Live read-only schema diagnosis is distinct from deferred tests.

## Constitution Check

Before and after design: preserve domain authority, strict known-value validation,
three judge anchors, evidence/publication/privacy controls and existing styles.
All unknowns resolved by source and safe live HTTP field/path inspection; no agents
needed. Checks stay pending. Dependency exception: branch from 5e67682 rather than
obsolete main, continuing the same human-directed consolidated implementation.

## Project Structure

Reuse frontend/src/types/index.ts, api/schemas.ts, api/__fixtures__/verdicts.ts,
components/role/verdicts/VerdictGapsPanel.tsx and existing API/container/panel tests;
update routes/dev.states.tsx. Feature artifacts are in this directory.

## Sequence

Author regressions first without executing suites; implement enum/type/recency
label; repeat read-only validation of the already-published response, optionally
inspect live rendering without analysis; update docs and commit bounded change.

## Complexity Tracking

No architecture change or unresolved design choice. No new design tokens/patterns.
