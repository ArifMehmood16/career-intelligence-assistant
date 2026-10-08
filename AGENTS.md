# Instructions for coding agents

This file applies to the whole repository and to every coding agent — Claude Code,
Cursor, Codex or anything else. `CLAUDE.md` imports it; never copy these rules into
another file. `frontend/AGENTS.md` adds frontend-only rules on top of this one.
Instructions the human gives in a session take precedence over this file.

## Which document settles what

| Question | Authority |
|---|---|
| What are the rules for agents? | `AGENTS.md` (this file) |
| What does a milestone require, and when is it done? | `PLAN.md` — milestone acceptance and release gates |
| What does a scoped change require? | `specs/<change>/spec.md`, linked to its root PLAN/BACKLOG item |
| How is that change designed and executed? | The feature `plan.md` and `tasks.md`; these are not a second roadmap |
| What constrains Spec Kit plans? | `.specify/memory/constitution.md`, derived from these rules and accepted ADRs |
| What is still open, and in what order? | `BACKLOG.md` — every open item in one list, each pointing at its `PLAN.md` id |
| What does the product do? | `docs/features.md`, including "Deliberately not features" |
| What is the wire format? | `docs/api-contract.md` |
| Which route uses which use case and adapter? | `docs/production-wiring.md` |
| Why is it built this way? | `docs/adr/` |
| What was measured? | `docs/evaluation.md` — the only place a quality number may appear |
| What did earlier sessions do? | `AI_DEVELOPMENT_LOG.md`, newest entry first |

When a document disagrees with the code, the code is what runs. Say so in your report,
then either fix the document or raise the defect in `BACKLOG.md`. Never leave the
disagreement silently in place.

## Spec Kit adoption

GitHub Spec Kit v1.0.13 is installed as repository-local Codex skills. Use
`$speckit-specify`, clarify when needed, plan, tasks and analyze for one bounded
change to this existing system. The setup and next steps are in
[docs/spec-kit.md](docs/spec-kit.md).

Feature specs elaborate the root milestone and must link to its PLAN/BACKLOG item.
Inspect and reuse existing modules; do not generate a new application, repeat the
roadmap, restore v1, or treat upstream example setup tasks as work for this codebase.
Keep completed feature artifacts as historical change records and maintain current
behavior in the existing product/API/architecture docs. Use the existing manual
Git workflow; a Git extension is not required.

The human explicitly resumed tests/lint and integration verification for PR #43's
CI repair. Follow the verification workflow below; the earlier
checkpoint's deferral no longer applies to this repair. Record observed checks,
not template completion, as evidence. Browser, security and measured release
work still requires its own acceptance evidence.

## Mission

Build an evidence-bound career intelligence assistant as a simple, production-minded
modular monolith. The product's value is that every statement it makes about a
candidate traces to a span of text in a real document. Protect that property above
feature count.

Demonstrate senior engineering judgement through explicit trade-offs, secure
boundaries, reliable tests and clear documentation — not through additional
frameworks or services.

## The invariant

**The model reads and judges. The server verifies. The domain computes fit.**

- The sole running analysis is chunk/search/judge with domain aggregation (ADR 016).
  Never rebuild the retired classifier/assessor pipeline or selector.
- Chunks are server-issued line ranges, reconstructed from stored text. Surface
  fields and evidence quotes must resolve verbatim to stored chunks/spans.
- The model may judge match, seniority and experience with explicit anchors, and
  phrase grounded output. It may not emit the fit score. Domain code aggregates
  validated judgments with the configured rubric.
- Incomplete chunking or judging fails the analysis and publishes no score/band or
  ranking position. A citation proves provenance, not semantic support.
- Fit, gaps, ranking, preparation, drafts, Ask and MCP consume the same validated
  publication. Shared view value types must not introduce an alternate score path.
- Ollama, OpenAI and Anthropic have independent provider builders and model profiles.
  Application code reads injected context/output/concurrency capabilities, never a
  vendor-name conditional. Hosted egress remains explicitly gated. Hermetic adapters
  are test fixtures at provider boundaries, executing the same application pipeline.
- Independent I/O may overlap using bounded threads. CPU-heavy binary parsing uses
  spawned processes. Do not pass SQL sessions/provider clients into parsing tasks.
  Progress/accounting/cancellation context must survive thread boundaries.

## Product scope

The feature catalogue and the "Deliberately not features" list in `docs/features.md`
are authoritative for product behaviour. Non-negotiable boundaries for this build:

- This is a **candidate's tool**, not an employer screening product.
- **One CV per workspace.** No multi-CV comparison.
- **No scanned-image** / OCR intake until that work is explicitly justified.
- **No authentication** or multi-tenancy yet — required before any untrusted user
  touches a deployment.
- Hard delete removes documents, spans, chunks, embeddings, claims, mappings,
  generated drafts, questions, answers, citations and operational audit rows
  (actions, events, HTTP envelopes, provider-call accounting). Nothing soft-survives.
- Absence of auto-apply, job-board ingestion, email integration, writing back into the
  CV file, and an overall "should I apply?" verdict is intentional.

## Working protocol

For every task:

1. Read this file, `BACKLOG.md`, the relevant `PLAN.md` phase and the newest relevant
   entries at the top of `AI_DEVELOPMENT_LOG.md`. Read `README.md`, and the page it
   links for the topic, when the task touches setup, scope or architecture.
2. Take the first open item in the `BACKLOG.md` "Now" section unless the human names
   another. Do not start a later phase while an earlier exit gate is open, unless the
   human overrides that and `PLAN.md` records the override.
3. Inspect the relevant code and tests before proposing edits.
4. Restate the task, its acceptance criteria and the files you expect to change.
5. Name assumptions and conflicts. Ask before making a material architectural choice
   that is not already approved.
6. Create the task branch from an up-to-date `main` (see [Git workflow](#git-workflow)).
7. Work in red-green-refactor cycles and commit each green step (see
   [Development style](#development-style)).
8. Run the full quality checks for the phase.
9. Inspect the complete branch diff (`git diff main...HEAD`) for unrelated changes,
   security issues, SonarQube-type findings and unnecessary complexity.
10. Update the documentation the task requires. Tick the `PLAN.md` box and the matching
    `BACKLOG.md` line in the same commit, and only after the exit criteria are proven.
11. Add a factual `AI_DEVELOPMENT_LOG.md` entry at the top of "Entries", based only on
    work actually performed.
12. Stop at the task checkpoint and give the [task report](#required-task-report). Do
    not push, open a pull request, merge or start the next task until the human says so.

If the red test cannot be demonstrated because the behaviour already exists, explain
why and add a regression test that would fail if the behaviour were removed.

## Development style

### TDD cycle and commit rhythm

- One behaviour per cycle, expressed as one focused test of an acceptance criterion.
- **Red:** write the test, run it, and confirm it fails for the expected behavioural
  reason — not an import error or a typo. Record the failure for the task report.
- **Green:** write the smallest correct implementation. Run the focused test and the
  tests around it. **Commit.**
- **Refactor:** improve names and structure with the same tests green. **Commit
  separately** with a `refactor:` subject, so behaviour changes and structure changes
  never share a commit.
- Every commit builds and passes its tests. A failing test is never committed on its
  own: the red run is evidence for the report and the log, not history. That keeps
  `git bisect` usable and every commit reviewable on its own.
- Commit small and often. If the subject needs "and", split the commit. Documentation
  for a change lands on the same branch, either with the change or as its own `docs:`
  commit.
- Before each commit, on the touched files. From `backend/`:
  `.venv/bin/pytest <test file> --no-cov`, `.venv/bin/ruff check <files>`,
  `.venv/bin/ruff format --check <files>` and `.venv/bin/mypy`. From `frontend/`:
  `bunx vitest run <test file>`, `bun run lint` and `bun run typecheck`. A focused
  pytest run needs `--no-cov`, because the configured 80% coverage gate fails on a
  partial run.
- Before the checkpoint, from the repository root: `make lint`, `make test`, and
  `make test-integration` when persistence, migrations or SQL adapters changed.
- Every production defect fixed gets a regression test first.
- Prefer fakes at provider boundaries and real collaborators inside domain and
  application code.

### Git workflow

- Never commit to `main`. One branch per task, lowercase and hyphenated, with the
  phase number and one concern: `feat/phase-15b-audit-sql-adapter`, not `p4` or `wip`.
- Branch names and commits are readable by someone who was not in the chat. Commit
  subjects are imperative and state the change, not a file list. Conventional
  prefixes (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`). A short body
  when the why is not obvious.
  Good: `feat(mapping): map job requirements to cited CV evidence spans`.
  Poor: `update`, `phase4`, `fixes`.
- Stage files explicitly. Never stage `config/app.env`, `.env`, coverage output, log
  files, or any private CV, cover letter, job description, prompt or provider response.
- Changes reach `main` through a pull request the human reviews and merges. No force
  push and no history rewrite on a pushed branch without approval.
- Leave the repository clean. If the environment cannot remove a `.git/*.lock` file it
  created, stop and report it rather than working around it.

### SonarQube-clean code

Write code that passes SonarQube's default quality gate on the first scan: no new
bugs, vulnerabilities or unreviewed security hotspots, at least 80% coverage on new
code, and no more than 3% duplication on new code. In practice:

- Cognitive complexity of 15 or less per function (rule S3776). Reduce it with guard
  clauses, a well-named extracted function, a lookup table or a strategy — not by
  hiding branches in a lambda.
- Control flow nested no more than three levels (S134). Return early.
- Seven parameters or fewer (S107). Group related values into a frozen dataclass or a
  typed object; avoid boolean flags that switch behaviour.
- No string literal repeated three or more times (S1192). Error codes, event names,
  statuses and prompt versions are constants or enums in one module.
- No unused imports, variables, parameters or private functions. No commented-out code
  (S125). No empty blocks. No `TODO` or `FIXME` left in code (S1135) — record the item
  in `BACKLOG.md` instead.
- Exceptions: catch the narrowest type, never a bare `except:` or a swallowed
  `except Exception`. Re-raise with `raise ... from exc`. Log a safe code, never
  `str(exc)` from a parser that may hold document text.
- Security hotspots: no hard-coded credentials, no `eval` or `exec`, no
  `shell=True`, no weak hashing for anything security-relevant, and no regular
  expression that can backtrack catastrophically on untrusted document text.
- TypeScript and React: no nested ternaries (S3358) — extract a component or a map; no
  array index as a `key` (S6479); component props typed `Readonly<...>` (S6759); no
  `any`; no unhandled promise; interactive elements are buttons or links, not a `div`
  with `onClick`.
- Test code is analysed too. Share fixtures and builders rather than copying setup
  between files.
- A genuine false positive may be marked `# NOSONAR` / `// NOSONAR` only with the rule
  id, a one-line reason and human approval, like any other suppression.
- Run SonarQube for IDE (SonarLint) or a local scan on the changed files before the
  checkpoint when available, and list any finding left open in the task report.

### SOLID and design patterns

Use them where the code already has the shape they solve. "No speculative
abstractions" still holds: a pattern must remove a real conditional, duplication or
coupling, never anticipate one.

- **Single responsibility.** A route translates HTTP to a use case and back. A use case
  orchestrates. The domain decides. An adapter talks to one external system. A module
  past roughly 400 lines or a function past roughly 50 is a signal to split it by
  responsibility.
- **Open/closed.** A new provider, extractor or store is a new adapter plus one
  registration in a factory or the composition root. If adding a variant means
  editing an `if provider == ...` chain, replace the chain with a registry first.
- **Liskov substitution.** Every adapter behind a port passes that port's contract
  suite. A fake that behaves differently from production is a defect in the fake.
- **Interface segregation.** Ports stay narrow — completion and embeddings are separate
  ports for this reason. Do not add a method to a port for one caller.
- **Dependency inversion.** Domain and application code depend on the ports in
  `application/ports/`. Concrete adapters are constructed only in factories and the
  composition root (`main.py`). The architecture guard test enforces the import
  direction.

Patterns already in the codebase. Extend these rather than inventing a parallel one:

| Pattern | Where | Use it for |
|---|---|---|
| Ports and adapters | `application/ports/`, `adapters/` | Every external system |
| Strategy | provider adapters, model and rules extractors, relatedness | Behaviour chosen at runtime |
| Factory | `adapters/providers/factory.py`, provider `builders.py`, `build_sql_stores` | Building adapters from configuration and the egress gate |
| Decorator | `AccountingCompletion`, `AccountingEmbedding` | Cross-cutting concerns without touching the wrapped adapter |
| Circuit breaker | `adapters/providers/resilience.py` | Provider failure isolation |
| Repository and unit of work | `adapters/persistence/` | Transactional persistence and one-transaction hard delete |
| Value object | frozen dataclasses in `domain/` | Immutable domain data |
| Container and presentational components | `frontend/src/components/` | Fetching separated from rendering |

Name the pattern in the commit body when you introduce or extend one.

## Architecture rules

- The backend stays a modular monolith.
- `domain/` and `application/` must not import FastAPI, SQLAlchemy or provider SDKs.
- HTTP routes translate requests and responses and invoke use cases. No business
  logic in routes.
- Interfaces and protocols only at external or meaningfully variable boundaries.
- Provider implementations live in `adapters/` — the hermetic test fixture, Ollama,
  OpenAI and Anthropic side by side behind the same port, with no vendor type escaping
  it. Adding a fifth must require no change outside `adapters/` and configuration.
- Configuration is injected. Domain code does not read environment variables.
- Persistence models do not become domain models by convenience.
- PostgreSQL 16 + pgvector is the production system of record for original uploads,
  parsed documents, roles, mappings, generated artefacts, chat history and the
  operational audit. Fakes are test-only; do not add a SQLite, filesystem or
  process-memory persistence fallback.
- Concrete experience in an uploaded CV or an uploaded cover letter can support a
  mapping, with its source shown and duplicates removed. An aspiration does not
  count, and a generated draft never raises the score
  ([ADR 011](docs/adr/011-evidence-assessment-contract.md)). The running analysis
  still excludes self-authored claims; implementing the letter policy is tracked in
  `BACKLOG.md`.
- Scoring lives in `domain/`, is pure, and is unit tested without a database or a
  model.
- The frontend stays feature-oriented. No global state unless genuinely shared.
- Prefer explicit Python and TypeScript over metaprogramming and framework magic.

## Test layers

- **Unit:** parsing, chunk/requirement contracts, evidence judging, retrieval,
  scoring rubric, prompt construction, intent routing.
- **Contract:** one suite that every completion adapter and every embedding adapter
  must pass, run against recorded fixtures. No live vendor calls in any default run.
- **API:** validation, status codes, response contracts, safe error mapping.
- **Integration:** PostgreSQL/pgvector, migrations, concrete adapters
  (`make test-integration`).
- **Component:** frontend interactions, accessibility, error and loading states.
- **End-to-end:** one critical journey — upload CV, add a job description, see the
  mapping, ask a gap question, open a citation — with deterministic providers
  (Playwright, `make test-e2e`, PLAN 16.5).
- **Evaluation:** current chunking, judgement and ranking quality against the
  labelled fixture set (PLAN 19.4). The retired v1 evaluator and command are removed.
- **Live evaluation:** explicitly enabled and synthetic-data-only, never in default
  runs. Current cold/warm latency and quality evaluation are tracked in PLAN 19.4;
  the retired Ollama classifier smoke entry point has been removed.

Default tests are deterministic, repeatable and independent of paid APIs or public
network access.

## Security and privacy rules

Treat uploads, document text, questions, retrieved spans and model output as
untrusted.

- Never execute or evaluate uploaded content.
- Enforce configurable limits on file size, page/character count, question length,
  context size and model output.
- Allowlist accepted file types. Reject on content inspection, not extension alone.
- Job-description, CV and cover-letter text cannot issue instructions to the
  application or override the system prompt. Retrieved text is delimited and labelled
  untrusted in every prompt. Keep the regression test for an injection attempt in a
  job description passing.
- Validate model output against a schema and resolve every span reference against
  stored server-side spans before it reaches the user.
- Escape document excerpts in the browser. Never inject them as raw HTML.
- Parameterised database access and workspace-scoped queries.
- Return safe external errors. Never expose stack traces, prompts, secrets or
  provider payloads.
- Content leaves the machine only through the egress gate. A hosted adapter is
  constructible only when `ALLOW_HOSTED_PROVIDERS` is true and that provider's key is
  present. Never add a network call to a model vendor outside that chokepoint, and
  never make a hosted provider the default.
- API keys are read at construction, never logged, and never returned by any route —
  not even masked. The redaction test covers this.
- Every answer and stored artefact records the provider and model tag that produced it
  and whether content left the machine. Removing that attribution is a security change.
- Never branch on a provider's name in the application. Read the capability descriptor
  and degrade deterministically.
- Do not log document text, raw uploads, questions, answers, embeddings, full prompts,
  credentials or model responses. Durable audit tables follow the same field
  contract: ids, counts, durations and codes only — never HTTP or model bodies.
  See [ADR 012](docs/adr/012-durable-operational-audit.md).
- Hard delete removes original document bytes and every derived record listed under
  [Product scope](#product-scope). Test that nothing survives it.
- Secrets live in environment variables locally and in a secret manager in production.

Update `docs/threat-model.md` when a trust boundary or control changes.

## Code quality rules

- Python is typed at public boundaries and passes the configured Ruff and mypy
  (strict) checks.
- TypeScript runs in strict mode; no unjustified `any`.
- Small functions, cohesive modules, descriptive names.
- Translate known infrastructure failures at boundaries and preserve causes internally
  without exposing them.
- Comments explain why, a constraint or a risk — not what obvious code does.
- Remove dead code, including empty packages and settings that nothing reads.
- Meet the configured coverage gate (80% branch coverage on the backend) on new and
  changed code without testing trivial details to inflate the percentage.
- The SonarQube, SOLID and pattern rules under [Development style](#development-style)
  apply to every change.

## Task boundaries

- Work on one `BACKLOG.md` item, or an explicitly assigned group, at a time.
- Do not change architecture, provider, database or public API without documenting
  the decision and receiving approval.
- Do not modify unrelated files or reformat the repository.
- Do not create speculative abstractions or unused extension points.
- Do not add a dependency without stating why the standard library or an existing
  dependency is insufficient.
- Do not silently change scope to make a test pass.
- Do not weaken, delete, skip or xfail tests to obtain green CI.
- Do not suppress lint, type, security or SonarQube findings without a narrow
  documented justification.
- Do not claim a command passed unless it was run and its result observed.
- Do not claim compliance, security or production readiness as an absolute.
- Do not restart superseded tasks (`PLAN.md` 5.3 and 7.2).

## Documentation rules

Documentation is part of the change.

- Keep `README.md` short: what the product does, one diagram, quick start and
  the documentation index. Development status belongs in `PLAN.md`, `BACKLOG.md`
  and the engineering journal. Detail lives in the page it links
  (`docs/running-locally.md`, `docs/architecture.md`, `docs/model-providers.md`
  and the rest). Keep commands and scope boundaries accurate.
- Keep `BACKLOG.md` current: add an item when you find open work, remove or tick it
  when its `PLAN.md` box is ticked. Do not restate acceptance criteria there — link
  the `PLAN.md` id.
- Tick `PLAN.md` checkboxes only after exit criteria are proven.
- Add or amend an ADR for consequential, hard-to-reverse choices.
- Update `docs/engineering-journal.md` at phase checkpoints with commands run and
  outcomes observed.
- Update `docs/threat-model.md` for security boundary changes.
- Update `docs/evaluation.md` for datasets, metrics, thresholds or results. When a new
  measurement supersedes an older one, say so next to the older one.
- Add a factual entry to the top of `AI_DEVELOPMENT_LOG.md` for agent-assisted work.

Never invent command output, test results, commit hashes, dates, metrics or review
actions. Use `TBD` until evidence exists.

## AI-assisted development rules

- AI suggestions are proposals, not authority.
- Explain material options and trade-offs before implementing an unrecorded decision.
- Never send real CVs, secrets, credentials or personal data to an AI service or a
  hosted model provider. Use the synthetic fixtures in `sample-data/`. When a log
  entry records a live model run, state which data it used.
- Inspect every AI-generated diff.
- Verify suggested APIs and security claims against installed versions or official
  documentation.
- Record rejected or materially changed suggestions, not only the successful output.
- Name the human-owned decision and validation in each significant entry.

## Required task report

```text
Task: (BACKLOG item and PLAN id)
Status: completed | blocked | partial
Branch:

Commits:
- <short hash> <subject>

Changed:
- files and purpose

TDD evidence:
- failing test and the observed expected failure
- passing focused test

Verification:
- exact commands run
- observed result summary

Security, SonarQube and design review:
- findings, mitigations, and any finding left open with its reason

Documentation:
- files updated

Residual risks or decisions needed:
- items, or "none"
```

Stop and ask when credentials, external writes, destructive actions, scope expansion
or a material product or architecture choice requires human authority.
