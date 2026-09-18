# TDD Delivery Plan — Career Intelligence Assistant

Operational source of truth. Execute phases in order. A phase is complete only when
its tests, documentation and exit gate are satisfied.

**Current position:** Phase 11 API contracts in progress — SqlCvStore and
SqlRoleStore land SQL persistence for CV/spans/roles/jobs/analysis publish.
Next: SQL delete/reanalyse/drafts, production store wiring default, then 11.9+.

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
| Model integration | Narrow ports with four adapters: hermetic, Ollama, OpenAI, Anthropic | Prove the abstraction, not one vendor | A single vendor SDK in the application |
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
      hashing embeddings. No network, no keys, no downloads.
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
      hermetic) that handles bulleted requirement lists.
- [x] **5.3** Extraction against the Phase 2 completion port, schema validated, with
      the same acceptance tests passing on every configured provider.
- [x] **5.4** Output validation: reject any requirement whose source span does not
      resolve to stored text. Drop it, count it, never pass it through.
- [x] **5.5** Prompt-injection regression test: a job description containing
      instructions to the model does not change extraction behaviour.
- [x] **5.6** Vague-requirement detection: a requirement with a seniority or scope
      signal the description never quantifies is marked as such. This feeds
      "what to ask them" in the interview pack, so it is data, not a heuristic in the
      view.
- [x] **5.7** Requirements are extracted only from the stored job-description
      document for that role. An uploaded cover letter cannot contribute a requirement
      or alter a role analysis.

**Exit gate:** six fixture job descriptions produce requirement sets; every
requirement resolves to a real span; the injection fixture changes nothing.

## Phase 6 — Evidence extraction

- [x] **6.1** Domain type `Claim`: competency, context, duration signal, recency
      signal, source spans.
- [x] **6.2** Rule-based adapter as the default; model-backed extraction through the
      Phase 2 port, schema validated on every provider.
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
- [x] **7.2** Similarity support for mapping candidates via embeddings, with the
      decision still made by the policy.
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
- [ ] **11.8** Job, gap plan, interview pack, bullets, cover letter, export, ranking,
      compare and span routes.
      - Done so far: hermetic in-memory 11.8 surface; SqlCvStore; SqlRoleStore
        (create/list/get/require_analysis + HTTP) with roles.company migration.
        Remaining: SQL delete/reanalyse; durable generated drafts; default
        production create_app wiring to SQL stores.
- [ ] **11.9** SSE answer stream with the documented event sequence.
- [ ] **11.10** Every answer and every draft response carries the provider, the model
      tag and whether content left the machine.
- [ ] **11.11** Contract test: the generated OpenAPI schema and
      `frontend/src/types/index.ts` agree on every shared model, including the
      `spanId` required to open every `Evidence` citation.
- [ ] **11.12** Supporting-document routes: list/upload/delete uploaded cover letters
      and download an original document by id, all workspace-scoped. Responses expose
      metadata, never database paths or storage internals. Generated cover-letter
      routes remain role-scoped and distinct.
- [ ] **11.13** Message routes expose persisted conversation history. `POST` requires
      `clientRequestId`; both JSON and SSE transports return the same stored final
      answer id. `DELETE` performs the hard-delete contract.

**Exit gate:** OpenAPI is accurate; API tests cover each status path in the error
table.

## Phase 12 — Frontend integration

The screens exist. This phase makes them real. See
[docs/frontend-integration.md](docs/frontend-integration.md).

- [ ] **12.1** **Spike first:** prove a `text/event-stream` response and a
      `MAX_UPLOAD_BYTES` multipart upload both pass through a TanStack Start server
      route without buffering. Record the result. If either fails, take the
      direct-origin-plus-CORS fallback and add a follow-up entry to ADR 006 before
      continuing.
- [ ] **12.2** Catch-all server route proxying `/api/**` to `API_BASE_URL`, forwarding
      method, headers, body, cookie and stream. `Origin` checked on every non-`GET`.
      `API_BASE_URL` is a server variable, never `VITE_*`.
- [ ] **12.3** Replace `src/api/client.ts` with a real HTTP client keeping the existing
      exported signatures: one `request()`, the typed `ApiError` carrying `code` and
      `correlationId`, and zod validation of every response.
- [ ] **12.4** Move fixtures to `src/api/__fixtures__/` for tests and the state
      gallery. No component imports a fixture.
- [ ] **12.5** Additive types in `src/types/index.ts` — `RoleStatus`, `AnalysisJob`,
      `GapPlan`, `GapItem`, `InterviewPack`, `BulletDraft`, `CoverLetterDraft`,
      `RankedRole`, `Comparison`, `DraftProvenance`, persisted message fields and
      supporting documents. Add `spanId` to `Evidence`; this is a necessary correction
      because the current shape cannot open an exact stored span.
- [ ] **12.6** Wire the workspace: CV upload with real progress and real rejection
      messages, supporting cover-letter upload/list/delete, add role, delete and
      replace-CV confirmation. Make clear that cover letters are not score evidence.
- [ ] **12.7** Analysis job polling with react-query; the role list shows `Analysing`,
      then the score, or `Failed` with the reason and a retry.
- [ ] **12.8** Wire role detail: requirements, breakdown, evidence panel resolving
      spans through `GET /api/spans/{id}`.
- [ ] **12.9** Wire Ask against the SSE stream, including stop, citation chips,
      insufficient-evidence state, persisted history after reload, delete-history and
      the provider stamp. Client retries reuse the same `clientRequestId`.
- [ ] **12.10** Wire settings: provider list with real availability reasons, the
      hosted confirmation, and the re-index warning when the index provider changes.
- [ ] **12.11** Error handling across the app: every documented error code maps to a
      state the user can act on. Unknown codes fail visibly, not silently.
- [ ] **12.12** Component tests for every state of every wired screen, driven by props.

**Exit gate:** the full existing UI runs against the real backend with fixtures
loaded, including the failure paths. No mock data remains in `src/api/client.ts`.

## Phase 13 — Frontend: the new features

New screens, built in the existing design language. No new tokens, no new visual
patterns. See [docs/features.md](docs/features.md) for what each one shows.

- [ ] **13.1** Role detail gains tabs: Fit, Gaps, Prepare, Letter. Keyboard
      navigable, deep-linkable.
- [ ] **13.2** **Gaps**: ordered gap list with reason, adjacent evidence, score delta
      and action. "Draft a bullet" where the evidence exists.
- [ ] **13.3** **Bullet drafts**: the draft, its citation chips, the provenance line,
      copy, and the visible template-fallback state.
- [ ] **13.4** **Prepare**: the four sections, each evidence line clickable to its
      span, export.
- [ ] **13.5** **Letter**: tone and gap-line controls, paragraphs with citations,
      persisted version history, export, and the refusal state rendered as a next step
      rather than an error. Uploaded cover letters are shown separately as supporting
      documents, never as generated versions.
- [ ] **13.6** **Ranking** on the workspace: roles ordered with the reason named, ties
      shown as ties.
- [ ] **13.7** **Compare**: two roles side by side, shared and unique requirements,
      the differentiator.
- [ ] **13.8** Fill `/dev/states`: every component state on one page, rendered from
      props.
- [ ] **13.9** Accessibility: keyboard path through upload, tabs, table, drafts and
      chat; labels, focus management and live regions for streaming and job progress,
      tested.
- [ ] **13.10** Excerpts and generated text rendered as escaped text, never HTML.

**Exit gate:** `bun run lint`, `tsc --noEmit` and component tests pass; every state in
`/dev/states` has a test.

## Phase 14 — Evaluation

- [ ] **14.1** Labelled dataset: fixture CV/JD pairs with expected requirements,
      expected mapping outcomes and expected refusals.
- [ ] **14.2** Harness reporting requirement-extraction precision and recall, mapping
      accuracy, citation validity rate, insufficient-evidence correctness, score
      stability and **groundedness violation rate**.
- [ ] **14.3** Record thresholds and observed numbers with the date and provider
      configuration in `docs/evaluation.md`. `TBD` until a run has been observed.
- [ ] **14.4** `make test-evaluation` runs hermetically against the default providers.
- [ ] **14.5** Provider comparison: the same dataset on each configured provider —
      hermetic, Ollama, OpenAI, Anthropic — with quality, latency and cost per
      question side by side. Report the rows where the local model is competitive.
- [ ] **14.6** Generation comparison: groundedness violation rate and template
      fallback rate per provider. A provider that drafts beautifully and fails the
      validator is reported as exactly that.
- [ ] **14.7** Add a regression case proving an uploaded cover letter can be retrieved
      and cited for a direct question but cannot improve a fit mapping or score.

**Exit gate:** numbers recorded from an observed run, not estimated.

## Phase 15 — Observability and security pass

Kept light. No vendor APM, no dashboards.

- [ ] **15.1** Structured operation events: document ingested, job stage completed,
      requirements extracted, mapping computed, question answered, draft generated,
      draft rejected by the validator. Counts and durations only.
- [ ] **15.2** Redaction test: no document, question, answer, prompt, embedding, draft
      body or credential content appears in any log line.
- [ ] **15.3** `make security`: Bandit, pip-audit, `bun audit`, Gitleaks, Trivy.
- [ ] **15.4** Retention: configurable window and a documented deletion path,
      including original CV/job-description/cover-letter bytes, parsed text,
      embeddings, questions, answers, citations and generated drafts. Expiry is a
      hard delete and its database transaction is integration tested.
- [ ] **15.5** Rate limiting on upload, analysis and generation routes.
- [ ] **15.6** Update `docs/threat-model.md` with residual risks.

**Exit gate:** `make verify` passes; the redaction test is real, not aspirational.

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
- Hybrid lexical and vector retrieval, and reranking.
- A distributed job queue. The in-process worker is a stated limit.
- Bring-your-own-key in the browser.
- Kubernetes, service mesh, observability vendors.
