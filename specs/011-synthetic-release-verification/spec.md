# Feature Specification: Synthetic release verification

**Branch**: `test/phase-19-runtime-verification` (same PR #48 by human instruction)
**Created**: 2026-10-07
**Status**: Ready for planning
**Input**: Continue remaining PLAN 19.4 work in PR #48; README must describe the
product without development status. Reuse spec 001 for the existing benchmark.

Root acceptance: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product) and
[BACKLOG Now](../../BACKLOG.md#now--prove-the-current-product).

## User Scenarios & Testing

### US1 — Complete a real browser journey (P1)

A candidate uploads a synthetic CV, adds a role, sees completed fit, opens source
evidence, prepares, generates drafts and asks a cited question through the real web
proxy, SQL stores and worker. Reload preserves completed data.

Independent test: a reusable browser test runs against isolated production wiring;
no mocked API responses or personal workspace is used.
Acceptance: uploads and pasted descriptions use their contents; incomplete work
shows no fabricated fit; cited outputs resolve to stored source text.

### US2 — Start from a fresh private installation (P1)

The API starts with its runtime model/rubric/migration resources and migrates a fresh
isolated database before serving. Startup/readiness and shutdown are reproducible.

Independent test: fresh synthetic host/container startup plus the complete browser
journey. No application database or existing service is reset.

### US3 — Review honest release evidence (P2)

The maintainer sees observed timing/cache/call data, populated progress-migration
preservation, current dependency/security findings and synthetic model measurements.
README presents product use; PLAN/BACKLOG retain release evidence and open gaps.

Independent test: saved reports, scanner outputs and populated SQL assertions have
reproducible commands and provenance. Fixture timing never becomes a model-quality claim.

## Requirements

- **FR-001**: Preserve one PR/branch; extend existing production wiring, interfaces
  and privacy boundaries. No architecture replacement or personal DB migration.
- **FR-002**: Add/run one complete reusable synthetic Playwright journey through
  real browser/proxy/SQL/worker paths, including source evidence, drafts and persisted Ask.
- **FR-003**: Repair demonstrated startup/resource/migration and upload defects
  with regressions; define one reproducible private startup path.
- **FR-004**: Execute existing offline benchmark, save safe provenance/results;
  separately measure available local models against explicitly frozen current labels
  and record duration/calls/unsupported matches/ranking agreement and limits.
- **FR-005**: Prove historical task/job/document values survive the additive progress
  migration, with new defaults and constraints, in a dedicated disposable database.
- **FR-006**: Audit dependencies/source/secrets, repair actionable findings and record
  scoped false-positive justifications or remaining blockers. Do not weaken scans.
- **FR-007**: Keep README product-focused; update existing PLAN/BACKLOG/docs/logs
  only from observed evidence. Unobserved or unavailable checks remain open.

## Success Criteria

- **SC-001**: Full browser journey passes with zero external/paid provider requests.
- **SC-002**: Fresh startup reaches readiness and its migrated schema supports analysis.
- **SC-003**: Historical task values are unchanged; new counters default to 0/unknown
  and reject negative/excess completed counts.
- **SC-004**: Saved offline/local reports identify frozen inputs and actual models;
  failed/incomplete measurements expose no successful score.
- **SC-005**: Applicable lint/unit/SQL/browser checks pass; scan results are fully
  triaged without broad suppression or an absolute security/readiness claim.

## Assumptions and boundaries

Human explicitly assigned remaining 19.4 items as a group on existing PR #48.
Synthetic fixtures only. Installed local Ollama may be used without paid egress;
hosted measurements still require explicit authorization and keys. E2E gets one
Bun-managed test-only Playwright dependency because no browser runner exists.
Dependency fixes may extend existing version ranges when the patched release is
outside them; compatibility must be tested. Preserve the human-added npm lock.
