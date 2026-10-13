# Tasks: Debug logging a human can follow

- [x] T001 Context fields (`job_id`, `role_id`) appended to every line — FR-001
- [x] T002 ~~`summarize` content-free rules~~ — built, then dropped with T003
- [x] T003 ~~`traced` decorator~~ — built, then dropped at the human's request
- [x] T004 Successful GETs at DEBUG; single correlation id — FR-006
- [x] T005 Model/embedding call lines, wired in the factory — FR-002
- [x] T006 Reasoning tokens from OpenAI usage — FR-002
- [x] T007 Structured outcome lines with contract summaries — FR-002
- [x] T008 Task start/finish lines; job context bound per job; claim line — FR-001
- [x] T009 Readable step lines: analysis, uploads, roles, Ask, drafting, MCP — FR-003
- [x] T010 Privacy regression: hermetic analysis at DEBUG leaks no fixture text — SC-001
- [x] T011 Docs: running locally, ADR 017, threat model, AI log — SC-002
- [ ] T012 Human follows a real rerun in the log file — SC-003
