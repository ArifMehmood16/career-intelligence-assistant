# Threat model

Everything crossing a boundary is untrusted: uploaded files, document text, user
questions, retrieved spans, model output and generated drafts.

## Trust boundaries

| Boundary | Untrusted input | Primary controls |
|---|---|---|
| Browser to API | Uploads, questions | Type sniffing, size and page caps, schema validation, safe errors |
| File to parser | PDF/DOCX structure | Bounded parsing, no macro or embedded-object execution, resource limits |
| Document text to prompt | CV and job-description content | Delimited and labelled untrusted; instructions in the text are data |
| Model to application | Extraction JSON, answer text | Schema validation, span verification, drop unresolvable output |
| Generated draft to browser | Model-phrased or template prose | Groundedness validator against cited spans; template fallback; provenance on every artefact |
| Application to browser | Excerpts and drafts | Escaped text rendering, no raw HTML |
| Application to model provider | Prompts built from CV and job-description text | Egress gate; provider allowlist of hermetic, Ollama, OpenAI and Anthropic; per-provider timeout and breaker; keys never logged or returned |
| Application to database | Queries; stored personal data | Parameterised access, workspace scoping, hard delete of documents and derived records |
| Application to logs | Everything | Redaction; no document text, prompts, embeddings, draft bodies or credentials |

## Named risks

| Risk | Control | Residual |
|---|---|---|
| Prompt injection in a job description | Untrusted delimiting, schema validation, span verification, regression test | A crafted document may still degrade extraction quality |
| Fabricated experience in an answer | Every claim requires a resolvable span | Extraction may mis-attribute a real span |
| Fabricated experience in a generated draft | Groundedness validator; regenerate once; hermetic template fallback; refusal when evidence is thin | Validator false positives become template fallbacks |
| Malicious PDF or DOCX | Bounded parsing, no embedded execution, size and page caps | Parser library vulnerabilities; mitigated by dependency scanning |
| Resource exhaustion | Caps on size, pages, characters, context and output | A slow parse can still occupy a worker; timeouts TBD |
| Personal data retention | Hard delete of documents, spans, chunks, embeddings, claims, mappings and generated drafts; configurable retention window | Database backups retain data until they rotate |
| Cross-workspace leakage | Workspace scoping on every query, integration test | No authentication yet — see below |
| CV text reaching a third party | Hermetic and local providers by default; hosted adapters unreachable unless egress is enabled and a key is present; the selection is shown to the user and recorded on every artefact | A user who enables a hosted provider accepts that vendor's retention terms; the product makes that visible, it cannot make it safe |
| Leaked API key | Keys read at construction, never logged, never returned by any route including masked; redaction test | A compromised host still exposes the environment |
| Hosted provider outage or rate limit | Bounded retry on 429 and 5xx, timeout, breaker, safe error; no silent fallback to a different model | A degraded answer is still possible if fallback is explicitly enabled |

## Out of scope for this build

Stated as a decision, not an oversight:

- Authentication, authorization and multi-tenancy. Required before any untrusted user
  touches the system.
- Network hardening, WAF, rate limiting at a gateway.
- Malware scanning of uploads.
- Audit logging and incident response process.
