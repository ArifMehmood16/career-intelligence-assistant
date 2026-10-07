# Tasks: Runtime acceptance verification

Root: PLAN 19.2–19.3. Tests are explicitly required by this spec.

## Phase 1 — Existing-project prerequisites

- [x] T001 Inspect PLAN/BACKLOG, current implementations, merged history and
  existing acceptance tests; record dispositions in `research.md`.
- [x] T002 Author `spec.md`, `plan.md`, `data-model.md`, `quickstart.md` and this
  task list; analyze constitution alignment and requirement coverage.

## Phase 2 — US1: verify provider work before rebuilding it

- [x] T003 [US1] Run existing chunk/judge/cache/embedding/profile/gate contracts
  in `backend/tests/{unit,contract}/`; retain observed results for the root gate.
- [x] T004 [US1] Reconcile current delivery and stale/duplicate tasks in
  `PLAN.md`, `BACKLOG.md`, `README.md` and `docs/spec-kit.md` after proof.

## Phase 3 — US2: real parser lifecycle proof

- [x] T005 [US2] Add picklable synthetic stalled/crashed child helpers in
  `backend/tests/support/process_parse_probe.py`.
- [x] T006 [US2] Add timeout/crash termination, recreation and idempotent close
  regressions in `backend/tests/unit/test_process_parser.py`.
- [x] T007 [US2] Prove parser cleanup on app lifespan exit in
  `backend/tests/api/test_parser_lifespan.py`.
- [x] T008 [US2] Run focused parser/lifespan checks; repair
  `backend/src/career_assistant/parsing/process_pool.py` only for demonstrated defects.

## Phase 4 — US3: actual thread context proof

- [x] T009 [US3] Exercise cancellation/progress/accounting scopes and retries
  through bounded fanout in `backend/tests/unit/test_fanout.py`.
- [x] T010 [US3] Run surrounding runtime tests from `quickstart.md`, retaining
  existing ETA, cache, ordering and cancellation acceptance.

## Phase 5 — Checkpoint

- [x] T011 Run focused Ruff/mypy plus root `make lint` and `make test`; inspect
  the complete Git diff for privacy, lifecycle and design issues.
- [x] T012 Record observed evidence in `docs/engineering-journal.md` and
  `AI_DEVELOPMENT_LOG.md`; close only proven root gates and update this task list.
- [ ] T013 Commit/push the sole task branch and open one review PR; observe
  final-head CI and attach the PR to this chat. Human owns merging. This external
  delivery step is confirmed in the PR timeline after this committed checkpoint.

## Dependencies and implementation strategy

T001–T003 establish existing behavior before new tests. T005 precedes T006/T007;
T008 follows both. T009 and the parser test files can be edited independently,
but this session implements sequentially. T004/T012 gate closure depends on
T008/T010/T011. T013 follows complete checks and documentation. US1 is the
audit MVP; US2 and US3 independently add missing acceptance proof. No new app,
dependency, API, schema or paid measurement is introduced.

## Observed checkpoint (2026-10-07)

Provider suite: 185 pass. Runtime suite: 55 pass, including seven new lifecycle/context
regressions. Full make lint and make test pass: 825 backend, 192 frontend, three
existing skips, reported total coverage 85%. No production defect or red fix is
claimed; the added regressions catch removal of existing cleanup/context behavior.
Spec/plan/tasks analysis maps all five requirements and four success criteria; no
constitution conflict, unmapped task, ambiguity or duplication within this slice.
External PR publication/final-head CI is recorded by the GitHub delivery timeline.
