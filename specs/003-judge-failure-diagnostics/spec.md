# Feature Specification: Explain incomplete judging

**Feature Branch**: `fix/phase-19-judge-failure-diagnostics`
**Created**: 2026-10-02
**Status**: Implemented for review; application verification deferred
**Input**: Debug a scoring-stage assessment_incomplete failure after advert reading succeeds.
**Root scope**: [PLAN 19.2](../../PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider), verification under 19.4.

## User Scenarios & Testing

### User Story 1 — Identify why judgments are incomplete (Priority: P1)

An operator needs to distinguish a slow provider from an invalid judgment without
seeing document content, model output or credentials.

**Why this priority**: The reported failure has no cause beyond incompleteness.
**Independent Test**: Simulate failed requests and invalid judgments; inspect their
categories/counts while checking that private strings are absent from diagnostics.

**Acceptance Scenarios**:

1. Given a timeout, when an attempt fails, then diagnostics identify its phase and
   configured limit without endpoint, body or exception message.
2. Given an unanswered judge call, when it is handled, then diagnostics identify
   the initial/repair phase and a fixed failure category.
3. Given judgments rejected by server rules, when repair is attempted, then logs
   record accepted/rejected counts; missing judgments still prevent publication.

### User Story 2 — Allow a slow response to finish (Priority: P2)

The local operator can increase the existing request time limit for a slow model
without switching models or reducing evidence validation.

**Why this priority**: Read-only timings suggest three 60-second judge timeouts.
**Independent Test**: Inspect effective local settings after restarting; complete
synthetic analysis is separate, deferred verification.

**Acceptance Scenarios**:

1. Given this local setup, when the API restarts, then requests allow 180 seconds
   per attempt using existing configuration and the same bounded retry count.
2. Given no local override, when configured, then defaults remain unchanged.

### Edge Cases

- Connection, read, write and pool timeouts; arbitrary text in transport errors.
- Invalid structured output, truncation, refusals, oversized input and exhausted
  transient failures; domain repair still fails, or a smaller batch succeeds.
- Cached judgments and mixed valid/invalid replies; zero accepted verdicts must
  remain distinguishable from poor fit.

## Requirements

- **FR-001**: Transport diagnostics MUST retain only fixed categories, timeout
  phase and configured limit, never private request or error text.
- **FR-002**: Judge diagnostics MUST identify phase, fixed category and batch
  counts, distinguishing server rejection from unanswered calls.
- **FR-003**: Incomplete judging MUST continue to publish no score or ranking.
- **FR-004**: Existing egress, retries, caching and contracts MUST remain unchanged.
- **FR-005**: The local timeout mitigation MUST use existing configuration only;
  tracked defaults MUST remain unchanged. Tests/lint MUST remain pending.

### Key Entities

- Transport failure: fixed category and phase, configured time limit.
- Judge diagnostic: provider/model attribution, phase and numeric counts.

## Success Criteria

- **SC-001**: Simulated timeouts and judgment rejection are identifiable without
  retaining any private test string in diagnostic output.
- **SC-002**: Missing judgments still prevent every score publication.
- **SC-003**: Local settings show 180 seconds and two retries; this is a mitigation,
  not proof that a complete analysis succeeds.

## Assumptions

The consolidated branch at aae9b24 is the dependency base; main lacks that work.
Three attempts over roughly three minutes, with no successful judge accounting
row, strongly suggest timeouts but do not prove their cause. No personal documents
are dispatched during development. Test/lint deferral persists.
