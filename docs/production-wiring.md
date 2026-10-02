# Production wiring matrix

Every HTTP route in the production process (`create_production_app` →
`build_sql_stores`) must appear here. A passing unit or repository test is not
evidence that the route uses that code.

Hermetic `create_app()` used by default API tests still injects in-memory stores and
does not start `SqlAnalysisWorker`. That path is test-only.

Provider resolvers:

- `none` — no model call
- `completion_port_for` — workspace `answerProviderId` / `answerModel` through the
  Phase 2 completion factory, egress-checked at construction and call time
- `build_structured_port` — the workspace answer provider/model constructs the
  chunker/judge, with model-specific execution budgets and `AccountingCompletion`.
  `V2JobRunner` is the sole worker path. One document response also supplies inferred
  technology relationships; no separate taxonomy/extraction/assessment pipeline.
- `build_embedding_port` — independent workspace index provider/model, batched
  CV/query vectors, `AccountingEmbedding`, cache identity and hybrid search.
- `analyse_hermetic` — the same application pipeline with deterministic provider
  boundaries for test-only in-memory stores. Never a production persistence fallback.
- `list_provider_catalogue` / `apply_provider_choice` — catalogue and egress
  acknowledgement only; no document text leaves the process

| Route | Use case | Provider resolver | SQL adapter |
|---|---|---|---|
| GET /api/health | liveness | none | none |
| GET /api/ready | SettingsReadiness.check | none | SettingsReadiness (database + migrations) |
| GET /api/cv | get_cv | none | SqlCvStore |
| POST /api/cv | upload_bytes_cv / upload_pasted_cv | none on admit; build_structured_port on queued reanalysis | SqlCvStore; SqlRoleStore enqueue; SqlAnalysisWorker |
| DELETE /api/cv | delete_cv | none | SqlCvStore (hard delete + dependent roles) |
| GET /api/cover-letters | list_cover_letters | none | SqlSupportingDocumentStore |
| POST /api/cover-letters | upload_bytes_cover_letter / upload_pasted_cover_letter | none | SqlSupportingDocumentStore |
| DELETE /api/cover-letters/{document_id} | delete_cover_letter | none | SqlSupportingDocumentStore |
| GET /api/documents/{document_id}/download | get_downloadable | none | SqlSupportingDocumentStore |
| GET /api/spans/{span_id} | lookup_workspace_span + resolve_span | none | SqlCvStore, SqlSupportingDocumentStore, SqlRoleStore |
| GET /api/roles | list_roles | none | SqlRoleStore |
| POST /api/roles | create_role (commit analysing + queued job, 202) | build_structured_port and build_embedding_port on the worker, not on the request | SqlRoleStore; SqlAnalysisWorker; requirement_claim_similarities; SqlEmbeddingCache |
| GET /api/roles/{role_id} | get_role; build_fit_summary when ready | none | SqlRoleStore |
| DELETE /api/roles/{role_id} | delete_role | none | SqlRoleStore |
| POST /api/roles/{role_id}/reanalyse | reanalyse (202) | build_structured_port and build_embedding_port on the worker | SqlRoleStore; SqlAnalysisWorker; requirement_claim_similarities; SqlEmbeddingCache |
| GET /api/jobs/{job_id} | get_job | none | SqlRoleStore |
| GET /api/roles/{role_id}/requirements | stored mappings | none | SqlRoleStore |
| GET /api/roles/{role_id}/breakdown | stored score explanation | none | SqlRoleStore |
| GET /api/roles/{role_id}/gap-plan | build_gap_plan | none | SqlRoleStore |
| GET /api/roles/{role_id}/verdicts | stored v2 verdicts, fit, keyword coverage and gap plan (409 `analysis_incomplete` without a v2 analysis) | none | SqlV2ResultReader (SqlV2AnalysisRepository) |
| GET /api/roles/{role_id}/verdicts/{requirement_id}/trace | stored retrieval traces for one verdict | none | SqlV2ResultReader (SqlRetrievalTraceRepository) |
| GET /api/roles/{role_id}/interview-pack | generate_draft (phrasing) | completion_port_for | SqlRoleStore |
| POST /api/roles/{role_id}/bullets | generate_draft | completion_port_for | SqlRoleStore |
| POST /api/roles/{role_id}/cover-letter | generate_draft | completion_port_for | SqlRoleStore |
| GET /api/roles/{role_id}/cover-letters | list_cover_letters | none | SqlRoleStore |
| GET /api/roles/{role_id}/export/{artefact}.md | export_markdown / stored draft by version | completion_port_for when exporting interview-pack | SqlRoleStore |
| GET /api/ranking | rank_roles | none | SqlRoleStore |
| GET /api/compare | compare_requirement_sets | none | SqlRoleStore |
| GET /api/messages | list persisted conversation | none | SqlConversationStore |
| POST /api/messages | AskService (stream or JSON). Open questions use the agent when the answer model reports tool calling; otherwise scoped retrieval. Gaps, fit, comparison and interview preparation stay on the router | completion_port_for; build_tool_calling_port for the agent (hermetic, Ollama, OpenAI, Anthropic) | SqlConversationStore; retrieval via SqlCvStore, SqlSupportingDocumentStore, SqlRoleStore |
| DELETE /api/messages | hard-delete conversation | none | SqlConversationStore |
| GET /api/providers | list_provider_catalogue | list_provider_catalogue | none (server config) |
| GET /api/settings/providers | get persisted choice | none | SqlProviderSettingsStore |
| PUT /api/settings/providers | apply_provider_choice | apply_provider_choice + egress | SqlProviderSettingsStore |

Call accounting for completion and embeddings goes through `AccountingCompletion`
/ `AccountingEmbedding` into `SqlCallAccountant` / `provider_call_accounting`.
It stores provider, model, `left_machine` and token counts — never document,
question, prompt or embedding text.
