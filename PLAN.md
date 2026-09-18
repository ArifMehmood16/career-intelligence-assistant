# TDD Delivery Plan — Career Intelligence Assistant

Operational source of truth. Execute phases in order. A phase is complete only when
its tests, documentation and exit gate are satisfied.

**Current position:** Phase 3 (document intake and spans) exit gate is satisfied.
Next work is Phase 4 — persistence.

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
| Store | PostgreSQL 16 + pgvector | Structured mapping and vectors in one store | Dedicated vector DB |
| Persistence | SQLAlchemy 2, Alembic | Explicit schema, repeatable migrations | Raw SQL |
| Model integration | Narrow ports with four adapters: hermetic, Ollama, OpenAI, Anthropic | Prove the abstraction, not one vendor | A single vendor SDK in the application |
| Provider selection | Runtime workspace setting; hosted behind an explicit egress gate | The person asking should know where their text went | Deploy-time-only configuration |
| Credentials | Server configuration only; never accepted or returned by any route | A key in the browser is a key in a log | Bring-your-own-key in the UI |
| Long work | In-process job queue with a job resource the UI polls | Extraction takes minutes; it is a job, not a request | Celery, RQ |
| Orchestration | Direct use cases | Visible control flow | LangChain / LlamaIndex |
| Scoring | Deterministic rubric in domain code | Reproducible and explainable | Model-emitted score |
| Generated prose | Bound to cited spans, validated server-side, hermetic template fallback | A draft a person signs cannot contain invented facts | Prompt instructions alone |
| Extraction contract | JSON schema validated, spans verified server-side | Blocks fabricated experience | Free-text answers |
| Local run | Docker Compose and Make | Reproducible command surface | Kubernetes |
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

- [ ] **4.1** Alembic baseline migration: workspaces, documents, spans, chunks,
      embeddings, requirements, claims, mappings, jobs, generated drafts, provider
      settings.
- [ ] **4.2** Repository adapters behind application ports.
- [ ] **4.3** Workspace scoping on every query. Integration test proves a query cannot
      read another workspace's rows.
- [ ] **4.4** Hard delete: removing a document or a role removes its spans, chunks,
      embeddings, claims, mappings and generated drafts. Integration test asserts zero
      residue.
- [ ] **4.5** Workspace provider preference persisted, with the provider and model tag
      that produced each stored extraction recorded alongside it.
- [ ] **4.6** Replacing the CV invalidates every mapping and score rather than leaving
      stale ones readable.

**Exit gate:** `make test-integration` green against a real Postgres with pgvector.

## Phase 5 — Requirement extraction

- [ ] **5.1** Domain type `Requirement`: text, competency, seniority signal, must-have
      or desirable, source span, extraction confidence.
- [ ] **5.2** Extraction port and a deterministic rule-based adapter (default,
      hermetic) that handles bulleted requirement lists.
- [ ] **5.3** Extraction against the Phase 2 completion port, schema validated, with
      the same acceptance tests passing on every configured provider.
- [ ] **5.4** Output validation: reject any requirement whose source span does not
      resolve to stored text. Drop it, count it, never pass it through.
- [ ] **5.5** Prompt-injection regression test: a job description containing
      instructions to the model does not change extraction behaviour.
- [ ] **5.6** Vague-requirement detection: a requirement with a seniority or scope
      signal the description never quantifies is marked as such. This feeds
      "what to ask them" in the interview pack, so it is data, not a heuristic in the
      view.

**Exit gate:** six fixture job descriptions produce requirement sets; every
requirement resolves to a real span; the injection fixture changes nothing.

## Phase 6 — Evidence extraction

- [ ] **6.1** Domain type `Claim`: competency, context, duration signal, recency
      signal, source spans.
- [ ] **6.2** Rule-based adapter as the default; model-backed extraction through the
      Phase 2 port, schema validated on every provider.
- [ ] **6.3** Span verification identical to 5.4.
- [ ] **6.4** Recency and duration derived from dates in the CV, in domain code, not
      by the model. Undated experience is treated as undated, never assumed recent.

**Exit gate:** fixture CVs produce claim sets with resolvable spans and derived
recency, including the dated-experience fixture.

## Phase 7 — Mapping and scoring

- [ ] **7.1** Mapping policy in `domain/`: requirement × claims → `met`, `partial`,
      `missing`, with the justifying span ids and a reason code
      (`no_related_claim`, `adjacent_claim_only`, `evidence_too_old`,
      `evidence_thin`). Pure function, no I/O.
- [ ] **7.2** Similarity support for mapping candidates via embeddings, with the
      decision still made by the policy.
- [ ] **7.3** Deterministic rubric: must/desirable weights, status factors, recency
      decay, normalisation and bands exactly as documented in `docs/features.md`, read
      from configuration. Pure, unit tested.
- [ ] **7.4** Property tests: identical inputs give an identical score; adding a met
      requirement never lowers the score; every score is in 0–100.
- [ ] **7.5** Explanation object: every score component traceable to the mapping
      entries that produced it. This is what `GET /roles/{id}/breakdown` returns.
- [ ] **7.6** Counterfactual: score recomputed with one requirement set to met, as a
      pure function. This is the `scoreDelta` the gap plan orders by.

**Exit gate:** a fixture CV against a fixture role yields a stable score, a full
explanation and correct deltas, with no model call.

## Phase 8 — Analysis jobs

Extraction against a local or hosted model takes seconds to minutes. Making the user
wait on a request is the wrong shape, and so is pretending it is instant.

- [ ] **8.1** Job domain type and states: `queued`, `running`, `succeeded`, `failed`,
      with a stage and an error reason.
- [ ] **8.2** In-process worker with a bounded queue. No Celery, no Redis — stated as
      a limit in the README rather than hidden.
- [ ] **8.3** Role analysis pipeline as a job: parse → extract requirements → extract
      claims → map → score, each stage recorded.
- [ ] **8.4** Failure attribution: a failed job names the stage and a safe reason.
      Partial results are discarded, not shown as a low score.
- [ ] **8.5** Re-analysis: replacing the CV or changing the index provider enqueues
      re-analysis for every affected role and invalidates the stale mapping first.
- [ ] **8.6** Idempotence: the same role analysed twice produces the same stored
      mapping, and a duplicate enqueue does not double-run.

**Exit gate:** adding a role returns immediately; the job completes and the role
becomes `ready`; a forced failure leaves the role `failed` with a reason and no
partial mapping.

## Phase 9 — Question answering

- [ ] **9.1** Deterministic intent router: gaps, fit, compare roles, evidence for a
      requirement, interview preparation, open question.
- [ ] **9.2** Structured intents answer from the stored mapping. No vector search.
- [ ] **9.3** Open questions use workspace-scoped retrieval over spans.
- [ ] **9.4** Prompt construction: retrieved text delimited and labelled untrusted;
      budgets for question, context and output.
- [ ] **9.5** Answer validation: every citation resolves to a stored span or the
      answer is reduced to insufficient evidence before it is sent.
- [ ] **9.6** Comparison across multiple roles returns a ranking derived from stored
      scores, with the differentiating requirements named.
- [ ] **9.7** Streaming: the same use case serves a streamed and a non-streamed
      response, with citations validated after the text completes.

**Exit gate:** the example questions in `README.md` answer correctly on fixtures, each
with resolvable citations; an unanswerable question returns insufficient evidence; the
streamed and non-streamed answers to the same question agree.

## Phase 10 — Grounded generation

Everything here is governed by [ADR 007](docs/adr/007-grounded-generation.md). Build
the validator first; the features are built against it, not retrofitted to it.

- [ ] **10.1** Groundedness validator in `domain/`: given draft text and the cited
      spans, extract every number, date, duration, percentage, employer, product and
      technology token from the draft and assert each appears in the spans after
      normalisation. Pure, unit tested against adversarial fixtures — a changed
      figure, an added technology, an inflated duration, a renamed employer.
- [ ] **10.2** Generation pipeline: build input from stored claims and spans → phrase
      through the completion port → validate → regenerate once on failure → fall back
      to template. Provenance recorded at every step.
- [ ] **10.3** **Gap plan** — fully deterministic, no model. Ordered by `scoreDelta`,
      with reason code, adjacent evidence and action category.
- [ ] **10.4** **CV bullets** — per requirement, from the claims that relate to it.
      Hermetic template path first, then the model-phrased path through 10.2.
- [ ] **10.5** **Interview pack** — probes, evidence to lead with, thin areas, and
      questions to ask them. Section membership decided in domain code from the
      mapping and from 5.6; phrasing may come from the model.
- [ ] **10.6** **Cover letter** — structured from met requirements, one paragraph per
      requirement with its spans, optional honest gap line. Refuses below two met
      must-haves with `insufficient_matched_requirements`.
- [ ] **10.7** Markdown export for every artefact, byte-identical to what the screen
      shows.
- [ ] **10.8** Counters: validator failures, regenerations and template fallbacks, per
      provider. These are the numbers Phase 14 reports.

**Exit gate:** every artefact generates on fixtures under the hermetic default with no
model; the adversarial validator fixtures all fail closed; the cover letter refuses
when it should.

## Phase 11 — API contracts

Built against [docs/api-contract.md](docs/api-contract.md). Where code and that file
disagree, the file is corrected first and the change is deliberate.

- [ ] **11.1** Explicit Pydantic response models for every route, camelCase on the
      wire. No bare `dict`.
- [ ] **11.2** Workspace cookie issuance and scoping on every route.
- [ ] **11.3** Reject oversized uploads before buffering the whole body.
- [ ] **11.4** Safe error mapping to the documented code table: no stack traces,
      prompts, file paths or provider payloads.
- [ ] **11.5** Readiness endpoint reporting database, migration and provider state.
- [ ] **11.6** Correlation id on every request, echoed in responses and logs.
- [ ] **11.7** Provider endpoints: list with availability and the reason any is
      unavailable; set the workspace choice. Hosted selection is rejected server-side
      without `acknowledgedEgress`, so the confirmation is not only a UI convention.
- [ ] **11.8** Job, gap plan, interview pack, bullets, cover letter, export, ranking,
      compare and span routes.
- [ ] **11.9** SSE answer stream with the documented event sequence.
- [ ] **11.10** Every answer and every draft response carries the provider, the model
      tag and whether content left the machine.
- [ ] **11.11** Contract test: the generated OpenAPI schema and
      `frontend/src/types/index.ts` agree on every shared model.

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
      `RankedRole`, `Comparison`, `DraftProvenance`. Existing types unchanged.
- [ ] **12.6** Wire the workspace: CV upload with real progress and real rejection
      messages, add role, delete, replace-CV confirmation.
- [ ] **12.7** Analysis job polling with react-query; the role list shows `Analysing`,
      then the score, or `Failed` with the reason and a retry.
- [ ] **12.8** Wire role detail: requirements, breakdown, evidence panel resolving
      spans through `GET /api/spans/{id}`.
- [ ] **12.9** Wire Ask against the SSE stream, including stop, citation chips,
      insufficient-evidence state and the provider stamp.
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
      export, and the refusal state rendered as a next step rather than an error.
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

**Exit gate:** numbers recorded from an observed run, not estimated.

## Phase 15 — Observability and security pass

Kept light. No vendor APM, no dashboards.

- [ ] **15.1** Structured operation events: document ingested, job stage completed,
      requirements extracted, mapping computed, question answered, draft generated,
      draft rejected by the validator. Counts and durations only.
- [ ] **15.2** Redaction test: no document text, prompt, embedding, draft body or
      credential appears in any log line.
- [ ] **15.3** `make security`: Bandit, pip-audit, `bun audit`, Gitleaks, Trivy.
- [ ] **15.4** Retention: configurable window and a documented deletion path,
      including generated drafts.
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
- [ ] **16.2** Clean-room walkthrough: fresh clone, follow the README exactly, fix
      every step that does not work.
- [ ] **16.3** Playwright end-to-end following the session walkthrough in
      `docs/features.md`: upload CV, add a role, wait for analysis, read the mapping,
      open a gap, draft a bullet, open a citation, generate a letter, ask a question.
- [ ] **16.4** A second end-to-end run with a hosted provider selected, asserting the
      confirmation is required and the provenance is recorded. Skipped without a key,
      and skipping is reported rather than silent.
- [ ] **16.5** Screenshots into `docs/screenshots/`, referenced from the README.
- [ ] **16.6** README pass: commands, limitations and productionisation table accurate
      against the built system.

**Exit gate:** someone who has never seen the repository can run it from the README.

## Phase 17 — Final review

- [ ] **17.1** Read-only review of the full diff against `AGENTS.md`.
- [ ] **17.2** Confirm no fabricated metrics, dates or outputs anywhere in the docs.
- [ ] **17.3** `AI_DEVELOPMENT_LOG.md` contains at least one accepted, one changed and
      one rejected suggestion, each with the human decision named — including how the
      Lovable output was used and what in it was not kept.
- [ ] **17.4** Record the honest limitations list in the README.

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
