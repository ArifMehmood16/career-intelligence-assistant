# Feature Specification: Runtime acceptance verification

**Feature Branch**: `test/phase-19-runtime-verification`
**Created**: 2026-10-07
**Status**: Verified locally; external delivery recorded in PR timeline
**Input**: Continue development after reviewing remaining plan items for completed,
stale or redundant work. Root scope: PLAN 19.2–19.3; review 19.4 without claiming
its measurement or release gates.

## User Scenarios & Testing

### User Story 1 — Trust the remaining plan (Priority: P1)

The maintainer can distinguish implemented and verified provider/runtime work from
real remaining release work, without rebuilding existing features.

**Independent Test**: Inspect current code and passing acceptance checks against
each root checkbox; current delivery records agree with merged Git history.

**Acceptance Scenarios**:
1. Given existing provider efficiency features, when their contracts pass, then
   the corresponding root items record evidence and stop requesting duplicate work.
2. Given merged PRs and historical deferred checks, when current status is updated,
   then history remains factual and browser/quality/security gates stay open.

### User Story 2 — Recover from failed document parsing (Priority: P1)

A stalled or crashed document read releases its workers and lets a subsequent
synthetic upload succeed. Application shutdown releases active parser workers.

**Independent Test**: Exercise real child workers with synthetic files, bounded
   timeouts and deliberate child failure; prove termination and subsequent success.

**Acceptance Scenarios**:
1. Given a stalled binary reader, when its deadline expires, then the caller gets
   the existing safe unreadable error and no worker keeps running.
2. Given a crashed reader, when another upload is submitted, then it succeeds in
   a fresh pool rather than inheriting a broken pool.
3. Given a running parser pool, when the application closes, then its workers exit.

### User Story 3 — Preserve cancellation and honest progress (Priority: P2)

Parallel provider work observes the parent job's cancellation and attributes
physical attempts to the right task, including retries.

**Independent Test**: Exercise actual cancellation, progress and provider accounting
scopes across bounded threads with fake provider responses.

**Acceptance Scenarios**:
1. Given two independent calls, when one retries, then the task records all three
   physical attempts without losing concurrent increments.
2. Given cancellation in the parent scope, when a child tries another call, then
   the call does not start and it adds no completed request.

### Edge Cases

Plain text bypasses child startup. Parser close is idempotent; normal shutdown and
failure permit later lazy recreation. Unknown timing remains unknown. Cache hits,
skipped rechecks and failed publication retain existing contracts.

## Requirements

### Functional Requirements

- **FR-001**: Current PLAN/BACKLOG MUST distinguish proven, implemented-but-unverified,
  genuinely pending and superseded work, with links to acceptance evidence.
- **FR-002**: Provider verification MUST cover one-response reading, capacity limits,
  repairs, changed-candidate batching, cache reuse, native embedding batches,
  separate profiles and shared rate/concurrency controls.
- **FR-003**: Parser verification MUST prove real worker termination on timeout,
  child crash and application shutdown, safe errors and subsequent successful parsing.
- **FR-004**: Thread verification MUST exercise actual cancellation and task accounting
  scopes, including physical retries and no dispatch after cancellation.
- **FR-005**: This work MUST preserve existing product, publication and privacy
  contracts and leave unobserved browser, frozen-label quality, security and
  deployment acceptance open. No personal uploads, database migration or paid calls.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every remaining root milestone item has a current disposition; completed
  provider/runtime items link to observed passing checks.
- **SC-002**: Timeout, crash and shutdown scenarios leave zero live test-created
  parser workers and a subsequent synthetic binary upload succeeds.
- **SC-003**: Two calls with one retry record three attempts in the correct task;
  cancelled dispatch records zero additional attempts.
- **SC-004**: Full lint and hermetic suites pass; no unobserved release gate closes.

## Assumptions

Existing provider and concurrency implementations are reused. Tests are explicitly
part of this acceptance slice. Only demonstrated defects receive production edits.
The human's standing commit/push/PR authorization applies; merging remains human-owned.
Historical feature tasks stay historical; current roadmap status is authoritative.
