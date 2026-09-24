# Threat model

Everything crossing a boundary is untrusted: uploaded CVs, job descriptions and cover
letters, document text, user questions, retrieved spans, model output and generated
drafts.

## Trust boundaries

| Boundary | Untrusted input | Primary controls |
|---|---|---|
| Browser to API | Uploads, questions | Type sniffing, size and page caps, schema validation, safe errors |
| File to parser | PDF/DOCX structure | Bounded parsing, no macro or embedded-object execution, resource limits |
| Document text to prompt | CV, job-description and supporting-cover-letter content | Delimited and labelled untrusted; instructions in the text are data; [ADR 011](adr/011-evidence-assessment-contract.md) allows concrete uploaded-letter experience to count once validated, with its source shown and duplicates removed; an aspiration does not count and a generated draft must never raise the score; the running matcher still excludes self-authored claims; adjudication pairs are delimited the same way and only submitted pair ids are accepted |
| Model to application | Extraction JSON, answer text | Schema validation, span verification, drop unresolvable output |
| Generated draft to browser | Model-phrased or template prose | Groundedness validator against cited spans; template fallback; real verdict persisted (FAIL never rewritten to PASS); provenance on every artefact |
| Application to browser | Excerpts and drafts | Escaped text rendering, no raw HTML |
| Application to model provider | Prompts built from application documents and questions | Egress gate at construction and call time; explicit acknowledgement covering every data kind; provider allowlist of hermetic, Ollama, OpenAI and Anthropic; per-provider timeout and breaker; keys never logged or returned; call accounting stores identifiers and counts only |
| Application to database | SQL parameters; original uploads; parsed personal data; questions, answers and drafts; operational action, event and HTTP-envelope rows | Parameterised access, least-privilege database role, workspace scoping, explicit transactions, foreign keys and hard delete of originals plus derived records **including** action, event, HTTP-envelope and provider-call-accounting rows. Production uses `create_production_app` / `build_sql_stores` (PostgreSQL). Hermetic `create_app()` in-memory stores are test-only. Audit inserts are fail-open and must not roll back a successful document write. No request, response, prompt or completion bodies in any column including JSONB. [ADR 012](adr/012-durable-operational-audit.md). |
| Database container to storage | PostgreSQL data directory and backups | Private network in deployment, required non-default credentials, persistent volume, documented backup/restore and backup rotation |
| Application to logs | Everything | Field-based stdlib logs at HTTP, application, persistence, worker, provider and config boundaries, to stderr and to an optional rotating file when `LOG_FILE` is set. The same field contract applies to workspace-scoped action, event and HTTP-envelope records ([ADR 012](adr/012-durable-operational-audit.md)), held in memory until the PostgreSQL tables land in PLAN 15B.7. `format_fields` drops multiline and over-long values. A redacting filter masks `sk-` / Bearer tokens and configured API keys. Never document text, uploads, questions, answers, embeddings, prompts, draft bodies, DTO dumps, HTTP bodies or credentials. SQLAlchemy `echo` stays off; `hide_parameters` stays true. No `GET /api/logs` until authentication exists. |

## Named risks

| Risk | Control | Residual |
|---|---|---|
| Prompt injection in a job description or supporting cover letter | Untrusted delimiting, schema validation, span verification, document-kind policy and regression tests | A crafted document may still degrade extraction or retrieval quality |
| Fabricated experience in an answer | Every claim requires a resolvable span | Extraction may mis-attribute a real span |
| Fabricated experience in a generated draft | Groundedness validator; regenerate once; hermetic template fallback; refuse a bullet with no cited claim; SQL never stores FAIL as PASS | Validator false positives become template fallbacks |
| Malicious PDF or DOCX | Bounded parsing, no embedded execution, size and page caps | Parser library vulnerabilities; mitigated by dependency scanning |
| Resource exhaustion | Caps on size, pages, characters, context and output; one in-process analysis worker with a running-job timeout and startup recovery of stale running rows | A slow extract still occupies that worker until timeout; this build is a local personal tool |
| Personal data retention | Hard delete of original bytes, parsed text, spans, chunks, embeddings, claims, mappings, generated drafts, questions, answers, citations, action rows, event rows, HTTP envelopes and provider-call accounting. A configurable retention window is planned (PLAN 15.2); `DOCUMENT_RETENTION_DAYS` is not read yet, so nothing expires automatically | Database backups retain data until they rotate; until 15.2, data stays until the user deletes it |
| Original-file disclosure | Bounded originals stored in PostgreSQL `bytea`; workspace-scoped download; no filesystem path; database not publicly exposed in deployment | A database or backup compromise exposes the original documents; volume encryption and host security remain deployment responsibilities |
| Cross-workspace leakage | Workspace scoping on every query, including span lookup and retrieval; integration test | No authentication yet — see below |
| Cover-letter claims treated as experience | Uploaded letters extract as `self_authored` claims. The running matcher ignores them. [ADR 011](adr/011-evidence-assessment-contract.md) will allow concrete experience, with source shown and duplicates removed, and will keep aspirations and generated drafts from raising the score | A user may still copy unsupported claims into a replacement CV; the system can only reason over submitted evidence |
| Salary, benefit or logistics line scored as a skill | The model extracts `item_type`; only `requirement` and `responsibility` reach the mapping and the score. Pay, equity, location, travel and right-to-work are `benefit` or `logistics`. A missing or non-enum `item_type`, or a non-boolean `must_have`, is rejected and retried once, then the job is `extraction_incomplete` | A small local model may still choose the enum value `requirement` for a package line until the role is re-analysed |
| Partial or duplicate chat history | Persist the question first; store one final validated answer under a workspace-scoped idempotency key; never persist SSE token fragments. Production chat is `SqlConversationStore`; `create_app()` in-memory chat is test-only. | A client can abandon a request and leave a safely failed question record |
| SQL injection or accidental unscoped mutation | SQLAlchemy parameterisation; repository methods require workspace id; cross-workspace read and mutation tests | A future raw-SQL escape hatch would need separate review |
| Application data reaching a third party | Hermetic and local providers by default; hosted adapters unreachable unless egress is enabled and a key is present, re-checked on every call; the notice covers CVs, job descriptions, cover letters and questions; selection is recorded on every artefact | A user who enables a hosted provider accepts that vendor's retention terms; the product makes that visible, it cannot make it safe |
| Leaked API key | Keys read at construction, never logged, never returned by any route including masked; redaction test | A compromised host still exposes the environment |
| Document text in operational logs | Event names plus ids, counts, durations, stages and provider ids only, in stderr, optional log files and audit tables; planted-phrase and planted-key tests; `PYTHONUNBUFFERED=1` on `make run-api` so operators see those events instead of turning echo on | A future logger.exception on an intake error could still carry a snippet in the traceback |
| Durable operational metadata | Action, event and HTTP-envelope rows store allowlisted names, ids, counts and codes; provider accounting stores identifiers and token counts; fail-open inserts; cascade delete with the workspace; no read API | A database or backup compromise shows that a workspace uploaded a document and asked questions, with timings, but not the document text if the contract holds; fail-open can lose the trail during an outage; disk log files sit outside Postgres backup/restore |
| Hosted provider outage or rate limit | Bounded retry on 429 and 5xx, timeout, breaker, safe error; no silent fallback to a different model | A degraded answer is still possible if fallback is explicitly enabled |

## Out of scope for this build

Stated as a decision, not an oversight. The product is a personal career tool meant
to be run locally by one person. It is not intended to go live for multiple users,
so this build stays light on multi-user security controls.

- Authentication, authorization and multi-tenancy. Not required for local personal
  use. Required before any untrusted user or shared deployment.
- Network hardening, WAF, rate limiting at a gateway.
- Malware scanning of uploads.
- Incident response process.
- A public log-read API. Writes of workspace-scoped operational audit (actions,
  events, HTTP envelopes, provider-call accounting, optional log file) are in
  scope under [ADR 012](adr/012-durable-operational-audit.md). There is no
  `GET /api/logs` until authentication exists.
- Application-level encryption of individual database fields. Deployment is
  responsible for encrypted disks/volumes, TLS where traffic leaves a host, database
  credentials and encrypted backup storage.
