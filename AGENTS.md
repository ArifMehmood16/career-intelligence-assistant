# Instructions for Coding Agents

This file applies to the entire repository. Human instructions always take
precedence. `PLAN.md` is the authoritative execution order; `README.md` describes the
intended product and architecture.

## Mission

Build an evidence-bound career intelligence assistant as a simple, production-minded
modular monolith. The product's value is that every statement it makes about a
candidate traces to a span of text in a real document. Protect that property above
feature count.

Demonstrate senior engineering judgement through explicit trade-offs, secure
boundaries, reliable tests and clear documentation — not through additional
frameworks or services.

## The invariant

**The model extracts. The domain decides.**

- A language model may extract requirements from a job description and claims from a
  CV. It may phrase an answer.
- A language model may **not** produce the fit score, decide whether a requirement is
  met, or assert any fact about the candidate that is not backed by a stored span.
- Every requirement-to-evidence mapping carries the span identifiers that justify it.
  A mapping with no spans is `missing`, never a guess.
- If a change would let model output reach the user without passing the span check,
  stop and raise it. That is an architectural change, not an implementation detail.

- A provider is chosen, never assumed. The hermetic adapters are the default, the local
  and hosted adapters are equals behind the same port, and every one of them passes the
  same contract suite. Any behaviour that only works on one vendor is a bug in the port.

## Mandatory working protocol

For every task:

1. Read `README.md`, `PLAN.md`, `AGENTS.md` and the latest relevant entries in
   `AI_DEVELOPMENT_LOG.md`.
2. Locate the current phase and task in `PLAN.md`.
3. Inspect relevant code and tests before proposing edits.
4. Restate the selected task, acceptance criteria and expected files.
5. Identify assumptions or conflicts. Ask before making a material architectural
   choice that is not already approved.
6. Write or update the smallest failing test first.
7. Run it and confirm it fails for the expected behavioural reason.
8. Add the minimum implementation required to pass.
9. Run the focused test again.
10. Refactor only while the tests remain green.
11. Run the phase quality checks.
12. Inspect the complete diff for unrelated changes, security issues and unnecessary
    complexity.
13. Update the documentation the phase requires.
14. Draft a factual `AI_DEVELOPMENT_LOG.md` entry based only on work actually
    performed.
15. Stop at the phase checkpoint and report. Do not automatically begin the next
    phase.

If the environment cannot demonstrate the red test because the behaviour already
exists, explain why and add a regression test that would fail if the behaviour were
removed.

## Task boundaries

- Work on one unchecked `PLAN.md` task, or an explicitly assigned group, at a time.
- Do not start a later phase while an earlier exit gate is incomplete.
- Do not change architecture, provider, database or public API without documenting
  the decision and receiving approval.
- Do not modify unrelated files or reformat the repository.
- Do not create speculative abstractions or unused extension points.
- Do not add a dependency without stating why the standard library or an existing
  dependency is insufficient.
- Do not silently change scope to make a test pass.
- Do not weaken, delete, skip or xfail tests to obtain green CI.
- Do not suppress lint, type or security findings without a narrow documented
  justification.
- Do not claim a command passed unless it was run and its result observed.
- Do not claim compliance, security or production readiness as an absolute.

## Architecture rules

- Backend stays a modular monolith.
- `domain/` and `application/` must not import FastAPI, SQLAlchemy or provider SDKs.
- HTTP routes translate requests and responses and invoke use cases. No business
  logic in routes.
- Interfaces and protocols only at external or meaningfully variable boundaries.
- Provider implementations live in `adapters/` — the hermetic default, Ollama, OpenAI
  and Anthropic sit side by side behind the same port, with no vendor type escaping it.
  Adding a fifth must require no change outside `adapters/` and the configuration.
- Configuration is injected. Domain code does not read environment variables.
- Persistence models do not become domain models by convenience.
- Scoring lives in `domain/`, is pure, and is unit tested without a database or a
  model.
- Frontend stays feature-oriented. No global state unless genuinely shared.
- Prefer explicit Python and TypeScript over metaprogramming and framework magic.

## TDD standard

Red-green-refactor at behaviour boundaries.

- **Red:** one focused test expressing an acceptance criterion; confirm the failure
  is the expected one.
- **Green:** the smallest correct behaviour.
- **Refactor:** better names and structure with related tests green.

Prefer fakes at provider boundaries and real collaborators inside domain and
application code. Every production defect fixed gets a regression test first.

### Test layers

- **Unit:** parsing, requirement extraction contracts, evidence mapping, scoring
  rubric, prompt construction, intent routing.
- **Contract:** one suite every completion, embedding adapter must pass, run
  against recorded fixtures. No live vendor calls in any default test run.
- **API:** validation, status codes, response contracts, safe error mapping.
- **Integration:** PostgreSQL/pgvector, migrations, concrete adapters.
- **Component:** frontend interactions, accessibility, error and loading states.
- **End-to-end:** one critical journey — upload CV, add a job description, see the
  mapping, ask a gap question, open a citation — with deterministic providers.
- **Evaluation:** extraction and mapping quality against the labelled fixture set.
- **Smoke:** real Ollama provider, explicitly enabled, never in default runs.

Default tests are deterministic, repeatable and independent of paid APIs or public
network access.

## Security and privacy rules

Treat uploads, document text, questions, retrieved spans and model output as
untrusted.

- Never execute or evaluate uploaded content.
- Enforce configurable limits on file size, page/character count, question length,
  context size and model output.
- Allowlist accepted file types. Reject on content inspection, not extension alone.
- Job-description and CV text cannot issue instructions to the application or
  override the system prompt. Retrieved text is delimited and labelled untrusted in
  every prompt. Add a regression test for an injection attempt in a job description.
- Validate model output against a schema and verify every span reference against
  stored server-side spans before it reaches the user.
- Escape document excerpts in the browser. Never inject them as raw HTML.
- Parameterised database access, workspace-scoped queries.
- Return safe external errors. Never expose stack traces, prompts, secrets or
  provider payloads.
- Content leaves the machine only through the egress gate. A hosted adapter is
  constructible only when `ALLOW_HOSTED_PROVIDERS` is true and that provider's key is
  present. Never add a network call to a model vendor outside that chokepoint, and
  never make a hosted provider the default.
- API keys are read at construction, never logged, and never returned by any route —
  not even masked. Covered by the redaction test.
- Every answer and stored artefact records the provider and model tag that produced it
  and whether content left the machine. Removing that attribution is a security change.
- Never branch on a provider's name in the application. Read the capability descriptor
  and degrade deterministically.
- Do not log document text, raw uploads, embeddings, full prompts, credentials or
  model responses.
- Personal data: implement hard delete that removes documents, chunks, embeddings,
  extracted claims and mappings. Test that nothing survives it.
- Secrets in environment variables locally, a secret manager in production.

Update `docs/threat-model.md` when a trust boundary or control changes.

## Code quality rules

- Python typed at public boundaries; passes the configured Ruff and mypy checks.
- TypeScript strict mode; no unjustified `any`.
- Small functions, cohesive modules, descriptive names.
- Avoid boolean parameters that obscure behaviour.
- Avoid broad exception handling. Translate known infrastructure failures at
  boundaries and preserve causes internally without exposing them.
- Comments explain why, constraint or risk. Not what obvious code does.
- Remove dead code. No commented-out implementations.
- Meet the configured coverage gate on new and changed code without testing trivial
  details to inflate the percentage.

## Documentation rules

Documentation is part of the change.

- Keep `README.md` commands and scope boundaries accurate.
- Tick `PLAN.md` checkboxes only after exit criteria are proven.
- Add or amend an ADR for consequential, hard-to-reverse choices.
- Update `docs/engineering-journal.md` at phase checkpoints with commands run and
  outcomes observed.
- Update `docs/threat-model.md` for security boundary changes.
- Update `docs/evaluation.md` for datasets, metrics, thresholds or results.
- Add a factual entry to `AI_DEVELOPMENT_LOG.md` for agent-assisted work.

Never invent command output, test results, commit hashes, dates, metrics or review
actions. Use `TBD` until evidence exists.

## Branch and commit wording

Readable by someone who was not in the chat.

- Branches: lowercase hyphenated, include the phase number, one concern each.
  `feat/phase-5-requirement-extraction`, not `p4` or `wip`.
- Commits: imperative subject stating the change, not a file list. A short body when
  the why is not obvious. Conventional prefixes are fine.

Good: `feat(mapping): map job requirements to cited CV evidence spans`
Poor: `update`, `phase4`, `fixes`

## AI-assisted development rules

- AI suggestions are proposals, not authority.
- Explain material options and trade-offs before implementing an unrecorded decision.
- Never send real CVs, secrets, credentials or personal data to an AI service. Use
  the synthetic fixtures in `sample-data/`.
- Inspect every AI-generated diff.
- Verify suggested APIs and security claims against installed versions or official
  documentation.
- Record rejected or materially changed suggestions, not only the successful output.
- Name the human-owned decision and validation in each significant entry.

## Required task report

```text
Plan task:
Status: completed | blocked | partial

Changed:
- files and purpose

TDD evidence:
- failing test and expected failure
- passing focused test

Verification:
- exact commands run
- observed result summary

Security/quality review:
- findings and mitigations

Documentation:
- files updated

Residual risks or decisions needed:
- items, or "none"

Suggested branch:
Suggested commit:
```

Stop and ask when credentials, external writes, destructive actions, scope expansion
or a material product or architecture choice requires human authority.
