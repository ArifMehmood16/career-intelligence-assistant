# AI Development Log

A factual record of how AI coding tools were used on this project. One entry per
meaningful agent-assisted change. Entries are drafted by the agent on the task branch
and approved by the developer before the pull request is merged.

Record what was **accepted**, what was **changed**, and what was **rejected**. The
rejections are the most valuable entries: they show the judgement applied on top of
the tool.

Never record a command output, metric, date or commit hash that was not observed.

Entries are ordered newest first. Add a new entry directly under "Entries".

## Entry template

```text
### NNN — <short title>

- Date:
- Tool / model:
- Plan task:
- Prompt intent: (what was asked, not the full prompt)
- Suggestion: (what the tool proposed)
- Outcome: accepted | changed | rejected
- Reason: (why — the human-owned decision)
- Human validation: (tests run, diff reviewed, docs checked)
```

## Entries

### 130 — Requirement batches and rejected duplicate CV labels

- Date: 2026-09-24
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6c and 13D.6d corrective
- Prompt intent: requirement extraction should batch and retry like CV extraction, and a duplicated CV span id should not keep the last label.
- Suggestion: leave requirement extraction as one call with a 4096-token cap, and keep the later CV assignment when a span id is repeated.
- Outcome: rejected
- Reason: job-description spans are classified in bounded batches, a truncated batch is split, and spans still missing are retried once. A CV span id repeated in one response is dropped and retried. The retry's single classification is kept. An id from another batch is not counted as unknown.
- Human validation: pytest on requirement extraction, claim extraction and the Aviva-shaped fixture passed (51). Ruff and mypy passed on the two extractors.

### 129 — Weak CV lines are not evidence

- Date: 2026-09-24
- Tool / model: Cursor Grok 4.7
- Plan task: 13D corrective, retrieval abstain ahead of 14.7
- Prompt intent: reference lines must not become claims, and retrieval must be able to show the assessor nothing when every relevance signal is weak.
- Suggestion: keep accepting any long span the model calls experience, and keep sending the five least-weak claims so a paraphrase cannot be missed.
- Outcome: rejected
- Reason: a span needs a responsibility, qualification or outcome before it is a claim or reaches matching. Nearest-heading recovery does not apply to a line that fails that check. Retrieval returns no candidates when the best claim has no lexical overlap and similarity below 0.35. The 0.55 floor stays a rank signal, so the locked paraphrase at 0.42 still reaches the assessor. 0.35 is not a measured threshold; PLAN 14.7 still calibrates it.
- Human validation: focused pytest on evidence support, claim extraction, retrieval, the Aviva-shaped fixture and three-signal matching passed (46). Ruff and mypy passed on the changed Python files.

### 128 — Benefits and Logistics sections stay unscoreable

- Date: 2026-09-24
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6c corrective
- Prompt intent: a Benefits or Logistics section, including a Markdown heading, must stay display-only when the model calls it a requirement.
- Suggestion: leave section protection on About and Why only, and keep treating a heading as narrative only when it ends with a colon.
- Outcome: rejected
- Reason: body under a Benefits or Logistics heading is forced to `benefit` or `logistics` with `must_have` false. A Markdown heading starts that section the same way a colon heading does. A later requirements heading ends the block. Lines outside those headings are still classified by the model.
- Human validation: `pytest tests/unit/test_model_requirement_extraction.py` passed (22). Ruff format, Ruff check and mypy passed on the changed Python files.

### 127 — Documentation cleanup, combined backlog and agent development style

- Date: 2026-09-24
- Tool / model: Claude Opus 5.5, Cowork session
- Plan task: maintainer request (documentation; not a PLAN checkbox)
- Prompt intent: review the repository, recent commits and this log; remove
  contradicting and outdated statements from the agent instructions; add a
  development style covering frequent TDD commits, SonarQube-clean code, SOLID and
  design patterns; combine every pending item into one list; update the README.
- Suggestion: rewrite `AGENTS.md` around a document-authority table, a
  commit-per-green-cycle TDD rhythm, SonarQube default-gate rules and SOLID guidance
  tied to the patterns already in the code; add `CLAUDE.md` and `frontend/CLAUDE.md`
  that import the AGENTS files rather than copying them; add `BACKLOG.md`; condense
  the `PLAN.md` current position; add the README sections the assignment asks for
  (RAG/LLM approach, observability, productionisation, engineering standards, AI
  tool use); mark superseded notes in `docs/evaluation.md`; correct retention and
  durable-audit claims in `docs/threat-model.md`, `docs/features.md` and the
  observability plan; point `frontend/README.md` at `make run-web`, because a plain
  `bun run dev` starts the proxy without `API_BASE_URL`; give agents the exact
  per-commit commands, including `--no-cov` for focused pytest runs; order this log
  newest first.
- Outcome: pending human review of the diff.
- Changed from earlier practice: `PLAN.md` said the agent must not commit and the
  human commits. Agents now commit each green step on a task branch; pushing,
  pull requests and merging stay with the human. A failing test is never committed
  on its own.
- Rejected alternatives: copying the AGENTS rules into `CLAUDE.md` (two copies
  drift); a second plan that restates acceptance criteria (the backlog links
  `PLAN.md` ids instead); rewriting historical measurement sections in
  `docs/evaluation.md` (marked superseded instead); fixing `compose.yaml`, the
  unread settings and the hermetic Settings entry in the same change (those change
  behaviour, so they are recorded in `BACKLOG.md` as tasks and decisions).
- Findings recorded in `BACKLOG.md`: the Settings catalogue still offers the
  hermetic fixture although 13C.1 is ticked; `compose.yaml` drift, including an
  `OLLAMA_BASE_URL` the API container cannot reach; settings in
  `config/app.env.example` that no code reads; CI runs only when a pull request is
  opened; no SonarQube scan in CI; `evidence-assessment-v5` not yet measured; three
  empty packages; functions and modules likely above SonarQube's complexity limit.
- Human validation: pending. Documentation only — no application code changed and no
  test suite was run. Relative links in the changed Markdown files were checked with
  a script. A `git status` in the Cowork sandbox left a `.git/index.lock` it could not
  delete; it was moved into `.git/stale-locks/`. No commit was made from the sandbox.
  A concurrent Cursor session committed this entry's two `docs/threat-model.md` edits
  inside `081660e`.

### 126 — Invalid requirement classifications are not scoreable

- Date: 2026-09-24
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6c corrective
- Prompt intent: a missing or invalid `item_type` or `must_have` must not become a scoreable requirement.
- Suggestion: keep the fallback that scores an unrecognised kind as `requirement`, because dropping a real requirement was treated as the worse failure.
- Outcome: rejected
- Reason: an unrecognised or missing kind is not an accepted classification. Those spans are retried once; if they stay invalid the extraction is incomplete and no fit score is published. A valid heading label can still be forced to `non_requirement`.
- Human validation: `pytest tests/unit/test_model_requirement_extraction.py` passed (21). Ruff and mypy passed on `model_backed.py`.

### 125 — GitHub Actions is work evidence, not a contact line

- Date: 2026-09-24
- Tool / model: Cursor Composer
- Plan task: make test failure (unrelated to schema cleanup)
- Prompt intent: fix evaluation failures after `make test`.
- Suggestion: `_CONTACT` matched bare `\bgithub\b`, so the held-out paraphrase claim "GitHub Actions workflows..." was dropped before the assessor; empty `assessment_justification` on `_no_evidence_mapping` then failed the reason-carrying disagreement test.
- Outcome: accepted
- Reason: contact detection should target handles/URLs (`github.com`, `GitHub:`), not product names in work bullets.
- Human validation: unit evidence_support + evaluation quality baseline focused tests green.

### 124 — Schema cleanup: dead answer usage columns and draft soft-flag

- Date: 2026-09-24
- Tool / model: Cursor Composer
- Plan task: maintainer request (schema cleanup; not a PLAN checkbox)
- Prompt intent: remove unused tables/columns that stay empty or unused for the life of the app.
- Suggestion: drop never-written `answers.prompt_tokens|completion_tokens|latency_ms`; hard-delete generated drafts on CV replace and drop `generated_drafts.invalidated` (written but never filtered). Keep claim-detail columns and `provider_call_accounting` (in use / intentional). No orphan tables found.
- Outcome: accepted
- Reason: usage accounting already lives on `provider_call_accounting`; soft-invalidating drafts without a read filter left CV-derived draft text readable after CV replace — hard delete matches the privacy hard-delete contract better than finishing the soft-flag.
- Human validation: red then green integration tests for column absence and CV-replace draft deletion; `alembic upgrade head` on local `career_assistant`; persistence/draft/ask/analysis integration suite 25 passed.

### 123 — README how-to and feature screenshots; PR package

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: commit + PR docs
- Prompt intent: commit changes, create/update PR, document how to use features with screenshots in README.
- Suggestion: How to use section; docs/images screenshots; push onto existing PR 34.
- Outcome: accepted
- Reason: reviewers need a walkthrough and visuals for letter citations, fit evidence and gaps alongside the assessment accuracy fixes.
- Human validation: README updated; images under docs/images/; commit and PR update pending in the same turn.

### 122 — Numbered cover-letter citation glossary

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: Letter UI polish
- Prompt intent: replace hash span ids with numbered citations and a right-hand glossary of full passage text.
- Suggestion: `[n]` markers in the letter; sticky Citations panel; resolve passages via `getSpan` / `useQueries`.
- Outcome: accepted
- Reason: hashes are not readable; numbers plus the source passage keep provenance without exposing raw ids in the draft view.
- Human validation: `vitest` LetterPanel + letterCitations passed (7); `tsc --noEmit` clean.

### 121 — Cover letter STAR phrasing and transferability

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: grounded generation polish (cover letter prompt)
- Prompt intent: natural paragraph cover letters using STAR, covering important criteria and transferring CV evidence to gaps.
- Suggestion: versioned `cover-letter-v2` system prompt; brief labels MET/TRANSFER/GAP; limit met paragraphs; raise output tokens to 1200; strip labels in hermetic fallback.
- Outcome: accepted
- Reason: ADR 007 still binds facts to cited spans; the model only rephrases. Transfer paragraphs use partial/adjacent claims, never invented skills.
- Human validation: `pytest tests/unit/test_cover_letter_prompt.py tests/unit/test_generation_pipeline.py tests/api/test_grounded_generation_http.py --no-cov` passed (15); ruff clean.

### 120 — Reject non-evidential Met citations

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6g corrective (assessment false Mets)
- Prompt intent: Met rows cited location lines, profile headlines and role titles instead of work evidence; user asked for an LLM pass on match quality.
- Suggestion: keep the existing assessor; exclude non-evidential claims from retrieval; cite claim bodies only; demote met/partial without evidential bodies; bump prompt to `evidence-assessment-v5`.
- Outcome: accepted
- Reason: an LLM assessment already ran; the failure was accepting titles and locations as support. Domain validation decides what may justify Met; the model still assesses real work bullets.
- Human validation: `pytest tests/unit/test_structured_assessment.py tests/unit/test_evidence_support.py --no-cov` passed (14); ruff clean on changed modules.

### 119 — JD headings and About/Why pitch not scored as gaps

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6g corrective (requirement list noise)
- Prompt intent: Missing rows included section headings and About/Why marketing copy that are not requirements.
- Suggestion: force About/Why body and employer-pitch lines to `non_requirement`; list only scoreable items on `/requirements`.
- Outcome: accepted
- Reason: colon headings were already unscoreable but still rendered as Missing when unmapped; OpenAI also labelled About/Why paragraphs as responsibilities. Domain overrides decide; GenAI skill bullets stay scoreable.
- Human validation: `pytest tests/unit/test_model_requirement_extraction.py --no-cov` passed (18); ruff clean on changed modules.

### 118 — Soft claim-attach gate and project→role recovery

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6d corrective
- Prompt intent: OpenAI run failed with `claim_attach_failed` despite 34 accepted claims and zero scoreable unclassified spans.
- Suggestion: recover orphan project claims onto the nearest role heading; treat attach drops as incomplete only when no claims remain.
- Outcome: accepted
- Reason: five unattachable lines were failing a usable extraction. Scoreable unclassified spans still fail completeness; orphan drops stay diagnostic when claims remain.
- Human validation: `pytest tests/unit/test_model_claim_extraction.py --no-cov` passed (21); ruff clean on `claims_model.py`.

### 117 — Phase 15B.5 use-case action rows

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6
- Plan task: 15B.5
- Prompt intent: continue 15B with regular commits.
- Suggestion: bind the recorder on each request and emit allowlisted actions from CV, role, Ask, generation and provider-choice use cases.
- Outcome: accepted
- Reason: one ContextVar keeps HTTP and use cases aligned without putting FastAPI types in application code. Attributes stay prefixed ids/counts so planted phrases never persist.
- Human validation: `pytest` on audit actions, operational logging, architecture guard, generation, messages, CV and provider routes passed (45) with `--no-cov`.

### 116 — Phase 15B.4 persist HTTP envelopes

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6
- Plan task: 15B.4
- Prompt intent: continue 15B with regular commits.
- Suggestion: middleware records method/path/status/duration on the in-memory recorder; exception handlers stamp `error_code` on request state.
- Outcome: accepted
- Reason: envelopes answer which call failed without storing headers or bodies. Recording is fail-open so an audit write cannot fail the request.
- Human validation: `pytest tests/api/test_operational_logging.py --no-cov` passed (9).

### 115 — Phase 15B.3 in-memory audit recorder

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6
- Plan task: 15B.3
- Prompt intent: continue 15B with regular commits.
- Suggestion: `AuditRecorder` port, allowlisted names, sanitize attributes before an in-memory store.
- Outcome: accepted
- Reason: durable rows must drop free-text keys before they exist in memory so a later SQL adapter cannot persist a planted phrase.
- Human validation: `pytest tests/unit/test_audit_recorder.py tests/unit/test_architecture_guard.py --no-cov` passed (5).

### 114 — Phase 15B.2 rotating log file

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6
- Plan task: 15B.2
- Prompt intent: continue with the next logging work.
- Suggestion: optional `RotatingFileHandler` when `LOG_FILE` is set; same redaction as stderr; `LoggingSettings` at construction.
- Outcome: accepted
- Reason: stderr-only 13B lines die with the terminal; a file is opt-in so `make test` stays silent on disk. Bodies and planted phrases stay out of the file even at DEBUG.
- Human validation: `pytest tests/unit/test_logconfig.py tests/api/test_operational_logging.py --no-cov` passed (12).

### 113 — Phase 15B.1 durable operational audit contract

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6
- Plan task: 15B.1
- Prompt intent: continue with the next task in the observability logging plan.
- Suggestion: record ADR 012, move audit logging in-scope in the threat model, and add Phase 15B to `PLAN.md` without application code.
- Outcome: accepted
- Reason: the human continued into 15B while 13D.6g is open. Recommended defaults apply except sequence: durable HTTP envelopes, no bodies, no read API, cascade delete, optional `LOG_FILE`. Per-function tracing and payload dumps stay rejected.
- Human validation: documentation only; no tests run for this task.

### 112 — Analysis accounting, spans before publish, truncation split

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6d corrective + observability
- Prompt intent: failed analysis again; logging incomplete; no outgoing-call rows for analysis; no spans/claim spans in the database.
- Suggestion: only improve log lines.
- Outcome: changed
- Reason: live batches hit `output_tokens=max` with `parse_ok=False` (truncated JSON). Claim batches now use a higher per-span token budget, default size 12, and split when `finish_reason=length`. Analysis completion ports wrap `AccountingCompletion` with purposes `extract_requirements`, `extract_claims`, and `assess` so `provider_call_accounting` records those calls. Candidate JD/CV spans are persisted at analysis start so they exist even when claim publication is withheld on incomplete. Job stage is written while running.
- Human validation: `pytest` on claim extraction and analysis pipeline passed (31) with `--no-cov`.

### 111 — Claim attach recovery and analysis diagnostics

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6d corrective + observability
- Prompt intent: analysis still failed; user asked for logging on every backend function.
- Suggestion: add a log statement to every function in every backend file.
- Outcome: rejected then corrected
- Reason: logging every function would drown signal and risk document text in logs (threat model). Instrumented the analysis path with stage counts, per-batch claim classification, `incomplete_reasons`, and workspace-bound context. Live failure showed `roles_without_claims=7` and attach drops; empty role headings no longer fail completeness alone, and a missing `roleSpanId` attaches to the nearest preceding heading.
- Human validation: `pytest` on claim extraction and analysis pipeline passed (29) with `--no-cov`.

### 110 — Claim extraction batches so a real CV finishes

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6d corrective
- Prompt intent: live analysis still failed `extraction_incomplete` after the scoreable-evidence gate; user said CV items should not remain unclassified and that this was an app limitation.
- Suggestion: treat the failure as document quality or leave single-shot classification.
- Outcome: rejected then corrected
- Reason: the active CV produced 135 server spans; one response capped near 4096 output tokens cannot return an assignment for each. Claim extraction now classifies spans in bounded batches (`CLAIM_BATCH_MAX_SPANS`, default 20) with one retry for skipped ids, matching the assessment batching pattern. Safe counts are logged. The worker message no longer says "every part of the CV".
- Human validation: `pytest` on `test_model_claim_extraction.py` passed (16) with `--no-cov`. Observed live job `8c9f6bfe-…` failed at `extracting_claims` with 135 spans / ~4050-token estimated full assignment JSON.

### 109 — CV completeness is scoreable evidence, not every line

- Date: 2026-09-22
- Tool / model: Cursor Composer
- Plan task: 13D.6d
- Prompt intent: live OpenAI analysis failed incomplete; user rejected blaming the CV or cover letter and required the PLAN acceptance criterion.
- Suggestion: treat every unclassified CV span, or an unparsed year on a role heading, as `extraction_incomplete`.
- Outcome: rejected then corrected
- Reason: PLAN 13D.6d makes extraction incomplete when missing roles, lost associations or rejected claim spans affect scoreable evidence — not when skills, education or narrative lines are left unclassified, and not when an unparsed date becomes undated. Completeness now fails for unclassified employment or claim-like spans, claims without a valid heading, and roles with no claims. ADR 010 updated. ISO role dates such as `2022-01 — Present` parse in domain code.
- Human validation: `pytest` on `test_model_claim_extraction.py` and `test_analysis_pipeline.py` passed (25) with `--no-cov`.

### 108 — Aviva-shaped synthetic regression fixture

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6f
- Prompt intent: continue 13D.6 with the synthetic shape fixture after incomplete-status work.
- Suggestion: copy private smoke documents into the repo for an end-to-end score assertion.
- Outcome: changed
- Reason: added a public-safe Markdown JD and DOCX-shaped CV with labels. Hermetic tests lock the safe gates (no heading/benefit/logistics scoring, six roles and seventeen claims preserved, incomplete assessment unpublished) without requiring a stochastic fit score.
- Human validation: `pytest` on `test_aviva_shaped_fixture.py` passed (5). Ruff passed on the test file.

### 107 — Incomplete analysis is not a fit score on screen

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6a, 13D.6e
- Prompt intent: continue 13D.6 in TDD with regular commits; tick when acceptance is met.
- Suggestion: leave failed roles showing a generic failure and keep the role pointer on the empty reanalysis version.
- Outcome: changed
- Reason: a failed reanalysis now restores the previous published version so the last valid score stays visible. Job errors return `{code, message}` as the contract already described. The UI shows "Analysis incomplete" for `assessment_incomplete` and `extraction_incomplete`, never `/100` for those states, and offers Retry analysis. Ranking still excludes failed roles; a restored prior score returns to ready.
- Human validation: unit tests for the reanalysis pointer and job error shape passed; integration tests for fail-and-restore and first-failure passed; frontend RoleHeader, RolesPanel and analysis-status tests passed (16).

### 106 — The server owns CV claim spans

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6d
- Prompt intent: continue 13D.6 and tick a subtask only when its acceptance is met.
- Suggestion: keep verbatim CV quotes and fall back to the rules extractor when verification fails.
- Outcome: changed
- Reason: quote copying silently dropped claims and a rules fallback could publish a partial CV as complete. The server now segments the CV and the model assigns span ids. Dates are parsed from the heading. A skills list is not a claim. A project claim cites the project heading. Incomplete extraction fails the job with `extraction_incomplete` and does not replace a previous claim set. 13D.6b and 13D.6c are ticked. 13D.6a stays open because the screen still does not say the analysis is incomplete and a failed reanalysis is not yet shown as the previous valid result.
- Human validation: `pytest` on the claim extraction, cover-letter, analysis pipeline and worker failure tests passed (39). Ruff and mypy passed on the changed Python files.

### 105 — The server owns extraction spans

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6c
- Prompt intent: continue 13D.6 so job-description extraction no longer depends on the model copying quotes.
- Suggestion: keep verbatim quote matching and drop lines the model fails to reproduce.
- Outcome: changed
- Reason: exact quote copying discarded real requirements when Markdown markers were omitted and kept generic headings the model copied. The server now segments the stored text and the model classifies those ids. A missing classification fails the job with `extraction_incomplete` and publishes no score. A colon-only heading is not scoreable. ADR 010 records the amendment. CV claims are still 13D.6d.
- Human validation: `pytest` on the requirement extraction, model extraction, PDF-shape and analysis pipeline tests passed (42). Ruff check passed on the changed Python files.

### 104 — Assessment calls are batched and retried once

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6b
- Prompt intent: continue 13D.6 in TDD order after the unpublished-score contract.
- Suggestion: send every requirement in one assessment response and accept whatever comes back.
- Outcome: changed
- Reason: the reproduced call sent ten requirements and got one assessment back. The batch size now comes from an explicit output-token budget. A missing item is retried once, already accepted items are not sent again, and the log records counts rather than requirement or evidence text.
- Human validation: the new batch, retry and ten-item tests failed on import of `AssessmentBatchBudget`, then passed with the rest of `test_structured_assessment.py` (8). Ruff check and format passed on the changed files.

### 103 — An incomplete assessment is not a fit score

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6a
- Prompt intent: start Phase 13D.6 in TDD order, beginning with the incomplete-analysis contract.
- Suggestion: keep publishing a numeric score and only change the band when the arithmetic is zero.
- Outcome: changed
- Reason: a surviving partial assessment was producing a small positive score such as 4/100 while the rest of the requirements had no valid assessment. The existing failed-job state already has an error code, so incomplete analysis uses `assessment_incomplete` on that state. `analysis_incomplete` stays the 409 for work that has not finished. No new role status.
- Human validation: failing tests written first for an unpublished partial assessment and for a job that returns no assessments. `pytest` on `test_mapping_scoring.py`, `test_analysis_pipeline.py` and `test_analysis_attribution.py` passed (32). Ruff check and format passed on the changed Python files. `make test` and `make test-integration` were not run for this commit.

### 102 — A failing job took the whole worker down

- Date: 2026-09-22
- Tool / model: Claude Opus 5, Cowork session
- Plan task: 13D.6 (walkthrough)
- Prompt intent: fix the crash seen during a live run.
- Suggestion: treat the stack trace as three defects rather than one — the
  foreign-key violation that started it, the failure handler that raised on
  the job row, and the loop that ended on that exception.
- Outcome: accepted
- Reason: the reported error was the constraint violation, but the damaging
  one was the third. `run_forever` had no guard, so the thread ended and every
  later analysis in that process stayed queued with nothing shown anywhere in
  the interface. A crash that is loud in the log and silent in the product is
  worse than the error that caused it. The trigger is a real race: extraction
  runs for minutes, and a document replaced or deleted in that window takes its
  row with it, so the write now checks the documents and fails as
  `documents_changed` instead of surfacing a driver constraint.
- Human validation: three failing tests written first — the loop continuing
  after a job raises, the failure handler not raising when the job row is
  absent, and the named document check. Backend pytest exited 0 with coverage
  82.11%; ruff check, ruff format --check and mypy on 134 source files passed.
  `fail_job` also changed, and `make test-integration` has not been run against
  it from this session.

### 101 — Showing the cover letter made it worse, and was reverted

- Date: 2026-09-22
- Tool / model: Claude Opus 5, Cowork session
- Plan task: 13D.6
- Prompt intent: close the last gate failure, the contradiction case.
- Suggestion: show up to two self-authored claims to the assessor as context
  that cannot be cited, so a letter denying the CV is visible.
- Outcome: rejected after measurement
- Reason: on the same labels with `qwen2.5:7b`, disagreements went from 3 to 6
  and the contradiction case still was not `partial`. Two of the new failures
  printed an empty reason, which means the assessment was rejected in
  validation: the model was shown the letter, cited it, and lost the whole
  assessment because that span is not citable. `dev-letter-dup` was correct
  before the change and broke on it. Showing evidence that may not be cited
  turns a wrong answer into no answer. Reverted; a denial that lives only in a
  cover letter needs a contradiction check the server performs itself.
- Human validation: observed live output for v3 and v4 recorded in
  `docs/evaluation.md`, including the empty justifications. After the revert,
  backend pytest exited 0 with coverage 82.11%; ruff check, ruff format --check
  and mypy on 134 source files passed. `dev-overlap` and `dev-injection` also
  changed between the two runs with no code touching them, so the comparison is
  reported as one run per configuration rather than averaged.

### 100 — The completion model is part of the assessment contract

- Date: 2026-09-22
- Tool / model: Claude Opus 5, Cowork session
- Plan task: 13D.6
- Prompt intent: run the same labels against two local completion models and
  act on the result.
- Suggestion: ship the model that was measured, record the one that was not,
  and make one targeted prompt change for the single remaining gate failure.
- Outcome: accepted
- Reason: on `evidence-assessment-v2`, `llama3.2` disagreed on 12 of 24
  requirements, returned four unsupported `met` results and credited
  `dev-injection` / `req-inject` — the case whose untrusted text asks to be
  treated as a match. `qwen2.5:7b` on the same labels disagreed on 3, left the
  held-out split clean and passed every predeclared gate except unsupported
  `met`, which was the contradiction case. Defining the levels made the small
  model confidently wrong rather than uniformly refusing, which is the worse
  of the two failures, so the default model moved rather than the prompt being
  softened for it.
- Human validation: observed live output for both runs recorded in
  `docs/evaluation.md`. Failing tests written first for the default model, the
  shipped configuration example and the conflict rule. Backend pytest exited 0
  with coverage 82.11%; ruff check, ruff format --check and mypy on 134 source
  files passed. No run has been recorded against `evidence-assessment-v3`, and
  the held-out split is the check on whether that change is an improvement or
  an overfit to three development cases.

### 099 — Define the assessment levels after the model hedged

- Date: 2026-09-22
- Tool / model: Claude Opus 5, Cowork session
- Plan task: 13D.6
- Prompt intent: re-run the live pilot after the retrieval fix and act on the
  numbers.
- Suggestion: with retrieval measured at zero misses, revise the prompt rather
  than the retrieval, and make the completion model configurable so a weak
  model can be told apart from a weak prompt.
- Outcome: accepted
- Reason: the observed run disagreed on 15 of 24 requirements in both
  directions. No labelled `met` came back as `met`, and six labelled `missing`
  requirements came back `partial` with a cited span, including two that share
  no subject matter with the evidence. The prompt named met, partial and
  missing and defined none of them. Unsupported `met` of zero was not taken as
  progress, because the model returned `met` for nothing at all.
- Human validation: observed live output recorded in `docs/evaluation.md`:
  roles 20, disagreements 15, unsupported_met 0, order_disagreements 2,
  retrieval_misses 0, completion calls 19, p50 1.90s, p95 2.36s. Failing test
  written first for the level definitions and the version bump. Backend pytest
  exited 0 with coverage 82.10%; ruff check, ruff format --check and mypy on
  134 source files passed. No run has been recorded against the new prompt
  version.

### 098 — Rank retrieved evidence instead of gating it

- Date: 2026-09-22
- Tool / model: Claude Opus 5, Cowork session
- Plan task: 13D.3 (retrieval), 13D.6 (measurement)
- Prompt intent: decide whether to continue after the live pilot came back worse
  on disagreements and role order, then make the changes in TDD order.
- Suggestion: do not revise the assessment prompt yet. Six of the nine live
  disagreements were labelled `met` returned `missing`, which cannot be read
  until retrieval is measured. Record what the assessor was shown, replace the
  retrieval gate with a bounded ranked shortlist, stop falling back to the
  lexical path, and re-measure.
- Outcome: accepted
- Reason: a claim reached the assessor only on a shared keyword or a similarity
  above the floor. A paraphrase has neither, so `missing` was decided before the
  model saw anything and no prompt change could have fixed it. Measured on the
  pilot, the old gate decided 7 of 24 scoreable requirements with no assessor
  call and never showed 2 labelled supporting passages — the two paraphrase
  cases from the live run. Both are now zero. The assessment prompt was not
  touched.
- Human validation: four failing tests written first, each passing after its
  change: the recorded retrieval set, the paraphrase below the floor, the
  bounded candidate set, and a monkeypatched `map_requirements` proving the
  lexical path no longer runs behind the assessor. Backend pytest exited 0 with
  coverage 82.10%; ruff check, ruff format --check and mypy on 134 source files
  all passed. Run in a Linux virtual environment built for this session, not on
  the developer's machine: `make test-integration`, the frontend suite and the
  live Ollama smoke run have not been repeated since this change.

### 097 — Read a stored embedding when the driver returns an array

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6 (quality targets)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: keep the four Make quality targets moving. Wrap the one ruff
  line-length failure, format the four test files ruff format rejected, and
  accept a numpy embedding array as a numeric vector.
- Outcome: accepted
- Reason: `make lint` was already failing on tests from this branch, and the
  integration failure was a real read-back bug. The assessment prompt was not
  changed. 13D.6 stays open because the walkthrough and the remaining
  documentation are not done.
- Human validation: `make lint` failed first on a long assertion, then on four
  unformatted test files. After those edits, `make lint` passed, including
  mypy on 134 source files and the frontend typecheck and eslint. `make test`
  passed: backend 365 passed, 3 skipped, coverage 81.82%; frontend 119 passed.
  `make test-integration` then failed because a 1536-dimension numpy vector
  was not a sequence. The new unit test failed the same way. After the read
  accepted an iterable of numeric scalars, that unit test and the embedding
  integration test passed, and `make test-integration` exited 0.

### 096 — Measure the labelled pilot on local Ollama

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.6 (check set on the local model)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: score the labelled pilot through the local completion and
  embedding models, keep that run out of the default suite, and record the
  counts without changing the hermetic baseline.
- Outcome: accepted
- Reason: the live run did not beat the hermetic baseline on disagreements or
  role order. The assessment prompt was not revised, and no second model was
  added. 13D.6 stays open.
- Human validation: the new hermetic comparison failed to import
  `measured_policy_baseline`, then the baseline file passed (4) and mypy was
  clean on that module. `RUN_LLM_SMOKE=1` pytest of the smoke test passed in
  30.77s: 20 roles, 9 disagreements, 1 unsupported met, 1 order disagreement,
  p50 1.72s, p95 3.93s, 14 completion calls, 19 embedding calls, provider
  ollama, `left_machine` false. Ruff was clean on the smoke test.

### 095 — A restart reads the saved analysis

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (Fit, Gaps, Prepare and Letter read the saved result)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: lock a new SQL store to the saved ranking, fit, gaps, interview
  pack and letter, and lock the role, gap-plan and ranking reads so they do
  not add a completion call.
- Outcome: accepted
- Reason: the behaviour was already in the store and the read routes. These
  tests are regression locks. The first API assertion treated call records as
  a method; the corrected check compares the record tuple before and after
  the three reads. Interview-pack and cover-letter phrasing routes still call
  the completion model and are outside this lock. 13D.6 and both exit gates
  stay open.
- Human validation: the SQL restart test passed on the first run. The API
  test then failed with `TypeError: 'tuple' object is not callable`, and
  passed after the assertion used the `records` property. Ruff was clean on
  both test files. No production code changed. No live model call.

### 094 — A course does not meet years of leadership

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (course-versus-leadership regression)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: keep an introductory course from meeting a years-of-leadership
  requirement in domain mapping, on the API, and in the SQL worker. Apply the
  same cap when a validated model assessment says met.
- Outcome: accepted
- Reason: the prompted-JSON test was changed to use a production claim, so it
  still proves that a valid met is accepted. The course case is a separate
  test. The hermetic baseline was re-measured rather than edited by hand.
- Human validation: the domain test failed with status met, the model-path
  test failed with status met, and the API test failed with fit score 85.
  After the rule, those tests, the structured-assessment file, the mapping
  score file, the baseline, and the SQL worker test passed (30). The
  re-measured hermetic baseline is 7 disagreements, 5 unsupported met results,
  and 0 order reversals. mypy was clean on the mapping and relatedness
  modules. No live model call.

### 093 — Name the requirements that distinguish a tie

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (stable ties)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: keep equal scores on one competition rank, ordered by title then
  id, and replace the shared met requirements in that group with the ones that
  are not on every tied role.
- Outcome: accepted
- Reason: a role whose reasons are entirely shared keeps those reasons, so a
  tie of identical evidence is not blank. An untied role is unchanged.
- Human validation: the new ranking test failed because both tied roles still
  named `sql`. After the filter, both ranking tests passed. No live model call.

### 092 — Do not count overlapping jobs as separate years

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (concurrent employment)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: merge overlapping employment periods for the same skill, and
  keep a years requirement at partial when the merged stretch is shorter than
  the requirement states. Back-to-back jobs still add up. A single dated claim
  is left to the existing matcher.
- Outcome: accepted
- Reason: the year count is domain arithmetic. The model may still say met;
  the mapping is capped afterwards. A month of slack stops a calendar-year
  boundary from looking like a shortfall.
- Human validation: the overlap test failed with status `met`. After the merge,
  that test and the back-to-back test passed. Re-running the hermetic baseline
  observed 10 assessment disagreements and 8 unsupported `met` results;
  `dev-overlap` left the list. The course-versus-leadership pin is unchanged.
  Mapping, baseline and structured-assessment tests passed (26). mypy was clean
  on the four changed modules. No live model call.

### 091 — Score duplicate requirements once and cap uncertain coverage

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (coverage and deduplication)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: count identical requirement text once, cap a met assessment at
  partial when conditions are unknown or the evidence contradicts, and band a
  zero score from a failed assessment as incomplete rather than limited.
- Outcome: accepted
- Reason: the rubric weights stay as configured. A role that also has a met
  requirement keeps its numeric band; only an all-zero incomplete analysis
  changes band. Duplicate lines remain in the explanation with zero weight.
- Human validation: the three new scoring tests failed because
  `RequirementMapping` had no `unknown_conditions`. After the scoring rules,
  mapping, structured-assessment, item-type, cover-letter, fit and gap tests
  passed (39). mypy was clean on the three changed modules. No live model call.

### 090 — Record who assessed a saved analysis

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (attribution slice)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: store the assessment provider, model, prompt version, rubric
  version and whether content left the machine on the saved score, and record
  `assessment_incomplete` as a failure status rather than as a low fit.
- Outcome: accepted
- Reason: the score row stays the arithmetic. Attribution is a separate record.
  A missing stored attribution on a direct publish still fills the hermetic
  defaults and derives the failure status from the mappings.
- Human validation: `tests/unit/test_analysis_attribution.py` failed on import
  of `analysis_failure_status`. After the domain function, migration and
  worker wiring, that test, the claim-detail reload test and the SQL role-store
  analysis test passed (3). mypy was clean on the nine changed modules. No live
  model call.

### 089 — Persist claim detail and requirement seniority

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.5 (field round-trip only)
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: store employer, title, scope, technologies, outcome, employment
  dates, the real extraction confidence and requirement seniority, and reload
  them instead of inventing confidence 0.85 or dropping seniority. Keep a
  saved missing assessment as missing after a new unit of work.
- Outcome: changed
- Reason: a missing stored confidence reloads as 0.0 rather than the old
  invented 0.85. The rest of 13D.5 (provenance versions, coverage, dedupe,
  concurrent employment, ties, and every feature reading one saved result) is
  not in this change. The 13D.5 checkbox stays open.
- Human validation: the integration test failed first because `Claim` had no
  `period_start`, then because reloaded seniority was `None`. After the
  migration and mapper, that test, the analysis persistence file, and the
  claim extraction unit tests passed (21). mypy was clean on the six changed
  modules. No live model call.

### 088 — Ask phrases every intent from stored analysis

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.4
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: send fit, gaps, compare, evidence and preparation through the
  configured completion model, using the stored score as grounding; retrieve
  uploaded letters by token overlap; read the output cap from settings,
  default 2000, and clamp it to the model window.
- Outcome: changed
- Reason: an insufficient-evidence result still returns before any model call,
  and citations still come from the stored mapping rather than from model
  text. The model phrases; it does not rescore.
- Human validation: the new tests failed because `clamp_prompt_budget` was
  missing and structured intents did not call completion. After the change,
  the Ask, prompt, provider-default, structured-ask and message API tests
  passed (31). mypy was clean on the changed modules. No live model call.

### 087 — Structured assessment replaces boolean adjudication on the model path

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.3
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: validate a structured assessment server-side and, when the
  completion adapter decides support, treat a missing or invalid assessment as
  incomplete even if lexical and embedding signals agree. Keep the hermetic OR
  fallback so offline tests still score.
- Outcome: changed
- Reason: the boolean adjudicator stays on the hermetic fixture. Replacing it
  there would make every `make test` role incomplete. The model path no longer
  uses that boolean to decide a match.
- Human validation: `tests/unit/test_structured_assessment.py` failed on import
  of `parse_assessments`. After the validator, adapter and mapping branch, that
  file plus adjudication, three-signal, mapping-score and cover-letter tests
  passed (36 tests). mypy was clean on the three changed modules. No live model
  call.

### 086 — Record the evidence-assessment contract

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.2
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: add ADR 011 stating that the model assesses, the server validates
  and the domain calculates the score; concrete uploaded-letter experience can
  count, aspirations and generated drafts cannot; reconcile AGENTS, features and
  ADRs 004, 009 and 010.
- Outcome: accepted
- Reason: PLAN 13D.2 already stated the letter policy. The record says the
  running matcher still excludes self-authored claims, so the ADR is not a claim
  that the code already does this.
- Human validation: `tests/unit/test_evidence_contract.py` failed because ADR 011
  was absent and the older documents still forbade letter evidence. After the
  ADR and the reconciliations, that file, `test_phase0_baseline.py` and
  `test_production_wiring_matrix.py` passed (17 tests). No application code
  changed.

### 085 — Record the hermetic matcher against the labelled pilot

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: 13D.1
- Prompt intent: continue the remaining PLAN.md tasks in TDD order and commit
  each one.
- Suggestion: the labelled pilot already existed; add a comparison that runs
  today's NullAdjudicator path and records disagreements without writing them
  back into the labels.
- Outcome: accepted
- Reason: 13D.1 asked for the before-measurement. The cases and loader were
  already merged; the missing piece was what the current code gets wrong.
- Human validation: the new test failed on import of `current_policy_baseline`.
  After the runner, `tests/evaluation/test_quality_baseline.py` passed (3 tests).
  The observed hermetic result was 11 assessment disagreements, 9 unsupported
  `met` results and 1 order reversal. ruff and mypy were clean on the changed
  module. No live model call.

### 084 — CI runs only when a pull request is opened into main

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.7
- Plan task: none (workflow trigger change requested directly)
- Prompt intent: run the GitHub workflow only when a pull request is created into
  main, and not on every code push or on main.
- Suggestion: drop the `push` trigger and limit `pull_request` to `opened` against
  `main`.
- Outcome: accepted
- Reason: the developer asked for CI only at PR creation into main.
- Human validation: TBD

### 083 — Refocus the remaining plan on evidence assessment and ranking quality

- Date: 2026-09-22
- Tool / model: Codex
- Plan task: repository review and PLAN.md update following the product/LLM discussion
- Prompt intent: review current development and update the delivery plan around
  accurate role ranking, CV/cover-letter evidence, retrieval and focused LLM prompts.
- Suggestion: add Phase 13D with a labelled baseline, explicit policy decisions,
  structured assessment experiment and a measured adoption gate; extend Phase 14
  with retrieval/assessment/ranking metrics and independent generation evaluation.
- Outcome: documentation updated; implementation and policy adoption are pending.
- Reason: the merged three-signal matcher calls the model only on lexical/vector
  disagreements and receives a boolean. Synthetic diagnostics still return `met`
  for an introductory Python course against five years of production leadership,
  both when signals agree and when a disagreement receives no model decision.
  The token groundedness check also accepts unsupported leadership wording.
  Ask remains lexical; SQL reload loses structured claim details; cover-letter
  extraction support alone does not establish production use in assessment/drafting.
- Changed from earlier advice: recognised the now-merged Phase 13C adjudicator and
  configurable similarity floor rather than planning them as absent. Kept proposed
  cover-letter scoring and model assessment subject to an explicit contract/ADR
  decision before implementation; preserved existing completed implementation history.
- Rejected alternatives: require a non-zero score or an LLM win; treat fixture tests
  as measured model accuracy; add multiple models/frameworks before a bounded pilot;
  commit a private CV as a fixture; claim tokens or valid citations prove meaning.
- Agent verification: from `backend`, `.venv/bin/pytest
  tests/unit/test_mapping_scoring.py tests/unit/test_three_signal_matching.py
  tests/unit/test_model_adjudication.py tests/unit/test_open_question_prompt.py
  tests/unit/test_cover_letter_narrative.py
  tests/unit/test_model_requirement_extraction.py
  tests/unit/test_model_claim_extraction.py tests/unit/test_ranking.py --no-cov
  -o addopts='' -q` reported **59 passed**. Read-only synthetic diagnostics reported
  `met` with zero adjudicator calls for agreement, `met` with one empty adjudication
  for disagreement, and groundedness `pass` for unsupported leadership wording.
  Similarities were injected test values; no live provider accuracy was measured.
- Human validation: pending review of the plan and the proposed assessment/source
  policy. No application code changed; no hosted request or private-document run.

### 082 — Phase 13C.10 documentation reconciliation (TDD)

- Date: 2026-09-22
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.10
- Prompt intent: continue 13C.10 on the same branch and PR after 13C.5 and 13C.8 landed.
- Suggestion: extend the wiring-matrix docs tests so README cannot call hermetic the product default or leave 13C.8 open; update README, ADR 010, features.md, the threat model and production-wiring; tick PLAN 13C.10.
- Outcome: accepted.
- Reason: ADR 010 already existed from the first 13C.10 pass and is the audit page PLAN asked for. What remained was stale claims written before three-signal matching, output depth and live extraction fixes. The 13C exit gate is not ticked: it still needs the maintainer's real CV, five adverts and the full `make` gates.
- Rejected alternatives: a second ADR; claiming the 13C exit gate on documentation alone.
- Human validation: docs tests failed on the old README/ADR/features text; after the change, `test_production_wiring_matrix.py` and `test_phase0_baseline.py` pass (14 tests).

### 081 — Requirement extraction classifies package lines (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: live extraction defect (13C exit gate: no salary, benefit or logistics line is scored)
- Prompt intent: a "Package and practicalities" block (salary, share options, commission, remote/travel, right to work) was extracted as must-have requirements and lowered the fit score. Classify via the LLM, not a post-filter.
- Suggestion: domain heuristics to demote salary/location after extraction; alternatively enrich the extraction system prompt, JSON schema descriptions, a classification restatement after the untrusted JD, and pass the schema to Ollama as `format`.
- Outcome: changed.
- Reason: the human rejected filters. Item type is an extraction decision; the model must structure it. Scoring already ignores unscoreable kinds. The local adapter previously sent `format: "json"`, so schema enum descriptions never reached Ollama.
- Rejected alternatives: regex/keyword reclassification of extracted items; dropping package lines at extraction time (ADR 010 keeps them, unmapped).
- Human validation: new extraction tests failed on the old one-sentence prompt; after the change, focused extraction tests, the Ollama schema test and the completion contract suite pass.

### 080 — Phase 13C.8 output depth (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.8
- Prompt intent: continue Phase 13C; make every tab return something worth reading.
- Suggestion: domain `build_fit_summary` from scored mappings; optional
  `Role.fitSummary` on GET `/roles/{id}` only; interview templates quote
  `claim.context`; stop truncating requirement evidence at 80 characters.
- Outcome: accepted.
- Reason: the gap plan, cover letter and bullets already had depth. The missing
  pieces were a prose fit reading of the mapping, full quoted CV text on each
  requirement, and interview prompts that use the candidate's own claims. The
  summary is arithmetic over stored requirement text, not a model paraphrase.
  List and create still omit the paragraph so the workspace table stays a table.
- Rejected alternatives: a new HTTP route (the wiring matrix forbids one for
  this); putting the summary on every Role list row; letting the model write
  the paragraph.
- Human validation: fit-summary unit tests failed on the missing export; after
  the change, focused backend tests pass. RequirementTable and FitBreakdown
  component tests pass.

### 079 — Phase 13C.6 score only scoreable items; flag adjudication (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.6
- Prompt intent: continue Phase 13C after three-signal matching.
- Suggestion: additive `ScoreComponent.adjudicated` when the mapping's
  adjudication signal is true; persist `item_type` and `self_authored` so a SQL
  reload cannot score a salary line or map a cover letter.
- Outcome: accepted.
- Reason: the filter already lived in `map_requirements` (13C.2a). Without
  persisting the kind, a SQL reload defaulted every item to `requirement` and
  would score it. The flag is additive so 7.4 arithmetic and 7.5's object shape
  stay; old explanation JSON without the key reloads as false.
- Rejected alternatives: changing the score formula when the model confirmed a
  pair; treating "adjudication alone" as a third OR (13C.5 already made that
  a tie-break, so the flag means the model confirmed a disagreement).
- Human validation: the new explanation test failed on missing
  `adjudicated`; after the change, mapping-scoring and item-type tests pass.
  Full default pytest suite passed with 3 skipped; coverage 81.25%. ruff and
  mypy clean.

### 078 — Phase 13C.5 three-signal matching (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.5
- Prompt intent: continue Phase 13C; implement three-signal matching.
- Suggestion: relatedness as lexical overlap, embedding cosine, and model
  adjudication of XOR disagreements; combination in domain; floor in
  `config/scoring_rubric.toml`; hermetic `NullAdjudicator` falls back to OR so
  embedding-only adjacent matches survive; mappings record signal strength;
  persist JSONB `signals` and expose it on `Requirement`.
- Outcome: accepted, with one combination rule changed from a naive third OR.
- Reason: `related = lexical OR embedding OR adjudication` would never need the
  third signal — disagreement already has a true. Adjudication is a tie-break
  on XOR pairs. Hermetic must not veto embedding-only relatedness (the existing
  0.9 cosine test). Lexical overlap stayed a pure domain function rather than a
  port: it is not an I/O boundary. Embedding already had a port; only
  adjudication is new.
- Rejected alternatives: three RelatednessPorts wrapping lexical overlap;
  treating competency match as a fourth relatedness OR (status still uses it);
  letting adjudication fire on agreed pairs.
- Human validation: `test_three_signal_matching` failed on missing modules,
  then 10 tests there plus model-adjudication, mapping, analysis-pipeline,
  analysis-similarity, OpenAPI and wiring-matrix tests pass. Full default
  pytest suite passed with 3 skipped; coverage 81.24%. ruff and mypy clean.

### 077 — Phase 13C.10 ADR 010 for model-first extraction

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.10 (ADR and stale-claim updates; phase not closed)
- Prompt intent: document why deterministic extraction was replaced before
  opening the PR.
- Suggestion: ADR 010 records the 2026-09-21 audit, the failed intersect-with-
  rules model path, and the replacement: model extracts, server verifies the
  quote, domain decides. ADR 003, AGENTS.md, README, features.md, the threat
  model and production-wiring were aligned with the new default.
- Outcome: accepted as documentation for the work already on the branch.
  13C.10 stays open until 13C.5 and 13C.8 land.
- Reason: PLAN calls this ADR the most useful page in the repository for a
  reviewer. Shipping extraction without it would leave the old hermetic-default
  claims in the docs.
- Human validation: docs-only change plus ADR; wiring-matrix tests still apply.

### 076 — Phase 13C.7 bullets refuse adjacent-only evidence (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.7
- Prompt intent: stop drafting a CV bullet from an adjacent_claim_only match.
- Suggestion: `mapping_supports_cv_bullet` returns false for adjacent-only
  mappings. `post_bullets` raises the existing 409
  `insufficient_cited_claims`. The gap plan still recommends `evidence_it`
  but `can_draft_bullet` is false, so the UI does not offer a button that
  would 409. Cover-letter drafting already requires `MET` must-haves;
  interview `lead_with` is already MET-only — regressions confirm neither
  path has the same hole.
- Outcome: accepted.
- Reason: an adjacent claim is related, not supporting. Phrasing it as a
  cited bullet for that requirement would put the candidate's name on a
  claim the mapping itself called adjacent-only.
- Human validation: gap-plan and import tests failed first. After the
  change, generation, gap-plan and grounded-generation HTTP tests pass.

### 075 — Phase 13C.4 cover letter is narrative, never score evidence (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.4
- Prompt intent: extract uploaded cover letters without letting them change
  the fit score.
- Suggestion: extract cover letters into the same claim shape, flag
  `self_authored`, and filter those claims out inside `map_requirements` so
  every caller is covered. The 6.5 test no longer raises: extraction is
  allowed, mapping is not.
- Outcome: accepted.
- Reason: the same placement as the item-type filter — a rule every caller
  must remember is a rule one caller will forget. Ask already retrieves
  cover-letter spans; the new defence is that a self-authored dbt bullet
  cannot satisfy a dbt requirement.
- Rejected alternatives: keeping the ValueError and never extracting. PLAN
  13C.4 wants the letter available to drafting and Ask. Refusing extraction
  made that impossible.
- Human validation: 4 new tests failed (ValueError / missing field). After
  the change, focused cover-letter and claim tests plus the unit suite are
  green. ruff and mypy clean on the changed files. The analysis worker still
  extracts only the CV during a role job; the mapping filter is what would
  hold if those claims were mixed in.

### 074 — Phase 13C.3 structured CV extraction with verified quotes (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.3
- Prompt intent: continue 13C; extract every role, not only the first, with
  dates parsed in domain code.
- Suggestion: the model returns roles (employer, title, date-range quote) and
  nested claims (quote, competency, scope, technologies, outcome). The server
  locates each quote in the stored text. Recency and duration are derived from
  `parse_date_range` on the verified date quote — a model-supplied recency
  field is ignored. Employer and title are kept only when they appear in the
  document.
- Outcome: accepted.
- Reason: the audit's claim extractor stopped at the second role and dated
  nothing. Intersecting model output with the regex cannot recover a prose CV;
  verifying quotes can. Claim gained optional structure fields with defaults
  so every existing constructor stays valid.
- Rejected alternatives: trusting a model-emitted recency signal. PLAN 6.4
  forbids it. Invented employer names are blanked rather than attached to a
  verified claim.
- Human validation: 6 of 7 new tests failed against the old intersect-with-
  rules extractor (the regex-finds-nothing baseline already passed). After
  the change, focused claim tests 15 passed; full unit suite green; ruff and
  mypy clean on the changed files.

### 073 — Phase 13C.2b quote-verified requirement extraction (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13C.2 (second half — model extraction with verbatim quote check)
- Prompt intent: continue 13C from the uncommitted 13C.2b draft; TDD, regular
  commits, then a PR.
- Suggestion: stop intersecting model output with the rules extractor. The
  model returns a verbatim `quote` plus `item_type`; the server locates that
  quote in the stored normalised text and builds the span from those offsets.
  Unverifiable items are dropped and counted, never repaired.
- Outcome: accepted, with the injection test rewritten against the 5.5 fixture.
- Reason: the delivered model path could only remove what the regex had already
  found, so a prose advert produced nothing. Verbatim locating is PLAN 5.4 and
  is also the injection defence: a scripted model that obeys "add CUDA / ROS2 /
  a perfect match" cannot land those items unless they appear as quotes.
- Changed from the draft left in the working tree: the 5.5 test no longer
  asserted a tautology (`"ten years of Rust" in injected`); it now uses
  `jd-injection-attempt.txt` and three invented extras. Competency is the
  model's open vocabulary; seniority and vagueness are still derived from the
  verified quote in domain helpers, not trusted from the model.
- Rejected alternatives: fuzzy-matching a near-miss quote back into the
  document. PLAN 5.4 forbids repair. Falling back to the rules result only
  when *nothing* verifies, so a bulleted advert still analyses if the model
  invents everything.
- Human validation: 9 of 10 new tests failed against the old intersect-with-
  rules extractor (prose requirements empty; `dropped_unverifiable` missing).
  After the change, focused `test_model_requirement_extraction.py` plus
  `test_requirement_extraction.py` is 18 passed. Unit + contract + API
  hermetic run green. ruff clean on the changed files; mypy clean on the three
  source files.

### 072 — Phase 13C.2a extracted items carry their kind (TDD)

- Date: 2026-09-21
- Tool / model: Claude (Opus 5), agent session
- Plan task: 13C.2 (first half — the domain type and the scoring boundary)
- Prompt intent: stop the scorer treating a salary band as a must-have.
- Suggestion: an `ItemType` on `Requirement` — requirement, responsibility,
  benefit, logistics, non_requirement — with `SCOREABLE_ITEM_TYPES` holding the
  first two, and `map_requirements` skipping everything else.
- Outcome: accepted.
- Reason: the filter belongs in `map_requirements` rather than at each call
  site. Three callers build mappings (the SQL worker, the analysis service and
  the hermetic path) and a fourth would have been added by 13C.5; a rule that
  every caller must remember is a rule that one caller will forget. Unscoreable
  items are still extracted and still returned by the requirements route, so the
  UI can show what the advert pays without the scorer judging the candidate
  against it.
- Rejected alternatives: dropping non-scoreable items at extraction time. They
  are real content a reader wants — the salary, the location, what the role is
  explicitly not — and discarding them would make the product worse while
  hiding the classification from any future evaluation.
- Changed from the proposal: `item_type` defaults to `requirement` so the rules
  fixture extractor and every existing test keep working unchanged; only the
  model path in 13C.2b sets it deliberately.
- Human validation: the new test module failed collection first — `ItemType`
  and `SCOREABLE_ITEM_TYPES` did not exist — then 6 tests pass. Full suite
  `289 passed, 3 skipped, 52 deselected`. ruff and mypy clean.

### 071 — Phase 13C.1 a local model becomes the default (TDD)

- Date: 2026-09-21
- Tool / model: Claude (Opus 5), agent session
- Plan task: 13C.1
- Prompt intent: stop shipping the test fixture as the product default.
- Suggestion: `ProviderSettings` defaults move from `hermetic` to `ollama`;
  `config/app.env.example` selects Ollama and says in a comment that the
  hermetic adapters are a test fixture rather than a deployment option; the dead
  `EXTRACTION_STRATEGY` key is deleted from the example and the engineering
  journal.
- Outcome: accepted.
- Reason: `EXTRACTION_STRATEGY` was set in configuration and read nowhere in
  `backend/src` — extractor routing is decided in `selected.py` by provider id
  alone. A second switch that does nothing is worse than no switch. Deleting it
  was chosen over implementing it because provider id already carries the
  decision.
- Rejected alternatives: removing `hermetic` from the `GET /providers`
  catalogue as well. The plan item is about what configuration offers, and the
  catalogue is also how the test suite and the egress tests select a provider;
  changing it belongs with 13C.10's documentation pass if it is done at all.
- Human validation: 3 of 4 new tests observed failing for the intended reasons;
  the fourth — that the test app factory still builds a hermetic app — passed
  from the start and is kept as the guard that `make test` stays offline. After
  the change `pytest --no-cov` reports `283 passed, 3 skipped, 52 deselected`.
  `ruff check` and `ruff format --check` clean. `mypy` clean over 125 source
  files, on a fresh cache directory.
- Note: no test asserted the previous `hermetic` default, which is itself the
  finding — the shipped default was never covered.

### 070 — Phase 13C.9 repair the deterministic fixture path (TDD)

- Date: 2026-09-21
- Tool / model: Claude (Opus 5), agent session
- Plan task: 13C.9
- Prompt intent: the product returned a fit score of 0 for a real CV and a real
  job advert; find out why and repair the fixture extractors.
- Suggestion: three regression tests reproducing the shapes a PDF really
  produces, then the minimum fixes — accept a bullet glyph with no following
  space, treat a section boundary as a short standalone heading rather than any
  line beginning with a section word, and parse abbreviated month ranges.
- Outcome: accepted.
- Reason: observed on the real document. `pypdf` emits list items as
  "•Text" with no space; normalisation rewrites that to "-Text"; the bullet
  pattern required whitespace, so the claim extractor returned zero claims and
  every requirement mapped to `missing`. With that corrected, a wrapped body line
  reading "education customers. Live in production for two years." matched
  `_SECTION_STOP` and ended the experience section at the second role. Role dates
  were written "Jan 2026 - Present" and the range pattern only accepted full
  month names, so every claim came out undated.
- Changed from the proposal: one assertion in the new tests was wrong and
  exposed a fourth issue — a bullet that wraps is truncated at the line break.
  That is outside 13C.9 and disappears once 13C.3 has the model return a
  verified quote, so it is recorded as a named limitation test rather than
  fixed here.
- Rejected alternatives: using the maintainer's real CV as the fixture (personal
  contact details in a public repository; the manifest already says synthetic
  only) — a synthetic fixture carrying the same pypdf shapes is used instead.
  Also rejected: widening the extractor to join wrapped bullets, which would
  have grown this task into the work 13C.3 replaces entirely.
- Human validation: 4 of 6 new tests observed failing for the intended reasons
  before any source change; after the fixes `pytest --no-cov` reports
  `279 passed, 3 skipped, 52 deselected, 2 warnings`; `ruff check` clean,
  `ruff format` applied to one file, `mypy` clean over 125 source files.
  Integration tests were not run in this session — the agent shell cannot reach
  the developer's local PostgreSQL.

### 069 — Wire embedding similarity into requirement mapping (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.10 (corrects the 7.2 claim)
- Prompt intent: similarity support was ticked in PLAN 7.2 but did not change
  mapping outcomes; wire embeddings into requirement mapping and drop the unused
  chunk index.
- Suggestion: pair-keyed similarities, reachable `similarity >= floor` branch,
  batched embed + cache, unconstrained `embeddings` table keyed to requirement
  or claim, exact cosine, no Ask retrieval.
- Outcome: accepted.
- Reason: reading `_is_related` showed the similarity branch was dead — it
  required `_overlap_count(...) >= 1`, which the branch above already returned
  on. Callers passed `None`. `Vector(64)` could not store nomic/OpenAI sizes.
  `ChunkRow`/`EmbeddingRow` were referenced from models only.
- Rejected alternatives: adding an ivfflat/hnsw index; a document chunk pipeline;
  vector search for Ask (named non-goal); keeping a claim-id-only similarities
  dict.
- Human validation: focused unit tests 34 passed (`test_similarity`,
  `test_analysis_similarity`, `test_mapping_scoring`, `test_analysis_pipeline`,
  operational logging). Integration mapping test is in the tree; not run in this
  commit.

### 068 — Phase 13B operational logging (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13B.1–13B.7
- Prompt intent: backend terminal still showed no Python logs; add operational
  logs at controller, service, repository, security and config boundaries, and
  record Phase 13B in PLAN.md.
- Suggestion: stdlib `career_assistant` logger to stderr with correlation ids;
  HTTP middleware; application/persistence/worker/provider events; redacting
  filter; never DTO or document dumps.
- Outcome: accepted.
- Reason: uvicorn access lines were not enough to see intake or analysis; the
  process had no application loggers. Operators need events, not payloads.
- Rejected alternatives: adding a logging framework; SQLAlchemy `echo`;
  serialising request/response bodies; logging from domain.
- Human validation: focused logging tests 6 passed; hermetic pytest 272 passed,
  3 skipped; coverage 80.79%; ruff on logging modules and mypy on logconfig/HTTP
  green.

### 067 — Split host run so API and web logs are independent

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: none (human request)
- Prompt intent: `make run` should show backend logs, or open two terminals for
  API and web independently.
- Suggestion: background uvicorn and keep Vite in the foreground was the old
  shape; replace it with `make run-api` / `make run-web`, and have `make run` on
  macOS open two Terminal windows.
- Outcome: accepted.
- Reason: one process group hid uvicorn behind Vite, so uploads and jobs had no
  visible API log stream.
- Rejected alternatives: prefixing interleaved `[api]` / `[web]` lines in one
  terminal (still mixed); swapping which process is backgrounded (then the web
  log disappears instead).
- Human validation: `make help` lists the new targets; `make -n run-api` and
  `make -n run-web` print uvicorn and bun respectively.

### 066 — Frontend role hard-delete controls

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: none (human request after 13A.8)
- Prompt intent: add delete buttons for roles and wire them on the frontend.
- Suggestion: `deleteRole` client against existing `DELETE /api/roles/{id}`;
  confirm-then-delete on the workspace table/cards and role header, matching CV
  and cover-letter delete; invalidate roles/ranking and return to the workspace
  after a header delete.
- Outcome: accepted.
- Reason: the API already hard-deleted a role; the UI only exposed CV and
  supporting-letter delete.
- Rejected alternatives: clicking either duplicate Delete in tests (table plus
  CSS-hidden cards both stay in the accessibility tree without Tailwind);
  passing `onDelete={undefined}` under `exactOptionalPropertyTypes`.
- Human validation: focused vitest 24 passed; gallery smoke 1 passed;
  `tsc --noEmit` and eslint on the changed files green. Browser: gallery
  table Delete asked `Delete Senior Data Analyst? Its analysis, drafts and
  mappings will be removed.` and cancelled; live workspace had no roles so
  the wired delete path was not exercised against PostgreSQL in the browser.

### 065 — Phase 13A.9 production wiring matrix and stale README (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.9
- Prompt intent: continue remaining Phase 13A items.
- Suggestion: fail tests on stale README claims and missing route rows; add
  `docs/production-wiring.md`; update API contract, threat model, ADRs 001/007.
- Outcome: accepted.
- Reason: README still said Phase 10 and fixture UI; nothing listed which SQL
  adapter each production route actually uses.
- Rejected alternatives: walking `app.routes` (included routers are opaque mounts,
  so an empty matrix would pass); requiring the `docs/` prefix inside files that
  already live under `docs/`.
- Human validation: focused docs tests red then green; `make test` 255 passed,
  coverage 80.62%; frontend 113 passed; `make test-integration` 48 passed;
  `make lint` green after ruff format.

### 064 — Phase 13A.8 frontend async and failure states (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.8
- Prompt intent: continue 13A with regular TDD commits.
- Suggestion: explicit role-header states; tab-scoped fetches; retryable letter,
  compare, role-list, clipboard and export failures instead of empty success.
- Outcome: accepted.
- Reason: analysing/failed/404 kept a skeleton and fired child queries; failed
  generated/supporting letter and CV list queries looked empty; copy and export
  swallowed errors.
- Rejected alternatives: leaving child queries enabled and only hiding tabs
  (they still 409 in the background); treating a failed CV query as inert Add
  your CV first.
- Human validation: each slice had a failing test then a green; `make test` 252
  passed, coverage 80.62%; frontend 113 passed; `make test-integration` 48
  passed; `make lint` green after moving `deriveRolesPanelState`.

### 063 — Phase 13A.7 ranking, compare and versioned export (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.7
- Prompt intent: continue work after 13A.6 in the same TDD style with regular commits.
- Suggestion: competition ranks for equal scores; compare differentiator from a real
  status gap; export the selected cover-letter/bullet version with API and component
  regressions.
- Outcome: accepted.
- Reason: GET /ranking numbered ties 1 and 2; GET /compare returned the first shared
  requirement alphabetically even when statuses matched; export always dumped latest
  or every bullet version.
- Rejected alternatives: dense ranking 1,1,2 (PLAN asked for competition ranking);
  concatenating every bullet draft when version is omitted (the same latest-version
  rule as cover letters).
- Human validation: each slice had a failing test then a green; `make test` 252
  passed, coverage 80.62%; frontend 101 passed; `make test-integration` 48 passed;
  `make lint` green after the mypy rename.

### 062 — Phase 13A.6 grounded generation on HTTP and SQL (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.6
- Prompt intent: continue the next work in the same TDD style with regular commits.
- Suggestion: route bullets, interview packs and cover letters through `generate_draft`;
  persist the real groundedness verdict on SQL; honour Letter-tab tone and gap line;
  refuse a bullet with no cited claim.
- Outcome: accepted.
- Reason: cover letters and interview packs still returned domain templates without a
  completion call, SQL drafts were stored as PASS regardless of the validator, and an
  uncited bullet persisted an instruction as a grounded draft.
- Rejected alternatives: removing the Letter-tab controls until they were real (PLAN
  allowed that; implementing the validated path kept the shipped UI honest);
  introducing a mapping_claims table to restore justifying claim ids (span overlap
  from existing rows was enough).
- Human validation: each slice had a failing test then a green; `make test` 246 passed,
  coverage 80.14%; `make test-integration` 48 passed; `make lint` green.

### 061 — Phase 13A.5 workspace retrieval and span resolution (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.5
- Prompt intent: continue the next phase in the same TDD style with regular commits.
- Suggestion: one workspace-scoped span resolver for CV, supporting cover letters and
  role JDs; feed those kinds into Ask retrieval; keep cover letters out of claims,
  mappings and scores; prove it on hermetic and PostgreSQL HTTP tests.
- Outcome: accepted.
- Reason: GET /api/spans and Ask's retrieved pool were active-CV only, so cover-letter
  and JD citations 404'd and open questions could not cite them even though domain
  selection rules already existed.
- Rejected alternatives: widening CvStore.get_span to every document kind (lied about
  the store); putting retrieval assembly in the HTTP route (routes must not hold that
  policy).
- Human validation: cover-letter and JD GET tests failed 404 then passed; Ask retrieval
  tests failed on missing citation ids then passed; make test 242 passed, coverage
  80.12%; make test-integration 46 passed; make lint green.

### 060 — Phase 13A.4 provider selection drives actual work (TDD)

- Date: 2026-09-21
- Tool / model: Cursor Grok 4.6, agent session
- Plan task: 13A.4
- Prompt intent: implement 13A.4 in TDD style with regular commits.
- Suggestion: resolve workspace completion choice through Phase 2 factories for Ask,
  extraction and bullet phrasing; re-check hosted egress on every `complete()`;
  persist accounting without content; stop hard-coding hermetic draft provenance.
- Outcome: accepted, with the changes below.
- Reason: Ask still constructed `HermeticCompletionAdapter` regardless of the
  persisted choice, so selecting OpenAI never called it. Construction-only egress
  would still network if the gate closed after the adapter existed.
- Rejected alternatives: putting `http_transport` on `create_app()` before the first
  red (would have failed on TypeError instead of `provider == hermetic`); using
  `Model*Extractor` for hermetic analysis (SQL fit scores dropped to 0); reading
  env `COMPLETION_PROVIDER` in hermetic `create_app()` (API tests reached OpenAI).
- Human validation: each slice had a failing test then a green; `make test` 236
  passed, coverage 80.61%; `make test-integration` 42 passed; `make lint` green.

### 059 — Phase 13A.3 PostgreSQL analysis worker (TDD)

- Date: 2026-09-21
- Tool / model: Composer, agent session
- Plan task: 13A.3
- Prompt intent: continue 13A.3 with TDD; commit red then green.
- Suggestion: stop analysing in the HTTP request; persist JD + queued job; run a
  bounded SQL worker from FastAPI lifespan; CV replace/delete enqueue or fail in
  the same transaction; startup recovery for queued and stale-running jobs.
- Outcome: accepted.
- Reason: production `SqlRoleStore.create_role` still extracted hermetically and
  published `ready`/`succeeded` before returning 202, so evaluation would measure
  process-local behaviour rather than the shipped job path.
- Rejected alternatives: Celery/RQ (PLAN says in-process); using in-memory
  `AnalysisService` dicts as the production queue (they do not survive restart).
- Human validation: first HTTP test failed on `ready` vs `analysing`; worker suite
  then 7 green; `make test` 230 passed, coverage 80.04%; `make test-integration`
  40 passed; `make lint` green.

### 058 — Phase 13A.2 SQL chat and provider settings (TDD)

- Date: 2026-09-21
- Tool / model: Composer, agent session
- Plan task: 13A.2
- Prompt intent: continue Phase 13A; keep the product a local personal tool and
  document a lighter multi-user security posture.
- Suggestion: SQL ConversationStore and ProviderChoiceStore adapters; wire through
  `build_sql_stores` / `create_production_app`; UUID answer ids; `answers.kind` and
  provider model-tag migration; HTTP process-restart tests.
- Outcome: accepted.
- Reason: production HTTP still used process memory for chat and provider choice
  even though SQL tables existed. Hermetic `create_app()` stays in-memory.
- Rejected alternatives: installing extra security for a multi-user deployment;
  requiring nonempty citations on FIT answers (FIT has none by design).
- Human validation: survival suite 4 green against PostgreSQL; hermetic ask /
  message / provider / wiring tests green; `make test` 230 passed, coverage 80.28%;
  frontend 100 passed; `make test-integration` 33 passed; `make lint` green.

### 057 — Phase 13A.1 quality baseline (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13A.1
- Prompt intent: restore `make lint` after the observed Ruff format failure on
  `application/ports/persistence.py`, then run the exact quality targets.
- Suggestion: collapse `list_cover_letters` to one line; keep Alembic migrations
  outside Ruff's `backend/src backend/tests` target; record FastAPI/Starlette
  TestClient deprecation warnings as a Phase 15 risk instead of silencing them.
- Outcome: accepted.
- Reason: the lint miss was formatting only; adding `httpx2` or `filterwarnings`
  would weaken the gate. Installed versions observed: FastAPI 0.141.1, Starlette
  1.6.0, httpx 0.28.1, anyio 4.15.1.
- Rejected alternatives: installing `httpx2`; widening `fastapi>=0.141,<0.142`;
  adding pytest `filterwarnings`.
- Human validation: `make lint`, `make typecheck`, `make test` (230 passed, 3
  skipped, 29 deselected; frontend 100 passed), `make test-integration` (29
  passed). Two third-party warnings remain and are recorded in PLAN Phase 15.

### 056 — Post-Phase-13 logic and production-wiring audit

- Date: 2026-09-18
- Tool / model: Codex
- Plan task: audit checkpoint before Phase 14
- Prompt intent: verify all logic through Phase 13, identify defects and record the
  required corrections before evaluation.
- Suggestion: add mandatory Phase 13A remediation for SQL-backed chat/provider
  settings, real queued production analysis and CV-replacement jobs, runtime provider
  use, supporting-letter retrieval and general span resolution, grounded generation,
  correct ties/differentiators/version export, frontend failure states and honest
  documentation.
- Outcome: pending human review; no application behaviour changed in this audit.
- Reason: hermetic, component and direct repository tests pass, but production routes
  still instantiate process-memory chat/provider state, run synchronous hermetic
  analysis, omit supporting documents from retrieval, and bypass the existing
  provider and grounded-generation application paths. Evaluation before correcting
  those paths would report results for a different system than the shipped app.
- Human validation: `make test` observed 230 passed, 3 skipped and 29 deselected;
  frontend Vitest observed 100 passed when run with local socket access;
  `make test-integration` observed 29 passed against local PostgreSQL; `make
  typecheck` passed. Exact `make lint` remains red because Ruff would reformat one
  method declaration in `application/ports/persistence.py`.

### 055 — Phase 13.9–13.10 a11y live regions and escaped text (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.9, 13.10
- Prompt intent: close Phase 13 exit gate after /dev/states.
- Suggestion: polite aria-live for parsing, analysing, and streaming chat; regression
  tests that XSS-looking excerpts never become DOM nodes.
- Outcome: accepted.
- Reason: progress must be announced; React text children already escape — tests
  lock that property.
- Rejected alternatives: aria-live=assertive for streaming (too noisy).
- Human validation: a11y 3 green; escaped-text 2 green; full frontend vitest 100;
  tsc/lint.

### 054 — Phase 13.8 /dev/states gallery fill (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.8
- Prompt intent: continue Phase 13 after Compare.
- Suggestion: add Gaps/Bullet/Prepare/Letter/Ranking/Compare/tabs/cover-letter
  states to /dev/states; export DEV_STATE_SECTION_TITLES; gallery smoke test.
- Outcome: accepted.
- Reason: exit gate requires every gallery state to have a test; component unit
  tests already cover behaviours, gallery test locks the section list.
- Rejected alternatives: omitting gallery coverage for Phase 13 surfaces.
- Human validation: gallery test 1 green; full frontend vitest; tsc/lint.

### 053 — Phase 13.7 Compare panel (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.7
- Prompt intent: continue Phase 13 after Ranking.
- Suggestion: ComparePanel with two role selectors; GET /compare; shared/unique/
  differentiator; Gaps shortcuts into role detail.
- Outcome: accepted.
- Reason: comparison is server-derived from stored mappings.
- Rejected alternatives: client-side diff of requirement tables.
- Human validation: ComparePanel tests 2 green; full frontend vitest; tsc/lint.

### 052 — Phase 13.6 workspace ranking (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.6
- Prompt intent: continue Phase 13 after Letter.
- Suggestion: RankingPanel on workspace from GET /ranking; show rank, tied label,
  because texts, link into role detail.
- Outcome: accepted.
- Reason: ranking is derived from stored scores, not a client re-sort of the table.
- Rejected alternatives: replacing RolesPanel sort with ranking (table stays for
  column sort; ranking is the named-reason view).
- Human validation: RankingPanel tests 2 green; full frontend vitest; tsc/lint.

### 051 — Phase 13.5 Letter tab (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.5
- Prompt intent: continue Phase 13 after Prepare.
- Suggestion: LetterPanel with tone/gap controls, generate, version history,
  export, refusal → Open Gaps, supporting uploads listed separately.
- Outcome: accepted.
- Reason: 409 `insufficient_matched_requirements` is a next step, not an error toast.
- Rejected alternatives: merging uploaded letters into generated version history.
- Human validation: LetterPanel tests 3 green; full frontend vitest; tsc/lint.

### 050 — Phase 13.4 Prepare / interview pack (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.4
- Prompt intent: continue Phase 13 after bullet drafts.
- Suggestion: PreparePanel with four sections from GET /interview-pack; evidence
  opens EvidencePanel; Export Markdown via GET /export/interview-pack.md.
- Outcome: accepted.
- Reason: matches features.md Prepare flow; export is a download, not a new store.
- Rejected alternatives: inventing probe questions in the client.
- Human validation: PreparePanel tests 2 green; full frontend vitest; tsc/lint.

### 049 — Phase 13.3 bullet draft panel (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.3
- Prompt intent: continue Phase 13 after Gaps panel.
- Suggestion: BulletDraftPanel + POST /bullets; citation chips, copy, provenance,
  visible template-fallback banner; Gaps "Draft a bullet" triggers the mutation.
- Outcome: accepted.
- Reason: matches features.md grounding labelling; hermetic path uses fallback
  template which the UI must show honestly.
- Rejected alternatives: writing drafts back into the CV (explicitly out of scope).
- Human validation: BulletDraftPanel tests 2 green; full frontend vitest; tsc/lint.

### 048 — Phase 13.2 Gaps panel (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.2
- Prompt intent: continue Phase 13 after role tabs.
- Suggestion: GapsPanel presentational list from GET /gap-plan; Draft a bullet
  control when canDraftBullet; adjacent evidence opens shared EvidencePanel.
- Outcome: accepted.
- Reason: gap plan is deterministic server-side; UI only presents ordered items.
- Rejected alternatives: inventing gap order in the client (API already sorts by
  scoreDelta).
- Human validation: GapsPanel tests 2 green; full frontend vitest; tsc/lint.

### 047 — Phase 13.1 role detail tabs (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 13.1
- Prompt intent: continue Phase 13 after SQL supporting store.
- Suggestion: Fit/Gaps/Prepare/Letter tabs with `?tab=` deep-link search param;
  Gaps/Prepare/Letter placeholders until later slices.
- Outcome: accepted.
- Reason: matches features.md navigation; Fit keeps existing breakdown + table.
- Rejected alternatives: path segments per tab (search param is enough and keeps
  one route file).
- Human validation: RoleDetailTabs tests 3 green; full frontend vitest; tsc/lint.

### 046 — Phase 13 carry-forward: SQL supporting cover letters (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 12 exit-gate carry-forward into Phase 13
- Prompt intent: continue next phases after cover letters were not durable.
- Suggestion: SqlSupportingDocumentStore + wire into create_production_app /
  build_sql_stores.
- Outcome: accepted.
- Reason: Phase 12 exit gate already deferred SQL supporting store to Phase 13;
  uploads were process-memory only.
- Rejected alternatives: leaving cover letters in-memory until 13.5 Letter UI.
- Human validation: production wiring unit test; integration SQL store test;
  supporting API tests; ruff/mypy clean on touched modules.

### 045 — Phase 12 exit gate + Ask incomplete-analysis 409 (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 12 exit gate (plus defect found during it)
- Prompt intent: continue TDD with regular commits through Phase 12.
- Suggestion: run host API + Start proxy against sample fixtures; exercise UI;
  map Ask `RoleOperationRejected` to AppError 409.
- Outcome: accepted.
- Reason: exit gate requires a real backend path; 500 on incomplete analysis was
  a visible failure path bug.
- Rejected alternatives: declaring the gate met from unit tests alone; leaving
  Ask incomplete analysis as internal_error.
- Human validation: proxy walkthrough + browser role detail; SSE pytest green;
  frontend vitest 76 previously green for 12.12.

### 044 — Phase 12.12 wired screen component states (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.12
- Prompt intent: continue TDD with regular commits through Phase 12.
- Suggestion: prop-driven Vitest coverage for every wired presentational screen
  state (loading/empty/error/ready and analysis-status variants).
- Outcome: accepted.
- Reason: PLAN 12.12 requires component tests driven by props before the exit gate.
- Rejected alternatives: only container integration tests (would couple UI copy to
  network timing).
- Human validation: focused component tests green; full frontend vitest 76;
  typecheck/lint green.

### 043 — Phase 12.11 API error code → actionable UI (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.11
- Prompt intent: continue TDD with regular commits.
- Suggestion: describeApiError catalogue from api-contract; wire containers to use it.
- Outcome: accepted.
- Reason: unknown codes must fail visibly; known codes need a next step.
- Rejected alternatives: switching on message text.
- Human validation: errors tests green; full vitest 60; typecheck/lint.

### 042 — Phase 12.10 provider settings wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.10
- Prompt intent: continue TDD with regular commits.
- Suggestion: re-index warning dialog; keep hosted confirm; show unavailableReason;
  setProviderChoice acknowledgedEgress + optional reindex response.
- Outcome: accepted.
- Reason: matches api-contract egress ack and index-change invalidation warning.
- Rejected alternatives: silent index changes without user confirmation.
- Human validation: ProviderSettings tests green; full vitest 56; typecheck/lint.

### 041 — Phase 12.9 Ask SSE wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.9
- Prompt intent: continue TDD and commit regularly after 12.8.
- Suggestion: postMessageStream + ChatContainer real SSE; delete history; retry
  with stable clientRequestId; provider stamp includes leftMachine.
- Outcome: accepted.
- Reason: replaces fake token interval with the documented stream transport.
- Rejected alternatives: EventSource (POST body required).
- Human validation: stream tests green; full vitest 53; typecheck/lint green.

### 040 — Phase 12.8 role detail span resolution (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.8
- Prompt intent: continue Phase 12 after job polling.
- Suggestion: getSpan client; EvidencePanel loading/error resolve states;
  RoleDetailContainer fetches span when panel opens.
- Outcome: accepted.
- Reason: api-contract requires unresolved citations to fail visibly.
- Rejected alternatives: rendering inline requirement.evidence without a span GET.
- Human validation: spans + EvidencePanel tests green; full vitest 49; typecheck/lint.

### 039 — Phase 12.7 analysis job polling (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.7
- Prompt intent: continue Phase 12 after workspace wiring.
- Suggestion: getJob/reanalyseRole; RolesPanel Analysing/Failed/Retry; react-query
  refetchInterval on roles and jobs.
- Outcome: accepted.
- Reason: matches api-contract polling model without inventing a job list endpoint.
- Rejected alternatives: polling only the roles list (loses failure reason from job).
- Human validation: jobs + RolesPanel tests green; full frontend vitest 45;
  typecheck/lint green.

### 038 — Phase 12.6 workspace upload wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.6
- Prompt intent: continue Phase 12 in TDD after additive types.
- Suggestion: multipart `uploadCv`/`uploadCoverLetter`; backend multipart routes;
  confirmations; cover-letter “not score evidence” card; ApiError messages in UI.
- Outcome: accepted; added `python-multipart` dependency.
- Reason: api-contract already required multipart; paste-only could not admit PDF/DOCX.
- Rejected alternatives: reading PDF client-side into paste JSON; deferring multipart
  to a later phase.
- Human validation: upload + component tests green; CV/supporting API tests green;
  frontend typecheck/lint green; locks regenerated.

### 037 — Phase 12.5 additive frontend types (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.5
- Prompt intent: continue Phase 12 in TDD style after 12.3–12.4.
- Suggestion: additive types from api-contract; Role.status/updatedAt; extend
  OpenAPI↔TS contract suite.
- Outcome: accepted.
- Reason: screens for gaps/prepare/letter need typed contracts before wiring.
- Rejected alternatives: optional Role.status (API always returns it; required
  keeps the list UI honest for 12.7 polling).
- Human validation: additive + client tests green; full frontend vitest 33 green;
  OpenAPI contract pytest green; typecheck/lint green.

### 036 — Phase 12.3–12.4 real HTTP client and fixture move (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.3, 12.4
- Prompt intent: continue Phase 12 in TDD style.
- Suggestion: zod schemas + `request()`/`ApiError` client; move fixtures to
  `__fixtures__/`; ban fixture imports from components.
- Outcome: accepted.
- Reason: screens already call `@/api/client`; swapping the implementation keeps
  signatures and removes mock data from the production path.
- Rejected alternatives: keeping fixtures co-located with `client.ts`; CORS
  browser client (proxy already proven).
- Human validation: client tests 6 green; fixtures + eslint-guard tests green;
  typecheck and lint green.

### 035 — Phase 12.1–12.2 API proxy spike and catch-all (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 12.1, 12.2
- Prompt intent: continue to Phase 12; spike SSE/upload through Start, then proxy.
- Suggestion: `proxyToUpstream` with Node http spike tests; `src/routes/api.$.ts`
  catch-all; record pass on ADR 006 / PLAN.
- Outcome: accepted; spike passed — no CORS fallback.
- Reason: ADR 006 risk was buffering in the Node proxy; proofs close that risk
  before the real client depends on it.
- Human validation: api-proxy tests (6) green; full frontend vitest (12) green;
  typecheck/lint green.

### 034 — Phase 11.12–11.13 supporting docs and message history (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.12, 11.13 (Phase 11 exit)
- Prompt intent: complete Phase 11 with TDD.
- Suggestion: supporting cover-letter CRUD + safe download; GET/DELETE messages;
  SSE replay messageId; error-table intake/provider coverage tests.
- Outcome: accepted; Phase 11 checked complete in PLAN.md.
- Reason: closes the remaining API contract surface before frontend integration.
- Rejected alternatives: SQL supporting/ask stores in this slice (hermetic first,
  matching prior Phase 11 pattern).
- Human validation: supporting + message history API tests green; full API suite
  green; make lint green.

### 033 — Phase 11.11 OpenAPI and TypeScript type parity (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.11
- Prompt intent: continue Phase 11 after provenance.
- Suggestion: contract test mapping shared TS interfaces to OpenAPI components;
  require Evidence.spanId on both sides; update fixtures/client for the new fields.
- Outcome: accepted; PLAN 12.5 note adjusted so spanId is not re-added later.
- Reason: citations cannot open stored spans without spanId; contract file is the
  authority when halves disagree.
- Human validation: contract tests green; frontend typecheck/lint green; make lint
  green.

### 032 — Phase 11.10 answer and draft provenance (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.10
- Prompt intent: continue Phase 11 after SSE stream.
- Suggestion: API regression for provider/model/leftMachine on SSE meta, JSON
  ChatMessage, and draft/interview-pack provenance; extend AskEvent + SSE framing;
  add JSON Accept path sharing AskService.ask.
- Outcome: accepted; api-contract meta event updated with leftMachine.
- Reason: AGENTS requires every answer/artefact to record provider, model tag and
  egress; drafts already had DraftProvenanceWire.
- Human validation: provenance API tests green; API + ask use-case suites green;
  `make lint` green.

### 031 — Phase 11.9 SSE answer stream (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.9
- Prompt intent: continue Phase 11 after production SQL wiring.
- Suggestion: API test for documented SSE sequence; `format_ask_sse` +
  `POST /api/messages` over AskService.stream; InMemoryConversationStore.
- Outcome: accepted; JSON Accept / GET / DELETE left for 11.13.
- Reason: Phase 9 already owns stream/non-stream parity in the use case; 11.9 is
  the HTTP transport framing only.
- Human validation: message SSE API test green; full API suite green; `make lint`
  green.

### 030 — Phase 11.8 production SQL app wiring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (complete — production entrypoint)
- Prompt intent: continue Phase 11; wire SQL as the uvicorn/Docker default.
- Suggestion: `build_sql_stores` + `create_production_app`; keep `create_app()`
  hermetic for API tests; unit-test module `app` store types.
- Outcome: accepted; 11.8 checked off in PLAN.md.
- Reason: AGENTS forbids process-memory as a production persistence path;
  Docker/Make run `career_assistant.main:app`.
- Rejected alternatives: changing `create_app()` default to SQL (would force
  every hermetic API test onto Postgres).
- Human validation: production wiring unit tests green; API suite green;
  `make lint` green.

### 029 — Phase 11.8 durable drafts on SqlRoleStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — durable generated drafts)
- Prompt intent: continue Phase 11 with TDD.
- Suggestion: persist cover-letter/bullets through DraftRepository; prove survival
  across a fresh SqlRoleStore; reconstruct wires in analysis routes.
- Outcome: accepted; production SQL create_app default still deferred.
- Reason: generated artefacts must outlive the process like CV/roles.
- Human validation: durable-draft integration green; full SqlRoleStore + draft
  persistence suites green; hermetic API green; mypy/ruff clean.

### 028 — Phase 11.8 SqlRoleStore delete and reanalyse (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL role lifecycle)
- Prompt intent: continue Phase 11 with TDD.
- Suggestion: RoleRepository.delete + bump_analysis_version; SqlRoleStore
  delete/reanalyse; version-scoped list_mappings; HTTP integration coverage.
- Outcome: accepted; durable drafts and production SQL default still deferred.
- Reason: finish role lifecycle persistence before draft durability.
- Human validation: 4 SqlRoleStore integration tests green; hermetic API and
  analysis persistence green; ruff/mypy clean.

### 027 — Phase 11.8 SqlRoleStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL role/analysis persistence)
- Prompt intent: continue Phase 11 SQL slice after SqlCvStore.
- Suggestion: SqlRoleStore create/list/get/require_analysis publishing hermetic
  analysis; roles.company migration; create_app(role_store=…) injection.
- Outcome: accepted; delete/reanalyse/durable drafts deferred.
- Reason: prove role analysis rows round-trip through PostgreSQL before widening
  the store surface.
- Human validation: SqlRoleStore integration (2) green; related analysis/draft
  integration green; hermetic `tests/api/` green; ruff/mypy clean.

### 026 — Phase 11.8 SqlCvStore (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — SQL CV persistence)
- Prompt intent: continue Phase 11; first SQL slice for API stores.
- Suggestion: SqlCvStore implementing CvStore over SqlUnitOfWork; integration tests
  for port + HTTP CV/span routes with injected store.
- Outcome: accepted; create_app still defaults to InMemoryCvStore for hermetic
  API tests.
- Reason: production CV data must hit PostgreSQL without breaking offline contract
  tests; injection keeps both paths.
- Human validation: integration SqlCvStore + CV HTTP SQL tests green; hermetic
  `tests/api/` green; ruff/mypy clean.

### 025 — Phase 11.8 hermetic role lifecycle and draft list (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — lifecycle / drafts)
- Prompt intent: continue Phase 11 in the same PR.
- Suggestion: delete, reanalyse, cover-letter list, bullets/cover-letter export,
  analysis_incomplete coverage on the in-memory store.
- Outcome: accepted; SQL persistence still deferred.
- Reason: finish hermetic wire contracts before swapping stores for PostgreSQL.
- Human validation: lifecycle red→green; `pytest tests/api/ -q --no-cov` → 51
  passed; ruff and mypy clean on changed modules.

### 024 — Phase 11.8 hermetic analysis output routes (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial — analysis artefacts)
- Prompt intent: continue Phase 11 in the same PR; green the analysis/ranking reds.
- Suggestion: sync hermetic analyse on role create; routes for requirements,
  breakdown, gap-plan, interview-pack, bullets, cover-letter, export, ranking,
  compare using domain generation + scoring rubric.
- Outcome: accepted for hermetic API contracts; SQL persistence still deferred.
- Reason: artefact routes need a finished analysis; sync hermetic path keeps tests
  deterministic without a worker.
- Human validation: `pytest tests/api/test_role_analysis_routes.py
  tests/api/test_role_routes.py -q --no-cov` green (7 tests); ruff clean on changed
  files.

### 023 — Phase 11.8 partial CV/span/role/job routes (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.8 (partial)
- Prompt intent: continue on updated main with TDD after PR #22.
- Suggestion: CV paste lifecycle; span Evidence with spanId; roles requiring CV and
  returning queued jobs — hermetic in-memory stores first.
- Outcome: accepted as a contract slice; SQL persistence and remaining 11.8 artefacts
  deferred.
- Reason: prove workspace-scoped HTTP contracts before wiring the analysis worker.
- Human validation: focused API suites green; hermetic pytest (~84%), ruff, mypy.

### 022 — Phase 11.3 upload limit and 11.7 providers (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.3, 11.7
- Prompt intent: continue on updated main after PR #21; keep TDD.
- Suggestion: pure ASGI Content-Length gate; provider catalogue + choice routes with
  server-side egress acknowledgement; redaction assertion for API keys.
- Outcome: accepted; durable SQL provider_settings deferred.
- Reason: pre-buffer rejection is the contract requirement; hosted confirmation must
  not be UI-only.
- Human validation: API upload + provider suites green; hermetic pytest (~83%),
  ruff, mypy.

### 021 — Phase 11 API wire foundation (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 11.1, 11.2, 11.4, 11.5, 11.6
- Prompt intent: continue on updated main with TDD; start Phase 11 API contracts.
- Suggestion: shared camelCase `ApiModel`; workspace cookie middleware; correlation
  id middleware; safe error envelope; `/api/ready` with injectable probe (SQL probe
  kept under adapters/persistence).
- Outcome: accepted for the HTTP foundation; 11.3 upload limits and feature routes
  deferred to follow-up slices.
- Reason: every later route needs aliases, workspace identity, correlation ids and
  safe errors before CV/role handlers land.
- Human validation: focused API suites green; hermetic pytest (~83%), ruff, mypy;
  persistence boundary test green after moving SettingsReadiness into adapters.

### 020 — Phase 10.9 artefact persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 10.9
- Prompt intent: continue after Phase 10.1–10.8 merge; finish artefact store.
- Suggestion: red integration specs for save/versioning/reject-FAIL; migration for
  version + groundedness provenance; `DraftRepository` + `SqlDraftRepository` on UoW.
- Outcome: accepted.
- Reason: only PASS (or template-fallback that still passes validation) content may
  persist; regenerations must be immutable versions, not in-place updates.
- Human validation: draft persistence integration green; full `-m integration` green;
  hermetic pytest (~84%), ruff, mypy.

### 019 — Phase 10 grounded generation (TDD, 10.9 deferred)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 10.1–10.8
- Prompt intent: continue with TDD after Phase 9 persistence merged to main.
- Suggestion: groundedness validator; gap plan; generate_draft pipeline with
  counters; hermetic bullets; cover letter refuse; interview pack; markdown export
  — red commits before each green slice.
- Outcome: accepted for generation behaviour; 10.9 store deferred.
- Reason: ADR 007 requires fail-closed validation before any draft reaches a user;
  hermetic templates keep the feature model-free.
- Human validation: focused unit suites green; hermetic pytest (~84%), ruff, mypy.

### 018 — Phase 9 ask streaming and persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 9.7–9.9
- Prompt intent: continue next work with TDD after PR #17 merged to main.
- Suggestion: `AskService` with shared stream/non-stream path; in-memory red specs
  then green; conversation repo lookup/history/citations red integration then green.
- Outcome: accepted.
- Reason: exit gate needs stream parity, question-before-answer persistence, and
  idempotent clientRequestId without storing partial tokens.
- Human validation: unit ask use-case green; integration ask persistence green;
  full `-m integration` green; hermetic pytest (~84%), ruff, mypy.

### 017 — Phase 9 ask domain (TDD, partial)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 9.1–9.6, 9.10 (9.7–9.9 deferred)
- Prompt intent: continue with TDD-style development on the next phase.
- Suggestion: intent router; structured mapping answers + citation validation;
  open-question retrieval rules and untrusted prompt budgets — each as red then
  green commits.
- Outcome: accepted for the domain slice; streaming/persistence left open.
- Reason: structured intents must not use vector search; citations must resolve
  or become insufficient before any HTTP surface exists.
- Human validation: focused unit suites green; hermetic pytest (~84%), ruff, mypy.

### 016 — Phase 8 analysis jobs (TDD, red commits first)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 8.1–8.7
- Prompt intent: continue Phase 8 with team TDD — test commits before
  implementation.
- Suggestion: domain job lifecycle; `AnalysisService` orchestration with fakes;
  Alembic job/role columns; SQL role/job/analysis repos; transactional publish and
  fail discard; CV-replace reanalysis enqueue.
- Outcome: accepted.
- Reason: exit gate needs immediate enqueue, ready-on-success, failed-with-no-
  partials; Postgres is the system of record for jobs.
- Human validation: unit domain + pipeline green; integration persistence green
  (`-m integration`); hermetic pytest (~84%), ruff, mypy green.
- Process note: standing instruction — for future work, commit failing tests
  before implementation commits; assume concurrent teammates.

### 015 — Phase 7 mapping and scoring (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 7.1–7.6
- Prompt intent: continue with the next phase (mapping and scoring) under TDD.
- Suggestion: pure `domain/mapping.py` policy with reason codes; similarity as
  candidate hint only; `domain/scoring.py` + `application/scoring/rubric_loader`
  reading `config/scoring_rubric.toml`; property and counterfactual tests; fixture
  CV×JD exit-gate test with no model call.
- Outcome: accepted.
- Reason: exit gate requires a stable explained score and deltas without a model;
  the invariant keeps judgement in domain arithmetic, not the LLM.
- Human validation: nine focused mapping/scoring tests green; hermetic pytest
  (~84%), ruff, mypy green.

### 014 — Phase 6 evidence / claim extraction (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 6.1–6.5
- Prompt intent: continue with Phase 6 evidence extraction.
- Suggestion: domain Claim; pure date-derived recency/duration; rules CV extractor;
  span validation; cover-letter rejection; model-backed path intersecting hermetic
  claims JSON with rule spans.
- Outcome: accepted.
- Reason: exit gate requires fixture CVs with resolvable spans and dated-experience
  recency that is not assumed recent.
- Human validation: eight focused claim tests green; hermetic pytest, ruff, mypy.

### 013 — Phase 5 requirement extraction (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 5.1–5.7
- Prompt intent: continue with the next phase (requirement extraction).
- Suggestion: domain Requirement; rules extractor for bulleted JD sections; span
  validation; injection and vague fixtures; cover-letter rejection; model-backed path
  intersecting CompletionPort JSON with rule spans.
- Outcome: accepted.
- Reason: exit gate requires six fixture JDs with resolvable spans and no injection
  leakage; rules stay default so hermetic runs need no network.
- Human validation: eight focused extraction tests green; hermetic pytest (~81%),
  ruff, mypy green.

### 012 — Dedicated PostgreSQL application schema

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: follow-up to Phase 4 (persistence)
- Prompt intent: stop using the public schema; use a dedicated schema.
- Suggestion: `career_assistant` schema, MetaData.schema, search_path, forward
  migration moving tables out of public; keep `vector` in public.
- Outcome: accepted.
- Human validation: unit + integration tests green; `\dt career_assistant.*` shows
  21 tables; `make db-migrate` / `make db-check` green.

### 011 — Phase 4 PostgreSQL persistence (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 4.1–4.13
- Prompt intent: continue with the next incomplete PLAN work (Phase 4 persistence).
- Suggestion: red tests for DatabaseSettings and the adapter boundary; then SQLAlchemy
  models, Alembic baseline, repository unit-of-work, integration suite, and Make
  db-check/db-migrate targets.
- Outcome: accepted.
- Reason: exit gate requires migrations and scoped document/conversation round-trips
  on real PostgreSQL with no production SQLite/memory fallback.
- Human validation: hermetic pytest (~82% coverage), ruff, mypy green; eight
  integration tests green against local pgvector; `make db-check` and `make db-migrate`
  observed green.

### 010 — PostgreSQL persistence design review

- Date: 2026-09-18
- Tool / model: Codex
- Plan task: Unplanned design review before Phase 4
- Prompt intent: inspect the remaining plan for gaps and make PostgreSQL the explicit
  source of truth for uploaded CVs and cover letters, questions and answers, with a
  local database for Make and a container database for Compose/deployment.
- Suggestion: expand Phase 4 onward with bounded original-file storage, conversation
  and citation tables, transaction/idempotency rules, local/test database separation,
  container persistence and backup/restore; amend the controlling ADR, API contract,
  feature specification and threat model.
- Outcome: changed
- Reason: uploaded cover letters are stored and queryable as requested, but are
  deliberately excluded from candidate claims and fit scoring because self-authored
  prose is not independent evidence. Generated letters remain provenance-bearing
  drafts linked to cited CV spans.
- Human validation: pending review of the documentation diff. Automated consistency
  checks and existing quality gates are recorded in the task report.

### 009 — Phase 3 document intake and spans (TDD)

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 3.1–3.7
- Prompt intent: continue Phase 3 following TDD where possible.
- Suggestion: commit failing intake tests first; implement admit → extract → span
  pipeline for plain text, PDF and DOCX; span resolution and normalisation.
- Outcome: accepted.
- Reason: exit gate requires fixture CV → spans round-trip and safe rejection of
  bad uploads; tests encode that before parsers land.
- Human validation: intake tests red then green; full hermetic pytest, ruff, mypy
  observed green.

### 008 — Remove Lovable branding and telemetry from the frontend

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: Phase 2 PR follow-up (branding)
- Prompt intent: strip Lovable mentions, logo, favicon and trackers; brand as CIA.
- Suggestion: delete lovable error-reporting hook, replace favicon with an original
  CIA monogram SVG, update shell/docs titles, keep `@lovable.dev/vite-tanstack-config`
  only as the existing Vite/Start build helper.
- Outcome: accepted.
- Reason: product branding should not ship editor telemetry or vendor marketing.
- Human validation: `bun run test` (6 passed), `bun run lint` (warnings only),
  `bun run typecheck` green.

### 007 — Phase 2 model providers

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 2.1–2.12
- Prompt intent: continue with the next phase (model providers) through completion.
- Suggestion: ports + capability descriptors; hermetic/Ollama/OpenAI/Anthropic
  adapters behind an egress gate; shared contract suite on recorded HTTP fixtures;
  resilience, accounting, key redaction, explicit fallback.
- Outcome: accepted.
- Reason: matches ADR 003/005; keeps default runs hermetic; no vendor SDK lock-in.
- Human validation: `pytest` hermetic suite green (coverage ≥80%), ruff and mypy
  clean on the package.

### 006 — Phase 1 frontend quality gates

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 1.3, 1.4, 1.8, 1.9
- Prompt intent: continue with the next phase through completion and PR.
- Suggestion: frontend hygiene, Vitest/Testing Library, ESLint design/fixture
  guards with red-green proof, Makefile typecheck/test wiring, GitHub Actions CI.
- Outcome: accepted.
- Reason: Phase 1 exit gate requires lint, typecheck and hermetic tests on both
  halves; Lovable as delivered failed Prettier-only lint until formatted.
- Human validation: `bunx vitest run` (5 passed, including red-then-green ESLint
  guards), `make typecheck`, `make lint`, and `make test` all observed green.

### 005 — Phase 0 repository baseline

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: 0.1–0.6 (Phase 0 exit gate)
- Prompt intent: complete Phase 0 with TDD-style commits, then open a PR.
- Suggestion: failing hermetic baseline tests first; then AGENTS product scope,
  threat-model draft/personal-data coverage, synthetic fixtures, evaluation stub,
  scoring rubric config, ADR date confirmation, PLAN/journal updates.
- Outcome: accepted.
- Reason: Phase 0 requires decisions and fixtures before application behaviour;
  pinning those with tests keeps the exit gate enforceable.
- Human validation: focused `pytest tests/unit/test_phase0_baseline.py --no-cov`
  observed red then green; full hermetic `pytest` passed with 100% package coverage
  on the existing skeleton.

### 004 — Backend Python bumped to 3.14

- Date: 2026-09-18
- Tool / model: Composer, agent session
- Plan task: unplanned — unblock `make setup` after host Python mismatch
- Prompt intent: upgrade the project to the most recent Python on the system
  (3.14.4) instead of installing 3.13.
- Suggestion: widen `requires-python` to include 3.14; bump Docker, ruff, mypy,
  README/PLAN/Makefile; add ADR 008; recreate the venv and re-run setup.
- Outcome: accepted.
- Reason: developer chose to track system Python 3.14 rather than maintain a
  separate 3.13 toolchain. The previous upper bound `<3.14` was the direct cause
  of the setup failure.
- Human validation: `make setup` succeeded on Python 3.14.4;
  `backend/.venv/bin/python --version` reports 3.14.4; `import career_assistant`
  succeeds. Regenerated stale `frontend/bun.lock` so the frozen install step
  could pass.

### 003 — Rejected: unpinned dependency ranges and an Ollama service in the default stack

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1, 16.1
- Prompt intent: as above.
- Suggestion: (a) install from `pyproject.toml` ranges in the image rather than a lock;
  (b) include the `ollama` service in the default Compose stack, as the sibling does.
- Outcome: rejected.
- Reason: (a) an image that resolves versions at build time is not the image that was
  tested; the lock is the point. (b) The default providers are hermetic, so a default
  `up` that pulls a multi-gigabyte Ollama image contradicts the product's own claim
  that a reviewer can clone and run with no model download. Ollama moved behind a
  Compose profile and is started only when asked for.
- Human validation: `docker compose --profile ollama` documented in `compose.yaml`,
  the README quick start and `make help`.

### 002 — Single dependency lock split into runtime and dev

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1
- Prompt intent: match the sibling repository's dependency handling.
- Suggestion: one `requirements.lock` containing runtime and development pins, as the
  sibling does, installed by both `make setup` and the container image.
- Outcome: changed.
- Reason: that ships pytest, bandit, mypy and pip-audit — 57 pins — into the runtime
  image, where they are attack surface that runs as the API user and never gets used.
  Split into `requirements.lock` (15 runtime pins, what the image installs) and
  `requirements-dev.lock` (what `make setup` installs). `make security` audits both.
- Human validation: both locks regenerated with `uv pip compile` against Python
  3.13.15 and diffed; the backend image copies only the runtime lock.

### 001 — Run and deploy surface brought forward

- Date: 2026-09-17
- Tool / model: Claude (Opus 5), agent session
- Plan task: 1.1, 1.2, 1.5, 1.6, 1.7, part of 16.1 — taken out of order at the
  developer's direction, before Phase 0 is closed.
- Prompt intent: build the Docker and Make run/deploy setup, patterned on the sibling
  repository `task-code-repository-rag`.
- Suggestion: mirror the sibling's `Makefile`, `compose.yaml` and Dockerfiles, and add
  the minimum backend needed for the stack to actually start.
- Outcome: accepted, with three changes recorded below.
- Reason: a Compose file that builds an image with nothing to run is a prop. The
  smallest honest version of "it runs" is a liveness endpoint, so Phase 1's first
  red-green cycle came with it.
- Human validation: pytest 4 passed with 100% coverage; ruff check and format clean;
  mypy strict clean on 10 source files; `make help` and `make -n config` parse;
  `compose.yaml` parses and every variable it interpolates exists in
  `config/app.env.example`. Docker was not available on this machine, so **no image
  was built and the stack was never started** — 16.1 stays open.
