# Tasks — fit explanations

## Setup and foundation
- [x] T001 Inspect code/tests and create spec/design in specs/008-fit-explanations/.
- [x] T002 Analyze spec/plan/tasks against .specify/memory/constitution.md.

## US1 — point attribution
- [x] T003 [US1] Red weighted/zero/unavailable tests in backend/tests/unit/test_scoring_v2.py and backend/tests/api/test_verdict_routes.py; round-trip in backend/tests/integration/test_v2_verdicts_http_sql.py.
- [x] T004 [US1] Domain point projection in backend/src/career_assistant/domain/scoring_v2.py; read original JSON components in adapters/persistence/v2_analysis_repos.py; extend application/ports/v2_results.py and api/schemas.py/routes_verdicts.py.
- [x] T005 [US1] Red arrow/label/filter-preservation tests in frontend/src/components/role/verdicts/VerdictsPanel.test.tsx; implement API/types, cards and synthetic fixtures/gallery, then green focused checks/commit.

## US2 — context and qualitative experience
- [x] T006 [US2] Red grounding/null/context/cache tests in backend/tests/unit/test_chunk_plan.py, test_judge_rules.py, test_judge_prompt.py and test_verdict_key.py.
- [x] T007 [US2] Verified optional experience_expected and overall seniority context in backend/src/career_assistant/domain/chunking.py, application/contracts/chunking.py, chunking/mapping.py/prompts.py and adapters/persistence/chunk_repos.py.
- [x] T008 [US2] Immutable document context, cache/budget/prompt anchors in backend/src/career_assistant/domain/judging.py/candidate_facts.py and application/analysis/v2.py, judge/prompt.py/cache.py; preserve recheck and evidence scope; adjust hermetic adapter fixtures to new contracts.
- [x] T009 [US2] Persist/expose verified asked expectations in backend/src/career_assistant/adapters/persistence/v2_analysis_repos.py, application/ports/v2_results.py and api; render asked/supported and anchor mode in frontend/src/components/role/verdicts/VerdictCard.tsx/verdict-copy.ts; green checks/commit.

## US3 — Ask processing
- [x] T010 [US3] Red pending/stream/terminal/cancellation tests in frontend/src/components/ask/ChatView.test.tsx and ChatContainer.test.tsx.
- [x] T011 [US3] Show accessible processing/answering status in frontend/src/components/ask/ChatView.tsx; protect request lifecycle in ChatContainer.tsx; add pending gallery state in frontend/src/routes/dev.states.tsx; green checks/commit.

## Checkpoint
- [x] T012 Full make lint/test and disposable SQL integration, branch review and synthetic Browser checks; update README.md, PLAN.md, BACKLOG.md, docs/features.md, docs/api-contract.md, docs/architecture.md, docs/engineering-journal.md and AI_DEVELOPMENT_LOG.md.
- [ ] T013 Explicit commit/push, create/attach review PR, inspect final CI; verify main plus active branch and one checkout.

Dependencies: T001 → T002; each story tests precede its source changes. Stories
independently verifiable; US1/US2 share API/card files so implemented sequentially.
US3 independent. All stories precede T012/T013. Research-only agent under Spec Kit;
root implements. FR001/002 T003–005; FR003–005 T006–009; FR006 T010–011;
FR007 T003–012; FR008 T001/T002/T012/T013. No unmapped requirement/task.
