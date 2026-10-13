# ADR 017 — method tracing and model-call logs

- Status: accepted by the human's 2026-10-13 request.
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
- Application services and adapters are traced with an explicit `@traced`
  decorator: `call.start`, `call.done` and `call.error` at DEBUG. Arguments and
  results are summarised by type; free text becomes `str[len=N]`. Domain code is
  not traced and stays free of logging.
- Responses are summaries only (human decision). No document text, prompt,
  question, answer, model response, embedding or credential is logged at any level.
- Terminal and file follow one `LOG_LEVEL`; the human runs locally at DEBUG.

## Consequences

The log answers "what ran, for which job, with which model, how long and with what
shape of result" without exposing private text. DEBUG is verbose by design;
INFO stays readable. Tracing costs one level check per call when DEBUG is off.
A summary that is too coarse can be refined by changing the contract's
`log_summary()`, never by logging text. Adding an excerpt option later would be
a new decision that supersedes this one.
