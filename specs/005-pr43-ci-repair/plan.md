# Implementation Plan: PR #43 CI repair

Branch: docs/phase-19-merged-checkpoint | Date: 2026-10-02 | [Spec](spec.md)
Root: PLAN 19.1–19.4; existing PR update explicitly authorized.

## Summary

Repair consolidation leftovers against current contracts. First resolve collection
and formatting, then execute suites to expose behavioral failures. Fix genuine
production defects with focused regressions. Add CI update/reopen triggers and
publish only observed validation outcomes.

## Technical Context

Existing Python 3.14, FastAPI/Pydantic, SQLAlchemy/PostgreSQL/pgvector; React,
TypeScript, Zod, Bun, pytest/Vitest, Ruff/mypy/ESLint and GitHub Actions. No new
product architecture or dependency. Local Docker daemon is unavailable; use an
isolated local PostgreSQL cluster if supported, otherwise rely on both CI images.
Never load personal provider env files or mutate the application database.

## Constitution Check

Before/after design: preserve sole chunk/search/judge pipeline, evidence checks,
domain scoring, provider capabilities and hard deletion. Do not revive retired
adapters or lower/skip/suppress gates. The human explicitly resumed tests/lint for
this repair; live benchmark/quality remains outside scope. Keep the existing PR
branch instead of creating another review. Initial unknowns were resolved by local source and actual CI logs. The managed
PostgreSQL follow-up consulted official float-output/role documentation, recorded
in research.md. No new technology or research agents were needed.

## Project Structure

Reuse backend/src, backend/tests, frontend/src and .github/workflows/ci.yml.
Current failures involve tests/support/in_memory_search.py, unit embedding/scoring/
worker tests and integration verdict imports. Formatter changes stay scoped to
reported files. Further repairs follow observed failures. Docs remain README,
AGENTS, PLAN/BACKLOG, engineering journal and AI log; feature artifacts live here.

## Sequence

Reproduce -> align moved imports and current test contracts -> format/check -> run
hermetic/frontend suites -> repair meaningful failures -> isolated database/CI
verification -> docs and commits -> push/update PR -> observe CI final head.

## Complexity Tracking

No architecture exception. Existing PR naming is retained for authorized updates.
