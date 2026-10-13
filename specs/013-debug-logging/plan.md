# Implementation Plan: Debug logging a human can follow

**Spec**: [spec.md](spec.md) · **ADR**: [017](../../docs/adr/017-method-tracing-and-model-call-logs.md)

## Design

- `logconfig.py` keeps formatting and redaction. A `log_context` context variable
  carries extra fields (`job_id`, `role_id`) that the formatter appends to every
  line; `bind_log_context(**fields)` scopes them. Existing thread fan-out already
  copies context.
- `tracing.py` (new, stdlib only): `traced` decorates a function or every public
  method of a class; `summarize(name, value)` turns any argument or result into a
  short content-free description. Strings are shown only when they are UUIDs, hex
  digests or values of known identifier parameters; everything else is `str[len=N]`.
- `application/providers/logging_ports.py`: `LoggingCompletion` and
  `LoggingEmbedding` decorators (the same pattern as accounting), applied in the
  provider factory so every caller gets them. `StructuredCompleter` sets the
  current operation (contract and attempt) for them and logs the parse outcome
  with the contract's `log_summary()`.
- Analysis tasks: `TrackedProgress` logs `task.start` / `task.done` /
  `task.skipped` with duration, units and calls. The worker binds the job
  context at claim.
- HTTP: successful GETs at DEBUG; drop the duplicated `correlation_id` field.

## Order (one TDD cycle per behaviour, commit each green step)

1. Context fields on every line.
2. `summarize` rules; `traced` start/done/error; no work above DEBUG.
3. HTTP noise and duplicate field.
4. `LoggingCompletion` / `LoggingEmbedding` and factory wiring; reasoning tokens.
5. Structured outcome events and contract summaries.
6. Task events and job context at claim.
7. Apply `traced` across application services and adapters.
8. Privacy regression over a full hermetic analysis at DEBUG; docs.
