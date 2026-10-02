# Backlog

Updated 2026-10-02 following the human's consolidation request. Milestone acceptance
criteria live in PLAN.md; linked feature specs elaborate only their scoped change.
The old v1 release gate and v1 comparison are superseded; historical quality
measurements remain in docs/evaluation.md.

Implementation for 19.1–19.3 is present. Final verification was deferred by the
human; unchecked items include those checks, not another implementation track.
The human also authorized the bounded [19.4 benchmark implementation](specs/001-synthetic-analysis-benchmark/spec.md)
ahead of those checks. The runner and a reported retirement-migration naming repair
are authored; tests/lint, benchmark execution and migration verification stay pending.

The reported OpenAI failure is scoped in the
[19.2 request repair](specs/002-openai-request-errors/spec.md): advert format
conversion and content-free rejection diagnostics. Synthetic request acceptance
is observed; the human later completed an analysis and read-only HTTP confirmed
its ready publication. Regression and reproducible synthetic release verification
are still open.

The later scoring failure is scoped in
[19.2 incomplete-judging diagnostics](specs/003-judge-failure-diagnostics/spec.md).
Safe timeout/judge events are authored; the local timeout mitigation still needs
deferred regression verification. The human has now reported successful analysis,
and read-only HTTP confirms a ready publication. Tests/lint remain deferred.

The [19.1 recency gap display repair](specs/004-recency-gap-display/spec.md) is
implemented: valid recency gaps no longer cause the shared Fit/Gaps response to be
rejected; their current weighting factor displays as a percentage. Live response
validation and synthetic gallery diagnosis were observed; regression suites stay open.

Development workflow: GitHub Spec Kit is installed for bounded changes to the
existing codebase; see [the adoption guide](docs/spec-kit.md). Keep one priority list.

The complete Phase 18/19 delivery is collected on `feat/phase-19-analysis-delivery`
for a human-reviewed PR. Older task branches can be removed only after their
commits are preserved on that published branch. No release gate is closed by
committing, publishing or cleaning up branches.

## Now — verify one working architecture

- [ ] [19.1](PLAN.md#191--retire-the-competing-analysis) — verify v1 retirement,
      current result projections, migration preservation/deletion and Fit/Gaps
      display regressions.
- [ ] [19.2](PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider) — verify
      one-call reading, provider budgets/batching, repairs, cache reuse and the
      OpenAI schema/failure-diagnostic regressions.
- [ ] [19.3](PLAN.md#193--bounded-concurrency-and-useful-progress) — verify bounded
      threads, spawned parsing, cancellation and remaining time/call accounting.
- [ ] [19.4](PLAN.md#194--prove-the-current-product) — disposable migration check,
      browser smoke, frozen-label quality/latency evaluation, release/security gate.

## Later

- Wire the shared Ask/MCP evidence-search and skill-experience tools to hybrid search
  and the knowledge graph instead of token-overlap retrieval.
- Persist Ask tool steps for reloaded conversations if that improves the experience.
- Remove the hermetic fixture from the user-facing provider catalogue.
- Complete durable audit retention/observability only where it helps this local tool.
- Authentication/multi-tenancy requires a separate product decision before a public
  deployment. OCR and employer screening remain outside scope.
