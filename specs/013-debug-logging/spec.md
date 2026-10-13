# Feature Specification: Debug logging a human can follow

**Feature Branch**: `feat/phase-19-debug-logging`
**Created**: 2026-10-13
**Status**: In progress
**Input**: "Code-level logging to methods, inputs, method output, what started and
what finished, across all the code: which analysis, which job, which LLM was called
and what the response was (not the whole response), so humans can debug themselves."
**Root scope**: [PLAN debug logging — 2026-10-13](../../PLAN.md#debug-logging--2026-10-13),
human-requested after the 19.2 batching fix (stacked on `fix/phase-19-judge-batch-size-diagnostics`).
**Decision record**: [ADR 017](../../docs/adr/017-method-tracing-and-model-call-logs.md).

## Human decisions (2026-10-13)

- Model responses appear as **summaries only**: shape, counts, labels, tokens,
  finish reason and duration. No CV, advert, prompt or model text.
- Method tracing goes **everywhere** the level allows: terminal and file both
  follow `LOG_LEVEL`; the human runs locally at `DEBUG`.
- Amended the same day: the human wants **explicit readable lines in the existing
  code** ("extracting content from CV" with the workspace and file name), not a
  generic tracing decorator. File names, role titles and company names may be
  logged; text never.
- The batching fix ships as its own PR; this work is stacked on it.

## User Scenarios & Testing

### User Story 1 — Follow one analysis from claim to publication (P1)

Reading the log for one job, the human sees each pipeline task start and finish
with its duration, units and call counts, and every line carries the job and role.

**Independent test**: run the hermetic analysis with DEBUG logging; every line
emitted while the job runs carries `job_id=` and `role_id=`; task start/finish
events appear in order.

### User Story 2 — See every model call and what came back (P1)

Each completion and embedding call logs start and finish: provider, model, the
contract and attempt it serves, the pipeline task, input size, duration, tokens
(including reasoning tokens where the vendor reports them), finish reason and a
content-free summary of the parsed response (e.g. `verdicts=16 met=9 partial=4
missing=3`), or the failure category.

**Independent test**: scripted provider replies produce `llm.request`,
`llm.response` and `llm.structured` lines with those fields and none of the
reply text.

### User Story 3 — Readable step lines (P1, amended)

Each step of uploads, roles, the analysis, Ask, drafting and MCP says in a plain
sentence what it is doing and what came out: file names, role title and company,
ids, counts and durations.

**Independent test**: the analysis, upload, role, Ask, drafting and MCP tests
assert the sentences in order and that no document or question text appears.

### User Story 4 — Less noise (P3)

Successful `GET` requests (the UI polls `/api/roles` every 1.5 s) log at DEBUG;
writes and failures stay INFO. The request line no longer repeats `correlation_id`.

### Edge Cases

- Threads (judge batches, document indexing) keep the job context.
- Exceptions inside traced methods are logged once per frame as `call.error` and
  re-raised unchanged; the existing `log_failure` events stay.
- Generators and properties are not traced. Domain code stays silent (pure).
- Field values longer than the existing 200-character cap are still redacted.

## Requirements

- **FR-001**: Every log line emitted inside an analysis job MUST carry `job_id`
  and `role_id`, including lines from worker threads.
- **FR-002**: Every model and embedding call MUST log request and outcome with
  provider, model, operation (contract and attempt), task, sizes, duration, tokens
  and finish reason; structured replies MUST log a content-free summary.
- **FR-003**: Each step MUST log a readable start and result line in the code that
  performs it; values are ids, counts, durations, codes or human-given labels.
- **FR-004**: No log line may contain document text, prompts, questions, answers,
  model responses, embeddings or credentials (ADR 012, threat model).
- **FR-005**: Superseded with the tracing decorator (dropped 2026-10-13).
- **FR-006**: Successful GETs log at DEBUG; the request line has one correlation id.

## Success Criteria

- **SC-001**: A hermetic analysis run at DEBUG leaks none of its fixture CV or
  advert lines into the captured log, and every line during the job has `job_id`.
- **SC-002**: Full backend suite, ruff, format and mypy strict pass.
- **SC-003**: The human reruns an analysis and can follow it in the log file.

## Assumptions

Text log format stays sentence plus `key=value`. No new dependency. HTTP routes
are covered by the request middleware and the use cases they call.
