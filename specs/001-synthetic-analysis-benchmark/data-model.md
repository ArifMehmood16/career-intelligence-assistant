# Benchmark data model

- Case: `case_id`, CV/JD document ids, bytes fingerprints and immutable text held
  solely as analysis input. Paths must remain inside their fixture subdirectory.
- Probe: thread-safe per-operation physical attempts, logical operations,
  progress attempts per task, index/cache hits and observed provider/model tags.
  No content, endpoints, credentials or provider payloads.
- Observation: case id, repetition, temperature (`cold` or `warm`), status
  (`succeeded`, `failed`, `skipped`), elapsed seconds, counts, reuse, requirement
  count, incomplete count, score/band only when publishable, safe error code.
  Elapsed time is null for skipped work; failed/skipped scores are null.
- Report: `schema_version` fixed to `analysis-benchmark-v1`, UTC timestamp, source
  revision/dirty state, analysis date, fixture/config fingerprints, provider
  capabilities/execution and actual result tags, prompt/contract/rubric versions,
  observations and per-case/per-temperature summaries. Failed observations are
  counted separately and excluded from successful-run latency percentiles.
- Repetitions: integer in [1, 20]; a fresh runtime is built per pair/repetition.
  Warm reuses cold runtime only after a complete publishable result.
