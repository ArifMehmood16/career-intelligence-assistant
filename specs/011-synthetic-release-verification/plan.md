# Implementation Plan: Synthetic release verification

Branch: `test/phase-19-runtime-verification`; same PR #48 (human override of the
usual fresh branch/checkpoint rule). Date: 2026-10-07. [Spec](spec.md).

Root acceptance: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product) and
[BACKLOG Now](../../BACKLOG.md#now--prove-the-current-product).

## Summary and technical context

Reuse Python 3.14/FastAPI/PostgreSQL/pgvector and Bun/React/TanStack. Add Playwright
only to the empty e2e test workspace. Use existing migrations, provider factories,
RoleAnalysisV2, SQL worker and synthetic fixtures. No production API/storage
redesign. Docker Desktop and local Ollama are available; no paid providers needed.

Tests: existing pytest/Vitest layers, a populated additive-migration regression,
real browser/proxy/SQL journey, isolated startup and dependency/source/secrets scans.
Performance: record observations without claiming fixture times as product latency.

## Constitution check

Before research: all six principles pass. This is the human-assigned remaining
19.4 group on one PR. Synthetic input, safe reports and isolated database only.
After design: preserve repo source/resource ancestry in the container rather than
introducing a resource service. Add test-only browser dependency because the
existing unit DOM tests cannot verify a complete browser/SQL journey. Existing
cryptography range excludes required patched versions; minimally update it and
locks, then check compatibility. Local model measurements retain evidence validation.

## Research and design

Read-only research identified absent populated call-progress upgrade coverage;
seed raw historical task columns, preserve their values plus jobs/documents,
check 0/unknown defaults and constraints, always restore head.

Container startup currently omits TOML/Alembic resources and resolves repository
paths incorrectly after wheel installation. Use root build context, explicit
source/config/migration COPY and source PYTHONPATH matching checked-in ancestry.
Run checked-in migrations before uvicorn; readiness must check migrated schema.
Keep credentials out of build context and runtime image.

JD file control currently submits File.name as text. Correct text-file content
reading, bound it to the format the existing JSON endpoint supports, preserve
pasted input and error state; record binary JD upload separately rather than
silently treating binary bytes as description text.

E2E: one Playwright journey against production SQL/worker and frontend proxy.
Unused loopback ports, dedicated database name ending _e2e, explicit hermetic
providers and closed hosted gate, temporary cwd/no personal env, no reuse of
existing user services. Browser-generated workspace is cleaned up by its own UI.
Use accessible user selectors and real responses, persist Ask/drafts and citations.

Security: audit pinned Python/frontend deps, source and tracked files for secrets;
fix advisory-reported packages within ranges where possible. Narrowly triage
static false positives; do not weaken tests/scans or claim absolute security.
Local-model quality uses explicitly frozen synthetic labels, reports unsupported
matches/ranking agreement and source/model/prompt/call provenance. No silent reuse
of retired v1 measurements as current truth.

## Structure

Existing: backend/Dockerfile, compose.yaml, Makefile, existing migrations and
application modules; frontend workspace AddRoleDialog and component tests.
New: e2e/package.json + bun.lock + config/spec + isolated startup helper;
backend/tests/integration/test_call_progress_migration.py and narrow startup test;
spec-linked frozen current labels/measurement CLI only if required for evidence.
Docs: existing evaluation/running-locally/architecture/PLAN/BACKLOG/journal/AI log.

## Sequence

Offline benchmark (spec 001) is already observed; save its safe report first.
Then startup/upload red regressions and fixes, migration preservation, browser
journey, security repairs/scans and local measurement. Run affected focused checks
per commit, full lint/unit/SQL/e2e before checkpoint; update PR #48 and observe CI.
Keep unavailable/unobserved gates visibly open. Human owns merge.

## Authorized continuation — 2026-10-08

After local models failed structural chunk validation, the human explicitly asked
to use OpenAI already configured in the project directory. Run existing benchmark
with explicit OpenAI provider selections; ProviderSettings loads model tags and
hosted authorization/key from the normal project environment. Use only the same
frozen synthetic fixtures/labels and record actual off-machine attribution. No
provider implementation, prompt, secret file or production database change.
