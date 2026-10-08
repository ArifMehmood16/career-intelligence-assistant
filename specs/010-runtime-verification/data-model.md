# Existing values and lifecycle

No schema, entity or wire-format change.

- UploadDocument is immutable bytes plus filename/kind/media type/admission limits.
  Only this value crosses the spawned parser boundary.
- ProcessUploadParser lazily creates its bounded pool; timeout/crash closes it and
  returns DOCUMENT_UNREADABLE. Later binary input may recreate a pool. Plain text
  stays inline; repeated close is safe.
- Progress tasks retain existing planned/done physical model and embedding counts.
  Retry increments plan and completion; cancellation before dispatch adds no attempt.
- Test PID markers contain only child identifiers in temporary synthetic files.
  Tests verify process exit and close every pool in finally/context cleanup.
