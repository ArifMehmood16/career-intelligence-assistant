# API contract

The single agreement between the FastAPI backend and the TanStack Start frontend.
Both sides are written against this file, and it is the first thing to change when
the shape changes.

- Backend routes live under `/api`.
- The browser always calls the **same origin**. The Start server proxies `/api/**` to
  the backend, so there is no CORS configuration and no API URL in browser code. See
  [frontend-integration.md](frontend-integration.md).
- All field names are `camelCase` on the wire. Python models use `snake_case`
  internally with an alias generator; the wire format matches the TypeScript types in
  `frontend/src/types/index.ts` exactly.
- Every route has an explicit Pydantic response model. No bare `dict`.
- Times are RFC 3339 UTC strings.

---

## Workspace identity

This is a personal tool intended for local single-user use, not a live multi-user
deployment. There is no authentication in this build. The server resolves a workspace
from a `workspace` cookie, issuing one on first request (`HttpOnly`, `SameSite=Lax`).
Every query is scoped by workspace id, and an integration test proves one workspace
cannot read another's rows — so the scoping is real even though identity is a local
cookie, not a login.

PostgreSQL is the source of truth behind every route. Original document bytes, parsed
spans, roles, generated artefacts, questions, final answers, citations and workspace
provider choices are durable; the production API never falls back to process memory,
SQLite or a filesystem upload directory. Hermetic `create_app()` tests may still use
in-memory stores. Which use case, provider resolver and SQL adapter each route uses
is listed in [production-wiring.md](production-wiring.md).

---

## Error envelope

Every non-2xx response:

```json
{ "error": { "code": "role_not_found", "message": "No role with that id.", "correlationId": "01J..." } }
```

- `code` is a stable machine string; the frontend switches on it, never on `message`.
- `message` is safe to display. No stack traces, prompts, provider payloads or file
  paths ever appear in it.
- `correlationId` is on every request and every log line for it.

| Code | Status | Meaning |
|---|---|---|
| `validation_failed` | 422 | Request body failed schema validation |
| `cv_required` | 409 | The action needs a parsed CV and none exists |
| `document_too_large` | 413 | Over `MAX_UPLOAD_BYTES`, rejected before buffering |
| `document_unsupported` | 415 | Not PDF, DOCX or plain text |
| `document_unreadable` | 422 | Encrypted, scanned, or no extractable text |
| `role_not_found` / `cv_not_found` / `cover_letter_not_found` / `span_not_found` | 404 | Unknown id in this workspace |
| `analysis_incomplete` | 409 | Output requested before the analysis job finished |
| `insufficient_evidence` | 200 | Not an error — an answer kind. Listed here so it is not mistaken for one |
| `insufficient_cited_claims` | 409 | Bullet requested for a requirement with no cited CV claim |
| `insufficient_matched_requirements` | 409 | Cover letter refused because fewer than two must-haves are met |
| `provider_unavailable` | 409 | Selected provider is not usable; `message` gives the reason |
| `egress_not_permitted` | 403 | Hosted provider selected while the gate is closed |
| `egress_not_acknowledged` | 409 | Hosted selection without `acknowledgedEgress` |
| `provider_failed` | 502 | Upstream provider error after retries |
| `rate_limited` | 429 | Local request limit |
| `internal_error` | 500 | Anything else, logged with the correlation id |
| `misconfigured` | 500 | Start proxy only — `API_BASE_URL` missing or invalid (`correlationId` may be `proxy`) |
| `csrf_rejected` | 403 | Start proxy only — non-GET without a matching same-origin `Origin` |

---

## Health

| Route | Returns |
|---|---|
| `GET /api/health` | `{ "status": "ok" }` — liveness, no dependencies touched |
| `GET /api/ready` | `{ "database": "ok", "migrations": "current", "completionProvider": "hermetic", "embeddingProvider": "hermetic", "hostedEgress": false }` |

---

## CV

```http
GET    /api/cv           → CvDocument | null
POST   /api/cv           → 201 CvDocument
DELETE /api/cv           → 204
```

`POST /api/cv` accepts either `multipart/form-data` with a `file` part, or
`application/json` with `{ "text": "...", "filename": "pasted.txt" }`.

```ts
CvDocument { id, filename, pageCount: number, parsedAt: string }
```

Unchanged from the existing frontend type. Uploading replaces the current CV and
enqueues re-analysis of every role; the response carries `reanalysis: { jobIds: [] }`
as an additive field the current UI may ignore.

On successful admission and parsing, PostgreSQL stores the original bounded bytes,
sniffed media type, SHA-256, normalised text and spans in one transaction. A rejected
or unreadable upload is not retained. Replacement does not expose a half-written CV:
the new document becomes active and dependent results are invalidated atomically.

---

## Supporting cover letters

```http
GET    /api/cover-letters       → SupportingDocument[]
POST   /api/cover-letters       → 201 SupportingDocument
DELETE /api/cover-letters/{id}  → 204
GET    /api/documents/{id}/download → original bytes
```

`POST` accepts the same multipart or pasted-text shapes as the CV route. The original
bounded bytes, metadata, normalised text and spans are stored in PostgreSQL.

```ts
SupportingDocument {
  id; kind: "cover_letter"; filename; mediaType; byteLength: number;
  pageCount: number; parsedAt: string; createdAt: string;
}
```

Uploaded cover letters are supporting documents: open questions may retrieve and cite
their spans, but requirement extraction, candidate claims, mappings and scores must
ignore them. This prevents self-authored or generated prose from becoming evidence of
experience. The document download route is workspace-scoped and uses a safe
`Content-Disposition`; it never exposes a database path or storage implementation.

---

## Roles

```http
GET    /api/roles                    → Role[]
POST   /api/roles                    → 202 RoleCreated
GET    /api/roles/{id}               → Role
DELETE /api/roles/{id}               → 204
POST   /api/roles/{id}/reanalyse     → 202 { jobId }
```

```ts
Role {
  id; title; company;
  fitScore: number;            // 0 when not yet scored
  bandLabel: string;           // "Strong match" | "Partial match" | "Limited match" | "Not scored yet"
  counts: { met: number; partial: number; missing: number };
  status: "analysing" | "ready" | "failed";   // additive
  updatedAt: string;                          // additive
  fitSummary: string | null;                  // additive; GET /roles/{id} once ready, otherwise null
}

RoleCreated { role: Role; jobId: string }
```

`POST /api/roles` body: `{ title, company, description }` as JSON, or multipart with
`file` plus `title` and `company`. It returns immediately with `status: "analysing"`;
the analysis runs as a job. The job description is stored as a `job_description`
document with original bytes/text and spans before analysis is queued.

---

## Analysis jobs

Extraction against a local or hosted model takes seconds to minutes. It is a job, and
the UI shows it as one.

```http
GET /api/jobs/{id} → AnalysisJob
```

```ts
AnalysisJob {
  id;
  kind: "role_analysis" | "cv_parse" | "reindex";
  state: "queued" | "running" | "succeeded" | "failed";
  stage: "parsing" | "extracting_requirements" | "extracting_claims" | "mapping" | "scoring" | null;
  startedAt: string | null;
  finishedAt: string | null;
  error: { code: string; message: string } | null;
}
```

The frontend polls this with react-query while `state` is `queued` or `running`, at a
fixed interval, and stops on a terminal state. A failed job leaves the role at
`status: "failed"` with the reason, and `POST /reanalyse` is the retry.

---

## Role analysis output

```http
GET /api/roles/{id}/requirements   → Requirement[]
GET /api/roles/{id}/breakdown      → BreakdownRow[]
GET /api/roles/{id}/gap-plan       → GapPlan
GET /api/roles/{id}/interview-pack → InterviewPack
```

All four return `409 analysis_incomplete` until the role's analysis has succeeded.

```ts
Requirement {
  id; roleId; text;
  type: "must" | "desirable";
  status: "met" | "partial" | "missing";
  evidence: Evidence | null;
  signals: RelatednessSignals | null;  // which of lexical / embedding / adjudication fired
}

RelatednessSignals {
  lexical: boolean;
  lexicalOverlap: number;
  embedding: boolean;
  embeddingSimilarity: number;
  adjudication: boolean | null;  // null = not asked (agreement or hermetic)
  related: boolean;
}

Evidence { spanId; documentId; page: number; paragraph: string; highlight: string }
// highlight is always an exact substring of paragraph — enforced server-side.

BreakdownRow { id: "must" | "desirable" | "recency"; label; value: number; requirementIds: string[] }
```

`Requirement` and `Evidence` are unchanged from the existing frontend types. Evidence
is returned inline so the requirement table renders in one request; `GET /api/spans/{id}`
exists for citation chips that arrive without it.

### Gap plan

```ts
GapPlan {
  roleId;
  currentScore: number;
  items: GapItem[];          // ordered by scoreDelta descending
}

GapItem {
  requirementId; requirementText;
  type: "must" | "desirable";
  status: "partial" | "missing";
  reason: "no_related_claim" | "adjacent_claim_only" | "evidence_too_old" | "evidence_thin";
  adjacentEvidence: Evidence | null;
  scoreDelta: number;        // points gained if this one requirement became met
  action: "evidence_it" | "learn_it" | "accept_it";
  canDraftBullet: boolean;   // true when adjacentEvidence exists
}
```

`scoreDelta` is computed by re-running the rubric with that requirement at met. No
model is involved in this route at all.

### Interview pack

```ts
InterviewPack {
  roleId;
  probes:    { requirementId; question: string; status: RequirementStatus }[];
  leadWith:  { requirementId; evidence: Evidence; note: string }[];
  thinAreas: { requirementId; requirementText; nearest: Evidence | null }[];
  askThem:   { question: string; requirementId: string | null }[];
  provenance: DraftProvenance;
}
```

Probe questions, lead-with notes and ask-them lines are phrased through the same
generation pipeline as drafts. Citations on `leadWith` and `thinAreas.nearest` are
dropped unless the span still resolves in this workspace.

---

## Generated drafts

```http
POST /api/roles/{id}/bullets       → BulletDraft
POST /api/roles/{id}/cover-letter  → CoverLetterDraft
GET  /api/roles/{id}/cover-letters → CoverLetterDraft[]
GET  /api/roles/{id}/export/{artefact}.md → text/markdown
```

`artefact` is one of `gap-plan`, `interview-pack`, `cover-letter`, `bullets`.

`GET /api/roles/{id}/export/cover-letter.md` and `.../bullets.md` accept an optional
`version` query matching the immutable draft `version` shown on screen. Omitted
`version` exports the latest draft only. An unknown version is `422 validation_failed`.
Gap-plan and interview-pack ignore `version`. The Letter tab always sends the selected
cover-letter version so the file matches the paragraphs on screen. The same query is
the rule for bullet versions.

```ts
DraftProvenance {
  provider: string;          // provider id that produced it
  model: string | null;      // null for the hermetic template path
  leftMachine: boolean;      // true when a hosted provider was used
  generatedAt: string;
  grounded: boolean;         // passed the validator
  fallback: "none" | "regenerated" | "template";
}

BulletDraft {
  id; version: number; createdAt: string;
  requirementId;
  bullets: { text: string; spanIds: string[]; evidence: Evidence[] }[];
  provenance: DraftProvenance;
}

CoverLetterDraft {
  id; version: number; createdAt: string;
  roleId;
  paragraphs: { text: string; requirementIds: string[]; spanIds: string[] }[];
  omittedReason: string | null;   // set when a paragraph was dropped by the validator
  provenance: DraftProvenance;
}
```

`POST /api/roles/{id}/bullets` body: `{ requirementId }`.
`POST /api/roles/{id}/cover-letter` body: `{ tone: "plain" | "warm", includeGapLine: boolean }`.

The cover letter returns `409` with code `insufficient_matched_requirements` when
fewer than two must-haves are met, with a message that points at the gap plan.

A bullet returns `409` with code `insufficient_cited_claims` when the requirement has
no cited CV claim. The instruction is not stored as a grounded draft.

**Every bullet, interview-pack and cover-letter route runs `generate_draft` before
responding:** phrase through the selected completion port, validate groundedness
against cited span text, regenerate once, then fall back to the deterministic
template. Citations are resolved against stored workspace spans. Cover-letter `tone`
and `includeGapLine` change the template that enters that pipeline. Template-fallback
drafts persist the validator's real verdict (`provenance.grounded` may be `false`);
the SQL adapter never rewrites `FAIL` to `PASS`. Model output that fails twice is not
stored as a passing draft.

Every returned draft is stored in PostgreSQL as an immutable version linked to the
role-analysis version and its cited spans. Regeneration creates another version; it
does not overwrite provenance. Uploaded supporting cover letters are separate
documents and never appear in this generated-draft history.

---

## Cross-role

```http
GET /api/ranking              → RankedRole[]
GET /api/compare?a={id}&b={id} → Comparison
```

```ts
RankedRole { role: Role; rank: number; tied: boolean; because: string[] }   // because = requirement texts that decided the position

Comparison {
  a: Role; b: Role;
  shared:   { text: string; aStatus: RequirementStatus; bStatus: RequirementStatus }[];
  onlyInA:  Requirement[];
  onlyInB:  Requirement[];
  differentiator: string;
}
```

Both are derived from stored scores, so they cannot disagree with a role page.

`rank` is standard competition ranking (1224): equal fit scores share a rank and the
next distinct score skips. `tied` is true for every row in a shared-score group.

`differentiator` names the largest mapping disagreement — a shared requirement whose
status differs, otherwise a unique requirement that changes the comparison — not the
first shared requirement alphabetically. When nothing distinguishes the two roles it
is `"No clear differentiator"`.

---

## Spans

```http
GET /api/spans/{id} → Evidence
```

The citation chip contract. One workspace-scoped resolver opens every citation
emitted by Ask or generated artefacts: the active CV, uploaded supporting cover
letters, and job-description spans in this workspace. A span id that does not
resolve, or that belongs to another workspace, is a `404`, and the frontend treats
that as a bug worth surfacing rather than an empty panel — an unresolvable citation
is the one failure this product must never hide.

---

## Ask

```http
GET    /api/messages  → ChatMessage[]
POST   /api/messages  → text/event-stream (or application/json)
DELETE /api/messages  → 204
```

```ts
ChatMessage {
  id; conversationId; author: "user" | "assistant"; content;
  kind: "question" | "answer" | "insufficient";
  citations: Citation[];
  model: string | null;
  provider: string | null;
  leftMachine: boolean;
  createdAt: string;
}

Citation { id; label; evidence: Evidence }
```

`frontend/src/types/index.ts` is the canonical TypeScript statement of this contract,
including persisted-message fields and exact span ids.

`POST /api/messages` body:
`{ content, roleId?: string, clientRequestId: string }`. `clientRequestId` is unique
within the workspace and makes browser retries idempotent. With
`Accept: text/event-stream` it streams; with `Accept: application/json` it returns the
finished `ChatMessage`. Both paths run the same use case — streaming is a transport,
not a second implementation.

Event sequence:

```text
event: meta      data: { "questionId": "...", "messageId": "...", "intent": "gaps", "provider": "ollama", "model": "...", "leftMachine": false }
event: token     data: { "text": "..." }            (repeated)
event: citations data: { "citations": [ ... ] }     (after the text, once)
event: done      data: { "kind": "answer" | "insufficient" }
event: error     data: { "code": "provider_failed", "message": "..." }
```

Citations arrive **after** the text because they are validated against stored spans
once the answer is complete. An answer whose citations do not all resolve is reduced
to `kind: "insufficient"` before `done` is sent.

Open questions retrieve workspace-scoped spans from the active CV and uploaded
supporting cover letters. When `roleId` is set they may also retrieve that role's job
description, never another role's. Cover-letter text cannot become a claim, mapping
or score input. Every citation, including supporting-letter and JD spans, opens
through `GET /api/spans/{id}`.

The user question is committed before processing. Exactly one final validated answer
or insufficient-evidence result, its citations and provider provenance are committed
after validation. Token events, incomplete text and raw provider payloads are never
stored as answer history. On failure the question keeps only a safe failure code.
`GET /api/messages` reads the persisted history in creation order, including after an
API restart; repeating a `clientRequestId` returns the existing final result rather
than creating duplicate rows. `DELETE /api/messages` hard-deletes the conversation,
questions, answers and citations.

---

## Providers and settings

```http
GET /api/providers          → Provider[]
GET /api/settings/providers → ProviderChoice
PUT /api/settings/providers → ProviderChoice
```

```ts
Provider {
  id; name;
  kind: "local" | "hosted";
  models: string[];
  available: boolean;
  unavailableReason: string | null;
  supports: { completion: boolean; embedding: boolean };   // additive
  capabilities: {                                          // additive
    structuredOutput: boolean;
    contextWindow: number | null;
    maxOutputTokens: number | null;
    embeddingDimensions: number | null;
  };
}

ProviderChoice { answerProviderId; answerModel; indexProviderId; indexModel }
```

`PUT` body is a `ProviderChoice` plus `acknowledgedEgress: boolean`.

- `403 egress_not_permitted` — hosted provider while `ALLOW_HOSTED_PROVIDERS` is false
  or no key is configured. The same code is returned if the gate closes after a
  hosted choice was stored: Ask and generation refuse and make no network attempt.
- `409 egress_not_acknowledged` — hosted provider without `acknowledgedEgress: true`.
  The confirmation dialog is enforced server-side, not only in the UI.
- Changing `indexProviderId` or `indexModel` invalidates embeddings and returns
  `reindex: { jobId }` as an additive field.

The persisted `answerProviderId` / `answerModel` is what Ask, requirement/claim
extraction and bullet phrasing actually call. `indexProviderId` stays independent.
Answer and draft `provider` / `model` / `leftMachine` come from that completion
port, not a hard-coded hermetic tag. Call accounting records those identifiers and
token counts only — never question, CV or prompt text.

**No key, in any form, is ever accepted or returned by any route.** Not plaintext, not
masked, not a boolean per key beyond `available`. A redaction test asserts that the
string of a configured key appears in no response body and no log line.

---

## Type parity

`frontend/src/types/index.ts` is the canonical TypeScript statement of everything
above. A contract test asserts the generated OpenAPI schema and the TypeScript types
agree on every shared model. When they disagree, this file is what they are both
wrong about.
