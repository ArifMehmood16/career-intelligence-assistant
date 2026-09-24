# Backlog

The ordered list of work that still matters for a credible release. `PLAN.md` remains
the source of acceptance criteria and exit gates; this file decides priority.

Last reviewed 2026-09-24 on `main`, after pull request #39 merged.

**How to use it.** Work top to bottom in [Now](#now--release-path). Do not start an
item in [Later](#later--valuable-after-the-release-path) or
[Parking lot](#parking-lot--not-needed-for-this-release) unless the human explicitly
promotes it. When a `PLAN.md` task is completed, update its checkbox and the matching
line here in the same commit.

This backlog is intentionally scoped to a local, private, single-user candidate tool.
Authentication, multi-tenancy and Internet-facing operation would require a separate
product and threat-model decision.

## Where things stand

- Phases 0–13, 13A and 13B are complete.
- Phase 13C is implemented; its representative-model verification is folded into the
  Phase 13D release evaluation below.
- Phase 13D.1–13D.5 and 13D.6a–13D.6f are complete. **13D.6g is the current gate.**
- Phase 14 is reduced to the evaluation work needed to support honest quality claims.
- Phase 15 keeps practical security and privacy checks. Hosted-service controls are
  parked.
- Phase 15B.1–15B.5 remain implemented. Further durable-audit work is not a release
  blocker.
- Phase 16 supports one truthful startup path and one small end-to-end journey.
- Phase 17 is one consolidated release review rather than five separate tasks.

## Now — release path

- [ ] **13D.6g — run one consolidated local-Ollama release evaluation.** Use the
      current `evidence-assessment-v5` path and combine the previously separate pilot,
      production-path, Aviva-shaped and 13C representative-CV checks. Include at least
      five representative job adverts. Settle and record the two human-owned label
      questions (`role-strong` / `req-sql` and `role-partial` /
      `req-reliability`) before tuning. Record requirement classification,
      unsupported matches, ranking agreement and latency in `docs/evaluation.md`.
      The live entry point is:
      `RUN_LLM_SMOKE=1 .venv/bin/pytest tests/smoke/test_ollama_pilot.py -m smoke --no-cov -s`.
- [ ] **13D.6g — verify the complete journey and close the evidence gate.** Check
      progress and loading states, actionable failures, readable resolving citations,
      honest refusals and working exports. Fix only defects that block matching,
      evidence, exports or comprehension. Update the documents named by the plan,
      then tick 13D.6g, 13D.6, the 13C carried verification and the 13D exit gate
      together.

**Recorded scope decision:** a contradiction found only in a cover letter is not CV
matching evidence. Cover letters remain narrative-only supporting documents and do
not affect fit scoring. Record `dev-contradiction` as this known limitation; it does
not block 13D.

- [ ] **14.1–14.4, 14.6 and 14.7 — complete the minimum credible evaluation.** Keep a
      small versioned dataset across representative roles and advert formats; report
      the stages that determine fit; freeze held-out labels and thresholds before the
      final run; calibrate retrieval on development data; and verify the existing
      offline and live entry points. Generated-artefact evaluation is limited to
      unsupported-claim and safe-refusal probes, not a subjective usefulness study.
- [ ] **Release corrections — remove inconsistencies without adding features.**
      Remove `hermetic` from the user-facing provider catalogue while retaining it as
      a test fixture; add the pull-request `synchronize` and `reopened` CI events;
      identify the synthetic/public-safe data class behind logged hosted runs; and
      delete genuinely unused or misleading configuration rather than implementing
      features to justify it.
- [ ] **15.1 — run the practical security checks.** Record the observed Bandit,
      dependency-audit and secret-scan results. Run container/filesystem scanning only
      for a supported container path.
- [ ] **16.1 and 16.4 — choose and prove the Docker support outcome.** Either repair
      the known Compose/provider/configuration drift, build the images and verify one
      clean startup, or remove Docker from the supported quick-start claims. Do not
      maintain two equivalent clean-room walkthroughs merely for symmetry.
- [ ] **16.5 — add one minimal Playwright smoke journey.** Upload a CV, add a role,
      wait for analysis, then view fit and cited evidence. Keep duplicate uploads,
      restart behaviour, generation edge cases and detailed failures in lower-level
      tests.
- [ ] **15.4 and 17.1–17.5 — perform one privacy, deletion and final release review.**
      Reconcile the threat model, personal-data inventory, schema relationships and
      hard-delete tests. Inspect the complete diff for unsupported claims, fabricated
      metrics, security regressions and unnecessary complexity, and confirm the
      factual AI-development record.
- [ ] **16.8, 16.9 and 17.4 — finish the README and deployment wording.** Document
      only the startup path actually verified and keep deployment explicitly private
      and single-user until authentication exists. Keep the limitations explicit and
      commands reproducible.

## Later — valuable after the release path

These items may improve maintainability, but none should interrupt the evidence,
security or walkthrough work above.

- [ ] **15B.8 — enrich provider-call accounting** with `correlation_id`, `success`
      and safe `error_code` fields if operational diagnosis demonstrates the need.
- [ ] **15B.9 — keep one logging/redaction regression** across the logging outputs
      that remain supported. Fold it into security work rather than creating a new
      observability phase.
- [ ] **Maintenance — revisit the FastAPI/Starlette TestClient deprecation warnings**
      when a compatible dependency upgrade exists; do not silence them.
- [ ] **Targeted refactoring — address a function or module only when tests,
      SonarLint, an observed defect or active work demonstrates a concrete problem.**
      File length and branch counts alone do not justify a release task.

## Parking lot — not needed for this release

These are deliberately not active work. Promote one only after a documented product
need or deployment change, and update `PLAN.md`/ADRs before implementation where the
decision changes architecture.

- **15B.6, 15B.7 and 15B.10 — full durable operational audit.** SQL action/event/HTTP
  tables, recorder persistence and associated documentation add migrations, privacy
  surface and deletion work without improving CV matching for a local user. Existing
  structured logging and provider-call accounting are sufficient for this release.
- **14.5 and 16.6 — hosted-provider benchmarking and hosted end-to-end runs.** Provider
  contract tests remain required, but OpenAI/Anthropic comparison studies are not part
  of the local-first release thesis.
- **14.8 — cover-letter scoring or contradiction policy.** Cover letters remain
  narrative-only and outside CV-fit scoring unless a future product decision changes
  the evidence model.
- **15.2 — automatic retention windows.** Hard delete remains required. Scheduled
  expiry becomes relevant only for a hosted service with an agreed retention policy.
- **15.3 — rate limiting.** Add it with authentication and an Internet-facing threat
  model, not to a local single-user process.
- **16.2 and 16.3 — production database topology and formal backup/restore drills.**
  Revisit for an actual hosted deployment. A private local portfolio walkthrough does
  not need platform-grade operations.
- **SonarQube Cloud CI and coverage conversion solely for Sonar.** Existing lint,
  type, test and security gates remain authoritative unless external assessment
  explicitly requires SonarQube.
- **Speculative provider abstractions and blanket large-file refactors.** Four known
  providers do not justify more indirection without a demonstrated change cost or
  quality finding.
- **Additional screenshot work.** Maintain the existing `docs/images/` captures when
  the UI changes; do not create a second screenshot directory or a separate release
  task.

## Repository maintenance — does not block release

- Delete merged local or remote branches only when they are confirmed unnecessary and
  no active worktree depends on them.
- Remove stale `.git` lock files only after confirming no Git process is running.
- Replace `TBD` validation text in log entry 084 only with observed evidence; otherwise
  leave it explicitly unresolved.

## Deferred retrieval experiments

Revisit only if the evaluation set demonstrates a need: PostgreSQL full-text plus
pgvector hybrid retrieval, an approximate vector index, a second reviewing model, or
per-sentence semantic groundedness checks. Multi-CV comparison, authentication and
the rest of the product's deliberately excluded features remain out of scope.
