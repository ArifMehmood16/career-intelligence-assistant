# Backlog

Updated 2026-10-02 following the human's consolidation request. Milestone acceptance
criteria live in PLAN.md; linked feature specs elaborate only their scoped change.
The old v1 release gate and v1 comparison are superseded; historical quality
measurements remain in docs/evaluation.md.

Implementation for 19.1–19.3 is present. Final verification was deferred by the
human; unchecked items include those checks, not another implementation track.

Development workflow: GitHub Spec Kit is installed for bounded changes to the
existing codebase; see [the adoption guide](docs/spec-kit.md). Keep one priority list.

## Now — verify one working architecture

- [ ] [19.1](PLAN.md#191--retire-the-competing-analysis) — retire v1 code, selector,
      legacy result reads and storage; one frontend path.
- [ ] [19.2](PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider) — one-call
      document reading, provider-specific batching, batched corrective judging and
      embeddings, cache reuse.
- [ ] [19.3](PLAN.md#193--bounded-concurrency-and-useful-progress) — bounded threads,
      spawned parsing workers, estimated remaining time and physical API calls.
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
