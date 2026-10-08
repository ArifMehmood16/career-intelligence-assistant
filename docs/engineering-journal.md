# Engineering journal

One entry per phase checkpoint. Commands actually run and outcomes actually observed.
Nothing predicted, nothing rounded up.

## Template

```text
## Phase N — <name>

- Date:
- Commands run:
- Observed result:
- Decisions made:
- Problems hit and how they were resolved:
- Carried forward:
```

## Entries

## Phase 19.4 — Configured OpenAI measurement continuation

- Date: 2026-10-08. Human requested configured OpenAI from the project directory
  after isolated local failures. Ran existing quality/live benchmark from root;
  exact command and safe original report are in docs/evaluation.md.
- Observed: process exits 0; every frozen cold/warm observation succeeds with
  complete verdicts. Configured gpt-5-mini/text-embedding-3-small attribution shows
  off-machine synthetic input, fallback false; original source clean 46650d0.
  Report bytes, label-file hash, provider attribution and transport totals checked.
- Decision: close root measurement execution, which has no numeric quality
  threshold. Keep clause-alignment gaps, null unsupported-met rates and narrow
  ranking sample explicit in evaluation.md; human calibration remains future work.
  Do not retune labels/prompts, relax validators or erase local failure reports.
- Scope: no application server/database or private uploads used. Normal settings
  loaded, no secret file modified. This report is model/application work with
  fixture retrieval, not SQL/browser latency or an end-to-end hosted deployment.
- Delivery: continue same PR #48/branch. Production source unchanged; prior full
  checks and four green CI jobs at 46650d0 remain applicable. Observe updated-head
  CI after committing this evidence before declaring the delivery checkpoint.


## Phase 19.4 — Delivery checkpoint

- Date: 2026-10-08. Same PR #48 title/description updated to final scope; pushed
  test/phase-19-runtime-verification without rewriting history or merging.
- Observed checkpoint 99c86d1 passes all four jobs in CI run 37761425946:
  lint/typecheck/hermetic, PostgreSQL 16, Supabase Postgres 17 and browser journey.
- All spec 011 implementation/delivery tasks have observed evidence. The broader
  root model-quality gate stays open because both local models failed before
  judging. Frozen development labels still require human calibration for thresholds.
- Complete branch whitespace review passes after license formatting normalization;
  106 changed-document local file links resolve. Temporary Compose services/volume
  and standalone API/disposable database containers were removed; no extra checkout
  or redundant branch remains. Final checkpoint edits are documentation only.


## Phase 19.4 — Local model attempts and final regression checks

- Date: 2026-10-08. Exact isolated commands and safe original reports are in
  docs/evaluation.md. Shipped synthetic adjacent CV/partial and poor jobs only;
  frozen labels preceded calls. Hosted gate/fallback false, keys blank, no personal
  dotenv or database used. Models qwen2.5:7b and qwen2.5:14b, local nomic selection.
- Observed: both commands exit 1. Each model has two failed cold and two skipped
  warm observations; chunk validation still fails after repair. A metadata-only
  diagnostic confirms two remaining structural problems. No score/band, successful
  quality count or ranking comparison; the root model-quality gate remains open.
- Original reports precede tuning. A later bounded adjacency/coverage prompt
  clarification still failed on both cases and was fully reverted. No profile/label
  change or complete-line validation relaxation shipped. Failure
  reports retain physical calls, source/input/label/prompt/model provenance; no
  raw response, prompt or exception payload was logged or saved.
- Final checks: make lint passes; make test passes 838 backend/195 frontend,
  three existing skips, 85.22% coverage. Disposable SQL suite passes 150. Full
  browser rerun passes after adding explicit role deletion before CV deletion.
- Branch review: inspected changed startup/build, browser, intake, benchmark and
  dependency code for unrelated changes, egress and unnecessary abstractions.
  Same branch/PR #48; no extra branch, worktree, force push or merge.


## Phase 19.4 — Scoped security review

- Date: 2026-10-08. Commands: make security-dependencies security-secrets;
  backend/.venv/bin/bandit -r backend/src -f json; npm audit --json from frontend.
- Observed: both Python lock audits pass; full frontend Bun audit (446 packages)
  and browser-runner Bun audit (26 packages) pass; npm audit reports zero advisories.
  Trivy HIGH/CRITICAL dependency scan finds none; redacted Gitleaks finds none.
  Container scans use committed tracked files at f7344a9, including runner/fonts
  and both synchronized frontend locks, excluding ignored configuration/uploads.
- Source: Bandit reports 22 findings (three medium, nineteen low), reviewed in
  docs/threat-model.md by exact site/group. Constant SQL templates, private container
  bind, fixed command vectors, internal invariants and result enum are justified.
  No suppression/baseline was added; Bandit and aggregate make security remain
  nonzero. No SonarQube or image-OS scan claim.
- Control repair: make security container inputs now come from git archive HEAD;
  Gitleaks redacts instead of verbose source output, Trivy explicitly scans
  vulnerabilities only. Commit intended changes before this tracked-source scan.
- Compatibility: latest make test passes 838 backend and 195 frontend tests,
  three existing skips, reported coverage 85.22%; new quality module has 100%
  statement/branch coverage. Earlier make lint and 150 SQL/browser checks pass.
- Carried forward: local-model measurement results and updated-head CI.


## Phase 19.4 — Browser, startup and populated progress acceptance

- Date: 2026-10-08. Commands: make lint; make test; make test-integration with
  distinct disposable application/test URLs on port 55444; make test-e2e with a
  dedicated loopback *_e2e database; e2e bun run typecheck and bun audit.
- Observed: lint passes; 827 backend and 195 frontend tests pass, three existing
  skips, reported coverage 85%; all 150 SQL tests pass. Browser journey passes:
  upload, text-file role, Fit filters/evidence, Prepare quote, persisted cited draft,
  streamed Ask/source, reload and own workspace cleanup. Zero external browser requests.
- Defects: job-file control submitted its filename and discarded retry input;
  focused red assertions reproduced both. Original API image import failed with
  missing scoring_rubric.toml. Packaging now preserves TOML/source/migrations and
  startup migrates before serving; full fresh Compose stack reaches ready and
  completes analysis through the production web proxy. Final API shutdown exits 0.
- Browser regression initially completed product flows but caught Google Fonts
  egress. Self-host the same licensed faces/weights, preserving original OFL notices;
  the external-request assertion now passes. No new design tokens or typography.
- Progress migration: real populated c1 -> b2 upgrade preserves documents, jobs,
  task timestamps/counts, scores, drafts and citations; added counters default to
  zero/unknown and reject invalid counts. Test finally restores migration head.
- Tooling: Playwright is a test-only dependency because DOM component checks cannot
  prove browser/proxy/SQL persistence. CI adds an isolated synthetic browser job;
  failure artifacts contain only test fixtures and expire after seven days.
- Carried forward: local-model quality and final scoped security results. No paid
  providers, personal database migration or SonarQube server scan claimed.


## Phase 19.4 — Offline benchmark evidence

- Date: 2026-10-08; measurement executed 2026-10-07.
- Command: make benchmark BENCHMARK_ARGS='--repetitions 3 --output /private/tmp/career-analysis-offline-20261007.json'.
- Observed: 36 successful synthetic observations, zero physical provider requests,
  clean source 9c2f27e, fixture-only retrieval. Safe report saved under
  docs/evaluation-results/offline-2026-10-07.json; cache/call/timing provenance verified.
- Decision: close offline execution only; local model quality, SQL/browser latency,
  startup, populated progress preservation and security need separate evidence.
- Continuation: specs/011-synthetic-release-verification defines 21 linked tasks;
  seven requirements/five success criteria covered, all five specification checklist
  items pass, no blocking consistency finding. No extension hooks installed.


## Phase 19.2–19.3 — Plan reconciliation and runtime acceptance

- Date: 2026-10-07
- Trigger: human requested review of remaining done/stale/redundant work before
  continuing development. Spec Kit record: specs/010-runtime-verification.
- Audit: provider reading/budgets/native batches/repair/cache/profiles and bounded
  concurrency were already implemented. Missing acceptance proof concerned real
  parser failure/shutdown and combined thread cancellation/progress/accounting.
  Added seven regressions without changing production code or dependencies.
- Commands/results: provider command in spec quickstart passes 185 tests; runtime
  command passes 55, including real spawned timeout/crash/close/recreation and both
  application lifespan branches. Focused lifecycle/context suite passes 13.
  make lint passes Ruff/format/mypy/TypeScript/ESLint; make test passes 825 backend
  and 192 frontend tests, three existing skips and reported total coverage 85%.
  The existing Starlette/AnyIO deprecation warning is unchanged.
- SQL: no persistence/migration change, so local SQL was not rerun. The unchanged
  149 SQL contracts passed at spec 009 and final PR #47 CI on both database images.
  Final-head CI remains enforced for this branch.
- Disposition: close proven 19.2/19.3 gates; consolidate duplicate browser-smoke
  work into one complete Playwright journey. Separate unexecuted offline benchmark,
  current-model quality, progress-migration preservation, security and startup
  proof. Keep Ask hybrid retrieval/test-provider catalogue work relevant and
  tool-history/audit retention conditional on user value.
- Delivery state: PRs 46/47 merged; main synchronized at 6340cd0 before creating
  one task branch. Human-added npm lock untouched; historical logs preserved.
- Review: inspect complete branch diff, immutable test-only uploads, bounded cleanup
  and exact accounting; no new egress/storage/API boundary. Ruff/mypy pass; no
  SonarQube server scan is claimed. No paid provider call or personal database used.

## Phase 19.1 — Integrate merged PR #46 into PR #47

- Date: 2026-10-06
- Trigger: human merged PR #46 at 45ae5c8; GitHub reported PR #47 conflicting.
- Resolution: git fetch origin; git merge --no-commit origin/main on the existing
  PR #47 branch. Retained both documentation/development histories, verified
  retirement completion, score arrows/context/Ask features and expanded usage.
  Replaced conflicted screenshots with fresh merged-gallery captures; retained the
  existing processing image and current unaffected captures. No new runtime behavior.
- Checks: make lint passes; make test passes 818 backend and 192 frontend tests,
  three existing skips, 84.70% coverage. Explicit disposable database URLs on port
  55443 isolate make test-integration; all 149 cases pass. Source automatically
  merges; manual resolution is confined to docs/screenshots. Local link checks and
  conflict-marker/diff checks precede commit; updated-head CI is checked after push.
- Boundaries: no force push, history rewrite, paid model invocation or personal
  migration. Existing untracked frontend/package-lock.json is left untouched.
  The human still owns PR #47 review/merge. Remaining release gates stay open.


## Phase 19.1 — Same-PR documentation and screenshot refresh

- Date: 2026-10-06
- Scope: user-requested follow-up on PR #47, same canonical checkout/branch.
- Changes: README system diagram and detailed execution, publication/evidence,
  lifecycle and retirement diagrams; practical usage guide and nine synthetic
  screenshots, including new Letter/Ask captures. Corrected audit-storage scope.
  Gallery-only props/layout adjustments resolve the Letter source glossary and
  contain the completed chat's sticky composer. No design token or production
  route/provider/storage change.
- Commands/results: focused gallery Vitest passes; final make lint passes Ruff,
  format, mypy, TypeScript and ESLint; make test passes 810 backend and 180 frontend
  tests, three existing skips. Local links/images resolve. All nine final captures
  were inspected; clipped initial captures were replaced before staging.
- SQL integration: no persistence change in this follow-up; the 149 disposable SQL
  cases passed at the preceding checkpoint. Updated-head CI includes both database
  jobs again; its outcome will be observed after push, not predicted here.
- Boundaries: no personal document/provider capture or paid model invocation.
  Synthetic UI screenshots do not close full backend browser journeys or quality,
  performance, security and deployment gates. PR #46 remains separate; no merge.

## Phase 19.1 — Populated retirement and publication verification

- Date: 2026-10-06
- Scope: specs/009-retirement-verification; branch test/phase-19-retirement-verification,
  created from main 0362666 in the normal single checkout. PR #46 stays separate/open.
- Commands: Spec Kit resolve/setup/prerequisite and read-only artifact analysis;
  focused pytest migration/worker/architecture tests; disposable PG17 on port 55443
  with explicit distinct DATABASE_URL/TEST_DATABASE_URL; make lint, make test,
  make test-integration; focused post-refactor migration cycles; Bandit on the
  changed retirement migration; complete source/test diff and git diff --check.
- Red evidence: old queued jobs remained queued and a role with a valid current
  publication stayed analysing. Initial seed-version collisions were fixture errors,
  corrected before this behavioral red evidence. Upgrade now terminalizes only
  v1 live jobs, resolves roles while their marker exists and preserves v2 live jobs.
- Green evidence: 16 focused migration/schema/deletion cases and five migration/worker
  unit cases passed; 10 focused publication/preservation/MCP cases passed. Full lint
  and typechecks passed; 810 backend tests, 180 frontend tests, three existing skips,
  84.65% coverage and all 149 disposable SQL integration tests passed. Four focused
  SQL migration/cycle tests passed after static-SQL refactoring; three preservation
  tests passed after final fixture scope review.
- Consumer checks: stored score/components, gap projections and statuses agree;
  reads call no provider. Ask grounding uses stored score/band. Interview/bullet/letter
  generation and persisted citations resolve to uploaded text; exports work.
  Invalidation refuses consumers; reanalysis retains stable JD IDs but removes old
  CV chunks. Workspace deletion covers all mapped scoped tables and preserves another
  workspace. Historical upload/current-row snapshots match exactly through upgrade.
- Review: source inspection finds no executable v1 or production selector; shared
  score/citation/draft wire values remain useful. Bandit initially flagged seven fixed
  schema SQL interpolations; literal SQL removes all findings without suppression.
  Sonar scanner unavailable; manual security/design/diff review completed. No dependency,
  public API, trust boundary, paid provider or personal-database change.
- Decisions/limits: preserve the accepted ADR 016 architecture. Do not fail legitimate
  current jobs by guessing historical origin after applied migration identity erasure.
  This migration correction protects still-pending upgrades only. Browser release,
  provider efficiency, concurrency and quality/latency/security gates remain open.
- Delivery commits: 1a4e01e migration repair and populated regressions; 4252c6c publication
  consumers/deletion; 7b94331 static SQL; edbc145 workspace-scoped historical fixture.
  [PR #47](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/47) is open and attached. [CI run 37527404818](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37527404818)
  passed lint/typecheck/hermetic, PostgreSQL 16 and Supabase Postgres 17 on 3511aa9.
  The disposable server was stopped; one checkout remains with main and the two
  open PR branches. This final delivery record receives its own updated-head CI.
  No merge or removal of an unmerged feature branch was performed.

## Phase 19.1–19.3 — Fit explanations and Ask processing

- Date: 2026-10-06
- Scope: [spec 008](../specs/008-fit-explanations/spec.md), human-requested before
  broader release gates; Spec Kit research/analyze completed before implementation.
- Change: original publication weights project earned/possible/shortfall points;
  accessible green/red arrows; verified qualitative experience and overall CV/JD
  context in existing judge requests; context-sensitive cache/budget; asked/supported
  labels. Ask shows immediate processing, receiving and history refresh, with
  identity guards protecting successive requests after stop.
- Verification: behavioral red/green regressions; full make lint/test (818 backend,
  192 frontend, 84.70% coverage, 3 existing skips); 141 disposable PostgreSQL
  integration tests. No personal database or hosted development call. Bandit on
  18 changed backend modules reported no findings; manual branch/design/security
  review completed, Sonar scanner unavailable.
- Browser: synthetic arrow colors, numeric/qualitative explanations, Missing/low
  and Met/high filtering preserve point attribution and fit; pending Ask shows Stop.
  Four current JPEGs were captured and visually checked. Architecture diagram,
  ADR 014, README, API/product/usage docs and root scope were reconciled with code.
- Commits: 47d11cd, 53d414e, 5f291ea, 1b76dcc, b45590e.
- Delivery: PR #45 is merged at 0362666; canonical checkout has synced main plus
  feat/phase-19-fit-explanations. No worktrees or redundant local branches remain.
  [PR #46](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/46) is pushed/open and attached.
  [CI run 37525036496](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37525036496) passed all three
  jobs on d579923. The final documentation checkpoint receives updated-head CI;
  the agent performed no merge.
- Carried forward: reanalysis is needed for new judgments; larger interpretive
  context uses the existing capacity bound and may reduce batch size. No semantic
  model-quality claim follows from fixtures. Broader browser journeys, dependency/
  release scans and measured quality/latency remain open under 19.1–19.4.

## Phase 19.1 — Requirement filters and documentation refresh

- Date: 2026-10-05
- Commands run: Spec Kit scope/design/task analysis; focused red/green Vitest;
  frontend lint/typecheck; make lint; make test; Browser synthetic gallery
  interactions and screenshots; git diff origin/main...HEAD; git diff --check;
  git branch/worktree inspection, explicit commits and push.
- Observed result: red tests lacked the new controls. All 25 focused tests and
  full lint/typechecks passed. Full tests passed: 810 backend, 180 frontend,
  3 existing skips, 84.65% backend coverage. The first streaming fixture run
  could not bind under the sandbox; local socket permission made the full gate
  pass without modifying tests. Existing runtime repair verification covers
  all 141 disposable PostgreSQL integration cases; SQL code did not change again.
- Browser evidence: Missing with 0–24% showed one requirement; Met with 75–100%
  showed one; Met with 0–24% showed the distinct empty message; Clear filters
  restored all three. Seven current synthetic JPEGs were visually inspected.
  README system architecture and detailed pipeline/job-lifecycle diagrams now
  describe the SQL worker, spawned parsing, provider boundaries and publication.
- Decisions: filter stored domain scores as displayed whole percentages; keep
  null separate from zero and preserve overall fit, evidence and order. Reuse
  existing controls/tokens without a new dependency or API. Document fixture
  provenance explicitly; screenshots are not model-quality measurements.
- Delivery: 2b15940 contains filters/tests; 08ef56b contains current docs/screenshots.
  [PR #44](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/44)
  is merged at ad88781 and attached. [CI run 37301152754](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37301152754)
  passed all three jobs on 08ef56b. All three Mermaid diagrams rendered on GitHub.
  The human merged before final plan/log commit 0543da2 arrived and requested a
  new PR for the remaining docs. Main is synced to ad88781; the normal checkout
  uses docs/phase-19-current-checkpoint. Only these two branches remain locally.
  Temporary worktree and redundant preserved branches were removed. The disposable
  verification database was stopped; agent-created Browser tabs were closed.
  [PR #45](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/45)
  is open/attached for the remaining docs and receives its own head CI.
  pytest tests/unit/test_production_wiring_matrix.py --no-cov passed afterward.
- Review: complete source/test diff and whitespace inspected; Sonar scanner
  unavailable. No personal data writes or paid provider calls. Broader synthetic
  browser journeys, security/dependencies and measured release gates remain open.

## Phase 19.3 — Runtime expiry and batch progress

- Date: 2026-10-05
- Commands run: read-only job metadata; Spec Kit setup/prerequisites and scope
  analysis; focused red/green worker, resilience and component regressions;
  make lint; make test; make test-integration using two distinct disposable URLs
  on port 55443; Bandit on the three changed backend modules; git diff --check.
- Observed result: red blocked-provider tests left the job running past expiry;
  red terminal tests raised on late failure; red retry test dispatched after
  cancellation; red component tests lacked batch guidance and retained animation.
  After repair, 33 focused backend tests, 14 worker SQL tests and 10 progress UI
  tests passed. Full checks passed: 810 backend tests, 172 frontend tests, all
  141 PostgreSQL integration tests, unchanged coverage gate, lint/typechecks.
  Changed-module Bandit passed. Sonar scanner is unavailable; branch source/test
  diff was reviewed for privacy, bounded concurrency and complexity.
- Decisions: preserve selected model and existing 15-minute total limit; recover
  during the live worker loop using existing row locks and domain transitions.
  An already dispatched HTTP request cannot be forcibly stopped, but its result
  is discarded and subsequent retries check cancellation. Keep counters honest.
- Diagnosis limit: metadata confirms missing runtime expiry; it does not prove
  why the earlier provider request failed to finish. No paid development calls or
  personal database writes. Broader release/security/latency checks remain open.
- Commits: f6003c7 worker expiry and a39e583 batch progress. An isolated worktree
  protected the human's active analysis during implementation; consolidation and
  branch publication follow the human's request.

## Phase 19 — PR #43 CI repair

- Date: 2026-10-05
- Commands run: gh pr/run inspection and failed-run logs; Spec Kit setup and
  prerequisite scripts; pytest collection and focused red/green regressions;
  Ruff formatting/checks, mypy, TypeScript and ESLint via make lint; full make test;
  disposable PostgreSQL initdb/pg_ctl/createdb and make test-integration with
  explicit distinct URLs; repeated migration regression; git diff --check;
  explicit staging/commit/push; gh pr edit.
- Observed result: original run 37037340374 stopped at lint and five collection
  errors. Current local checks pass: 809 backend tests, 169 frontend tests,
  135 SQL integration tests and the unchanged coverage gate. [GitHub run 37293311548](https://github.com/ArifMehmood16/career-intelligence-assistant/actions/runs/37293311548) passed all three jobs on code head 5b8a585. First run 37292814674 passed PostgreSQL 16 and
  lint/typechecks; Supabase failed exact float read-back and role switching, and
  hermetic tests found documentation missing from the initial push. Reproduced
  reduced float precision locally, repaired connection defaults and explicit
  probe membership, and included the missing docs. All local suites pass again.
- Problems resolved: stale imports/contracts; missing fixture terms/undated
  experience; provider responses written after cancellation; scores remaining
  readable after evidence deletion; UUID-only history citation labels; vector
  type lookup failing after pgvector moves to extensions during migration cycles.
- Decisions: retain bounded parallel I/O and allow already-started calls while
  prohibiting new dispatch after deletion; preserve all gates and synthetic
  evidence verification. The disposable cluster uses port 55443 and UTF-8;
  the personal application configuration/database was not used.
- Carried forward: final documentation-head CI and human PR review/merge;
  finish separate browser/security/quality/latency release work. No model-quality
  or complete-release claim follows from these regression checks.

## Phase 19 — Delivery documentation and publication

- Date: 2026-10-02
- Commands run: Git status/history/ref and worktree inspection; `git fetch origin
  --prune`; `gh pr list --state all`; branch rename to
  feat/phase-19-analysis-delivery; source/document reads and documentation diff review;
  `git diff --check`; explicit staging and documentation commit `1c9a4e6`;
  `git push -u origin feat/phase-19-analysis-delivery`; `gh pr create --draft`;
  `gh pr view 42`; PR artifact attachment; `git merge-base --is-ancestor` and
  `git rev-list --count` for every cleanup ref; `git branch -d` and remote deletion.
- Observed result: at the start Phase 18/19 work was unmerged, there were no open
  PRs and only the active checkout used a branch. README, PLAN/BACKLOG and troubleshooting/limitations
  docs now distinguish the later successful analysis and recency diagnosis from
  pending regression and measured release work. [Draft PR #42](https://github.com/ArifMehmood16/career-intelligence-assistant/pull/42)
  is open against main and attached to the chat. Each superseded ref had zero
  unique commits outside the published delivery head. Five local and four remote
  branches were deleted; all their work remains in the delivery branch.
- Decisions made: preserve accumulated commit history in one delivery PR; keep it
  draft while checks are deferred. Publication/branch cleanup is explicitly
  authorized; merging remains the human's decision.
- Verification: documentation/source review and whitespace/ancestry inspection;
  no local tests/lint/typecheck, benchmark, migration, model call or security scan.
  GitHub CI started automatically on PR creation; the first observed snapshot was
  in progress. `gh run list`/`gh run view` subsequently confirmed the creation run
  on `1c9a4e6` failed lint/typecheck and both integration steps; hermetic tests were
  skipped. Later heads have no attached checks because the workflow only triggers
  on opened. Root PLAN/BACKLOG now record failure triage and trigger coverage.
  Whole-branch whitespace inspection found an inherited trailing blank line in
  candidate_spans.py; removal changes no behavior. No root gate closed by these
  observations. During final verification GitHub reported PR #42 externally merged
  at `2212790` and its remote head deleted. Fetched/pruned remote refs, fast-forwarded
  local main, checked merged delivery ancestry and deleted its local branch.
  A documentation follow-up starts from updated main on
  docs/phase-19-merged-checkpoint; the agent performed no merge.
- Carried forward: explicitly resume local checks, review CI results and execute
  the disposable migration/browser/quality/latency release work before release.

## Phase 19.1 — Recency gap display repair

- Date: 2026-10-02
- Commands run: branch creation from 5e67682; Spec Kit setup/prerequisite scripts;
  read-only local HTTP response inspection; Bun calls of actual roleVerdictsSchema
  against API and same-origin web proxy; targeted `bunx --no-install prettier
  --write`; source/diff review and local commit. Browser DOM/screenshot inspection
  used the local synthetic /dev/states gallery.
- Observed result: ready role publishes 18 verdicts. Before repair, eight gap
  dimension fields fail client validation as invalid_value. Their fixed value is
  recency, already supported by the domain. After repair both API and proxy HTTP
  200 responses pass the client schema: 18 verdicts, 9 gaps, 8 recency gaps.
  The synthetic gallery renders Evidence recency · current weight 60% and a
  Match · now 1 / 4 gap. A synthetic screenshot is outside Git.
- Decisions made: preserve judge anchors and server arithmetic; extend only the
  frontend gap category/type and show recency percentage weight. API/product docs
  disagreed with domain code and are corrected. Existing layout/tokens reused;
  no new visual pattern, backend behavior, model call, DB write or dependency.
- Verification: focused API/container/panel/gallery regressions authored, not run;
  tests/lint/typecheck/security and release checks remain deferred. Live diagnosis
  is not a passing release/quality gate. No raw personal content printed or saved.
  Source privacy/design review performed; no Sonar scan.
- Carried forward: refresh or Retry the existing publication after frontend reload;
  no reanalysis needed. Complete deferred checks when authorized.

## Phase 19.2 — Incomplete judge diagnostics

- Date: 2026-10-02
- Commands run: branch creation from aae9b24; Spec Kit template/setup/prerequisite
  scripts; read-only local job HTTP and successful-call accounting SQL reads;
  non-secret ProviderSettings inspection; targeted `ruff format`; source/diff
  review and local commit. Official OpenAI reasoning/model documentation fetched.
- Observed result: 18 requirements searched/handled, three physical judge calls,
  no successful judge accounting row. Embedding completed 16:06:47 UTC and the
  job failed 16:09:49 UTC. Configured limit was 60 seconds/two retries. The local
  ignored configuration now loads 180 seconds/two retries; no default change.
- Decisions made: suspected timeout mitigation plus fixed transport/judge log
  categories and numeric counts; retain incomplete-publication safeguard, current
  model and retry behavior. Do not print exception messages or validation details.
- Verification: regressions authored, not run. Tests/lint/typecheck/security,
  benchmark and complete analysis remain deferred. No personal model dispatch,
  DB mutation or release/quality claim. Main includes inherited consolidation;
  bounded source diff reviewed against aae9b24. No Sonar scan performed.
- Carried forward: restart API to load settings, human retry and preceding safe
  diagnostic events if failure persists. Timeout cause remains inferred.

## Phase 19.2 — OpenAI advert format repair

- Date: 2026-10-02
- Commands run: branch creation from 9de3d9d; Spec Kit create/setup/prerequisite
  scripts; `backend/.venv/bin/python /private/tmp/career-openai-diagnostic.py`
  with tiny synthetic inputs, configured builders and bounded requests; read-only
  provider/accounting SQL and local status HTTP reads; `ruff format` on touched
  Python files; source/diff inspection and local commits.
- Observed result: current gpt-5-mini CV request and text-embedding-3-small embedding
  request returned 200; the actual advert schema returned 400. Safe current job
  progress identifies read_advert, one completion attempt and no new CV calls.
  Keeping defaulted arrays non-nullable and null alternatives unique returned 200;
  final source conversion also returned 200 with diagnostic mutations removed.
- Decisions made: preserve original Pydantic/evidence validation and retry policy;
  add one OpenAI adapter helper for allowlisted failure metadata. No personal text
  read/dispatched by model diagnostics, no response content printed/saved, no DB
  mutations or new hosted path. API metadata reads did not rerun analysis.
- Verification: tests/lint/typecheck, benchmarks, security scan and full analysis
  remain deferred. Authored regressions are unexecuted. Request acceptance is not
  a release/quality result; no gate closed. The diagnostic script is temporary.
- Carried forward: human retry of a new analysis after reload/restart, focused/full
  regression verification and current synthetic end-to-end/quality release work.

## Phase 19.4 — Synthetic benchmark implementation, execution deferred

- Date: 2026-10-02
- Commands run: `git fetch origin` (restricted DNS failure, elevated read-only retry
  succeeded); `git switch -c feat/phase-19-synthetic-benchmark`; Spec Kit template
  resolver, `setup-plan.sh --json`, `setup-tasks.sh --json` and
  `check-prerequisites.sh --json --require-spec --require-tasks --include-tasks`;
  `backend/.venv/bin/ruff format` on the new benchmark modules/test/support files;
  Git source/diff inspection and local commits.
- Observed result: feature artifacts resolve and source files are present/formatted.
  The CLI drives the current application with explicit fixture retrieval, cold/warm
  caches and content-free physical request accounting. These are implementation
  observations, not test results or latency measurements.
- Decisions made: human explicitly retained deferred checks and authorized this
  slice ahead of earlier gates. Source baseline is the consolidated/adoption branch
  at `c603f33`; main is behind that dependency work. Offline operation reads no
  provider settings. Live operation reuses existing factories, egress and execution
  profiles. Fixture retrieval is labelled and excludes SQL/browser timing.
- User-reported defect: retirement SQL doubled check-constraint names. Code now
  uses `op.f()` for full names in both directions; SQL-compilation regression
  coverage is authored. Repair commit `f32f244`; no personal database action taken.
- Verification: no tests/lint/typecheck, benchmark/model calls, migrations, browser
  or security scans. Deferred tasks and all root release gates remain unchecked.
- Carried forward: focused and full checks, synthetic benchmark execution, observed
  results in evaluation.md, disposable migration preservation/deletion checks and
  frozen current-architecture quality/ranking evaluation.

## Phase 19 — Existing-project Spec Kit adoption

- Date: 2026-10-02
- Commands run: official release metadata read; pinned `uvx ... specify init --help`;
  initialization in place with Codex skills, Bash scripts and non-interactive options;
  constitution template resolver. All completed successfully.
- Observed result: Spec Kit v1.0.13 infrastructure/ten skills installed; constitution
  1.0.0 records current agreed boundaries. Commit `904a271` contains the scaffold,
  constitution and upstream attribution. Existing application source is unchanged.
- Decisions made: adoption uses the current implementation as baseline, feature
  specs elaborate root milestone items, and completed specs are historical change
  records. Manual Git remains the repository workflow; no optional extension added.
- Verification: no tests/lint or application/model runs, under the human's deferral.
  Installed files are present; fresh-chat skill discovery remains a user step.
- Carried forward: open the application repository itself in Codex, start a new chat,
  and choose one bounded PLAN item. Suggested first slice is current synthetic
  cold/warm duration and physical API-call measurement under 19.4. Existing final
  verification/migrations remain pending; no implementation started for that slice.

## Phase 19 — Consolidated architecture checkpoint

- Date: 2026-10-02
- Work recorded: consolidated plan committed as `ecadcaf`; implementation and
  handoff documentation prepared on `feat/phase-19-consolidated-analysis`.
- Observed result: one chunk/search/judge analysis replaces v1 runtime selection,
  extraction/scoring and UI. Each provider has its own construction and model
  execution profile. Document reading combines formerly separate calls, embeddings
  are batched, cached indexing avoids model probes, and independent work uses
  bounded threads. Binary parsing uses a bounded spawned process pool. Progress
  exposes physical model/embedding attempts, remaining-call estimates and ETA.
- Decisions made: the human superseded the old v1-before-retirement gate, requested
  tests/lint at the end, and then requested a stop after docs, commits and push.
  PLAN/BACKLOG now contain one delivery track. ADR 016 records the decision;
  API, feature, provider, run, wiring, limitation and threat documentation follow it.
- Verification state: partial checks ran before the stop-testing instruction. Final
  edits are unverified; the progress/retirement migrations are defined but unapplied.
  No live hosted/local-model benchmark or final browser journey was performed.
- Cleanup: removed dead v1 evaluator and its Make target, PDF reflow heuristics,
  duplicate frontend views and legacy test fixtures. The superseded architecture
  branch's work is preserved in the consolidated branch before branch removal.
- Carried forward: human final checks; disposable PostgreSQL migration verification;
  current synthetic quality/cold-warm latency evaluation; one browser journey and
  startup/deployment proof (PLAN 19.4). Ask/MCP hybrid/graph tool wiring remains in
  BACKLOG. No release gate or measured performance improvement is claimed.

## Phase 13C.10 — Documentation reconciled with model-first extraction

- Date: 2026-09-22
- Commands run:
  - `pytest tests/unit/test_production_wiring_matrix.py tests/unit/test_phase0_baseline.py -q --no-cov` — red first (README still called hermetic the product default; ADR 010 still said 13C.8 remained; features.md had no `unscored` band); then 14 passed
  - `ruff check` / `ruff format --check` on `test_production_wiring_matrix.py` — green
- Observed result: README names Ollama as the product default and hermetic as the test fixture, and links ADR 010. Features documents the empty-extract `unscored` band. The threat model records a salary/benefit/logistics line as a scoring-boundary risk. ADR 010 records 13C.5, 13C.6 and 13C.8 as landed. PLAN 13C.10 is ticked; the 13C exit gate (real CV, five adverts, `make test-integration`) is not claimed.
- Decisions made: keep ADR 010 as the audit record rather than writing a second ADR. Stale README phrases are pinned in the wiring-matrix suite so they cannot return.
- Problems hit: none after the red docs tests.
- Carried forward: Phase 13C exit gate, then Phase 14 evaluation. Do not start Phase 14 from this checkpoint.

## Phase 13B — Operational logging (console)

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_operational_logging.py -q --no-cov` — red first (`ModuleNotFoundError: career_assistant.logconfig`); then 6 passed after logger, middleware, redaction filter and layer events
  - `pytest -q` — 272 passed, 3 skipped; coverage 80.79%
  - `ruff check` / `ruff format --check` on logging modules — green after wrapping long `worker.stage` lines and sorting imports
  - `mypy` — `logconfig.StreamHandler` typed as `TextIO | None`
- Observed result: hermetic `create_app()` logs HTTP method/path/status, `cv.uploaded` and `role.created` without planted document phrases. A planted `sk-` key is redacted. `make run-api` sets `PYTHONUNBUFFERED=1` and lifespan re-applies the stderr handler so uvicorn `--reload` does not swallow application lines.
- Decisions made: stdlib logging only. Domain stays silent. DTOs are never dumped; `format_fields` refuses multiline and over-long values. SQLAlchemy `echo` remains off.
- Problems hit: the production process had zero `getLogger` usage, so uvicorn access lines were the only console output and were easy to miss under a buffered reloader.
- Carried forward: Phase 14 evaluation. Do not start it from this checkpoint.

## Phase 13A.10 — Embedding similarity for mapping candidates

- Date: 2026-09-21
- Commands run:
  - `pytest tests/unit/test_similarity.py tests/unit/test_analysis_similarity.py tests/unit/test_mapping_scoring.py tests/unit/test_analysis_pipeline.py tests/api/test_operational_logging.py -q --no-cov` — 34 passed
- Observed result: mapping treats cosine `similarity >= floor` as related without lexical overlap. Requirement and claim vectors are cached; the unused chunks table is dropped by migration `e9b7c4d1a2f0`. Ask retrieval is unchanged.
- Decisions made: exact cosine in Python; no ANN; hosted-gate miss degrades to lexical mapping rather than failing the job. ADR 009.
- Problems hit: none observed in the focused unit run.
- Carried forward: Phase 14 evaluation. Do not start it from this checkpoint.

## Phase 13A.9 — Documentation reconciled with observed production wiring

- Date: 2026-09-21
- Commands run:
  - `pytest tests/unit/test_production_wiring_matrix.py -q --no-cov` — red first (stale README; missing `docs/production-wiring.md`); OpenAPI collection replaced nested-router walk; then green
  - `make test` — 255 passed, 3 skipped, 48 deselected; coverage 80.62%; frontend Vitest 113 passed / 33 files
  - `make test-integration` — 48 passed
  - `make lint` — ruff needed a format pass on the new test; then ruff, mypy 121 files, frontend tsc and eslint green
- Observed result: README no longer describes Phase 10 or fixture-only UI. Every live `/api` route is named in `docs/production-wiring.md` with use case, provider resolver and SQL adapter. Threat model records `create_app()` in-memory stores as test-only. ADR 007 states HTTP drafts go through `generate_draft`. A new route without a matrix row fails the hermetic suite.
- Decisions made: collect routes from OpenAPI because `app.routes` keeps included routers as mounts. Relative `production-wiring.md` links from `docs/` are enough; README uses the `docs/` path.
- Problems hit: first route collector saw zero `/api` paths and would have let an empty matrix pass.
- Carried forward: Phase 14 evaluation. Do not start it from this checkpoint.

## Phase 13A.8 — Frontend asynchronous and failure-state gaps

- Date: 2026-09-21
- Commands run:
  - `bun run test src/components/role/RoleHeader.test.tsx` — red first (not-found/analysing/failed absent); then green after `RoleHeaderState`
  - `bun run test src/components/role/role-detail-tabs.test.ts` — red first (`shouldFetchRoleTabResource` missing); then green after ready-and-active `enabled` flags
  - `bun run test src/components/role/LetterPanel.test.tsx src/components/workspace/ComparePanel.test.tsx src/components/workspace/RolesPanel.test.tsx` — red first (empty success copy on failed queries); then green after retryable list states
  - `bun run test src/components/role/BulletDraftPanel.test.tsx src/components/role/LetterPanel.test.tsx src/components/role/PreparePanel.test.tsx` — red first (no clipboard/export retry); then green
  - `make test` — 252 passed, 3 skipped, 48 deselected; coverage 80.62%; frontend Vitest 113 passed / 33 files
  - `make test-integration` — 48 passed
  - `make lint` — ruff, mypy 121 files, frontend tsc green; eslint warning on exporting a helper from `RolesPanel.tsx` moved to `roles-panel-state.ts`
- Observed result: a missing or failed role no longer keeps a header skeleton. Tabs stay hidden until analysis is ready, and tab queries only run when that tab is active. Failed generated/supporting letters, compare role list, and a failed CV fetch show retry, not empty success. Copy and markdown export failures stay on screen with retry.
- Decisions made: header `onRetry` reanalyses a failed role and refetches otherwise. Disabled React Query flags are the fetch gate; hiding tabs alone would still fire child queries. Clipboard/export errors are component state, not query cache.
- Problems hit: analysing header tests collided without `cleanup()`; eslint `react-refresh/only-export-components` after putting `deriveRolesPanelState` on the panel module.
- Carried forward: 13A.9 documentation reconciliation. Do not start Phase 14.

## Phase 13A.7 — Ranking, comparison and immutable-version export

- Date: 2026-09-21
- Commands run:
  - `pytest tests/unit/test_ranking.py tests/api/test_role_analysis_routes.py::test_ranking_assigns_shared_rank_to_equal_scores -q --no-cov` — red first (import missing, then ranks 1 vs 2); then green after competition ranking
  - `pytest tests/api/test_role_analysis_routes.py::test_compare_differentiator_names_a_status_distinction -q --no-cov` — red first (`looker dashboards`); then green after status-gap differentiator
  - `pytest tests/api/test_role_lifecycle_routes.py::test_export_cover_letter_uses_selected_version tests/api/test_role_lifecycle_routes.py::test_export_bullets_uses_selected_version -q --no-cov` — red first (unknown version 200; version=1 concatenated all bullets); then green
  - `bun run test src/api/client.test.ts src/components/role/LetterPanel.test.tsx` — red first (unversioned URL; onExport received the click event); then green
  - `make test` — 252 passed, 3 skipped, 48 deselected; coverage 80.62%; frontend Vitest 101 passed / 32 files
  - `make test-integration` — 48 passed
  - `make lint` — ruff green; mypy 121 files after renaming reused loop/wire variables; frontend tsc and eslint green
- Observed result: equal fit scores share a 1224 competition rank. Compare names the largest mapping disagreement instead of the first shared requirement alphabetically. Cover-letter and bullet markdown export pin to `?version=`; the Letter tab sends the on-screen version.
- Decisions made: ranking and comparison live in `domain/` so hermetic and SQL stores cannot drift. Omitted export version still means latest; unknown version is 422. Bullets use the same version query even though the Gaps tab has no version picker yet.
- Problems hit: first ranking test commit landed on `main` after PR #26 merged; moved to `feat/phase-13a-ranking-compare-export` and reset local `main` to `origin/main`. mypy failed on reused `item` / `wire` names across incompatible types.
- Carried forward: 13A.8 frontend asynchronous and failure-state gaps.

## Phase 13A.6 — Generated prose through the grounded-generation use case

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_grounded_generation_http.py::test_bullet_without_cited_claim_is_refused_not_persisted -q --no-cov` — red first (200 vs 409); then green after `insufficient_cited_claims`
  - `pytest tests/integration/test_draft_persistence.py::test_template_fallback_fail_is_persisted_without_rewriting_to_pass -m integration --no-cov` — red first (must be pass); then green after allowing FAIL only on template fallback
  - `pytest tests/integration/test_sql_role_store.py::test_sql_role_store_persists_failed_template_fallback_verdict -m integration --no-cov` — red first (grounded stayed true); then green after mapping provenance to `GroundednessVerdict`
  - `pytest tests/api/test_grounded_generation_http.py::test_cover_letter_honours_tone_and_honest_gap_line -q --no-cov` — red first (CUDA always present); then green after tone/gap on the template
  - `pytest tests/api/test_grounded_generation_http.py::test_cover_letter_uses_generation_pipeline_and_drops_invented_facts -q --no-cov` — red first (`transport.calls` empty); then green after `generate_draft`
  - `pytest tests/api/test_grounded_generation_http.py::test_interview_pack_phrases_through_generation_pipeline -q --no-cov` — red first (`transport.calls` empty); then green after phrasing probes/notes
  - `make test` — 246 passed, 3 skipped, 48 deselected; coverage 80.14%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 48 passed
  - `make lint` — ruff, mypy 119 files, frontend tsc and eslint green
- Observed result: bullets, cover letters and interview packs (GET and markdown export) call `generate_draft`. Invented tokens such as Kubernetes are dropped via template fallback. Cover-letter tone and the honest gap line change that template. An uncited bullet is 409 and is not stored. SQL persists the real groundedness verdict and reconstructs justifying claim ids from mapping∩claim spans. The Letter tab controls stay; they now drive the validated path.
- Decisions made: persist FAIL for template-fallback drafts only; still refuse ungrounded model output with no fallback. Reconstruct claim ids from existing span overlap rather than a new mapping_claims table.
- Problems hit: SQL bullets 409'd on met requirements because `list_mappings` hard-coded empty `justifying_claim_ids`. Cover-letter HTTP previously ignored `tone`/`includeGapLine` (`del body`).
- Carried forward: 13A.7 ranking, comparison and immutable-version export.

## Phase 13A.5 — Database-backed retrieval and span resolution

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_span_routes.py::test_get_span_returns_evidence_for_uploaded_cover_letter -q --no-cov` — red first (404); then green after workspace span lookup
  - `pytest tests/api/test_span_routes.py::test_get_span_returns_evidence_for_role_job_description -q --no-cov` — red first (404); then green after role-store `get_span`
  - `pytest tests/api/test_retrieval_http.py -q --no-cov` — red first (cover-letter and same-role JD ids absent from Ask citations); then green after retrieval pool
  - `pytest -m integration tests/integration/test_retrieval_http_sql.py -q --no-cov` — 4 passed against PostgreSQL
  - `make test` — 242 passed, 3 skipped, 46 deselected; coverage 80.12%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 46 passed
  - `make lint` — ruff, mypy 119 files, frontend tsc and eslint green
- Observed result: `GET /api/spans/{id}` and generated-artefact evidence share one workspace-scoped resolver over the active CV, uploaded cover letters and role JD spans. Open questions retrieve those same kinds; a role-scoped question cannot cite another role's JD. Cover-letter text that would meet a requirement if it were a CV does not change mappings or scores. Cross-workspace span GET returns `span_not_found`. The same behaviours hold on SQL stores.
- Decisions made: lookup lives in application code (`lookup_workspace_span` / `retrieval_pool`); HTTP routes only translate. SQL finds any stored span row by workspace id, then filters by document kind at the supporting/role adapters.
- Problems hit: first JD GET fixture had no bullets so rules extraction produced no spans; switched to a Requirements list. Cover-letter Ask first asserted `spans[0]`, which was the greeting paragraph; the test now selects the Kubernetes span.
- Carried forward: 13A.6 route generated prose through the grounded-generation use case.

## Phase 13A.4 — Provider selection drives extraction, Ask and phrasing

- Date: 2026-09-21
- Commands run:
  - `pytest tests/api/test_provider_runtime_selection.py::test_open_question_calls_the_selected_scripted_provider -q --no-cov` — red first (`provider` was `hermetic`); then green after Ask used the workspace choice
  - `pytest tests/unit/test_providers.py::test_complete_rechecks_egress_and_makes_no_network_call -q --no-cov` — red first (DID NOT RAISE); then green after call-time egress wrap
  - `pytest tests/api/test_provider_runtime_selection.py::test_requirement_extraction_calls_the_selected_scripted_provider -q --no-cov` — red first (`transport.calls` empty); then green
  - `pytest tests/api/test_provider_runtime_selection.py::test_bullet_phrasing_calls_the_selected_scripted_provider -q --no-cov` — red first (`provider` was `hermetic`); then green
  - `pytest tests/api/test_provider_runtime_selection.py::test_open_question_records_accounting_without_document_text -q --no-cov` — red first (no `call_accountant`); then green
  - `make test` — 236 passed, 3 skipped, 42 deselected; coverage 80.61%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 42 passed
  - `make lint` — ruff, mypy 118 files, frontend tsc and eslint green
- Observed result: persisted answer provider is used for open questions, requirement/claim extraction (non-hermetic) and bullet phrasing. Completion and embedding choices stay independent. Hosted egress is checked at construction and again on `complete()`. A rejected hosted choice returns 403 with no transport calls. Answers, bullets and interview/cover-letter provenance come from the selected completion port rather than a hard-coded hermetic tag. Call accounting stores provider/model/`left_machine` and token counts, never document text; SQL-backed apps write `provider_call_accounting` rows.
- Decisions made: hermetic `create_app()` still defaults completion/embedding to hermetic so env `COMPLETION_PROVIDER=openai` cannot leak into API tests. Hermetic analysis stays on rules extractors; model-backed extractors wrap the Phase 2 factory only when the workspace answer choice is not hermetic. Local fallback never swallows `EgressNotPermittedError`.
- Problems hit: wrapping analysis in `Model*Extractor` for the hermetic default dropped SQL fit scores to 0 because hermetic structured output did not map cleanly; restored rules for hermetic choice. Env-hosted `ProviderSettings()` on the SQL worker similarly tried a real OpenAI call in integration tests; worker defaults without injected settings stay hermetic.
- Carried forward: 13A.5 database-backed retrieval and span resolution.

## Phase 13A.3 — PostgreSQL-backed analysis worker

- Date: 2026-09-21
- Commands run:
  - `pytest tests/integration/test_analysis_worker_http_sql.py::test_post_role_returns_analysing_and_queued_before_worker_runs -m integration --no-cov` — red first (`ready` vs `analysing`); then green after enqueue-only `create_role`
  - focused worker / SQL role / chat / CV / wiring tests — green
  - `make test` — 230 passed, 3 skipped, 40 deselected; coverage 80.04%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 40 passed
  - `make lint` — ruff, mypy 115 files, frontend tsc and eslint green
- Observed result: production SQL `POST /roles` and reanalyse commit `analysing` plus a queued job and return 202 before extraction. The in-process worker publishes or fails transactionally. CV replace enqueues job ids in the same transaction and never leaves a role `ready` with a stale score. CV delete marks roles `failed`. Startup recovers queued jobs and fails stale-running ones. Hermetic `create_app()` stays in-memory and still returns `ready` immediately.
- Decisions made: hermetic API tests keep the synchronous in-memory store; only the SQL path is asynchronous. Worker extractors remain hermetic until 13A.4. No Celery.
- Problems hit: existing SQL role/chat tests assumed in-request `ready`/`succeeded` — they now drain the worker. `fail_job` deletes only the current analysis version so sibling-role claims are not wiped.
- Carried forward: 13A.4 provider selection must affect actual extraction and answers.

## Phase 13A.2 — SQL chat and provider settings

- Date: 2026-09-21
- Commands run:
  - `pytest tests/integration/test_chat_provider_http_sql.py::test_messages_survive_fresh_app_process -m integration` — red first on empty FIT citations and a doubled check-constraint name; then green
  - focused hermetic ask/message/provider/wiring tests — 19 passed
  - `make test` — 230 passed, 3 skipped, 33 deselected; coverage 80.28%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 33 passed
  - `make lint` — ruff, mypy 114 files, frontend tsc and eslint green
- Observed result: production `create_production_app` wires SQL conversation and provider-choice stores. Questions, answers, citations, idempotent retries, deletion and provider model tags survive a fresh app process and stay workspace-scoped. `create_app()` remains in-memory for hermetic API tests.
- Decisions made: UUID answer ids from `id_factory`; additive `answers.kind` and provider model-tag columns; one conversation per workspace; local personal-use security posture documented (no multi-user auth in this build).
- Problems hit: FIT answers have empty citations by design — survival test uses an evidence question. Alembic naming doubled `ck_answers_answer_kind`.
- Carried forward: 13A.3 PostgreSQL-backed analysis worker in production.

## Phase 13A.1 — Restore the complete quality baseline

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/ruff format --check backend/src backend/tests` — 168 files
    already formatted after collapsing `list_cover_letters` in
    `application/ports/persistence.py`
  - `make lint` — ruff check/format green; mypy "Success: no issues found in 111
    source files"; frontend `tsc --noEmit` and `eslint .` green
  - `make typecheck` — mypy 111 files; frontend `tsc --noEmit` green
  - `make test` — backend 230 passed, 3 skipped, 29 deselected, 2 warnings;
    coverage 80.58%; frontend Vitest 100 passed / 32 files
  - `make test-integration` — 29 passed against local PostgreSQL; same 2 warnings
- Observed result: exact Make quality targets are green without changing Ruff's
  `backend/src backend/tests` scope. Alembic versions remain in
  `backend/migrations/`, outside that target.
- Decisions made: carry the two TestClient deprecation warnings as a Phase 15
  maintenance risk rather than adding `httpx2`, widening FastAPI, or filtering
  warnings.
- Problems hit: `list_cover_letters` was the only unformatted signature.
- Carried forward: 13A.2 SQL-backed chat and provider settings.

## Phase 13 — Accessibility and escaped text (13.9–13.10) + exit gate

- Date: 2026-09-18
- Commands run:
  - `bun run test src/a11y/phase13-accessibility.test.tsx` — 3 passed
  - `bun run test src/a11y/phase13-escaped-text.test.tsx` — 2 passed
  - `bun run test` — 100 passed / 32 files
  - `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: live regions on parsing, analysing, streaming; XSS strings stay
  text; Phase 13 exit gate met for frontend quality checks.
- Decisions made: polite live regions only.
- Problems hit: duplicate Analysing status in table+cards layouts — tests use
  getAllByRole.
- Carried forward: Phase 14 Evaluation.

## Phase 13 — /dev/states gallery (13.8)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/routes/dev.states.test.tsx` — 1 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: gallery lists Phase 13 surfaces; smoke test asserts every
  DEV_STATE_SECTION_TITLES h2 is present.
- Decisions made: export DevStatesPage + title list for the smoke test.
- Problems hit: getByRole heading name matching was flaky vs nested content;
  smoke test uses h2 text selector.
- Carried forward: 13.9 Accessibility.

## Phase 13 — Compare (13.7)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/workspace/ComparePanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: workspace Compare picks two roles, shows shared/unique/
  differentiator, and links into Gaps.
- Decisions made: only ready roles appear in the selectors.
- Problems hit: none material.
- Carried forward: 13.8 `/dev/states`.

## Phase 13 — Ranking (13.6)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/workspace/RankingPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: workspace shows ranked roles with because lines and Tied labels.
- Decisions made: RankingPanel sits below RolesPanel on `/`.
- Problems hit: none material.
- Carried forward: 13.7 Compare.

## Phase 13 — Letter tab (13.5)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/LetterPanel.test.tsx` — 3 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Letter tab drafts via POST /cover-letter, lists versions,
  exports Markdown, refuses with Open Gaps, and lists workspace supporting uploads
  separately.
- Decisions made: citation chips use span ids resolved through EvidencePanel.
- Problems hit: none material.
- Carried forward: 13.6 Ranking.

## Phase 13 — Prepare / interview pack (13.4)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/PreparePanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Prepare tab shows probes, lead-with, thin areas, ask-them;
  evidence is clickable; Export Markdown downloads the artefact.
- Decisions made: empty when all four sections are empty arrays.
- Problems hit: none material.
- Carried forward: 13.5 Letter tab.

## Phase 13 — Bullet drafts (13.3)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/BulletDraftPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Draft a bullet POSTs /bullets and shows text, citation chips,
  provenance, copy, and template-fallback status.
- Decisions made: draft panel sits under the Gaps list; dismiss resets the mutation.
- Problems hit: none material.
- Carried forward: 13.4 Prepare tab.

## Phase 13 — Gaps panel (13.2)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/GapsPanel.test.tsx` — 2 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: Gaps tab lists ordered gap items with reason, score delta,
  action, adjacent evidence, and Draft a bullet when canDraftBullet.
- Decisions made: draft click is wired as a no-op until 13.3; evidence reuses
  EvidencePanel via a synthetic Requirement selection.
- Problems hit: none material.
- Carried forward: 13.3 bullet draft surface.

## Phase 13 — Role detail tabs (13.1)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/role/RoleDetailTabs.test.tsx` — 3 passed
  - `bun run test` / `bun run lint` / `bunx tsc --noEmit` — green
- Observed result: role detail has Fit/Gaps/Prepare/Letter tabs; `?tab=gaps`
  deep-links; arrow keys move focus across the tablist.
- Decisions made: optional search param `tab` (default Fit); later panes are
  placeholders until 13.2–13.5.
- Problems hit: macOS case-insensitive clash between RoleDetailTabs.tsx and
  roleDetailTabs.ts — renamed constants module to role-detail-tabs.ts.
- Carried forward: 13.2 Gaps content.

## Phase 13 — SQL supporting cover letters (carry-forward)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_production_app_wiring.py tests/integration/test_sql_supporting_store.py tests/api/test_supporting_documents.py -q --no-cov`
  - ruff check + mypy on touched modules
- Observed result: production app wires SqlSupportingDocumentStore; cover letters
  persist in PostgreSQL documents (kind=cover_letter) with list/delete/download.
- Decisions made: close Phase 12 carry-forward before 13.1 UI tabs.
- Problems hit: none material.
- Carried forward: 13.1 role detail tabs; chunk/embedding index path; model-backed
  SqlRoleStore analysis.

## Phase 12 — Frontend integration (exit gate)

- Date: 2026-09-18
- Commands run:
  - Host API: `COMPLETION_PROVIDER=hermetic EMBEDDING_PROVIDER=hermetic
  - Frontend: `API_BASE_URL=http://127.0.0.1:8000 bun run dev -- --host 127.0.0.1`
  - Proxy walkthrough: POST `/api/cv` with `sample-data/fixtures/resumes/cv-strong-match.txt`,
    POST `/api/roles` with `jd-clean-match.txt`, poll job → succeeded, requirements/
    breakdown/SSE Ask tokens, pages `/` `/settings` `/ask` `/dev/states` → 200
  - Failure paths: empty file → `document_unreadable` 422; JPEG →
    `document_unsupported` 415; missing span → `span_not_found` 404; Ask with
    incomplete analysis → `analysis_incomplete` 409 (after fix)
  - Browser: workspace empty → upload CV → add role → score 73 / Partial match →
    role detail breakdown + requirements
  - `bun run test` — 76; Ask SSE pytest — 2 green after 409 mapping
- Observed result: Phase 12 exit gate criteria met for the wired screens; no mock
  data in `src/api/client.ts`.
- Decisions made: exit gate verified on hermetic providers, not the ollama values
  currently in `config/app.env`.
- Problems hit and how they were resolved:
  - Proxy mutations need `Origin` matching the app origin (csrf).
  - Dev server needs `API_BASE_URL` in the process environment.
  - Ask against incomplete analysis returned 500; mapped `RoleOperationRejected`
    to `AppError` (TDD).
- Carried forward:
  - Production supporting-document store still in-memory.
  - Playwright e2e (16.5); Docker image/stack (16.1).
  - Phase 13 new screens.

## Phase 12 — Frontend integration (12.12 wired screen states)

- Date: 2026-09-18
- Commands run:
  - `bun run test` (frontend) — 76 passed across 21 files
  - `bun run lint` — clean
  - `bunx tsc --noEmit` — clean
- Observed result:
  - Prop-driven state coverage for RolesPanel, CvCard, CoverLettersCard,
    FitBreakdown, RequirementTable, RoleHeader, ChatView, ProviderSettings
    (loading / empty / error / ready as applicable), plus prior EvidencePanel
    resolve states.
- Decisions made: none beyond the task.
- Problems hit and how they were resolved:
  - RequirementTable ready row text appears in table and card layouts; tests click
    `getAllByText(...)[0]`.
- Carried forward: Phase 12 exit gate against a running backend.

## Phase 12 — Frontend integration (12.11 error mapping)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/errors.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `describeApiError` covers every documented contract code; unknown codes surface
    with correlation id; wired into CV, roles, cover letters, chat, settings, and
    span resolve paths.
  - Frontend vitest 60 green.
- Decisions made: switch on code only; keep server `message` and append next-step copy.
- Problems hit: none after prettier.
- Carried forward: 12.12 component tests for wired screens.

## Phase 12 — Frontend integration (12.10 settings)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/components/settings/ProviderSettings.test.tsx` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - Unavailable reasons rendered from the API; hosted egress dialog retained;
    re-index confirmation when index provider/model changes; save errors surfaced
    from ApiError; setProviderChoice returns optional reindex job id.
  - Frontend vitest 56 green.
- Decisions made: warn before PUT on index changes (UI gate); hosted still requires
  acknowledgement; acknowledgedEgress only when a hosted provider is in the choice.
- Problems hit: duplicate reason text across answer/index selectors in tests.
- Carried forward: 12.11 error-code mapping across the app.

## Phase 12 — Frontend integration (12.9 Ask SSE)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/stream.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `postMessageStream` parses documented SSE events; ChatContainer streams tokens,
    stops via AbortController, deletes history, retries with the same
    `clientRequestId`, and resolves citation spans.
  - Frontend vitest 53 green.
- Decisions made: keep JSON `sendMessage` helper; Ask path uses SSE only.
- Problems hit: none after prettier/index-signature fixes.
- Carried forward: 12.10 settings wiring.

## Phase 12 — Frontend integration (12.8 role detail + span resolve)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/spans.test.ts src/components/EvidencePanel.test.tsx`
    (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `getSpan` client helper; role detail resolves selected evidence via
    `GET /api/spans/{id}`; unresolvable spans show a visible error (not the empty
    “no supporting text” copy).
  - Frontend vitest 49 green.
- Decisions made: always re-fetch by `spanId` when present rather than trusting
  inline requirement evidence alone.
- Problems hit: none after prettier fix.
- Carried forward: 12.9 Ask SSE wiring.

## Phase 12 — Frontend integration (12.7 analysis job polling)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/jobs.test.ts src/components/workspace/RolesPanel.test.tsx`
    (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
- Observed result:
  - `getJob` / `reanalyseRole` client helpers; roles query refetches while any role
    is `analysing`; job query polls while `queued`/`running`.
  - Roles list shows Analysing / Failed (+ reason + Retry analysis).
  - Frontend vitest 45 green.
- Decisions made: map OpenAPI string `AnalysisJob.error` to
  `{ code: "analysis_failed", message }` on the client; track role→jobId in
  container state from create/reanalyse responses.
- Problems hit: none material after exactOptionalPropertyTypes FitCell fix.
- Carried forward: 12.8 wire role detail.

## Phase 12 — Frontend integration (12.3–12.6 client, types, workspace)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/api/client.test.ts` / `src/api/upload.test.ts` /
    `src/types/additive.test.ts` (red then green)
  - `bun run test` / `bun run typecheck` / `bun run lint`
  - `backend/.venv/bin/pytest tests/contract/test_openapi_frontend_types.py -q --no-cov`
  - `backend/.venv/bin/pytest tests/api/test_cv_routes.py tests/api/test_supporting_documents.py -q --no-cov`
  - `make lock` (python-multipart)
- Observed result:
  - Real HTTP client with zod; fixtures under `__fixtures__/`; additive types;
    multipart CV/cover-letter upload on API + frontend; workspace shows ApiError
    rejection messages, replace/delete confirmations, supporting cover letters with
    “not score evidence” notice.
  - Frontend vitest 39 green; CV/supporting API tests green.
- Decisions made: add `python-multipart` for Starlette form parsing; keep paste
  JSON path alongside multipart; upload progress UI uses parsing busy state (byte
  progress deferred until XHR helper if needed).
- Problems hit: nested-brace TS parser for Role; exactOptionalPropertyTypes on
  fetch init / ChatMessage mapping.
- Carried forward: 12.7 analysis job polling.

## Phase 12 — Frontend integration (12.1–12.2 proxy spike and catch-all)

- Date: 2026-09-18
- Commands run:
  - `bun run test src/server/api-proxy.test.ts`
  - `bun run test` / `bun run typecheck` / `bun run lint`
  - `@tanstack/router-cli generate` (route tree includes `/api/$`)
- Observed result:
  - Spike **pass**: first SSE event arrives before upstream finishes; streaming
    upload body is forwarded without `arrayBuffer`/`text`/`json`; upstream reads
    the first byte before the client stream closes.
  - `src/routes/api.$.ts` proxies `/api/**` to `API_BASE_URL` with same-origin
    checks on non-GET.
- Decisions made: keep Start proxy path (no ADR CORS fallback); `API_BASE_URL`
  remains server-only.
- Problems hit: none after prettier fix.
- Carried forward: 12.3 real HTTP client replacing fixture `client.ts`.

## Phase 11 — API contracts (complete)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_supporting_documents.py` (red→green)
  - `pytest tests/api/test_message_history.py` (red→green)
  - `pytest tests/api -q --no-cov`
  - `pytest tests/api/test_error_table_coverage.py`
  - `make lint`
- Observed result:
  - Supporting cover letters: list/upload/delete + safe document download.
  - Messages: GET history, DELETE hard-delete, JSON/SSE share answer id on retry.
  - Full API suite green; lint/mypy/frontend typecheck green.
- Decisions made: hermetic InMemorySupportingDocumentStore (CV download bridge);
  conversation store remains process-local for API tests (SQL ask store deferred).
- Problems hit: download route needed response_class for the response_model gate;
  SSE replay omitted messageId until fixed.
- Carried forward: Phase 12; SQL supporting/ask stores; rate_limited/provider_failed
  HTTP surfaces when those controls exist.

## Phase 11 — API contracts (11.11 OpenAPI↔TS types)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/contract/test_openapi_frontend_types.py -q --no-cov` (red then green)
  - `make lint` / frontend `tsc` / `eslint`
- Observed result:
  - Shared models assert required camelCase fields on both OpenAPI and
    `frontend/src/types/index.ts`.
  - `Evidence.spanId` added to TS; fixtures and mock client updated.
  - `ChatMessage.leftMachine` (+ question kind) aligned with the wire contract.
- Decisions made: required-field intersection test (API may add fields); bring
  spanId forward from the Phase 12.5 note into 11.11 as PLAN requires.
- Problems hit: none after fixture/client updates.
- Carried forward: 11.12 supporting documents; 11.13 GET/DELETE messages + SQL.

## Phase 11 — API contracts (11.10 answer/draft provenance)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_provenance_responses.py -q --no-cov` (red then green)
  - `pytest tests/api tests/unit/test_ask_use_case.py -q --no-cov`
  - `make lint`
- Observed result:
  - SSE meta carries provider, model, leftMachine.
  - JSON Accept on POST /messages returns ChatMessageWire with the same fields.
  - Interview pack, bullets, cover-letter provenance already present — locked by
    regression.
- Decisions made: extend AskEvent/SSE meta with leftMachine; document it in
  api-contract.md; JSON ask path added early for provenance (GET/DELETE still 11.13).
- Problems hit: none after green.
- Carried forward: 11.11 OpenAPI↔TS; 11.12 supporting docs; 11.13 history/delete.

## Phase 11 — API contracts (11.9 SSE ask stream)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_message_sse.py -q --no-cov` (red then green)
  - `pytest tests/api -q --no-cov`
  - `make lint`
- Observed result:
  - `POST /api/messages` with `Accept: text/event-stream` returns
    meta → token(s) → citations → done over hermetic AskService.
  - Response-model gate allows StreamingResponse alongside PlainTextResponse.
- Decisions made: SSE framing in `api/sse.py`; in-memory conversation store for
  hermetic API; JSON Accept deferred to 11.13 with GET/DELETE.
- Problems hit: none after response_model exemption.
- Carried forward: 11.10 provenance; 11.13 full message routes + SQL conversation.

## Phase 11 — API contracts (11.8 production SQL app wiring)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_production_app_wiring.py -q --no-cov` (red then green)
  - `pytest tests/api -q --no-cov`
  - `make lint`
- Observed result:
  - Module `career_assistant.main:app` exposes SqlCvStore + SqlRoleStore.
  - `create_app()` without injection still uses in-memory stores for hermetic API
    tests (51 API tests green).
- Decisions made: `create_production_app` + `build_sql_stores` for the process
  entrypoint; keep `create_app` hermetic for test factories. Engine is lazy until
  first request.
- Problems hit: none.
- Carried forward: 11.9 SSE answer stream.

## Phase 11 — API contracts (11.8 durable drafts on SqlRoleStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py::test_cover_letter_and_bullets_persist_across_store_instances -m integration`
  - `pytest tests/integration/test_sql_role_store.py tests/integration/test_draft_persistence.py -m integration`
  - `pytest tests/api/ -q --no-cov`
  - `ruff` / `mypy`
- Observed result:
  - Cover letter and bullets persist in `generated_drafts` and reload via a fresh
    SqlRoleStore instance and HTTP list.
  - Routes reconstruct CoverLetterDraftWire / BulletDraftWire from
    GeneratedDraftRecord JSON bodies.
- Decisions made: draft body stores structured JSON; citations taken from paragraph/
  bullet spanIds; hermetic InMemoryRoleStore unchanged.
- Problems hit: none after green.
- Carried forward: production SQL create_app default; 11.9 SSE.

## Phase 11 — API contracts (11.8 SqlRoleStore delete/reanalyse)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/integration/test_analysis_persistence.py -m integration -q --no-cov`
  - `ruff` / `mypy` on changed persistence modules
- Observed result:
  - delete removes role (cascade) and JD document; get returns None.
  - reanalyse bumps analysis_version, publishes new hermetic results, new job id.
  - list_mappings scoped to current analysis_version.
  - HTTP delete/reanalyse against injected SQL stores green (4 SqlRoleStore tests).
- Decisions made: JD document deleted after role (RESTRICT FK); drafts still
  process-memory on SqlRoleStore.
- Problems hit: none after green.
- Carried forward: durable drafts; production SQL create_app default; 11.9 SSE.

## Phase 11 — API contracts (11.8 SqlRoleStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_role_store.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/integration/test_analysis_persistence.py
    tests/integration/test_draft_persistence.py … -m integration`
  - `ruff` / `mypy` on role_store
- Observed result:
  - SqlRoleStore create publishes hermetic analysis into PostgreSQL; role ready,
    job succeeded; require_analysis reloads requirements/mappings/score.
  - HTTP create role + requirements work with injected SqlCvStore + SqlRoleStore.
  - Migration `a1b2c3d4e5f6` adds `roles.company`.
- Decisions made: claim/requirement spans from hermetic extractors are ensured in
  the spans table before publish; drafts remain process-memory on SqlRoleStore for
  now; create_app still defaults to in-memory stores.
- Problems hit: none after green.
- Carried forward: SQL delete/reanalyse; durable drafts; production SQL default;
  11.9 SSE.

## Phase 11 — API contracts (11.8 SqlCvStore)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_sql_cv_store.py tests/integration/test_cv_http_sql.py -m integration -q --no-cov`
  - `pytest tests/api/ -q --no-cov`
  - `ruff` / `mypy` on `adapters/persistence/cv_store.py`
- Observed result:
  - SqlCvStore upload/get/span/delete round-trip via CvStore port against
    `TEST_DATABASE_URL`.
  - `create_app(cv_store=SqlCvStore(...))` serves CV + span HTTP routes from Postgres.
  - Hermetic API suite still green on InMemoryCvStore default.
- Decisions made: keep in-memory as create_app default for hermetic tests; inject
  SqlCvStore for SQL-backed runs. Roles/analysis SQL wiring deferred.
- Problems hit: none after green.
- Carried forward: SqlRoleStore / analysis persistence behind API; 11.9 SSE.

## Phase 11 — API contracts (11.8 hermetic lifecycle + draft list)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_role_lifecycle_routes.py -q --no-cov` (red then green)
  - `pytest tests/api/ -q --no-cov` → 51 passed
  - `ruff check` / `mypy` on changed modules
- Observed result:
  - DELETE role → 204 and subsequent get → `role_not_found`.
  - POST reanalyse → 202 with new succeeded job; role stays `ready`.
  - `analysis_incomplete` 409 when store marks role analysing.
  - Cover letters persisted and listed; bullets/cover-letter markdown export works.
- Decisions made: hermetic reanalyse remains synchronous; `mark_incomplete` is a
  store test helper, not an HTTP route.
- Problems hit: none after green.
- Carried forward: SQL-backed CV/role/analysis/draft persistence; 11.9 SSE.

## Phase 11 — API contracts (11.8 hermetic analysis artefacts)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_role_analysis_routes.py tests/api/test_role_routes.py -q --no-cov`
  - `ruff check` / `ruff format` on changed analysis modules
- Observed result:
  - Role create now runs hermetic rules extract→map→score synchronously; status
    `ready`, job `succeeded`.
  - Requirements, breakdown, gap-plan, interview-pack, bullets, cover-letter (or
    `insufficient_matched_requirements`), markdown export, ranking and compare
    routes pass the focused API suite (7 analysis + role tests).
- Decisions made: keep in-memory stores for hermetic API contracts; domain
  generation helpers remain the source of gap/interview/draft text; drafts stamp
  hermetic provenance with `leftMachine: false`.
- Problems hit: focused pytest hit the global 80% coverage gate — use `--no-cov`
  for slice runs; suite-wide coverage still via full `pytest`.
- Carried forward: SQL-backed CV/role/analysis persistence; generated cover-letter
  list; SSE ask (11.9); OpenAPI/frontend type agreement (11.11).

## Phase 11 — API contracts (11.8 partial: CV, spans, roles, jobs)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_cv_routes.py tests/api/test_span_routes.py tests/api/test_role_routes.py -q --no-cov`
  - `pytest tests/api/ -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - CV paste upload/get/delete with intake error mapping.
  - Span evidence includes `spanId`; unknown span → `span_not_found`.
  - Role create requires CV (`cv_required`); returns 202 with queued job; list/get work.
- Decisions made: hermetic in-memory CV/role stores for API contract tests; SQL UoW
  wiring and analysis worker execution deferred. Multipart CV upload deferred.
- Problems hit: none material after response_model union/204 guard update.
- Carried forward: gap/interview/drafts/export/ranking/compare; durable persistence.

## Phase 11 — API contracts (11.3 upload limit, 11.7 providers)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/test_upload_size_limit.py -q --no-cov`
  - `pytest tests/api/test_provider_routes.py -q --no-cov`
  - `pytest tests/api/ -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - ASGI Content-Length gate returns 413 `document_too_large` without calling `receive()`.
  - Provider catalogue reports availability/reasons; PUT enforces `egress_not_acknowledged`
    and `egress_not_permitted`; API keys absent from response bodies.
- Decisions made: workspace provider choice is process-memory for this slice
  (keyed by workspace cookie); SQL `provider_settings` wiring follows with CV/role
  persistence routes. Ollama listed available without a live reachability probe.
- Problems hit: FastAPI `list[Model]` response models broke the issubclass guard;
  renamed API provider test module to avoid colliding with `tests/unit/test_providers.py`.
- Carried forward: 11.8+ feature routes; durable provider_settings persistence.

## Phase 11 — API contracts (foundation: 11.1, 11.2, 11.4–11.6)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/api/ -q --no-cov`
  - `pytest tests/unit/test_persistence_boundary.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - `ApiModel` serialises snake_case → camelCase; every route declares `response_model`.
  - `workspace` cookie issued HttpOnly / SameSite=Lax; invalid values replaced.
  - `X-Correlation-Id` echoed or minted on every response.
  - Error envelope `{error:{code,message,correlationId}}`; unhandled exceptions do not
    leak paths or provider payloads.
  - `GET /api/ready` returns provider/database/migration status; 503 when unhealthy.
- Decisions made: SQL readiness probe lives in `adapters/persistence/readiness.py`;
  HTTP package keeps the protocol only. Upload size rejection (11.3) waits for CV
  routes.
- Problems hit: FastAPI 0.141 nests routes under `_IncludedRouter` — tests walk
  `original_router`.
- Carried forward: 11.3, 11.7–11.13 feature and message routes.

## Phase 10 — Grounded generation (complete, including 10.9)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/integration/test_draft_persistence.py -m integration -q --no-cov`
  - `make db-migrate` (revision `71f0c6b9147f`)
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Drafts persist body, citations, provider/model, `left_machine`, groundedness,
    template-fallback flag and regeneration count.
  - Regeneration allocates immutable `version` per `(role, kind)`; FAIL groundedness
    rejected at save.
- Decisions made: SQL draft repo omitted from hermetic coverage (integration-proven);
  HTTP draft routes remain Phase 11.
- Problems hit: none material.
- Carried forward: Phase 11 API contracts.

## Phase 10 — Grounded generation (10.1–10.8)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_groundedness.py -q --no-cov`
  - `pytest tests/unit/test_gap_plan.py -q --no-cov`
  - `pytest tests/unit/test_generation_pipeline.py -q --no-cov`
  - `pytest tests/unit/test_interview_export.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Adversarial groundedness fixtures fail closed; case variants pass.
  - Gap plan ordered by scoreDelta; evidence_it vs learn_it/accept_it.
  - Pipeline: validate → one regenerate → template fallback with counters.
  - Hermetic bullets; cover letter refuses below two met must-haves.
  - Interview pack sections from mapping; markdown export byte-stable.
- Decisions made: 10.9 PostgreSQL artefact versions deferred to a follow-up slice.
- Problems hit: none material.
- Carried forward: 10.9 persistence; Phase 11 API routes.

## Phase 9 — Question answering (complete)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_ask_use_case.py -q --no-cov`
  - `pytest tests/integration/test_ask_persistence.py -m integration -q --no-cov`
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - `AskService.ask` / `.stream` share one produce path; tokens never persisted mid-stream.
  - Question committed before answer; `clientRequestId` returns existing pair.
  - SQL `get_by_client_request_id`, `list_history`, citation list, hard delete.
- Decisions made: HTTP `/api/messages` remains Phase 11; behaviour proven at use-case
  + repository layers.
- Problems hit: same-timestamp history order — tests use ordered UUIDs; schema-
  qualified raw SQL in hard-delete assertions.
- Carried forward: Phase 10 grounded generation; wire AskService in Phase 11.

## Phase 9 — Question answering (domain slice)

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_intent_router.py -q --no-cov`
  - `pytest tests/unit/test_structured_ask.py -q --no-cov`
  - `pytest tests/unit/test_open_question_prompt.py -q --no-cov`
  - `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Deterministic `route_intent` for gaps/fit/compare/evidence/interview/open.
  - `answer_structured` builds answers from mappings only; bad citations →
    insufficient.
  - Open-question span selection respects cover-letter ask + role JD isolation;
    prompts delimit untrusted text and enforce budgets.
- Decisions made:
  - TDD red commits before each green slice; Phase 9 exit gate still needs
    streaming + persistence (9.7–9.9).
- Problems hit and how they were resolved: mypy loop-variable shadowing in compare.
- Carried forward: 9.7–9.9 application/API persistence and streaming.

## Phase 8 — Analysis jobs

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_analysis_job_domain.py -q --no-cov` (red then green)
  - `pytest tests/unit/test_analysis_pipeline.py -q --no-cov` (red then green)
  - `pytest tests/integration/test_analysis_persistence.py -m integration -q --no-cov`
  - `pytest -m integration -q --no-cov`, `pytest -q`, `ruff`, `mypy`
- Observed result:
  - Domain job lifecycle with stages, safe errors, stale-running recovery.
  - `AnalysisService` enqueues immediately, bounds concurrency, publishes only on
    success, discards on failure; CV-replace reanalysis covered in unit + SQL.
  - Migration `34b3a0846d82` adds role `status` and full job columns; SQL repos
    publish requirements/claims/mappings/score + terminal job atomically.
- Decisions made:
  - Red tests committed before each green implementation (team TDD).
  - SQL analysis repos omitted from hermetic coverage; proven by integration.
- Problems hit and how they were resolved:
  - Duplicate test module basename (`test_analysis_jobs.py`); renamed unit vs
    integration modules.
- Carried forward: Phase 9 question answering; HTTP role/job routes in Phase 11.

## Phase 7 — Mapping and scoring

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_mapping_scoring.py -q --no-cov`
  - `pytest -q`, `ruff check`, `ruff format`, `mypy`
- Observed result:
  - Domain `map_requirement` / `map_requirements` → `met` / `partial` / `missing`
    with reason codes and justifying span/claim ids; no I/O.
  - Optional similarity scores may surface candidates; high similarity alone never
    forces `met`.
  - `score_fit` reads `config/scoring_rubric.toml` via `load_scoring_rubric`;
    components and bands are deterministic; counterfactual delta is pure.
  - Fixture JD + CV (rules extractors) produce a stable score with no model call.
- Decisions made:
  - Mapping and scoring stay pure in `domain/`; rubric loading is application-layer
    configuration, not domain env access.
- Problems hit and how they were resolved:
  - Ruff E501 on long policy lines; reformatted with wrapped conditions / key helper.
- Carried forward: Phase 8 analysis jobs.

## Phase 6 — Evidence extraction

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_claim_extraction.py -q --no-cov`
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Claim` plus pure `derive_recency_signal` / `derive_duration_signal`.
  - Rules extractor reads EXPERIENCE bullets with role date ranges; undated stays
    undated; dated-experience Spark claims are not recent.
  - Span validation drops bad refs; cover letters rejected; model path keeps only
    span-backed texts.
- Decisions made:
  - Recency uses injectable `as_of` for deterministic tests (default `date.today()`).
- Problems hit and how they were resolved: none material.
- Carried forward: Phase 7 mapping and scoring.

## Phase 5 — Requirement extraction

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_requirement_extraction.py -q --no-cov`
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Requirement` with competency, seniority, must-have, confidence, vagueness.
  - `RulesRequirementExtractor` parses must/desirable bullet sections with exact spans.
  - Span validation drops non-resolving refs; injection fixture adds no override reqs.
  - Vague seniority fixture marks unquantified signals; cover letters are rejected.
  - Model-backed path uses CompletionPort JSON schema and keeps only span-backed texts.
- Decisions made:
  - Rules adapter remains the default; model path intersects model texts with rule
    spans so invented requirements cannot pass without a stored substring.
- Problems hit and how they were resolved: none material.
- Carried forward: Phase 6 evidence / claims extraction.

## Phase 4 — Persistence

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_database_settings.py … --no-cov` — red on missing
    `DatabaseSettings`, then green.
  - `pytest -m integration -q --no-cov` against local `career_assistant_test`
  - `pytest -q`, `ruff check`, `mypy`
  - `make db-check`, `make db-migrate`
- Observed result:
  - `DatabaseSettings` enforces `postgresql+psycopg://`, separate test URL, bounded
    pool/timeouts, and `hide_parameters` on the engine.
  - Alembic baseline creates `vector` plus the Phase 4 table set; upgrade/downgrade
    round-trips on an empty database.
  - Repository ports + `SqlUnitOfWork` store CV/cover-letter bytes with spans,
    workspace-scope reads, hard delete, CV replacement invalidation, and conversation
    uniqueness constraints.
  - `make db-check` / `make db-migrate` / `make run` use local `DATABASE_URL`.
- Decisions made:
  - Embedding column is `vector(64)` matching the hermetic default; dimensions are
    also stored per row. Hosted dims with a different size need a later migration.
  - SQLAlchemy stays under `adapters/persistence/` with a dedicated boundary guard.
- Problems hit and how they were resolved:
  - Answer citations flushed before the parent answer; fixed by flushing the answer
    first.
  - Local role `career` and databases created for integration runs; Docker was not
    required.
- Carried forward:
  - Phase 5 requirement extraction; HTTP upload routes still Phase 11.

## Phase 3 — Document intake and spans

- Date: 2026-09-18
- Commands run:
  - `pytest tests/unit/test_document_intake.py -q --no-cov` — observed red on missing
    `parsing.pipeline` and a ligature fixture typo; then green after implementation.
  - `pytest -q`, `ruff check`, `mypy`
- Observed result:
  - Domain `Document` / `Page` / `Span` with offset-backed citation units.
  - Admission sniffs PDF/DOCX/plain text; maps oversized and unsupported inputs to
    api-contract codes.
  - Normalisation expands ligatures/bullets and joins hyphenated line breaks; paragraph
    offsets round-trip.
  - Pipeline parses plain text fixtures plus synthetic PDF/DOCX bytes; encrypted and
    empty PDFs raise `document_unreadable`.
  - Span resolution guarantees `highlight ⊆ paragraph`.
- Decisions made:
  - Add `pypdf`, `python-docx`, and `cryptography` (AES encrypt fixtures / PDF crypto).
  - Generate PDF/DOCX test bytes in `tests/support` rather than committing binaries.
- Problems hit and how they were resolved:
  - Ligature test used `e`+`ﬁ`+`cient` (eficient); corrected to `ef`+`ﬁ`+`cient`.
  - TDD: failing tests committed first, then the pipeline implementation.
- Carried forward:
  - Phase 4 persistence; HTTP upload routes still later (Phase 11).

## Phase 2 — Model providers

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/pytest tests/contract tests/unit/test_providers.py -q --no-cov`
  - `backend/.venv/bin/pytest -q` (full hermetic suite)
  - `backend/.venv/bin/ruff check src tests`, `mypy`
- Observed result:
  - Completion and embedding ports live under `application/ports/` with no vendor
    shapes; capability descriptors drive behaviour.
  - Hermetic adapters are the default; Ollama/OpenAI/Anthropic use injectable HTTP
    transports and recorded fixtures in the shared contract suite (no live calls).
  - Hosted adapters raise `EgressNotPermittedError` when the gate is closed or the
    key is missing; scripted transport records zero calls in that case.
  - Resilience (retry 429/5xx, breaker), explicit fallback flag, call accounting, and
    `ProviderSettings.public_snapshot()` key redaction are covered by unit tests.
  - Coverage 86% on the package; architecture guard still forbids SDKs in
    domain/application.
- Decisions made:
  - Use `httpx` as the only runtime HTTP client for provider adapters (no vendor
    SDKs in the lock yet).
  - Anthropic embedding requests fail closed at the factory — ports stay independent.
- Problems hit and how they were resolved:
  - Needed `pythonpath = ["src", "."]` so contract tests can import `tests.support`.
- Carried forward:
  - Phase 3 document intake and spans.
  - Provider HTTP routes and workspace selection land in Phase 11 / 4.

## Phase 1 — Skeleton and quality gates (remainder)

- Date: 2026-09-18
- Commands run:
  - `bunx tsc --noEmit` — passed on Lovable sources as delivered.
  - `bun run lint` — failed as delivered with 226 Prettier errors; after
    `bun run format`, lint passed with 2 pre-existing react-refresh warnings only.
  - `bunx vitest run` — StatusMark component tests and ESLint guard tests green.
  - `make lint` and `make test` after wiring frontend into the Make targets.
- Observed result:
  - Deleted `frontend/package-lock.json` and empty `src/app/` stubs; ignored
    `.output` / `.wrangler` build artefacts.
  - Vitest + Testing Library + jsdom added; first test covers `StatusMark` from props.
  - Custom ESLint plugin bans hex / raw Tailwind palette classes in
    `src/components/**`; fixture imports banned outside tests (exceptions:
    `api/client.ts`, `api/fixtures.ts`, `routes/dev.states.tsx`).
  - GitHub Actions workflow `.github/workflows/ci.yml` runs install, `make lint`,
    `make test` on Python 3.14 and Bun 1.4.0.
- Decisions made:
  - Keep temporary fixture imports in `api/client.ts` until Phase 12 replaces the
    fixture store; the guard still blocks components and routes.
  - Format the as-delivered Lovable tree so the Phase 1 exit gate can pass; record
    the Prettier failure as the only as-delivered defect.
- Problems hit and how they were resolved:
  - ESLint `lintText` guards initially pointed at `src/` instead of the frontend
    root; fixed the test path resolution.
- Carried forward:
  - Phase 2 model providers.
  - Phase 16.1 still needs a real Docker/bun image build verification.

## Phase 0 — Repository baseline and decisions

- Date: 2026-09-18
- Commands run:
  - `backend/.venv/bin/pytest tests/unit/test_phase0_baseline.py -q --no-cov`
    observed failing on missing Product scope, threat-model draft coverage, fixtures,
    dataset stub and scoring rubric config (intended red).
  - Same command after the Phase 0 assets landed — all Phase 0 baseline tests passed.
  - `backend/.venv/bin/pytest -q` (full hermetic suite) after the green cycle.
- Observed result:
  - AGENTS.md now carries a Product scope section aligned with features.md
    “Deliberately not features”, and hard delete explicitly includes generated drafts.
  - ADRs 001–007 confirmed accepted and dated 2026-09-18; contents match PLAN fixed
    direction (monolith, Postgres/pgvector, pluggable providers + egress, deterministic
    scoring, runtime provider selection, TanStack Start, grounded generation).
  - threat-model.md names upload, document/job-description text, model output,
    generated drafts, personal data and egress controls.
  - Fixtures: 3 synthetic CVs, 6 synthetic JDs, manifest pairings for clean / partial /
    poor / vague seniority / injection / recency decay.
  - `sample-data/evaluation/dataset.json` stub with the documented case shape.
  - Starting rubric weights in `config/scoring_rubric.toml`, referenced from features.md.
- Decisions made:
  - Scope boundaries stay as features.md states; no product expansion in Phase 0.
  - Rubric constants are configuration from day one, not deferred until scoring code.
- Problems hit and how they were resolved:
  - Host Python was already on 3.14 from the preceding commit; Phase 0 tests run on that
    interpreter.
- Carried forward:
  - Phase 1 remaining: frontend hygiene (1.3), Vitest (1.4), colour/fixture ESLint guard
    (1.8), CI (1.9).

## Phase 1 (partial) — run and deploy surface

- Date: 2026-09-17
- Commands run:
  - `uv venv --python 3.13 backend/.venv` and `uv pip install -e ".[dev]"`
  - `backend/.venv/bin/pytest tests/api/test_health.py --no-cov` **before** `main.py`
    existed
  - `make test`, `ruff check`, `ruff format --check`, `mypy`
  - `uv pip compile pyproject.toml [--extra dev] --no-header`
  - `make help`, `make -n config`, and a YAML parse of `compose.yaml`
- Observed result:
  - The liveness test failed on collection with no `career_assistant.main` — the
    intended red.
  - After `main.py`: 4 passed, 100% statement and branch coverage, coverage gate 80%
    satisfied.
  - ruff: "All checks passed", 12 files already formatted. mypy strict: "Success: no
    issues found in 10 source files".
  - Runtime lock 15 pins, dev lock 57 pins, both from Python 3.13.15.
  - `compose.yaml` parses to services db, api, web, ollama and volumes postgres_data,
    ollama_data.
- Decisions made:
  - Two dependency locks rather than one (AI_DEVELOPMENT_LOG 002).
  - Ollama behind a Compose profile rather than in the default stack (003).
  - Multi-stage images, both running as a non-root user, with health checks on the API
    and the web server. The sibling repository runs a dev server in its frontend image;
    this one builds and serves the Nitro output.
  - `alembic upgrade head` is deliberately absent from the backend image command and
    from `make run` until there is a schema, at phase 4.
- Problems hit and how they were resolved:
  - The workspace this was written from has no Docker and no bun, so neither image was
    built, the stack was never started, and `bunx tsc --noEmit`, `bun run lint` and the
    frontend build were not executed. Recorded as open on plan task 16.1 rather than
    asserted as working.
- Carried forward:
  - Build both images and run the stack. The two likeliest fixes are the Nitro preset
    and the `.output/server/index.mjs` path in `frontend/Dockerfile`.
  - Phase 0 is still open: threat model, synthetic fixtures, evaluation dataset shape.
  - Frontend hygiene (plan task 1.3) and frontend test tooling (1.4) are untouched.
