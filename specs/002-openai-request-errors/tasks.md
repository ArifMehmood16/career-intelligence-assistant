# Tasks: OpenAI analysis request repair

Root: [PLAN 19.2](../../PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider)
Inputs: [spec](spec.md), [plan](plan.md), [research](research.md).

## Setup and foundation

- [x] T001 Inspect current adapters, contracts, tests and human deferral; record diagnostic evidence in specs/002-openai-request-errors/research.md.
- [x] T002 Define scoped requirements/design and operator contract in specs/002-openai-request-errors/spec.md, plan.md and contracts/logging.md.

## User Story 1 — Accepted advert-reading format

- [x] T003 [US1] Author defaulted-array/explicit-null/real-contract regressions in backend/tests/unit/test_schema_dialects.py (FR-001, FR-002).
- [x] T004 [US1] Repair optional collection and duplicate null conversion in backend/src/career_assistant/adapters/providers/schema_dialects.py (FR-001, FR-002, FR-005).
- [x] T005 [US1] Record one post-repair synthetic request acceptance using existing adapters in specs/002-openai-request-errors/research.md (SC-001, FR-005).

## User Story 2 — Safe provider diagnostics

- [x] T006 [US2] Author hostile/malformed response, operation logging and retry classification regressions in backend/tests/unit/test_openai_errors.py (FR-003, FR-004, FR-005).
- [x] T007 [US2] Implement bounded allowlisted error classification in backend/src/career_assistant/adapters/providers/openai/errors.py (FR-003, FR-004).
- [x] T008 [US2] Wire errors.py into OpenAI completion.py, embedding.py and the OpenAI caller in backend/src/career_assistant/adapters/providers/tool_calling.py (FR-003, FR-005).

## Documentation and pending verification

- [x] T009 Update docs/model-providers.md, docs/running-locally.md, PLAN.md, BACKLOG.md, AI_DEVELOPMENT_LOG.md and docs/engineering-journal.md with scope, retry instructions and observed evidence.
- [ ] T010 Run focused and normal checks described in specs/002-openai-request-errors/quickstart.md only when the human lifts deferral (SC-001, SC-002, SC-003).

## Dependencies and execution

T001–T002 precede both stories; US1: T003 → T004 → T005; US2:
T006 → T007 → T008. The two stories can be designed independently but are implemented
sequentially by one agent. T009 follows both; T010 remains pending. No deployment,
push or PR is authorized. Each story retains its independent acceptance scenarios.
