# ADR 017 — readable step logs and model-call logs

- Status: accepted by the human's 2026-10-13 request; amended the same day.
- Extends: ADR 012 (durable operational audit) field contract to process logs.

## Context

The application log had request lines, a few worker events and judge diagnostics.
A failed analysis showed one minute of silence between claim and the first judge
event, and no line said which model was called, how long it took or what it
returned. The human wants to debug from the log alone: what ran, for which job,
with which inputs and outputs, and what each model call returned.

## Decision

- Every line inside an analysis job carries `job_id` and `role_id` from a context
  variable, so thread fan-out keeps them.
- Every completion and embedding call logs `llm.request` and `llm.response` (or
  `llm.failed`) at INFO: provider, model, operation (contract and attempt), task,
  sizes, duration, tokens including reasoning tokens, finish reason. Structured
  replies log `llm.structured` with a summary built by the contract itself
  (counts, labels and scores only).
- Each step says what it is doing and what came out, as a plain sentence written
  in the existing code (for example "Reading CV into chunks" then "Read CV into
  chunks ... chunks=20"), with ids, counts, durations and labels as fields. Domain
  code stays free of logging; its callers log the result.
- A generic `@traced` decorator (call.start/call.done for every method) was built
  and dropped the same day: the human asked for explicit, readable lines instead.
- Labels the human typed or uploaded may be logged: CV and cover-letter file
  names, role titles and company names (human decision, 2026-10-13).
- Responses are summaries only (human decision). No document text, prompt,
  question, answer, model response, embedding or credential is logged at any level.
- Terminal and file follow one `LOG_LEVEL`; the human runs locally at DEBUG.

## Consequences

The log answers "what ran, for which job, with which model, how long and with what
shape of result" without exposing private text. A new step needs its own lines;
nothing is logged automatically. File names, titles and company names now sit in
the local log file.
A summary that is too coarse can be refined by changing the contract's
`log_summary()`, never by logging text. Adding an excerpt option later would be
a new decision that supersedes this one.
