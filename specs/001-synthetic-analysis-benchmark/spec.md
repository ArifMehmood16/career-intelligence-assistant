# Feature Specification: Synthetic analysis benchmark

**Feature Branch**: `feat/phase-19-synthetic-benchmark`
**Created**: 2026-10-02
**Status**: Implementation requested; execution deferred
**Input**: Continue the development plan; keep checks deferred and implement the
synthetic benchmark. Also repair the retirement migration reported by the human.

Root ownership: [PLAN 19.4](../../PLAN.md#194--prove-the-current-product),
[BACKLOG Now](../../BACKLOG.md#now--verify-one-working-architecture).
The migration prerequisite belongs to [PLAN 19.1](../../PLAN.md#191--retire-the-competing-analysis).

## User Scenarios & Testing

### User Story 1 — Repeat an offline timing experiment (Priority: P1)

As the developer, I can benchmark synthetic document pairs twice and compare
empty-cache and reused-cache runs without credentials or network access.

**Why this priority**: A reproducible baseline is needed before paid measurements.
**Independent Test**: Run one shipped pair with deterministic fixtures and inspect
both observations, input fingerprints, timing and reuse counts.

**Acceptance Scenarios**:

1. Given no provider configuration, when I run the benchmark, then it uses only
   shipped synthetic fixtures and records zero physical API attempts.
2. Given a successful cold analysis, when the warm analysis runs, then it retains
   the same document identities, analysis date and caches and reports actual reuse.
3. Given an incomplete or failed cold analysis, when the report is emitted, then
   no successful fit is claimed, the warm run is skipped and the command fails.

### User Story 2 — Measure explicitly selected real providers (Priority: P2)

As the developer, I can opt into model measurements with the same synthetic
inputs and identify the models, prompts, operational budgets and network attempts.

**Why this priority**: Fixture timing cannot establish model performance.
**Independent Test**: Supply recorded transport responses with a retry and inspect
the attempted requests, including failures and metadata lookups.

**Acceptance Scenarios**:

1. Given a live provider selection without explicit live opt-in, when I invoke the
   command, then it rejects the selection before constructing or contacting providers.
2. Given hosted opt-in but a closed egress gate, when I invoke the command, then
   existing provider construction refuses it; no bypass or automatic fallback occurs.
3. Given a retry, when the report is emitted, then each physical request is counted
   once, separately from logical completion/embedding operations and metadata calls.

### Edge Cases

- Unknown case, escaping fixture path, invalid repeat count or malformed manifest:
  fail before model work.
- Warm retrieval still embeds queries; cache reuse must not imply zero total calls.
- Provider failures and unscoreable outputs retain attempts and elapsed duration,
  with safe error codes and no text or exception messages in the report.
- Cold means empty application caches, not an unloaded model or reset vendor cache.
- The pasted migration failure must be repaired without running a personal migration.

## Requirements

### Functional Requirements

- **FR-001**: Default execution MUST be offline and accept only named, shipped
  synthetic pairs, with no arbitrary document input option.
- **FR-002**: Each repetition MUST create fresh application caches and immediately
  repeat a successful analysis with the same caches and frozen analysis date.
- **FR-003**: The report MUST distinguish measured elapsed time, physical completion,
  embedding and metadata attempts, logical operations, and document/vector/verdict reuse.
- **FR-004**: The report MUST record input, rubric and model-configuration fingerprints,
  source revision/dirty state, provider/model/digest, prompt/contract versions,
  execution profiles and whether selected providers can send content off-machine.
- **FR-005**: Live work MUST require explicit opt-in and existing egress controls.
  Fixture results MUST be labelled as fixture measurements; fallback is disabled.
- **FR-006**: Failed/incomplete runs MUST retain observed accounting, expose no
  successful score, and cause a nonzero exit. Reports MUST exclude document text,
  prompts, responses, credentials, endpoints and raw exception messages.
- **FR-007**: JSON reports MUST have a versioned contract, predictable cold/warm
  ordering and separate latency summaries for each case and temperature.
- **FR-008**: Public application interfaces, production persistence and runtime
  architecture MUST remain unchanged. Regression tests MUST be written, with
  execution, lint and benchmark runs pending under the human's deferral.

### Key Entities

- Benchmark case: synthetic pair identity and fingerprints.
- Observation: cold/warm measurement, counts, reuse and completion status.
- Report: configuration/attribution and the observations from one invocation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every selected pair has one cold and one warm observation per requested
  repetition, including explicitly skipped warm observations after cold failure.
- **SC-002**: An offline observation reports no physical API attempts; a recorded
  retry experiment reports exactly the requests actually attempted.
- **SC-003**: Identical successful cold/warm inputs retain their score and stable
  requirement identities, and warm observations identify cache reuse.
- **SC-004**: Every report identifies its inputs and configuration without exposing
  their contents; no performance or model-quality conclusion is made before execution.

## Assumptions

- The human explicitly authorized benchmark implementation ahead of deferred
  19.1–19.3 validation; those gates remain open.
- The harness reuses the running chunk/search/judge application with explicit
  fixture index/search/cache adapters. Live runs measure model plus application
  work with fixture retrieval, not PostgreSQL performance or browser latency.
- Frozen quality labels, unsupported-match and ranking evaluation are separate
  remaining 19.4 work; historical v1 labels are not silently repurposed.
- This branch builds on the consolidated implementation and Spec Kit adoption,
  which are ahead of main. Remote references were refreshed before branching.
