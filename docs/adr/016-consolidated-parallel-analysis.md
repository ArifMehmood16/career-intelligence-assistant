# ADR 016 — consolidate analysis and tune execution per provider

- Status: accepted by the human's 2026-10-02 development request.
- Supersedes: ADR 010/011 extraction/assessment runtime and the old staged v1
  retirement gate. ADR 013/014/015 evidence, aggregation and shared-tool boundaries
  remain applicable.

## Decision

Remove the alternate span classifier/assessor pipeline and pipeline selector now.
Keep one model-defined chunk, hybrid-search, model-judge and domain-aggregation
analysis. Current views and generated-artifact inputs project those stored results;
shared value objects remain only where useful. Define a migration to retire old
storage and stale analyses while preserving original uploads and current results.
Do not apply the migration to a personal database during development.

Combine document structure/detail/technology-relation extraction into one structured
response. Batch judgments and corrected judgments within actual model budgets.
Independent I/O uses bounded threads; CPU-heavy binary parsing uses spawned
processes. Preserve thread context for progress, cancellation and accounting.
Use native embedding batches and cache identity rather than warm-up/probe calls.

Separate Ollama/OpenAI/Anthropic modules own provider payloads. Execution profiles
configure per-model context/output/concurrency instead of a smallest-provider
ceiling. Larger hosted models may use their larger output capacity. Rate headers
and the existing hosted egress gate still apply. No new service/dependency is added.

## Consequences

One maintained matching/scoring behavior removes duplicate work and consumers no
longer find empty legacy tables. Old tests solely exercising the retired pipeline
are removed together with it; current evidence/citation/groundedness contracts remain.
Historical evaluation remains available but is not a quality claim for the new path.
The human explicitly waived comparison-before-retirement, not current evaluation.

Physical call counts and estimated remaining time are visible. Undiscovered work,
repairs and approximate token sizing keep those estimates honest. Larger requests
reduce repeated context but can cost more per failed response; bounded fallback
and validation remain necessary. A local model's safe concurrency depends on its
hardware and configuration, so the default is conservative and tunable.
