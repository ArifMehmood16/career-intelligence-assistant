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

### User Story 3 — Method-level tracing (P2)

At DEBUG, each traced application and adapter method logs `call.start` with its
arguments and `call.done` with duration and result, or `call.error` with the
exception type. Arguments and results are summarised: ids, enums, numbers, sizes,
lengths and hashes, never free text.

**Independent test**: a traced function given an id, an enum, a long string and a
dataclass logs the id/enum verbatim, `str[len=N]` for the text, and the dataclass's
ids; nothing is emitted, and no summary is built, above DEBUG.

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
- **FR-003**: Traced methods MUST log start, finish (duration, result summary) and
  error (type) at DEBUG, with argument summaries that never contain free text.
- **FR-004**: No log line may contain document text, prompts, questions, answers,
  model responses, embeddings or credentials (ADR 012, threat model).
- **FR-005**: With the level above DEBUG, tracing MUST NOT build summaries.
- **FR-006**: Successful GETs log at DEBUG; the request line has one correlation id.

## Success Criteria

- **SC-001**: A hermetic analysis run at DEBUG leaks none of its fixture CV or
  advert lines into the captured log, and every line during the job has `job_id`.
- **SC-002**: Full backend suite, ruff, format and mypy strict pass.
- **SC-003**: The human reruns an analysis and can follow it in the log file.

## Assumptions

Text log format stays `key=value`. No new dependency. Tracing is applied to
application services and adapters by explicit decorators; HTTP routes are covered
by the request middleware and the use cases they call.
