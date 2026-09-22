# TDD Delivery Plan — Career Intelligence Assistant

Operational source of truth. Execute phases in order. A phase is complete only when
its tests, documentation and exit gate are satisfied.

**Current position:** Phase 13C implementation tasks 13C.1–13C.10 are complete.
Its live exit gate has not been observed. 13D.1–13D.4 are implemented. 13D.5
has started: claim detail and requirement seniority round-trip through
PostgreSQL; a saved non-match stays missing after reload; the saved result
records provider, model, prompt version, rubric version, whether content left
the machine, and a failure status that marks an incomplete assessment apart
from a poor fit. Duplicate requirement text scores once. Unknown conditions
and contradictions cap coverage at partial, and a zero score from an incomplete
assessment is banded `incomplete` rather than `limited`. Overlapping jobs in
the same skill count as one stretch of time. Still open on 13D.5: stable ties
that name the differentiating requirements, and Fit, Gaps, Prepare and Letter
reading that saved result with no further model call on restart. The course-versus-leadership regression is
proven at the SQL boundary only. Hermetic analysis still uses the OR fallback.
13D's closure includes the outstanding 13C verification; do not claim either
gate has passed or start the full Phase 14 comparison before then.

## Product objective and quality priority

Rank job roles for one candidate using their CV, uploaded cover letters and the
actual job requirements. Explain the evidence, uncertainty and gaps behind each
rank. Keep Fit, Gaps, Prepare and Letter as consumers of that same analysis.

The immediate priority is accuracy of evidence assessment and role ordering.
More model calls, more prose, a higher score and passing fixture tests are not
substitutes for measured quality. Preserve the modular monolith, configurable
local/hosted providers and PostgreSQL system of record. Make continues to use
local PostgreSQL; Compose/deployment uses container PostgreSQL.

**Planning status:** Phase 13D records the proposed direction from the product
discussion, not a shipped feature or approval to send personal data to hosted
models. Before implementing changed scoring/cover-letter semantics, record the
decision and reconcile `AGENTS.md`, the feature contract and ADRs as specified in
13D.2. Earlier checked tasks remain implementation history; they are not proof
of ranking accuracy, nor should superseded unchecked 5.3/7.2 be restarted.

The Lovable frontend design has landed in `frontend/` and is the shipped frontend
([ADR 006](docs/adr/006-tanstack-start-frontend.md)).

Read alongside this plan:

| File | What it settles |
|---|---|
| [AGENTS.md](AGENTS.md) | The working protocol and the invariant |
| [docs/features.md](docs/features.md) | What each feature does and how it is used |
| [docs/api-contract.md](docs/api-contract.md) | The wire contract both halves are built against |
| [docs/frontend-integration.md](docs/frontend-integration.md) | How the Lovable app becomes the shipped app |

## How to use this plan

Start each agent session with:

```text
Read AGENTS.md, README.md, PLAN.md and AI_DEVELOPMENT_LOG.md.
Identify the first incomplete task in PLAN.md. Do not modify files yet.

Report:
1. the selected task and acceptance criteria;
2. relevant existing code and tests;
3. the tests to write first and why they should fail;
4. expected production files to change;
5. security or architectural considerations;
6. assumptions or decisions requiring approval.

Wait for approval before implementation.
```

After approving the proposal:

```text
Proceed only with the approved PLAN.md task and follow AGENTS.md.
Demonstrate red-green-refactor. Run focused verification, inspect the diff,
update the required documentation, and draft a factual AI_DEVELOPMENT_LOG.md entry.
Stop at the task checkpoint and give the required task report.
Do not commit or start the next task until I approve.
```

The human reviews the diff, confirms verification, approves the log entry, commits.

## Fixed technical direction

Approved for the initial implementation. A change requires an ADR and human approval.

| Area | Decision | Reason | Deferred alternative |
|---|---|---|---|
| Shape | Modular monolith | Clear boundaries without operational overhead | Services |
| Backend | Python 3.14+, FastAPI, Pydantic | Typed API, mature AI ecosystem | Node/NestJS |
| Frontend | TanStack Start (React 19, Vite, strict TS), as designed in Lovable | The design is the deliverable; the Start server carries the API proxy | Vite SPA |
| Frontend packages | `bun` | Lovable maintains `bun.lock` | npm |
| Store | PostgreSQL 16 + pgvector as the system of record | Original uploads, parsed documents, roles, mappings, drafts, questions, answers and vectors stay transactionally consistent | Dedicated vector DB or split object storage |
| Persistence | SQLAlchemy 2, Alembic; bounded originals in `bytea` | Explicit schema and migrations; the configured limits keep database-backed files small enough for this portfolio workload | Raw SQL or filesystem uploads |
| Model integration | Narrow ports with four adapters: hermetic, Ollama, OpenAI, Anthropic | Prove the abstraction, not one vendor. Hermetic is a test fixture so `make test` runs offline; it is never a product default | A single vendor SDK in the application |
| Extraction | Model-first, with every extracted item carrying a verbatim quote verified against the stored text; local Ollama by default | Deciding what counts as a requirement is a language task. A regex cannot do it, and the 2026-09-21 audit is the evidence | Deterministic parsing as the product default |
| Provider selection | Runtime workspace setting; hosted behind an explicit egress gate | The person asking should know where their text went | Deploy-time-only configuration |
| Credentials | Server configuration only; never accepted or returned by any route | A key in the browser is a key in a log | Bring-your-own-key in the UI |
| Long work | In-process job queue with a job resource the UI polls | Extraction takes minutes; it is a job, not a request | Celery, RQ |
| Orchestration | Direct use cases | Visible control flow | LangChain / LlamaIndex |
| Scoring | Deterministic rubric in domain code | Reproducible and explainable | Model-emitted score |
| Generated prose | Bound to cited spans, validated server-side, hermetic template fallback | A draft a person signs cannot contain invented facts | Prompt instructions alone |
| Extraction contract | JSON schema validated, spans verified server-side | Blocks fabricated experience | Free-text answers |
| Local run | Make uses the developer's local PostgreSQL through `DATABASE_URL`; Compose uses its PostgreSQL container | Both paths exercise the same migrations and adapters without silently starting a second database | SQLite or in-memory persistence |
| Deployment database | PostgreSQL 16 + pgvector container with a persistent volume, private network and required credentials | Matches development semantics while keeping database state outside disposable application containers | Embedded database |
| Tests | pytest, Vitest, React Testing Library, Playwright | Layered behaviour tests | — |

Model tags are configuration values, never hard-coded. Tests stay provider
independent.

## Global definition of done

- Acceptance criteria satisfied.
- The test was observed failing for the intended reason before implementation.
- Focused and related tests pass.
- Formatting, lint and type checks pass on changed code.
- Security implications reviewed.
- No unrelated changes.
- Documentation accurate.
- `AI_DEVELOPMENT_LOG.md` contains only verifiable facts.
- A small, coherent commit is ready.

---

## Phase 0 — Repository baseline and decisions

- [x] **0.1** Confirm the product scope and the invariant in `AGENTS.md` against
      `docs/features.md`; record any amendment before code exists.
- [x] **0.2** ADRs 001–005 written up: modular monolith, Postgres + pgvector,
      pluggable providers with a local default and an egress gate, deterministic
      scoring, provider selection as runtime state. ADR 006 (frontend) and ADR 007
      (grounded generation) exist — confirm they match what is about to be built.
- [x] **0.3** Fill `docs/threat-model.md`: trust boundaries for upload, document text,
      job-description text as untrusted input, model output, generated drafts and
      stored personal data.
- [x] **0.4** Create the synthetic fixture set — three CVs and six job descriptions in
      `sample-data/fixtures/`, covering: a clean match, a partial match, a poor match,
      a description with vague seniority signals, a description containing an
      injection attempt, and a CV with dated experience that exercises recency decay.
      Synthetic only — never a real person's CV.
- [x] **0.5** Define the evaluation dataset shape in `docs/evaluation.md` and stub
      `sample-data/evaluation/dataset.json`.
- [x] **0.6** Confirm the scoring rubric constants in `docs/features.md` are the
      starting values, and that they are configuration rather than literals.

**Exit gate:** decisions recorded, fixtures exist, no application code written.

## Phase 1 — Skeleton and quality gates

- [x] **1.1** `backend/pyproject.toml` with Ruff, mypy strict on the package, pytest
      with coverage; locked dependency install.
- [x] **1.2** Package skeleton `backend/src/career_assistant/` with `domain/`,
      `application/`, `adapters/`, `parsing/`, `matching/`, `generation/`,
      `evaluation/`, `ops/`.
- [x] **1.3** Frontend hygiene: delete `package-lock.json` (keep `bun.lock`), delete
      the empty `src/app/` directories, confirm `tsc --noEmit` and `bun run lint` pass
      on the Lovable output as delivered. Record anything that does not.
- [x] **1.4** Frontend test tooling: Vitest, Testing Library, jsdom, coverage, and a
      first component test against a Lovable component rendered from props.
- [x] **1.5** `Makefile` targets: `setup test lint typecheck run verify security`,
      covering both halves.
- [x] **1.6** Liveness endpoint with an API test. First backend red-green cycle.
- [x] **1.7** Architecture guard test: fail if `domain/` or `application/` imports
      FastAPI, SQLAlchemy or a provider SDK.
- [x] **1.8** Frontend guard: an ESLint rule failing the build on a hex colour or raw
      Tailwind palette class in `src/components/**`, and on a fixture import outside
      tests.
- [x] **1.9** CI workflow running lint, typecheck and the hermetic test suites on both
      halves.

**Exit gate:** `make lint`, `make typecheck` and `make test` pass on a clean clone
with no key, no database and no model download.

## Phase 2 — Model providers

Built before anything depends on it, so no later phase is written against one vendor's
shape. Extraction and phrasing are the only model-facing work in this product, so the
extraction contract is what every adapter is judged against.

- [x] **2.1** Completion port and embedding port. Small and use-case specific, with no
      vendor concepts in the signatures — no `messages`, no `tools`, no vendor error
      types leaking into the application.
- [x] **2.2** Capability descriptor per provider: structured-output support, context
      window, maximum output, embedding dimensions. The application reads capabilities
      and degrades deterministically. It never branches on a provider's name.
- [x] **2.3** Hermetic adapters as the default: a rule-based extractor and lexical
      hashing embeddings. No network, no keys, no downloads. *Hermetic exists so
      `make test` runs offline. Superseded as the product default by 13C.1.*
- [x] **2.4** Ollama adapter — local models, model tags from configuration.
- [x] **2.5** OpenAI adapter — completion and embeddings.
- [x] **2.6** Anthropic adapter — completion only. Embeddings stay on whichever
      provider is configured for them; the two ports are independent by design.
- [x] **2.7** One contract test suite that every adapter passes, against recorded
      fixtures rather than live calls: schema-valid structured output, refusal
      handling, oversized-input rejection, and stable behaviour for identical input.
      An adapter that cannot satisfy the contract is fixed or removed, not
      special-cased.
- [x] **2.8** Egress gate: a single enforced chokepoint decides whether content may
      leave the machine. A hosted adapter is constructible only when
      `ALLOW_HOSTED_PROVIDERS` is true and that provider's key is present. A test
      proves no adapter can reach the network around the gate.
- [x] **2.9** Resilience: per-provider timeout, bounded retry with backoff on 429 and
      5xx only, and a breaker that returns a safe error rather than hanging a request.
- [x] **2.10** Accounting: provider, model tag, input and output token counts, latency
      and estimated cost recorded per call. Identifiers and counts only, never content.
- [x] **2.11** Key handling: keys read at construction, never logged, never returned by
      any route in any shape including masked, covered by the redaction test.
- [x] **2.12** Fallback policy: a hosted provider that fails does not silently fall
      back to a local model. If it falls back, the response says so.

**Exit gate:** every adapter passes the same contract suite; `make test` stays
hermetic and needs no key; the egress test proves hosted providers are unreachable
while the gate is closed.

## Phase 3 — Document intake and spans

- [x] **3.1** Domain model for a document, a page/section and a **span** (stable id,
      offsets, text). Spans are the citation unit for the whole product.
- [x] **3.2** PDF text extraction with span offsets preserved.
- [x] **3.3** DOCX text extraction with span offsets preserved.
- [x] **3.4** Plain text and pasted-text intake.
- [x] **3.5** Admission policy: type sniffing, size cap, page cap, character cap,
      safe rejection messages mapped to the error codes in `docs/api-contract.md`.
- [x] **3.6** Normalisation: whitespace, ligatures, bullet glyphs, hyphenation at line
      breaks. Offsets must survive normalisation — test it.
- [x] **3.7** Span resolution: a span id returns the exact source text and the page it
      sits on, and `highlight` is always an exact substring of the returned paragraph.

**Exit gate:** a fixture CV parses to spans; a span id round-trips to the exact source
text. Malformed, encrypted and oversized files are rejected safely.

## Phase 4 — Persistence

- [x] **4.1 Database topology and configuration contract.** PostgreSQL 16 with
      pgvector is the only production persistence implementation. `make run`, Alembic
      and `make test-integration` use the local instance named by `DATABASE_URL`
      (documented default `localhost:5432`). Compose API containers use the `db`
      service on port 5432. Fakes are test-only; no SQLite, filesystem or in-memory
      production fallback.
- [x] **4.2 Database packages and Alembic baseline migration.** Add the minimum
      SQLAlchemy 2, Alembic, psycopg 3 and pgvector packages to the runtime lock. Create
      `vector` and the tables for workspaces; documents; spans; chunks; embeddings;
      roles; requirements; claims; mappings and score explanations; analysis jobs;
      conversations; questions; answers; answer citations; generated drafts and draft
      citations; provider settings; and provider-call accounting.
- [x] **4.3 Original document storage.** `documents` records `kind` (`cv`,
      `job_description`, `cover_letter`), filename, sniffed media type, byte length,
      SHA-256, original bytes in bounded `bytea`, normalised text, parse status and
      timestamps. Pasted text is stored as UTF-8 bytes. Rejected or unreadable input
      is not retained. Uploaded cover letters are supporting documents: queryable and
      citable, but never evidence for claims, fit mappings or scores.
- [x] **4.4 Relational integrity and indexes.** UUID primary keys; UTC timestamps;
      foreign keys with deliberate delete behaviour; a partial unique constraint for
      one active CV per workspace; uniqueness for one role analysis version; indexes
      beginning with `workspace_id`; vector dimensions tied to the recorded embedding
      provider/model. Migration upgrade and downgrade are tested from an empty
      database.
- [x] **4.5 Repository adapters behind application ports.** Application and domain
      code depend on narrow repositories; SQLAlchemy models do not cross the adapter
      boundary. A guard test proves no non-adapter import of SQLAlchemy. Every API and
      worker read after Phase 4 comes from PostgreSQL, not process memory.
- [x] **4.6 Transaction boundaries.** An admitted upload, its document metadata,
      original bytes and parsed spans commit atomically. Establish an explicit
      SQLAlchemy unit-of-work for later analysis and answering use cases. A failed
      parse leaves no half-readable document. Phase 8 and Phase 9 add forced-failure
      tests for their complete mapping and answer transactions.
- [x] **4.7 Workspace scoping.** Every repository method requires `workspace_id` and
      every query filters it. Integration tests attempt cross-workspace reads and
      mutations for documents, roles, spans, drafts, conversations and messages.
- [x] **4.8 Hard delete and retention graph.** Deleting a CV, uploaded cover letter or
      role removes its original bytes, spans, chunks, embeddings, claims,
      requirements, mappings, scores, jobs, generated drafts, questions/answers and
      citations that depend on it. Deleting chat history removes questions, answers
      and citations. Integration tests assert zero orphaned personal data.
- [x] **4.9 Provider and provenance persistence.** Store the workspace provider
      preference plus provider, model tag, `left_machine`, token counts and timing on
      each extraction, answer and generated draft. Never store keys or raw provider
      payloads.
- [x] **4.10 CV replacement transaction.** Replacing the CV stores the new admitted
      document, makes it active and invalidates every existing role mapping, score and
      draft atomically; the old CV and its dependent records are hard-deleted only
      after the replacement succeeds. Phase 8 adds re-analysis job creation to this
      same unit of work.
- [x] **4.11 Conversation schema contract.** Enforce foreign keys, a workspace-scoped
      unique `client_request_id` on each question, at most one final answer per
      question, and unique `(answer_id, span_id)` citations. Phase 9 adds the
      repositories/use case once the answer domain behaviour exists; partial streaming
      tokens and provider payloads have no persistence column.
- [x] **4.12 Local database workflow.** Add `make db-check`, `make db-migrate` and a
      migration step to `make run`; they use the developer's local PostgreSQL and fail
      clearly when PostgreSQL, the target database or pgvector is unavailable.
      `TEST_DATABASE_URL` must name a separate database and integration tests refuse
      to run when it equals `DATABASE_URL`.
- [x] **4.13 Connection safety.** Configure bounded pooling, connection health checks,
      statement/lock timeouts and UTC sessions. Dispose sessions at each unit-of-work
      boundary. SQL logging is off by default and must never print bound values that
      could contain document, question or answer text.

**Exit gate:** migrations upgrade and downgrade on a clean PostgreSQL 16 + pgvector
database; integration tests prove scoped round-trips for original CV and cover-letter
bytes plus spans, replacement invalidation, conversation/message constraints and
zero-residue document deletion. `make run` uses the local PostgreSQL instance; no
production path falls back to memory or SQLite.

## Phase 5 — Requirement extraction

- [x] **5.1** Domain type `Requirement`: text, competency, seniority signal, must-have
      or desirable, source span, extraction confidence.
- [x] **5.2** Extraction port and a deterministic rule-based adapter (default,
      hermetic) that handles bulleted requirement lists. *Superseded as the product
      default by 13C.2; retained as the hermetic test fixture only.*
- [ ] **5.3** *Superseded by 13C.2.* The delivered implementation ran the rule
      extractor first and then discarded every model requirement whose text was not
      already in the rule output, taking competency, seniority and spans from the
      rules result. The model could only remove what the regex had already found; it
      could never extract a requirement the regex missed.
- [x] **5.4** Output validation: reject any requirement whose source span does not
      resolve to stored text. Drop it, count it, never pass it through.
- [x] **5.5** Prompt-injection regression test: a job description containing
      instructions to the model does not change extraction behaviour.
- [x] **5.6** Vague-requirement detection: a requirement with a seniority or scope
      signal the description never quantifies is marked as such. This feeds
      "what to ask them" in the interview pack, so it is data, not a heuristic in the
      view. *Folded into the typed extraction schema in 13C.2.*
- [x] **5.7** Requirements are extracted only from the stored job-description
      document for that role. An uploaded cover letter cannot contribute a requirement
      or alter a role analysis.

**Exit gate:** six fixture job descriptions produce requirement sets; every
requirement resolves to a real span; the injection fixture changes nothing.

## Phase 6 — Evidence extraction

- [x] **6.1** Domain type `Claim`: competency, context, duration signal, recency
      signal, source spans.
- [x] **6.2** Rule-based adapter as the default; model-backed extraction through the
      Phase 2 port, schema validated on every provider. *Superseded as the product
      default by 13C.3 for the same reason as 5.3; retained as the test fixture.*
- [x] **6.3** Span verification identical to 5.4.
- [x] **6.4** Recency and duration derived from dates in the CV, in domain code, not
      by the model. Undated experience is treated as undated, never assumed recent.
- [x] **6.5** Candidate claims are extracted only from the active stored CV. Uploaded
      or generated cover letters are self-authored prose, not independent evidence,
      and are excluded from claims, mappings and scores by a regression test.

**Exit gate:** fixture CVs produce claim sets with resolvable spans and derived
recency, including the dated-experience fixture.

## Phase 7 — Mapping and scoring

- [x] **7.1** Mapping policy in `domain/`: requirement × claims → `met`, `partial`,
      `missing`, with the justifying span ids and a reason code
      (`no_related_claim`, `adjacent_claim_only`, `evidence_too_old`,
      `evidence_thin`). Pure function, no I/O.
- [x] **7.2** *Superseded by 13C.5.* Mapping computes `(requirement_id, claim_id)`
      cosine similarities and treats `similarity >= similarity_floor` as related, with
      status still decided by domain policy — but the floor is a guessed 0.55 over
      64-dimension hermetic hash vectors, which is a lexical signal wearing a vector
      costume. Three-signal matching replaces it; Phase 14 calibrates the floor.
- [x] **7.3** Deterministic rubric: must/desirable weights, status factors, recency
      decay, normalisation and bands exactly as documented in `docs/features.md`, read
      from configuration. Pure, unit tested.
- [x] **7.4** Property tests: identical inputs give an identical score; adding a met
      requirement never lowers the score; every score is in 0–100.
- [x] **7.5** Explanation object: every score component traceable to the mapping
      entries that produced it. This is what `GET /roles/{id}/breakdown` returns.
- [x] **7.6** Counterfactual: score recomputed with one requirement set to met, as a
      pure function. This is the `scoreDelta` the gap plan orders by.

**Exit gate:** a fixture CV against a fixture role yields a stable score, a full
explanation and correct deltas, with no model call.

## Phase 8 — Analysis jobs

Extraction against a local or hosted model takes seconds to minutes. Making the user
wait on a request is the wrong shape, and so is pretending it is instant.

- [x] **8.1** Job domain type and states: `queued`, `running`, `succeeded`, `failed`,
      with a stage and an error reason.
- [x] **8.2** In-process worker with a bounded dispatcher and PostgreSQL-backed job
      records. No Celery or Redis. On startup, persisted `queued` jobs are dispatched;
      stale `running` jobs are deterministically failed or re-queued according to an
      explicit timeout policy; no job remains permanently running after a process
      restart.
- [x] **8.3** Role analysis pipeline as a job: parse → extract requirements → extract
      claims → map → score, each stage recorded.
- [x] **8.4** Failure attribution: a failed job names the stage and a safe reason.
      Partial results are discarded, not shown as a low score.
- [x] **8.5** Re-analysis: replacing the CV or changing the index provider enqueues
      re-analysis for every affected role in the same database transaction that
      invalidates the stale mapping.
- [x] **8.6** Idempotence: the same role analysed twice produces the same stored
      mapping, and a duplicate enqueue does not double-run.
- [x] **8.7** Publish analysis results transactionally: requirements, claims,
      mappings, score explanation and terminal job state become visible together.
      Readers never see partial results as a low score.

**Exit gate:** adding a role returns immediately; the job completes and the role
becomes `ready`; a forced failure leaves the role `failed` with a reason and no
partial mapping.

## Phase 9 — Question answering

- [x] **9.1** Deterministic intent router: gaps, fit, compare roles, evidence for a
      requirement, interview preparation, open question.
- [x] **9.2** Structured intents answer from the stored mapping. No vector search.
- [x] **9.3** Open questions use workspace-scoped retrieval over spans.
- [x] **9.4** Prompt construction: retrieved text delimited and labelled untrusted;
      budgets for question, context and output.
- [x] **9.5** Answer validation: every citation resolves to a stored span or the
      answer is reduced to insufficient evidence before it is sent.
- [x] **9.6** Comparison across multiple roles returns a ranking derived from stored
      scores, with the differentiating requirements named.
- [x] **9.7** Streaming: the same use case serves a streamed and a non-streamed
      response, with citations validated after the text completes.
- [x] **9.8** Persist the user question before processing, then persist exactly one
      final validated answer or insufficient-evidence result with citations,
      provider/model provenance and `left_machine`. Never persist partial SSE tokens
      as the answer. A repeated `clientRequestId` returns the existing result.
- [x] **9.9** Stored history survives an API restart and is returned in deterministic
      order. Deleting history hard-deletes the conversation, questions, answers and
      citations. Failed attempts retain only a safe status/code, never provider
      payloads or partial generated text.
- [x] **9.10** Open-question retrieval may cite uploaded cover letters when the user
      asks about them, but those spans remain excluded from fit scoring and candidate
      evidence. Role-scoped questions cannot retrieve another role's description.

**Exit gate:** the example questions in `README.md` answer correctly on fixtures, each
with resolvable citations; an unanswerable question returns insufficient evidence; the
streamed and non-streamed answers to the same question agree; persisted history and
citations survive an API restart; retrying a request does not duplicate it.

## Phase 10 — Grounded generation

Everything here is governed by [ADR 007](docs/adr/007-grounded-generation.md). Build
the validator first; the features are built against it, not retrofitted to it.

- [x] **10.1** Groundedness validator in `domain/`: given draft text and the cited
      spans, extract every number, date, duration, percentage, employer, product and
      technology token from the draft and assert each appears in the spans after
      normalisation. Pure, unit tested against adversarial fixtures — a changed
      figure, an added technology, an inflated duration, a renamed employer.
- [x] **10.2** Generation pipeline: build input from stored claims and spans → phrase
      through the completion port → validate → regenerate once on failure → fall back
      to template. Provenance recorded at every step.
- [x] **10.3** **Gap plan** — fully deterministic, no model. Ordered by `scoreDelta`,
      with reason code, adjacent evidence and action category.
- [x] **10.4** **CV bullets** — per requirement, from the claims that relate to it.
      Hermetic template path first, then the model-phrased path through 10.2.
- [x] **10.5** **Interview pack** — probes, evidence to lead with, thin areas, and
      questions to ask them. Section membership decided in domain code from the
      mapping and from 5.6; phrasing may come from the model.
- [x] **10.6** **Cover letter** — structured from met requirements, one paragraph per
      requirement with its spans, optional honest gap line. Refuses below two met
      must-haves with `insufficient_matched_requirements`.
- [x] **10.7** Markdown export for every artefact, byte-identical to what the screen
      shows.
- [x] **10.8** Counters: validator failures, regenerations and template fallbacks, per
      provider. These are the numbers Phase 14 reports.
- [x] **10.9** Store every final generated artefact in PostgreSQL with its input role
      analysis version, cited spans, groundedness result and provenance. Regeneration
      creates a new immutable version; only validated or template-fallback content is
      persisted. Uploaded cover letters remain separate `documents`.

**Exit gate:** every artefact generates on fixtures under the hermetic default with no
model; the adversarial validator fixtures all fail closed; the cover letter refuses
when it should.

## Phase 11 — API contracts

Built against [docs/api-contract.md](docs/api-contract.md). Where code and that file
disagree, the file is corrected first and the change is deliberate.

- [x] **11.1** Explicit Pydantic response models for every route, camelCase on the
      wire. No bare `dict`.
- [x] **11.2** Workspace cookie issuance and scoping on every route.
- [x] **11.3** Reject oversized uploads before buffering the whole body.
- [x] **11.4** Safe error mapping to the documented code table: no stack traces,
      prompts, file paths or provider payloads.
- [x] **11.5** Readiness endpoint reporting database, migration and provider state.
- [x] **11.6** Correlation id on every request, echoed in responses and logs.
- [x] **11.7** Provider endpoints: list with availability and the reason any is
      unavailable; set the workspace choice. Hosted selection is rejected server-side
      without `acknowledgedEgress`, so the confirmation is not only a UI convention.
- [x] **11.8** Job, gap plan, interview pack, bullets, cover letter, export, ranking,
      compare and span routes. Hermetic in-memory API surface; SqlCvStore /
      SqlRoleStore (create/list/get/delete/reanalyse + durable drafts);
      `create_production_app` wires SQL stores for uvicorn/Docker while
      `create_app()` stays hermetic for API tests.
- [x] **11.9** SSE answer stream with the documented event sequence
      (`meta` → `token`* → `citations` → `done`) on `POST /api/messages` with
      `Accept: text/event-stream`, driven by the existing AskService (not a second
      implementation). JSON Accept and GET/DELETE remain for 11.13.
- [x] **11.10** Every answer and every draft response carries the provider, the model
      tag and whether content left the machine. SSE `meta` includes `leftMachine`;
      JSON `POST /api/messages` returns `ChatMessage` with the same fields; draft and
      interview-pack `provenance` covered by API regression.
- [x] **11.11** Contract test: the generated OpenAPI schema and
      `frontend/src/types/index.ts` agree on every shared model, including the
      `spanId` required to open every `Evidence` citation.
- [x] **11.12** Supporting-document routes: list/upload/delete uploaded cover letters
      and download an original document by id, all workspace-scoped. Responses expose
      metadata, never database paths or storage internals. Generated cover-letter
      routes remain role-scoped and distinct.
- [x] **11.13** Message routes expose persisted conversation history. `POST` requires
      `clientRequestId`; both JSON and SSE transports return the same stored final
      answer id. `DELETE` performs the hard-delete contract.

**Exit gate:** OpenAPI is accurate; API tests cover each status path in the error
table. (`rate_limited` and `provider_failed` have no dedicated HTTP surface yet —
mapped in SSE framing / deferred until a rate-limit middleware and live provider
failure path land.)

## Phase 12 — Frontend integration

The screens exist. This phase makes them real. See
[docs/frontend-integration.md](docs/frontend-integration.md).

- [x] **12.1** **Spike first:** prove a `text/event-stream` response and a
      `MAX_UPLOAD_BYTES` multipart upload both pass through a TanStack Start server
      route without buffering. Record the result. If either fails, take the
      direct-origin-plus-CORS fallback and add a follow-up entry to ADR 006 before
      continuing.
      - Result (2026-09-18): **pass.** `proxyToUpstream` delivers the first SSE
        event before upstream finishes, and forwards a streaming request body
        (representative of `MAX_UPLOAD_BYTES`) so upstream reads the first byte
        before the client stream closes. No ADR 006 follow-up required.
- [x] **12.2** Catch-all server route proxying `/api/**` to `API_BASE_URL`, forwarding
      method, headers, body, cookie and stream. `Origin` checked on every non-`GET`.
      `API_BASE_URL` is a server variable, never `VITE_*`.
- [x] **12.3** Replace `src/api/client.ts` with a real HTTP client keeping the existing
      exported signatures: one `request()`, the typed `ApiError` carrying `code` and
      `correlationId`, and zod validation of every response.
- [x] **12.4** Move fixtures to `src/api/__fixtures__/` for tests and the state
      gallery. No component imports a fixture.
- [x] **12.5** Additive types in `src/types/index.ts` — `RoleStatus`, `AnalysisJob`,
      `GapPlan`, `GapItem`, `InterviewPack`, `BulletDraft`, `CoverLetterDraft`,
      `RankedRole`, `Comparison`, `DraftProvenance`, persisted message fields and
      supporting documents. (`Evidence.spanId` and `ChatMessage.leftMachine` already
      landed in 11.11.)
- [x] **12.6** Wire the workspace: CV upload with real progress and real rejection
      messages, supporting cover-letter upload/list/delete, add role, delete and
      replace-CV confirmation. Make clear that cover letters are not score evidence.
- [x] **12.7** Analysis job polling with react-query; the role list shows `Analysing`,
      then the score, or `Failed` with the reason and a retry.
- [x] **12.8** Wire role detail: requirements, breakdown, evidence panel resolving
      spans through `GET /api/spans/{id}`.
- [x] **12.9** Wire Ask against the SSE stream, including stop, citation chips,
      insufficient-evidence state, persisted history after reload, delete-history and
      the provider stamp. Client retries reuse the same `clientRequestId`.
- [x] **12.10** Wire settings: provider list with real availability reasons, the
      hosted confirmation, and the re-index warning when the index provider changes.
- [x] **12.11** Error handling across the app: every documented error code maps to a
      state the user can act on. Unknown codes fail visibly, not silently.
- [x] **12.12** Component tests for every state of every wired screen, driven by props.

**Exit gate:** ~~the full existing UI runs against the real backend with fixtures
loaded, including the failure paths. No mock data remains in `src/api/client.ts`.~~
**Met 2026-09-18** — host API (`create_production_app` + SQL CV/role stores) and
TanStack Start proxy with `API_BASE_URL`; sample-data CV/JD via proxy; browser
workspace → add role → role detail; failures: empty upload, JPEG reject,
`span_not_found`, Ask `analysis_incomplete` → 409. No fixtures in `client.ts`.
SQL supporting cover-letter store landed at the start of Phase 13 (was
in-memory on the production entrypoint through Phase 12). Playwright walkthrough
is Phase 16.5.

## Phase 13 — Frontend: the new features

New screens, built in the existing design language. No new tokens, no new visual
patterns. See [docs/features.md](docs/features.md) for what each one shows.

- [x] **13.1** Role detail gains tabs: Fit, Gaps, Prepare, Letter. Keyboard
      navigable, deep-linkable.
- [x] **13.2** **Gaps**: ordered gap list with reason, adjacent evidence, score delta
      and action. "Draft a bullet" where the evidence exists.
- [x] **13.3** **Bullet drafts**: the draft, its citation chips, the provenance line,
      copy, and the visible template-fallback state.
- [x] **13.4** **Prepare**: the four sections, each evidence line clickable to its
      span, export.
- [x] **13.5** **Letter**: tone and gap-line controls, paragraphs with citations,
      persisted version history, export, and the refusal state rendered as a next step
      rather than an error. Uploaded cover letters are shown separately as supporting
      documents, never as generated versions.
- [x] **13.6** **Ranking** on the workspace: roles ordered with the reason named, ties
      shown as ties.
- [x] **13.7** **Compare**: two roles side by side, shared and unique requirements,
      the differentiator.
- [x] **13.8** Fill `/dev/states`: every component state on one page, rendered from
      props.
- [x] **13.9** Accessibility: keyboard path through upload, tabs, table, drafts and
      chat; labels, focus management and live regions for streaming and job progress,
      tested.
- [x] **13.10** Excerpts and generated text rendered as escaped text, never HTML.

**Exit gate:** `bun run lint`, `tsc --noEmit` and component tests pass; every state in
`/dev/states` has a test.

## Phase 13A — Pre-evaluation logic and production-wiring remediation

This is a mandatory audit-remediation gate, not new product scope. Phase 13's UI
slice is complete, but the 2026-09-18 logic audit found that several earlier phase
contracts exist in isolated domain/repository tests without being used by the
production HTTP path. Close these gaps before Phase 14 so evaluation measures the
real application.

- [x] **13A.1 Restore the complete quality baseline.** Format
      `application/ports/persistence.py`, then run the exact repository lint,
      typecheck, hermetic and PostgreSQL integration targets. Keep generated Alembic
      migrations outside Ruff's hand-written-source target; do not broaden or weaken
      the configured checks merely to obtain green output. Record the two current
      third-party deprecation warnings and either remove them through compatible
      dependency upgrades or carry them as an explicit Phase 15 maintenance risk.
- [x] **13A.2 Make PostgreSQL the production source of truth for chat and provider
      settings.** Add application adapters over the existing conversation repository
      and `provider_settings` table, including selected model tags; wire them through
      `build_sql_stores` / `create_production_app`. Remove production fallbacks to
      `InMemoryConversationStore` and `app.state.provider_choices`. Prove through the
      HTTP surface that questions, final answers, citations, idempotent retries,
      deletion and provider choices survive construction of a fresh app process and
      remain workspace-scoped.
- [x] **13A.3 Use the PostgreSQL-backed analysis worker in production.** Adding or
      reanalysing a role must commit an `analysing` role and queued job, return 202
      before extraction completes, and let the bounded worker publish results or a
      safe failure transactionally. Wire startup recovery for persisted queued and
      stale-running jobs. CV replacement must invalidate stale results and enqueue
      every affected role in the same transaction, return those job ids, and never
      leave a role marked `ready` with a missing or stale score; CV deletion needs an
      equally explicit non-ready/deletion outcome. Add production-path tests for
      queued/running/succeeded/failed states, restart recovery and no partial results.
- [x] **13A.4 Make provider selection affect actual work.** Resolve the persisted
      workspace choice through the Phase 2 factories for requirement extraction,
      claim extraction, open-question answers and generated phrasing. Keep the
      completion and embedding choices independent, enforce the hosted egress gate at
      construction and call time, and persist truthful provider/model/`left_machine`
      provenance plus accounting. Remove hard-coded hermetic provenance from routes;
      tests must use scripted adapters to prove the selected provider is called and a
      rejected hosted choice makes no network attempt.
- [x] **13A.5 Complete database-backed retrieval and span resolution.** Open questions
      may retrieve workspace-scoped spans from the active CV and uploaded supporting
      cover letters, while role-scoped retrieval may additionally use only that
      role's job description. A single workspace-scoped span resolver must open every
      citation emitted by Ask or generated artefacts, not only active-CV spans.
      Preserve the hard boundary that cover-letter text cannot become a claim,
      mapping or score input. Cover this through production HTTP tests, including
      cross-workspace and cross-role rejection.
- [x] **13A.6 Route all generated prose through the grounded-generation use case.**
      Bullet, interview-pack and cover-letter HTTP routes must call the Phase 10
      generation pipeline, verify citations against stored spans, run the
      groundedness validator, retry/fall back as specified and persist the real
      verdict. The SQL draft adapter must never replace an untrusted or failed verdict
      with `PASS`. Either implement the Letter tab's tone and honest-gap-line inputs
      through this validated path or remove the controls until they are real. Refuse
      a bullet when no cited claim supports it instead of persisting an uncited
      instruction as a grounded draft.
- [x] **13A.7 Correct ranking, comparison and immutable-version export.** Equal scores
      receive the same displayed rank with deterministic competition ranking; the
      comparison differentiator must identify an actual status/score distinction,
      not the first shared requirement alphabetically. Export the exact cover-letter
      version selected on screen (and define the same rule for bullet versions), with
      byte-for-byte API and component regressions.
- [x] **13A.8 Close frontend asynchronous and failure-state gaps.** Role detail must
      render explicit not-found, failed and analysing states rather than an indefinite
      header skeleton plus failing child queries. Fetch tab-specific resources only
      when the role is ready and the tab is active. Surface generated/supporting
      letter, role-list/compare, clipboard and export failures with retryable UI
      states; do not show a successful empty state while its query failed.
- [x] **13A.9 Reconcile claims and documentation with observed behaviour.** Update the
      stale README status, API contract, architecture/provenance documentation,
      threat model and engineering journal after the fixes are proven. Add a
      production-wiring matrix that names each route's application use case, provider
      resolver and SQL adapter so an isolated tested implementation cannot be mistaken
      for a wired feature again.

- [x] **13A.10 Wire embedding similarity into requirement mapping.** PLAN 7.2
      accepted a similarities dict the policy never reached: `_is_related`'s
      third branch required overlap the second branch already returned on, the
      dict was keyed by claim id alone, and no caller computed vectors. Map
      with `(requirement_id, claim_id)` scores; treat `similarity >= floor` as
      related with no overlap condition; compute one batched embed of uncached
      requirement text and claim context per analysis (cache by owner, provider,
      model and text sha256). Exact cosine in Python — no chunk table, no ANN
      index, no Ask retrieval change. Persist unconstrained vectors; changing
      the index provider re-embeds; CV hard delete leaves zero embeddings;
      a closed hosted gate makes no network attempt and does not fail the job.
**Exit gate:** exact `make lint`, `make typecheck`, `make test` and
`make test-integration` targets pass. A production-app test using PostgreSQL proves
chat, provider choice, roles, jobs, uploaded supporting letters, citations and drafts
survive an app restart. An observable queued job becomes ready through the bounded
worker; a forced failure exposes no partial analysis. A scripted non-hermetic provider
proves runtime selection and truthful provenance. An invalid generated claim fails
closed. A direct question retrieves and opens a supporting-letter citation without
changing any fit score. Ties, comparison differentiators and selected-version export
are deterministic and covered at API and component level. Only then begin Phase 14.

## Phase 13B — Operational logging (console)

The production process had no application loggers. Uvicorn access lines (when they
appear) are not enough to see intake, analysis stages, persistence or provider
choice. Add stdlib logging to stdout/stderr so `make run-api` shows what the
process is doing. Do not add a logging framework.

**Invariant:** logs are operational, not dumps. Never write document text, raw
uploads, questions, answers, embeddings, prompts, draft bodies, credentials or
model payloads. Do not serialise request/response DTOs. Log field names, entity
ids, counts, durations, stages, provider ids and safe error codes only.

- [x] **13B.1 Process logging.** Configure the `career_assistant` logger at
      INFO to stderr (same stream as uvicorn), unbuffered, with correlation and
      workspace ids on every line. Re-apply after uvicorn's own logging setup so
      the reloader does not swallow application logs. `PYTHONUNBUFFERED=1` on
      `make run-api`.
- [x] **13B.2 HTTP layer.** Middleware logs method, path, status and duration for
      every request. Exception handlers log the contract error code, not the
      request body. Query strings that are only ids (compare, export version) may
      appear; bodies must not.
- [x] **13B.3 Application / use cases.** Log CV admit, cover-letter admit, role
      create/delete/reanalyse, Ask, and grounded generation as events with
      document/role/job ids, byte length, page count and span count — never
      filename-as-content or parsed text.
- [x] **13B.4 Persistence adapters.** SQL CV, supporting-document, role, job and
      conversation adapters log the operation name and ids. SQLAlchemy `echo`
      stays off; `hide_parameters` stays true.
- [x] **13B.5 Analysis worker.** Log claim, each recorded stage, success and
      safe failure (stage + code). No extracted requirement text, claim text or
      mapping excerpts.
- [x] **13B.6 Config, security, providers.** Startup logs completion/embedding
      provider ids, hosted-egress boolean and database host:port — never URLs
      with passwords or API keys. Provider factory logs which adapter was
      constructed. A redaction test fails if a planted document phrase or key
      appears in any captured line.
- [x] **13B.7 Documentation.** Threat model, README `make run-api` note and
      engineering journal record the log contract.

**Exit gate:** focused redaction and HTTP-log tests pass; `make run-api` prints
application lines for a CV upload and a queued role job without document text.
`make lint` and the hermetic backend tests stay green.

## Phase 13C — Model-first extraction, matching and output

The 2026-09-21 output audit ran the maintainer's real CV and a real job advert through
the shipped pipeline. The results are why this phase exists:

- The claim extractor produced **zero claims**. `pypdf` emits bullets as `•Text`
  with no following space; normalisation rewrites that to `-Text`; the bullet pattern
  requires whitespace after the glyph. Every requirement therefore mapped to `missing`
  and the fit score was 0.
- With that one character corrected it produced **4 claims out of roughly 14**, all
  from the first role. `_SECTION_STOP` matched a wrapped line that happened to begin
  with the word "education", ending experience parsing at the second job.
- Every claim came out `undated`, because `pypdf` puts role dates on the role line and
  the parser expects them on a line of their own.
- The advert produced **18 requirements, all must-have, all competency `general`**,
  including the salary band, share options, the remote-working policy, the
  right-to-work line, and the three bullets under *What this role is not*.
- With claims present the mapping then reported **11 met, 7 partial** — asserting the
  candidate *meets* "£70,000 - £80,000 depending on experience".

The scoring layer was never the problem, and it does not change. Deterministic,
explainable scoring is the one thing here a reviewer has not seen elsewhere. What
changes is everything upstream of it: deciding what counts as a requirement is a
language task, and a hermetic test fixture should never have been what a real user
hits.

- [x] **13C.1 Make a real model the default and demote the hermetic path.** A running
      instance defaults to a local Ollama model for completion and embeddings.
      Hermetic becomes a fixture the test suite selects and no user-facing
      configuration offers. `EXTRACTION_STRATEGY` is currently written in
      `config/app.env` and read nowhere in the code — make it real or delete it and
      every document that mentions it. `make test` still runs offline with no key and
      no model download.
- [x] **13C.2 Typed requirement extraction with verified quotes.** The model returns,
      per item: a verbatim `quote` from the advert, an `item_type` of `requirement`,
      `responsibility`, `benefit`, `logistics` or `non_requirement`, must vs
      desirable, a competency from an open vocabulary, a seniority signal and a
      vagueness flag. Each quote is located verbatim in the stored normalised text and
      the span is built from those offsets; anything that does not verify is dropped
      and counted, per 5.4 — never repaired, never fuzzy-matched. Only `requirement`
      and `responsibility` items reach the mapping, so a salary line, a benefit or a
      "this role is not" bullet can never be scored. The 5.5 injection fixture must
      still change nothing: verbatim verification is the defence.
- [x] **13C.3 Structured CV extraction.** The model returns roles with employer, title
      and date range, and claims beneath them carrying competency, scope, technologies,
      outcome and a verbatim quote. Dates are parsed and recency and duration derived
      in domain code, never supplied by the model — 6.4 still holds. Every role in the
      document is extracted, not only the first. Span verification and the drop count
      are identical to 13C.2.
- [x] **13C.4 Cover letter as narrative evidence.** An uploaded cover letter is
      extracted into the same structured shape and flagged self-authored. It stays
      excluded from claims, mappings and the fit score — 4.3, 5.7 and 6.5 stand — and
      becomes available to letter drafting, interview preparation and Ask. A
      regression proves an uploaded letter is citable and changes no score.
      *Review correction: the extractor supports letters, but the SQL analysis
      worker still extracts only the CV. Production narrative use and the proposed
      evidence policy are addressed in 13D.2, 13D.3 and 13D.4; this checkbox does not prove
      uploaded-letter extraction is wired into drafting and preparation.*
- [x] **13C.5 Three-signal matching.** A requirement and a claim are related by any of
      three signals: lexical overlap, embedding cosine, and model adjudication for the
      pairs the first two disagree on. Each signal is computed in an adapter behind a
      port. The combination, the status and the reason code stay pure domain code, and
      every mapping records which signals fired and at what strength so the breakdown
      can show it. The similarity floor moves to configuration and is set by the
      Phase 14 calibration run rather than guessed. Replaces 7.2.
- [x] **13C.6 Score only what is scoreable.** The rubric consumes only items typed
      `requirement` or `responsibility`. Recency uses the parsed role dates from
      13C.3. A requirement met through model adjudication alone says so in the
      explanation. The rubric arithmetic, the 7.4 property tests and the 7.5
      explanation object are unchanged.
- [x] **13C.7 Bullet generation refuses unsupported evidence.** `post_bullets` drafts
      from any mapping's justifying claims with no reason filter, so an
      `adjacent_claim_only` match — now reachable since 13A.10 — can become a cited CV
      bullet for a requirement it does not support. Refuse it with the existing 409
      `insufficient_cited_claims`. Confirm the cover-letter and interview-pack paths
      do not have the same hole.
- [x] **13C.8 Output depth.** Every tab returns something worth reading: a prose fit
      summary naming the strongest and weakest requirements, per-requirement evidence
      showing the actual quoted CV text, a gap plan with concrete actions and score
      deltas, tailored bullets, a cover letter that references this role and company,
      and interview questions each carrying the candidate's own evidence. All of it
      stays span-bound and validated by the Phase 10 pipeline.
- [x] **13C.9 Repair the deterministic fixture path.** The rules extractors remain the
      hermetic fixture, so they must be honest: accept a bullet glyph with no
      following space, stop treating a wrapped line beginning with a section word as a
      section boundary, and read role dates from the role line. Those are the three
      bugs the audit found. Add synthetic fixtures reproducing the observed CV and
      advert shapes so the failure cannot return unnoticed; keep the maintainer's
      private documents out of the repository.
- [x] **13C.10 Reconcile documentation with the new direction.** Update the README
      architecture claims, `docs/features.md`, `docs/production-wiring.md`, the threat
      model where extraction changed, and ADR 003. Write a new ADR recording why
      deterministic extraction was tried, exactly what it produced on a real document,
      and why model-first extraction with server-verified quotes replaced it. That ADR
      is the most useful page in this repository for a reviewer.

**Outstanding exit verification (carried into 13D.6):** on representative CVs and
at least five job adverts, every extracted item carries a type and a verified
quote; no salary or benefit is scored as a skill; logistical constraints are
identified separately; claims preserve the correct employment/date association;
scores and ranks agree with the labelled evidence within predeclared tolerances.
A genuinely poor match may score zero; no scoreable requirements means unscored.
Fit, Gaps, Prepare and Letter must reflect that result, including honest refusals.
The workflow runs on local Ollama with no API key and the four Make quality
targets pass. Use synthetic/public-safe fixtures in the repository; any optional
maintainer-document smoke run stays local and private. This review does not close
the gate.

## Phase 13D — Assessment accuracy and a polished product

The product is close. This phase does three things only: make the evidence
assessment trustworthy, make every feature read the same saved result, and
finish the user journey. Keep PostgreSQL, the existing provider options, the
existing screens and the existing rubric. No agent framework, no multi-model
voting, no new service, no prompt-management system, no evaluation platform.

### Repository review evidence — 2026-09-22

Reviewed at `e0d74e2` with a clean working tree. SQL persistence, queued analysis,
provider selection, extraction prompts and three-signal matching already exist.
Do not rebuild Phase 13A or 13C.

- `application/analysis/relatedness.py` calls the model only when the lexical and
  vector signals disagree, and `adapters/relatedness/model.py` returns a bare
  boolean with no spans, conditions or explanation. Agreement skips the model, and
  a missing decision falls back to lexical OR embedding relatedness.
- Diagnostic: "Five years leading production Python systems" against "Completed an
  introductory Python course" returned `met` both when the signals agreed and when
  the adjudicator returned nothing.
- `domain/groundedness.py` returned `pass` for "Led production Python systems"
  citing only that introductory-course sentence. It checks tokens, not support.
- `domain/prompts.py` selects Ask context by token overlap and only includes
  uploaded letters when the question contains the literal phrase "cover letter".
  `application/ask/service.py` answers every structured intent from a deterministic
  template, caps open questions at 512 output tokens, and `llm_max_output_tokens`
  in `settings.py` is declared but never read.
- `ClaimRow`, `analysis_repos.py` and `role_store.py` drop employer, title, scope,
  technologies, outcome and requirement seniority on reload, and reset extraction
  confidence to `0.85`. An assessment cannot depend on data the reload loses.
- The provider adapters advertise the same structured-output support but enforce it
  differently: Ollama receives a schema, OpenAI a schema response format, Anthropic
  schema instructions in text. Receiving JSON is not proof of a valid assessment.
- 59 focused tests pass. They prove the implemented contracts, not live accuracy.

### Tasks

- [x] **13D.1 Build a small check set.** Assemble roughly fifteen labelled cases in
      the repository as synthetic, public-safe fixtures: strong, partial and poor
      matches, a paraphrase with no shared keywords, matching keywords with too
      little scope or duration, a negation, a contradiction between CV and letter,
      an aspiration, an injection attempt and a role with nothing scoreable. Label
      the supporting passage, the expected assessment and the expected role order.
      Record what the current code gets wrong. This is the before-and-after
      measurement for the rest of the phase; a poor match may score zero and a role
      with no scoreable requirements stays unscored.
- [x] **13D.2 Record the evidence contract in one ADR.** State the boundary: the
      model assesses evidence against the stated criteria, the server validates the
      assessment, and the domain calculates the score. A citation proves where text
      came from, not that it supports the claim. Decide the letter policy in the
      same ADR: concrete experience in an uploaded CV or uploaded letter counts,
      with its source shown and duplicates removed; aspirations and generated drafts
      never raise the score. Reconcile AGENTS, `docs/features.md` and ADRs 004, 009
      and 010 with that decision.
- [x] **13D.3 Replace the boolean adjudicator with one structured assessment step.**
      Reuse the existing completion port and extraction prompts. Send one versioned
      prompt per requirement batch containing the requirement, its conditions and
      the retrieved evidence with source labels. Require `requirementId`, an
      assessment enum, supporting span ids, unmet or unknown conditions, a
      contradiction flag and a short justification. Do not ask for hidden reasoning
      or a model-emitted score. Assess even when the retrieval signals agree.
      Validate types, allowed span ids, completeness and duplicates server-side for
      every provider, and test both the native-schema and prompted-JSON paths plus
      refusals, truncation and malformed output. A failed or missing assessment is
      recorded as incomplete and never becomes a match. Keep the existing embeddings
      and lexical matching for evidence retrieval; widen the retrieval limit and
      include adjacent sentences so negation and dates survive.
- [x] **13D.4 Answer every Ask question with the configured LLM.** Route all
      intents — fit, gaps, compare, evidence, preparation and open questions —
      through the configured completion model. Structured intents supply the saved
      analysis as the grounding material so the model phrases the answer from the
      stored numbers and never recalculates a score. Open questions supply the
      retrieved spans, and uploaded letters become eligible on relevance rather than
      on the literal phrase "cover letter". Replace the hardcoded 512-token cap:
      read `llm_max_output_tokens` from settings, default it to 2,000, and clamp it
      to the selected model's advertised output limit. Raise the input budget to
      roughly 4,000 characters of question and 24,000 characters of context, trimmed
      to the model's context window. Instruct the prompt to match answer length to
      the question — a couple of sentences for a direct factual question, several
      paragraphs for a comparison or an explanation — with no padding and no answer
      cut off mid-sentence. Citation validation and the insufficient-evidence result
      stay exactly as they are; streamed and non-streamed answers must still agree.
- [ ] **13D.5 Save one analysis result and make every feature read it.** Round-trip
      employer, title, scope, technologies, outcome, dates, real extraction
      confidence and requirement conditions. Persist the validated assessments,
      cited span ids, provider, model, prompt and rubric versions and a safe failure
      status under an analysis version. Keep the rubric arithmetic and the must
      versus desirable weighting as they are; define how unknown and conflicting
      evidence affect coverage, and show an incomplete analysis differently from a
      poor fit. Deduplicate requirements, do not count concurrent employment twice,
      and keep ties stable with the differentiating requirements named. Fit, Gaps,
      Prepare and Letter all read this saved result, and a restart reproduces the
      same ranking with no further model calls. Add the course-versus-leadership
      case as a regression test at the domain, API and SQL round-trip boundaries.
- [ ] **13D.6 Verify and polish.** Run the check set from 13D.1 against the real
      production path on local Ollama with no API key, and record the before-and-after
      error rate, ranking agreement and latency. Run `make lint`, `make typecheck`,
      `make test` and `make test-integration`. Then finish the journey: loading and
      progress states on analysis and Ask, clear and actionable error messages,
      citations that resolve and are readable, honest refusals where evidence is
      missing, and working exports. Complete the walkthrough carried over from 13C.
      Update README, `docs/features.md`, `docs/production-wiring.md`, the API
      contract and the journal to say what is implemented, what was measured and
      what was deferred.

**Exit gate:** on the check set, unsupported leadership cannot be `met`, a missing
or malformed assessment cannot raise a score, generated drafts cannot raise a score,
and letter handling matches the recorded policy. Ask answers every intent through
the configured model at a sensible length with resolvable citations. A restart
reproduces the saved ranking. The four Make targets pass and the walkthrough runs
end to end. If the new assessment does not beat the old one on the check set,
record that and revise it rather than adding more calls.

**Deferred — revisit only if the check set shows a real need.** PostgreSQL
full-text and pgvector hybrid retrieval with fusion and ablations; an approximate
vector index; a second reviewing model; per-sentence semantic groundedness checks
on generated drafts; a versioned multi-family labelled dataset and the wider
retrieval and provider comparisons, which stay in Phase 14.

## Phase 14 — Evaluation

Expand the check set from 13D.1 into a reproducible quality report.
Measure extraction, retrieval, assessment, ranking and generation separately.
Committed fixtures must be synthetic or public-safe; optional private local smoke
data never goes into Git, logs, public reports or hosted-provider comparisons.

- [ ] **14.1** Expand and version the pilot labels across job families, seniorities
      and advert formats (bulleted, prose, numbered, agency-reformatted). Include
      CV/letter combinations, missing/conflicting evidence and expected role order,
      with tie/ambiguity labels. Freeze a held-out set before tuning prompts, weights
      or retrieval thresholds. State reviewer disagreement and dataset limitations.
- [ ] **14.2** Report item classification, requirement/claim precision and recall,
      quote-verification failures, retrieval recall@k, assessment confusion matrix
      (especially unsupported `met`), citation support, abstention/coverage and
      pairwise role-ranking agreement or nDCG with justified labels. Distinguish
      deterministic replay of saved assessments from fresh-run model variability.
- [ ] **14.3** Record thresholds before held-out runs and observed results with
      dataset, prompt/schema/rubric versions, provider/model, settings and date in
      `docs/evaluation.md`. Include failures and skips; keep `TBD` until observed.
- [ ] **14.4** `make test-evaluation` tests the harness offline using scripted
      responses/fixtures. Add a separate explicit live-model evaluation entrypoint;
      fixture success is never reported as a live model's accuracy.
- [ ] **14.5** Compare configured Ollama, OpenAI and Anthropic completion paths and
      the current policy baseline on the same eligible dataset. Change one variable
      at a time; keep embeddings/retrieved evidence fixed when comparing assessors.
      Hosted runs require explicit enablement and public-safe data. Report quality,
      calls, tokens, p50/p95 latency, fallback rate and cost using a recorded pricing
      basis when available; unavailable providers are skipped, never simulated as
      successful. No provider or LLM workflow is required to win.
- [ ] **14.6** Measure generated artefact usefulness and unsupported-claim rate using
      independently labelled probes, including semantic errors with valid tokens and
      citations. Separately report schema validity, citation resolution, evidence
      support, refusal correctness and template fallback. Do not use the same token
      validator as the sole ground-truth judge of its own success.
- [ ] **14.7** Calibrate retrieval floors/fusion and assessment policy on development
      data only. Publish lexical-only, semantic-only and combined retrieval ablations,
      plus current boolean adjudication versus structured assessment. Include impact
      on role ordering and runtime, and held-out results without retuning.
- [ ] **14.8** Evaluate the approved cover-letter policy: additional concrete
      evidence, duplicates, contradictions and aspirations, with visible sources.
      Generated drafts and duplicate uploads cannot inflate the score. If the
      narrative-only policy is retained, report that limitation explicitly.

**Exit gate:** reproducible observed results against the predeclared criteria,
including failures, uncertainty, model variability and remaining limitations.
Neither a positive fit score nor superiority of an LLM is an acceptance condition.

## Phase 15 — Observability and security pass

Kept light. No vendor APM, no dashboards.

**Maintenance risk carried from 13A.1 (do not silence):** FastAPI 0.141.1 /
Starlette 1.6.0 TestClient emits two third-party warnings on the hermetic and
integration suites — `StarletteDeprecationWarning` that `httpx` with
`starlette.testclient` is deprecated in favour of `httpx2`, and
`DeprecationWarning` that `anyio.abc.BlockingPortal` should be
`anyio.from_thread.BlockingPortal`. They originate in site-packages, not
application code. Do not add `httpx2`, widen the FastAPI pin, or add
`filterwarnings` to obtain green output. Revisit on a compatible FastAPI /
Starlette upgrade that still fits Python 3.14 and the existing constraints.

Operation events and the redaction test were delivered by Phase 13B (13B.3, 13B.5,
13B.6); they are not repeated here.

- [ ] **15.1** `make security`: Bandit, pip-audit, `bun audit`, Gitleaks, Trivy.
- [ ] **15.2** Retention: configurable window and a documented deletion path,
      including original CV/job-description/cover-letter bytes, parsed text,
      embeddings, questions, answers, citations and generated drafts. Expiry is a
      hard delete and its database transaction is integration tested.
- [ ] **15.3** Rate limiting on upload, analysis and generation routes.
- [ ] **15.4** Update `docs/threat-model.md` with residual risks.

**Exit gate:** `make verify` passes; the 13B.6 redaction test still holds after the
13C extraction changes.

## Phase 16 — Containers and walkthrough

- [ ] **16.1** Nitro `node-server` preset for the frontend build; non-root backend and
      frontend images; `compose.yaml` with health checks for Postgres, API and web.
      *Written on 2026-09-17 and unverified: no Docker was available on the machine
      that wrote them. Building both images and running the stack is what closes this
      task — treat the frontend build output path and the Nitro preset as the two
      things most likely to need a fix.*
- [ ] **16.2** Database deployment profile: PostgreSQL 16 + pgvector container on a
      private Compose network, no published database port, required non-default
      credentials, immutable image version/digest, persistent named volume, health
      check, migration job before API readiness, graceful shutdown and documented
      resource limits. Development Compose may publish
      `${POSTGRES_HOST_PORT:-5433}` without changing the API's internal `db:5432`
      connection.
- [ ] **16.3** Backup and restore: documented `pg_dump`/`pg_restore` commands and an
      observed restore smoke test that includes one original document, one generated
      cover letter and one cited answer. State explicitly that deleting the volume is
      destructive and that backups retain personal data until rotation.
- [ ] **16.4** Two clean-room walkthroughs: (a) fresh clone with `make run` against a
      developer-managed local PostgreSQL on `localhost:5432`; (b) fresh clone with
      Compose-managed PostgreSQL. Run the same migrations and critical workflow on
      both and fix every divergence.
- [ ] **16.5** Playwright end-to-end following the session walkthrough in
      `docs/features.md`: upload CV, add a role, wait for analysis, read the mapping,
      open a gap, draft a bullet, upload a supporting cover letter, open a citation,
      generate a letter, ask a question, restart the API and verify history persists.
      Extend with several roles and expected ranking, a letter duplicate that cannot
      inflate fit, an insufficient-evidence outcome, and replay of saved assessments
      after restart under the 13D contract.
- [ ] **16.6** A second end-to-end run with a hosted provider selected, asserting the
      confirmation is required and the provenance is recorded. Skipped without a key,
      and skipping is reported rather than silent.
- [ ] **16.7** Screenshots into `docs/screenshots/`, referenced from the README.
- [ ] **16.8** README pass: commands, database topology, backup/restore, persistence
      guarantees, limitations and productionisation table accurate
      against the built system.
- [ ] **16.9** Deployment remains private/single-user until authentication and
      authorization exist. The deployment guide must not present the workspace cookie
      as protection suitable for an Internet-facing service.

**Exit gate:** someone who has never seen the repository can run it from the README
against either a local or Compose PostgreSQL instance; original uploads, generated
drafts and cited chat history survive application-container recreation and an observed
backup/restore round trip.

## Phase 17 — Final review

- [ ] **17.1** Read-only review of the full diff against `AGENTS.md`.
- [ ] **17.2** Confirm no fabricated metrics, dates or outputs anywhere in the docs.
- [ ] **17.3** `AI_DEVELOPMENT_LOG.md` contains at least one accepted, one changed and
      one rejected suggestion, each with the human decision named — including how the
      Lovable output was used and what in it was not kept.
- [ ] **17.4** Record the honest limitations list in the README.
- [ ] **17.5** Inspect the final schema, foreign keys and deletion tests against the
      personal-data inventory. Confirm there is no filesystem or process-memory source
      of truth and no orphaned upload, question, answer, citation or draft path.

**Exit gate:** ready to show.

---

## Deliberately not in scope

Named so the absence reads as a decision. The user-facing list is in
[docs/features.md](docs/features.md#deliberately-not-features); these are the
engineering ones:

- Authentication and multi-tenant authorization. Required before untrusted users.
- Employer-side screening. Would need a bias and fairness evaluation.
- Scanned-image CVs and OCR.
- Automatic job-board ingestion, auto-apply, email integration.
- A distributed job queue. The in-process worker is a stated limit.
- Bring-your-own-key in the browser.
- A model-emitted fit score. The model extracts and adjudicates; the score is
  arithmetic in domain code, or the product has nothing to explain.
- Deterministic extraction as a product default. It is kept as a test fixture only —
  see the model-first extraction ADR written in 13C.10.
- Kubernetes, service mesh, observability vendors.
