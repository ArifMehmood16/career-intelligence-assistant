# Backlog

Every open item for this repository, in one list, in the order to work it.
`PLAN.md` says what each task requires and when it is done; this file says what is
still open and what comes next. Items point at their `PLAN.md` id rather than
restating acceptance criteria.

Last reviewed 2026-09-24 on `fix/phase-13d-evidence-gates`. Pull request #37
is merged. The extraction correctives on this branch are implemented and
unmeasured; they do not close 13D.6g.

**How to use it.** Work top to bottom. Take the first open item in [Now](#now--close-phase-13d)
unless the human names another. When a `PLAN.md` box is ticked, tick the matching line
here in the same commit. Open work found during a task is added here — never left as a
`TODO` in code. Decisions marked **Decision** are the human's; agents do not take them.

## Where things stand

| Phase | State |
|---|---|
| 0–13, 13A, 13B | Done |
| 13C — model-first extraction | 13C.1–13C.10 implemented. Its exit verification is carried into 13D.6g |
| 13D — assessment accuracy | 13D.1–13D.5 and 13D.6a–13D.6f done. **13D.6g open** — the phase gate |
| 14 — evaluation | Not started. Blocked until 13D.6g closes |
| 15 — security pass | 15.1–15.4 open |
| 15B — durable audit | 15B.1–15B.5 done; 15B.6–15B.10 open. Started early by maintainer override on 2026-09-22; it does not close 13D, 13C or 15 |
| 16 — containers and walkthrough | Open. 16.1 files exist but were never built or run |
| 17 — final review | Open |

## Now — close Phase 13D

Blocks Phase 14. `PLAN.md` 13D.6g holds the full command list and the exit gate.

- [ ] **Remeasure the labelled pilot on the current assessor.** The last measured
      configuration is `evidence-assessment-v3` with `qwen2.5:7b`. The code now runs
      `evidence-assessment-v5` plus the evidence-support and classification changes
      in log entries 119, 120, 125, 126, 128, 129, 130 and 131, none of which has
      been measured. That includes weak CV lines, the 0.35 retrieval abstain,
      batched requirement classification, rejected duplicate CV labels, and the
      adversarial package fixture.
      With Ollama running, from `backend/`:
      `RUN_LLM_SMOKE=1 .venv/bin/pytest tests/smoke/test_ollama_pilot.py -m smoke --no-cov -s`
      (`SMOKE_COMPLETION_MODEL` defaults to `qwen2.5:7b`). Record the printed result
      in `docs/evaluation.md`.
- [ ] **Decision — settle the two label questions** in `docs/evaluation.md`
      ("The two remaining disagreements are label questions"): `role-strong` /
      `req-sql` and `role-partial` / `req-reliability`. Change a label only by human
      decision, and record it.
- [ ] **Decision — the cover-letter contradiction gate.** `dev-contradiction` fails
      because the denial lives only in a cover letter, which the assessor never sees.
      Recommended: record it as a known 13D limitation and close it with the letter
      policy in 14.8, because letters are excluded from scoring until ADR 011's
      policy is implemented. The alternative is a server-side contradiction check now.
- [ ] **Run the 13D.6g verification on the production path** with local Ollama and no
      API key: the 13D.1 check set with before-and-after error rate, ranking agreement
      and latency, and the synthetic Aviva-shaped walkthrough.
- [ ] **Close the 13C exit verification** carried into 13D.6g: representative CVs and
      at least five job adverts (`PLAN.md` "Outstanding exit verification").
- [ ] **Finish the journey** listed in 13D.6g: loading and progress states on
      analysis and Ask, actionable error messages, readable resolving citations,
      honest refusals, working exports.
- [ ] **Update the documents 13D.6g names** after verification, then tick 13D.6g,
      13D.6 and the 13D exit gate together.

## Next — finish Phase 15B (durable operational audit)

Instructions: [docs/observability-logging-plan.md](docs/observability-logging-plan.md).
Contract: [ADR 012](docs/adr/012-durable-operational-audit.md). Until 15B.7 lands,
action, event and HTTP-envelope records live only in the in-memory recorder and are
lost on restart; `provider_call_accounting` is already durable.

- [ ] **15B.6** Event rows from the worker and persistence adapters.
- [ ] **15B.7** `SqlAuditRecorder`, Alembic migration, cascade hard delete, production
      wiring.
- [ ] **15B.8** `correlation_id`, `success` and `error_code` on
      `provider_call_accounting` — no payloads.
- [ ] **15B.9** Module-logger presence test and the 13B redaction regression on
      stderr, file and store.
- [ ] **15B.10** README, production wiring, engineering journal and checklist.

## Then — Phase 14 evaluation

Starts only after 13D.6g closes.

- [ ] **14.1** Versioned labels across job families, seniorities and advert formats;
      freeze a held-out set before tuning.
- [ ] **14.2** Stage-by-stage report: classification, precision/recall, retrieval
      recall@k, assessment confusion matrix, citation support, ranking agreement.
- [ ] **14.3** Thresholds recorded before held-out runs; observed results with
      versions, provider, settings and date.
- [ ] **14.4** Offline harness test in `make test-evaluation` plus a separate live
      entrypoint.
- [ ] **14.5** Ollama, OpenAI and Anthropic on the same public-safe dataset, one
      variable at a time.
- [ ] **14.6** Generated-artefact usefulness and unsupported-claim rate on
      independently labelled probes.
- [ ] **14.7** Calibrate the similarity floor (`config/scoring_rubric.toml`) and
      assessment policy on development data; publish the retrieval ablations.
- [ ] **14.8** Evaluate and implement the ADR 011 cover-letter policy, or report the
      narrative-only limitation explicitly.

## Then — Phase 15 security pass

- [ ] **15.1** `make security` (Bandit, pip-audit, `bun audit`, Gitleaks, Trivy). The
      target exists; a passing run has never been recorded.
- [ ] **15.2** Retention window and expiry hard delete. `DOCUMENT_RETENTION_DAYS` is
      declared in `config/app.env.example` and read by nothing.
- [ ] **15.3** Rate limiting on upload, analysis and generation routes.
      `RATE_LIMIT_UPLOADS_PER_HOUR` and `RATE_LIMIT_GENERATIONS_PER_HOUR` are declared
      and read by nothing.
- [ ] **15.4** Residual risks in `docs/threat-model.md`.
- [ ] **Maintenance risk** carried from 13A.1: the two FastAPI/Starlette TestClient
      deprecation warnings. Revisit on a compatible upgrade; do not silence them.

## Then — Phase 16 containers and walkthrough

- [ ] **16.1** Build both images and run the stack. Fix the drift in `compose.yaml`
      first: it still defaults the API to `hermetic` providers, passes the deleted
      `EXTRACTION_STRATEGY`, leaves `OLLAMA_COMPLETION_MODEL` empty, and its
      `MAX_QUESTION_CHARS` (1000), `MAX_CONTEXT_CHARS` (12000) and
      `LLM_MAX_OUTPUT_TOKENS` (1024) fallbacks disagree with `settings.py` (4000,
      24000, 2000). Its header comment still says the default providers are hermetic.
      `config/app.env` sets `OLLAMA_BASE_URL=http://localhost:11434`, which overrides
      the Compose fallback `http://ollama:11434`, so the API container would look for
      Ollama inside itself.
- [ ] **16.2** Database deployment profile.
- [ ] **16.3** Backup and restore with an observed restore smoke test.
- [ ] **16.4** Two clean-room walkthroughs: `make run` on local PostgreSQL, and
      Compose.
- [ ] **16.5** Playwright end-to-end journey. `e2e/tests/` is empty today, so
      `make test-e2e` has nothing to run.
- [ ] **16.6** Hosted-provider end-to-end run, reported as skipped without a key.
- [ ] **16.7** Screenshots. The README already shows maintainer captures from
      `docs/images/`; `docs/screenshots/` is empty. Keep one folder — recommended
      `docs/images/`, and amend 16.7 to match.
- [ ] **16.8** README pass against the built system.
- [ ] **16.9** Deployment guide stays private and single-user until authentication
      exists.

## Then — Phase 17 final review

- [ ] **17.1** Read-only review of the full diff against `AGENTS.md`.
- [ ] **17.2** No fabricated metrics, dates or outputs in any document.
- [ ] **17.3** Accepted, changed and rejected AI suggestions in the log, including the
      Lovable output.
- [ ] **17.4** Honest limitations list in the README.
- [ ] **17.5** Schema, foreign keys and deletion tests against the personal-data
      inventory.

## Decisions needed

Found in the 2026-09-24 repository review. Each has a recommendation; none is
implemented until the human decides.

- [ ] **Decision — hermetic in the Settings screen.** 13C.1 is ticked as "hermetic is a
      fixture no user-facing configuration offers", but `list_provider_catalogue`
      still offers it and the README settings screenshot shows it. Recommended: remove
      it from the production catalogue (keep it for `create_app()` tests), because a
      user who picks it gets the rules extractor that ADR 010 rejected as a product
      default.
- [ ] **Decision — CI trigger.** CI runs only when a pull request is *opened*
      (log entry 084), so commits pushed to an open pull request are never checked.
      Recommended: `types: [opened, synchronize, reopened]`, still without a push
      trigger on `main`. This matters more now that commits are small and frequent.
- [ ] **Decision — SonarQube in CI.** There is no `sonar-project.properties` and no
      scan in CI, so SonarQube findings are only seen locally. Recommended: add a
      SonarQube Cloud scan on pull requests that imports backend `coverage.xml` and
      frontend LCOV, with the default quality gate. The frontend needs `lcov` added to
      the Vitest coverage reporters first; it has no coverage threshold today.
- [ ] **Decision — record the data behind live hosted runs.** Log entries 109, 118 and
      119 record live OpenAI analysis runs without saying which documents were used.
      The 13D constraints forbid sending personal documents to a hosted provider.
      Recommended: amend those entries to state the data source.

## Code quality — SonarQube and SOLID follow-ups

From a static size and branch-count scan on 2026-09-24, not a SonarQube run. Confirm
each with SonarQube before changing anything, and refactor only under green tests, one
`refactor:` commit per function.

- [ ] **Long or branch-heavy functions** likely above the cognitive-complexity limit
      of 15: `application/analysis/service.py` `_run_job` (219 lines),
      `adapters/persistence/analysis_repos.py` `publish` (133),
      `adapters/persistence/role_store.py` `_load_bundle` (129),
      `application/analysis/similarity.py` `requirement_claim_similarities` (97),
      `domain/assessment.py` `_one`, `domain/mapping.py` `map_requirement`,
      `domain/generation.py` `draft_cover_letter` and `build_interview_pack`,
      `main.py` `create_app`, `api/errors.py` `install_exception_handlers`.
- [ ] **Large modules to split by responsibility:** `api/routes_analysis.py` (891
      lines — check it for business logic that belongs in use cases),
      `adapters/persistence/analysis_worker.py` (744), and in the frontend
      `routes/dev.states.tsx` (941), `api/client.ts` (750) and
      `components/role/RoleDetailContainer.tsx` (638).
- [ ] **Provider-name branching in the application.**
      `application/providers/catalogue.py` chooses default models with
      `if provider_id == ...` chains. Move each provider's defaults into its catalogue
      entry so a new provider needs no edit there (open/closed).
- [ ] **Dead code:** the `career_assistant/generation`, `matching` and `ops` packages
      contain only `__init__.py`. Delete them.
- [ ] **Dead configuration:** `config/app.env.example` declares settings no backend
      code reads — the `SCORE_*` rubric keys (the rubric is read from
      `config/scoring_rubric.toml`, so the comment "changing these changes every
      stored score" is wrong), `GENERATION_*`, `COVER_LETTER_MIN_MET_MUSTS`, `JOB_*`,
      `RATE_LIMIT_*` and `DOCUMENT_RETENTION_DAYS`. Wire each through settings or
      delete it along with every mention in `compose.yaml` and the docs.
- [ ] **Coverage visibility.** Six persistence modules are omitted from the hermetic
      coverage gate and covered only by `make test-integration`. SonarQube will count
      them as uncovered unless the integration coverage is combined into the report.

## Housekeeping

- [ ] Delete the merged local branches `chore/schema-drop-unused-answer-draft-columns`,
      `docs/readme-live-screenshots` and `feat/phase-13d-assessment-accuracy`, and the
      last two on `origin`.
- [ ] Delete the lock files earlier agent sessions left in `.git/` (`stale-locks/`,
      `index.lock.*`, `HEAD.lock.*`) while no git process is running.
- [ ] Log entry 084 still has `Human validation: TBD`.

## Superseded — do not restart

- `PLAN.md` 5.3, replaced by 13C.2.
- `PLAN.md` 7.2, replaced by 13C.5.

## Deferred — revisit only if the check set shows a need

From `PLAN.md` 13D: PostgreSQL full-text plus pgvector hybrid retrieval with fusion and
ablations; an approximate vector index; a second reviewing model; per-sentence
semantic groundedness checks on drafts. Multi-CV comparison, authentication and the
rest of "Deliberately not in scope" in `PLAN.md` stay out of this build.
