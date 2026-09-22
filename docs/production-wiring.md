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
- `analysis_ports_for_choice` — hermetic stays on rules extractors and a
  null adjudicator so `make test` is offline; any other workspace answer
  choice uses the quote-verified model extractors (item types classified in
  the prompt and schema) and one structured evidence assessment for every
  retrieved requirement, including when lexical and embedding signals agree.
  A missing or invalid assessment is `assessment_incomplete` and is not a
  match. The job fails with that code and no fit score is published. Hermetic analysis still uses the null adjudicator and the OR
  fallback so `make test` stays offline. Cover letters extract as
  self-authored claims and are not
  mapped yet. [ADR 011](adr/011-evidence-assessment-contract.md) records the
  contract those claims will follow: concrete experience can count, with its
  source shown and duplicates removed; an aspiration does not, and a generated
  draft must never raise the score. Salary, benefit and logistics items are
  stored and never mapped.
- `build_embedding_port` — workspace `indexProviderId` / `indexModel` through the
  Phase 2 embedding factory, egress-checked at construction and call time; used
  by `SqlAnalysisWorker` to propose mapping candidates. Ask does not retrieve
  over vectors.
- `list_provider_catalogue` / `apply_provider_choice` — catalogue and egress
  acknowledgement only; no document text leaves the process

| Route | Use case | Provider resolver | SQL adapter |
|---|---|---|---|
| GET /api/health | liveness | none | none |
| GET /api/ready | SettingsReadiness.check | none | SettingsReadiness (database + migrations) |
| GET /api/cv | get_cv | none | SqlCvStore |
| POST /api/cv | upload_bytes_cv / upload_pasted_cv | none on admit; analysis_ports_for_choice on queued reanalysis | SqlCvStore; SqlRoleStore enqueue; SqlAnalysisWorker |
| DELETE /api/cv | delete_cv | none | SqlCvStore (hard delete + dependent roles) |
| GET /api/cover-letters | list_cover_letters | none | SqlSupportingDocumentStore |
| POST /api/cover-letters | upload_bytes_cover_letter / upload_pasted_cover_letter | none | SqlSupportingDocumentStore |
| DELETE /api/cover-letters/{document_id} | delete_cover_letter | none | SqlSupportingDocumentStore |
| GET /api/documents/{document_id}/download | get_downloadable | none | SqlSupportingDocumentStore |
| GET /api/spans/{span_id} | lookup_workspace_span + resolve_span | none | SqlCvStore, SqlSupportingDocumentStore, SqlRoleStore |
| GET /api/roles | list_roles | none | SqlRoleStore |
| POST /api/roles | create_role (commit analysing + queued job, 202) | analysis_ports_for_choice and build_embedding_port on the worker, not on the request | SqlRoleStore; SqlAnalysisWorker; requirement_claim_similarities; SqlEmbeddingCache |
| GET /api/roles/{role_id} | get_role; build_fit_summary when ready | none | SqlRoleStore |
| DELETE /api/roles/{role_id} | delete_role | none | SqlRoleStore |
| POST /api/roles/{role_id}/reanalyse | reanalyse (202) | analysis_ports_for_choice and build_embedding_port on the worker | SqlRoleStore; SqlAnalysisWorker; requirement_claim_similarities; SqlEmbeddingCache |
| GET /api/jobs/{job_id} | get_job | none | SqlRoleStore |
| GET /api/roles/{role_id}/requirements | stored mappings | none | SqlRoleStore |
| GET /api/roles/{role_id}/breakdown | stored score explanation | none | SqlRoleStore |
| GET /api/roles/{role_id}/gap-plan | build_gap_plan | none | SqlRoleStore |
| GET /api/roles/{role_id}/interview-pack | generate_draft (phrasing) | completion_port_for | SqlRoleStore |
| POST /api/roles/{role_id}/bullets | generate_draft | completion_port_for | SqlRoleStore |
| POST /api/roles/{role_id}/cover-letter | generate_draft | completion_port_for | SqlRoleStore |
| GET /api/roles/{role_id}/cover-letters | list_cover_letters | none | SqlRoleStore |
| GET /api/roles/{role_id}/export/{artefact}.md | export_markdown / stored draft by version | completion_port_for when exporting interview-pack | SqlRoleStore |
| GET /api/ranking | rank_roles | none | SqlRoleStore |
| GET /api/compare | compare_requirement_sets | none | SqlRoleStore |
| GET /api/messages | list persisted conversation | none | SqlConversationStore |
| POST /api/messages | AskService (stream or JSON) | completion_port_for for every intent; insufficient evidence does not call the model | SqlConversationStore; retrieval via SqlCvStore, SqlSupportingDocumentStore, SqlRoleStore |
| DELETE /api/messages | hard-delete conversation | none | SqlConversationStore |
| GET /api/providers | list_provider_catalogue | list_provider_catalogue | none (server config) |
| GET /api/settings/providers | get persisted choice | none | SqlProviderSettingsStore |
| PUT /api/settings/providers | apply_provider_choice | apply_provider_choice + egress | SqlProviderSettingsStore |

Call accounting for completion and embeddings goes through `AccountingCompletion`
/ `AccountingEmbedding` into `SqlCallAccountant` / `provider_call_accounting`.
It stores provider, model, `left_machine` and token counts — never document,
question, prompt or embedding text.
