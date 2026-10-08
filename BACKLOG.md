# Backlog

Updated 2026-10-07 after reviewing all remaining PLAN items against current code,
acceptance tests and merged history. PLAN.md owns acceptance; linked specs elaborate
bounded changes. Historical delivery records live in the AI log and engineering journal.

19.1 retirement, 19.2 provider efficiency and 19.3 concurrency/progress are verified.
[Runtime verification](specs/010-runtime-verification/spec.md) reuses existing code
and adds missing lifecycle/context proof. Local lint, 825 backend tests and 192
frontend tests pass; three existing backend skips remain. The unchanged 149 SQL
contracts passed at the retirement checkpoint and on both final PR #47 CI images.
No live provider quality or production latency claim follows from these checks.

PRs [46](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/46) and
[47](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/47) are merged.
Main was clean and synchronized at `6340cd0` before the single current branch
`test/phase-19-runtime-verification`. There is one checkout; no checkpoint branch
is needed. Final PR #47 head `7ff3ac4` passed all three jobs in
[CI run 37532319038](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37532319038).
Updated-head CI remains enforced and merging is human-owned.

## Now — prove the current product

- [x] [19.1](PLAN.md#191--retire-the-competing-analysis) — retirement, populated
      preservation/deletion, uniform publications/citations and Fit/Gaps regressions.
- [x] [19.2](PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider) — provider
      reading/budgets/batching/repair/cache/profile contracts; no duplicate implementation.
- [x] [19.3](PLAN.md#193--bounded-concurrency-and-useful-progress) — bounded threads,
      real spawned-parser cleanup, cancellation, retry accounting and honest progress.
- [ ] [19.4](PLAN.md#194--prove-the-current-product) — offline benchmark executed; implement/run the complete synthetic browser journey, measure frozen
      current-model labels, prove progress-migration preservation, run security checks
      and verify startup. One Playwright journey covers the former duplicate smoke task.

The retired v1 comparison/release track is superseded. CI repair, empty migration
cycles and retirement checks are complete; they are not new pending work. The
offline benchmark has 36 successful observations and zero physical requests;
its fixture timing does not close the current-model measurement gate.

## Later — relevant or conditional follow-ups

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
