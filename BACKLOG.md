# Backlog

Updated 2026-10-06 following retirement verification and merged fit/Ask improvements. Milestone acceptance
criteria live in PLAN.md; linked feature specs elaborate only their scoped change.
The old v1 release gate and v1 comparison are superseded; historical quality
measurements remain in docs/evaluation.md.

Implementation for 19.1–19.3 is present. The human explicitly resumed validation
for [PR #43's CI repair](specs/005-pr43-ci-repair/spec.md). Local lint/typechecks,
hermetic suites and all disposable PostgreSQL integration tests pass. Repairs
cover current test contracts/fixtures, cancellation after provider responses,
evidence-deletion invalidation, citation history and repeatable migrations.
The workflow now checks synchronized and reopened heads. [CI](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37293311548)
passed lint/hermetic, PostgreSQL 16 and Supabase 17 on code head `5b8a585`.

PR #43 is merged at `8333b39`. The subsequent human-reported endless spinner is
addressed by the bounded [runtime expiry repair](specs/006-running-analysis-expiry/spec.md)
under 19.3: existing timeout enforcement, terminal-state preservation, retry
cancellation and honest batch guidance. Full local lint/hermetic checks and all
141 disposable SQL integration tests pass; broader acceptance remains open.

The bounded [requirement filters and documentation](specs/007-requirement-filters-docs/spec.md)
under 19.1 are implemented: combined status/domain-score selection, shown counts,
clear/reset and unscored handling preserve fit and evidence. Current architecture
diagrams and synthetic screenshots are refreshed; component and browser checks
pass. The merged checkpoint branch and redundant preserved worktrees were removed.
Phase 19.1 acceptance is now verified by spec 009.

[PR #44](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/44)
is merged at `ad88781`; [CI run 37301152754](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37301152754)
passed all three jobs on `08ef56b`. The human requested another PR for the
remaining plan/log checkpoint: [PR #45](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/45)
is merged at `0362666`, with all three checks green on `a1f24c2`.
Documentation-head CI remains enforced.

The bounded [fit explanation and Ask follow-up](specs/008-fit-explanations/spec.md)
is implemented under 19.1–19.3: stored earned/shortfall points, verified qualitative
experience, overall CV/JD context, asked/supported explanations and immediate Ask
status. Lint, 818 backend/192 frontend tests and 141 disposable SQL checks pass.
Synthetic Browser checks preserve point shares through filters and show pending
Ask. Reanalysis is needed for new contextual judgments; original arithmetic remains.
[PR #46](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/46) is merged at `45ae5c8`; [CI run 37525036496](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37525036496)
passed all three jobs on `d579923`. Its features are now included in the
PR #47 branch through a merge from main.
The merged checkpoint branch was removed after confirming its commits on main.

The request-schema, judge-diagnostic and recency-display regressions are included
in the passing local suites. The bounded
[19.4 benchmark implementation](specs/001-synthetic-analysis-benchmark/spec.md)
remains unexecuted. Browser, security and measured quality/latency release work
still needs its own evidence. CI success will not close all 19.1–19.4 acceptance.

Development workflow: GitHub Spec Kit is installed for bounded changes to the
existing codebase; see [the adoption guide](docs/spec-kit.md). Keep one priority list.

The complete Phase 18/19 delivery is merged in [PR #42](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/42)
at `2212790`. Superseded task branches and the merged delivery branch are removed
after verifying that all their commits are preserved on `main`. Publication,
merge and branch cleanup close no release verification gate.

[Phase 19.1 verification](specs/009-retirement-verification/spec.md) passes populated
upgrade, current consumer/citation/artifact, invalidation/reanalysis and workspace
hard-delete regressions. After incorporating merged PR #46, local lint, 818 backend,
192 frontend and 149 disposable SQL tests pass.
The migration now ends retired live jobs before erasing their identity; already-applied
revisions cannot safely recover that erased marker. The normal checkout uses
`test/phase-19-retirement-verification`; PR #46 is merged and PR #47 includes it.
There is one checkout. Only merged/preserved branches are cleanup candidates.
[PR #47](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/47) is open; [CI run 37527404818](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37527404818) passed all three jobs
on 3511aa9. The final checkpoint record receives updated-head checks.

## Now — verify one working architecture

- [x] [19.1](PLAN.md#191--retire-the-competing-analysis) — verify v1 retirement,
      current result projections, migration preservation/deletion and Fit/Gaps
      display regressions.
- [ ] [19.2](PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider) — verify
      one-call reading, provider budgets/batching, repairs, cache reuse and the
      OpenAI schema/failure-diagnostic regressions.
- [ ] [19.3](PLAN.md#193--bounded-concurrency-and-useful-progress) — verify bounded
      threads, spawned parsing, cancellation and remaining time/call accounting.
- [ ] [19.4](PLAN.md#194--prove-the-current-product) — disposable migration check,
      browser smoke, frozen-label quality/latency evaluation, release/security gate;
      local and both-image CI regression checks pass on PR #43 code head 5b8a585.
      Updated-head CI remains enforced; broader release verification stays open.

## Later

- Wire the shared Ask/MCP evidence-search and skill-experience tools to hybrid search
  and the knowledge graph instead of token-overlap retrieval.
- Persist Ask tool steps for reloaded conversations if that improves the experience.
- Remove the hermetic fixture from the user-facing provider catalogue.
- Complete durable audit retention/observability only where it helps this local tool.
- Authentication/multi-tenancy requires a separate product decision before a public
  deployment. OCR and employer screening remain outside scope.
