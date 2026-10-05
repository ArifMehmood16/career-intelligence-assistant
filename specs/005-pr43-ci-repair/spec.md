# Feature Specification: Repair PR #43 verification

**Feature Branch**: `docs/phase-19-merged-checkpoint`
**Created**: 2026-10-02
**Status**: Implemented and verified on code head 5b8a585; documentation head rechecked at delivery
**Input**: Review PR #43 CI, fix its failures, update the PR and observe passing checks.
**Root scope**: PLAN 19.1–19.3 verification and 19.4 release checks; BACKLOG Now.

## User Scenarios & Testing

### User Story 1 — Trust the reviewed change (Priority: P1)

The maintainer can review a change whose full existing checks execute and pass,
with failures corrected against the current analysis rather than bypassed.

**Independent Test**: Run existing local code checks and deterministic suites.

**Acceptance Scenarios**:
1. Given stale tests after consolidation, when verification runs, then all tests
   collect and exercise current behavior without restoring the retired analysis.
2. Given a genuine defect, when repaired, then a focused regression demonstrates
   the failure and passes with the repair.
3. Given the published change, when remote verification finishes, then both database
   variants and the combined code-check/deterministic-test job succeed.

### User Story 2 — Check the current review head (Priority: P2)

The maintainer sees fresh checks on subsequent changes to an existing review.

**Independent Test**: Push a repair to PR #43 and inspect its new validation run.

**Acceptance Scenarios**:
1. Given an open review, when its head changes, then validation starts on that head.
2. Given a run, when reporting results, then the report identifies the head and
   observed outcome rather than reusing a prior success.

### Edge Cases

- Collection fails before database tests run; diagnose shared imports first.
- Database checks target disposable data, never the running personal app.
- A skipped suite cannot be reported as passing.
- Provider fixtures remain offline and use synthetic inputs.
- Managed PostgreSQL defaults must preserve exact float round trips; RLS probes
  must test a real restricted role rather than assume superuser SET permission.

## Requirements

### Functional Requirements

- **FR-001**: Existing checks MUST collect and verify the current single analysis.
- **FR-002**: Repairs MUST preserve evidence validation, scoring and deletion rules.
- **FR-003**: Checks MUST remain enforced, with no lowered coverage, new skips or
  suppression introduced to conceal failures.
- **FR-004**: Updated/reopened reviews MUST receive fresh validation of their head.
- **FR-005**: PR #43 and docs MUST reflect final scope and observed results, with
  unmeasured quality and other release work left open.
- **FR-006**: Checks MUST use synthetic inputs, no paid model calls and no mutation
  or migration of personal application data.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing local code and deterministic checks complete successfully.
- **SC-002**: Both remote database checks and the deterministic/code-check job pass
  for the final published review head.
- **SC-003**: The update creates zero new bypasses of existing verification gates.

## Assumptions

- The user explicitly resumes tests/lint for this repair and authorizes updating
  the existing PR; no merge is authorized.
- Keep the published branch name to update PR #43 without rewriting history.
- Repair current contracts/fixtures; historical v1 behavior is superseded.
- Initial failures: 26 locally reproduced Ruff issues and five collection errors;
  more failures may become visible after these blockers are removed.
