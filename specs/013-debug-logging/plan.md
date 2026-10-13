# Implementation Plan: Debug logging a human can follow

**Spec**: [spec.md](spec.md) · **ADR**: [017](../../docs/adr/017-method-tracing-and-model-call-logs.md)

## Design (as built)

- `logconfig.py` keeps formatting and redaction. A `log_context` context variable
  carries fields (`job_id`, `role_id`, judge `batch`) that the formatter appends
  to every line; `bind_log_context(**fields)` scopes them. Thread fan-out already
  copies context. The worker binds the job and role around each job.
- `application/providers/logging_ports.py`: `LoggingCompletion` and
  `LoggingEmbedding` decorators, applied in the provider factory, write "Calling
  model", "Model replied" and "Model call failed" lines. `StructuredCompleter`
  names the contract and attempt and logs whether the reply parsed, needed a
  repair or was cut off; contracts describe a parsed reply with `log_summary()`.
- Readable step lines are written in the code that performs each step: the v2
  runner and worker, chunker, indexer, analysis, matcher, judge, progress tasks,
  CV and cover-letter intake, the SQL role store, Ask and its agent, drafting and
  the MCP server.
- HTTP: successful GETs at DEBUG; the request line has one correlation id.
- Alembic's `fileConfig` no longer disables application loggers.

A generic `@traced` decorator was built first and removed at the human's request.
