# Tasks: Debug logging a human can follow

- [ ] T001 Context fields (`job_id`, `role_id`) appended to every line — FR-001
- [ ] T002 `summarize` content-free rules — FR-003, FR-004
- [ ] T003 `traced` start/done/error at DEBUG, no work above DEBUG — FR-003, FR-005
- [ ] T004 Successful GETs at DEBUG; single correlation id — FR-006
- [ ] T005 Model/embedding request and response events, wired in the factory — FR-002
- [ ] T006 Reasoning tokens from OpenAI usage — FR-002
- [ ] T007 Structured outcome events with contract summaries — FR-002
- [ ] T008 Task start/finish events; job context bound at claim — FR-001
- [ ] T009 `traced` applied to application services and adapters — FR-003
- [ ] T010 Privacy regression: hermetic analysis at DEBUG leaks no fixture text — SC-001
- [ ] T011 Docs: running locally, threat model, AI log — SC-002
