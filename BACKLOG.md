# Backlog

Updated 2026-10-08 from current code, observed acceptance tests and merged history. PLAN.md owns acceptance; linked specs elaborate
bounded changes. Historical delivery records live in the AI log and engineering journal.

19.1 retirement, 19.2 provider efficiency and 19.3 concurrency/progress are verified.
[Runtime verification](specs/010-runtime-verification/spec.md) adds missing
lifecycle/context proof; [release verification](specs/011-synthetic-release-verification/spec.md)
adds browser/startup/populated-progress evidence and scoped security review.
Local lint, 838 backend tests, 195 frontend tests and all 150 disposable SQL cases
pass; three existing backend skips remain. The complete browser journey passes.
The authorized configured OpenAI run supplies successful synthetic measurement
execution after local attempts failed before judging. Alignment gaps and null
unsupported-met rates remain explicit; no calibrated quality or production latency
pass is inferred. Detailed measurements belong in docs/evaluation.md.

PRs [46](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/46) and
[47](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/47) are merged.
Main was clean and synchronized at `6340cd0` before the single current branch
`test/phase-19-runtime-verification`. There is one checkout; no checkpoint branch
is needed. Final PR #47 head `7ff3ac4` passed all three jobs in
[CI run 37532319038](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37532319038).
PR #48 hosted-evidence checkpoint `929ee26` passes all four jobs in
[CI run 37764143176](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37764143176),
including the new browser journey. Updated-head CI remains enforced and merging is human-owned.

## Now — prove the current product

- [x] [Licensing policy](PLAN.md#licensing-policy--2026-10-08) — unchanged PolyForm
      Noncommercial with required owner notice, retained copyright and standard
      organisational permissions. Separate commercial agreements may negotiate
      fees/revenue sharing outside existing grants; no automatic revenue claim.

- [x] [19.1](PLAN.md#191--retire-the-competing-analysis) — retirement, populated
      preservation/deletion, uniform publications/citations and Fit/Gaps regressions.
- [x] [19.2](PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider) — provider
      reading/budgets/batching/repair/cache/profile contracts; no duplicate implementation.
- [x] [19.3](PLAN.md#193--bounded-concurrency-and-useful-progress) — bounded threads,
      real spawned-parser cleanup, cancellation, retry accounting and honest progress.
- [x] [19.4](PLAN.md#194--prove-the-current-product) — offline/configured OpenAI
      synthetic measurements, complete browser journey, populated progress
      preservation, private startup and scoped security review have observed proof.
      Measurement limits remain in docs/evaluation.md; local chunk failures are
      unresolved. Updated-head CI stays required before merge. One Playwright
      journey covers the former duplicate smoke task.

The retired v1 comparison/release track is superseded. CI repair, empty migration
cycles and retirement checks are complete; they are not new pending work. The
offline benchmark has 36 successful observations and zero physical requests;
its fixture timing does not close the current-model measurement gate.

## Later — relevant or conditional follow-ups

- Calibrate model quality before setting a quality threshold: human-review frozen
  labels and clause alignment, include labelled positive predictions and broader
  independent cases. Diagnose local Qwen chunk coverage if local operation is
  needed. Measurement execution is complete under [19.4](PLAN.md#194--prove-the-current-product);
  this follow-up does not reinterpret null rates as a quality pass.

- Add server-side PDF/DOCX job-description upload if needed. The current role API
  accepts description text; the UI supports pasted text and `.txt` file contents.

- Wire shared Ask/MCP evidence-search and skill-experience tools to hybrid search
  and the knowledge graph. Still relevant: `application/ask/registry.py` currently
  ranks evidence using token overlap.
- Persist Ask tool steps for reloaded conversations only if that improves the
  experience. Conditional: current history stores answers/citations, not tool steps.
- Remove the hermetic fixture from the user-facing provider catalogue. Still relevant:
  `application/providers/catalogue.py` exposes the test fixture alongside real providers.
- Complete durable audit retention/observability only where it helps this local tool.
  Conditional: provider accounting exists; a durable HTTP action audit is separate.
- Authentication/multi-tenancy requires a product decision before public deployment.
  OCR and employer screening remain outside scope; none blocks this private-tool slice.
