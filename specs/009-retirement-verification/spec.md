# Feature Specification: Retirement verification

**Feature Branch**: `test/phase-19-retirement-verification`
**Created**: 2026-10-06
**Status**: Implemented; local and CI verification passed on 3511aa9; human review pending
**Input**: Continue the development plan; verify the first open Phase 19.1 retirement gate.
**Root scope**: [PLAN 19.1](../../PLAN.md#191--retire-the-competing-analysis) and [BACKLOG Now](../../BACKLOG.md#now--verify-one-working-architecture).

## User Scenarios & Testing

### User Story 1 - Preserve documents during retirement (Priority: P1)

As a candidate upgrading the app, I keep my uploads and current results while retired results become unavailable for reanalysis.

**Why this priority**: An upgrade must not lose original evidence or display unsupported historical scores.
**Independent Test**: Upgrade a disposable synthetic workspace with mixed historical and current analyses, and compare originals, results, drafts and citations before and after.
**Acceptance Scenarios**:
1. Given original CV and job documents and current results, when the app upgrades, then all original bytes, current evidence, results and associated drafts remain unchanged.
2. Given retired results and associated drafts, when the app upgrades, then those results and drafts disappear and affected roles require reanalysis.
3. Given a current role with an older retired result, when the app upgrades, then only the retired version disappears and the current role remains ready.

### User Story 2 - Use one publication everywhere (Priority: P1)

As a candidate, I see consistent fit, requirements and gaps across analysis, ranking, preparation, drafts, Ask and connected tools.

**Why this priority**: A conflicting score or stale evidence undermines the analysis.
**Independent Test**: Complete a synthetic analysis and read each consumer against its stored publication; open cited evidence and generate grounded artifacts.
**Acceptance Scenarios**:
1. Given a published analysis, when each result consumer runs, then its scores, requirements and evidence agree with that publication.
2. Given no valid current publication, when result consumers run, then no score or ranking position is published and grounded generation is refused.
3. Given a changed CV and reanalysis, when consumers run, then they use only the new publication.

### User Story 3 - Keep retirement and deletion permanent (Priority: P2)

As a candidate, I cannot select the retired analysis and deleting my data removes originals and derived records.

**Why this priority**: The old path and deleted personal evidence must not reappear.
**Independent Test**: Verify unavailable retired selection and delete populated synthetic workspaces and CVs.
**Acceptance Scenarios**:
1. Given current configuration and routes, when retired selection is attempted, then no retired pipeline can execute.
2. Given populated uploads, analysis, drafts, conversations and audit records, when the workspace is deleted, then none of its records survive.

### Edge Cases

- Retired score payload with no pipeline tag, explicit retired tag, or an invalidated result.
- Historical retired result alongside the latest current result for one role.
- Current results invalidated before migration remain unavailable.
- No completed current result must not be presented as a genuine zero fit.
- Migration downgrade restores historical schema only, never erased retired data.

## Requirements

### Functional Requirements

- **FR-001**: Retirement MUST preserve all original uploads, stored text and source spans.
- **FR-002**: Retirement MUST preserve valid current results, current evidence and their drafts and citations.
- **FR-003**: Retirement MUST remove retired results and associated drafts and make affected roles unavailable until reanalysis.
- **FR-004**: All result consumers MUST reuse the current validated publication without alternate fit computation.
- **FR-005**: Missing or invalid current results MUST expose neither a published score nor a ranking position.
- **FR-006**: The retired analysis MUST have no executable or selectable production path.
- **FR-007**: Hard deletion MUST remove originals and derived analysis, artifacts, conversations and operational records within workspace scope.
- **FR-008**: Verification MUST use disposable storage and synthetic evidence only, without paid provider calls or personal database changes.

### Key Entities

- **Original document**: Candidate upload, immutable original bytes, stored text and source spans.
- **Publication**: Versioned validated requirements, verdicts, evidence, domain score and gaps for a role.
- **Generated artifact**: Grounded draft tied to its publication version and citations.
- **Workspace**: Scope for documents, roles, publications, artifacts, conversations and operational records.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every seeded original and valid current artifact survives retirement with identical content and identity.
- **SC-002**: No seeded retired score or its associated artifact remains after retirement.
- **SC-003**: Every tested result consumer agrees with one stored publication and rejects unavailable results.
- **SC-004**: No record from a deleted synthetic workspace survives, and another workspace remains intact.

## Assumptions

- ADR 016 already authorizes retirement; existing implementation is reused and corrected only where verification demonstrates a defect.
- Tests are required for this verification under the repository workflow; existing behavior receives meaningful regression coverage when no red defect is present.
- This closes only the bounded Phase 19.1 gate. Provider efficiency, concurrency, full browser release, security audits and measured model quality/latency remain separate gates.
- Open PR 46 contains spec 008; number 009 avoids a future merge collision while this branch starts from current main.

## Same-PR documentation follow-up — 2026-10-06

The user explicitly requested updated architecture diagram details, tool usage and
screenshots in PR #47. Extend its documentation scope without changing runtime
architecture: reconcile README and detailed execution/publication/retirement diagrams,
expand the existing how-to guide, and refresh synthetic gallery captures including
Ask and Letter. Preserve PR #46's independent feature scope. Acceptance is accurate
code-backed prose, complete readable diagrams and screenshots, local checks and
updated-head CI; no personal document or live provider capture is required.

## Merge integration follow-up — 2026-10-06

After the human merged PR #46, incorporate main at 45ae5c8 into the same PR #47
branch, preserving both accepted changes and their historical records. Current
architecture/usage/screenshots must include merged fit/context/Ask behavior alongside
retirement. Resolve conflicts without rewriting pushed history; verify combined
lint, hermetic and disposable SQL suites and final-head CI before reporting success.
