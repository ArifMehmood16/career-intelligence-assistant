# Features and evidence contract

Current product behavior, 2026-10-06. [Architecture](architecture.md),
[API contract](api-contract.md), [delivery plan](../PLAN.md) and
[limitations](limitations.md) contain implementation details and open verification.

**The model reads and judges. The server verifies. The domain computes fit.**

## Workspace and documents

Upload one CV, optional supporting cover letters and multiple job descriptions.
Plain text, text PDF and DOCX are accepted after content inspection and configured
byte/page/character caps. Binary parsing uses bounded spawned CPU workers; plain
text stays lightweight. Raw uploads and parsed text remain in PostgreSQL. Scanned
images/OCR are outside scope. Replacing a CV invalidates affected analyses and queues
reanalysis. Deletes remove original bytes and derived data with their citations.

Supporting letters are narrative context for questions/drafts and remain excluded
from fit scoring. Aspirations and generated drafts never count as evidence.
The concrete-experience policy in [ADR 011](adr/011-evidence-assessment-contract.md)
distinguishes experience from aspiration and requires duplicate evidence to be
deduplicated. Scoring uploaded letter experience remains future work in BACKLOG.
A role is queued/analysing before the model finishes. Loading, failed, incomplete,
unscored and a valid zero remain distinct states. Progress shows completed stages,
physical model/embedding attempts, estimated calls remaining and estimated time.
Undiscovered stages and retries make the count an estimate; no timing history means
unknown time. Parallel reads retain independent start/finish state.

## Fit and evidence

A fitting document is read in one structured response: server-numbered line ranges,
chunk kinds and details, technology terms, atomic job requirements and inferred
technology relationships. The server requires complete line coverage, reconstructs
text from stored lines, and checks every quoted/surface field verbatim. Bad coverage
or incomplete judging fails analysis rather than producing a low score.
Benefits, salary and application logistics are contextual chunks; they do not
become scored requirements.

CV chunks are embedded in one batch and indexed with full-text/graph evidence.
Requirements share a query-embedding wave and hybrid retrieval. Judge batches are
sized for the selected model's input and output capacity, then run independently
within its concurrency budget. A bounded corrective retrieval wave rejudges only
requirements that gained new candidates.

Fit shows each requirement's met/partial/missing verdict, up to three 0–4 dimension
judgments (match, seniority, experience), their rationale, validated verbatim evidence,
server adjustments and an optional retrieval trace. Rationales and technology
relationships are interpretation/general knowledge, never candidate evidence.
Nonzero match judgments need a resolvable retrieved quote. Years are derived from
stored role/date facts with overlapping experience deduplicated. Named-tool skills
may support an appropriately narrow tool requirement; listed skills cannot prove
stated delivery depth, leadership or tenure.

The Requirements section filters by Met/Partial/Missing and the stored requirement
score together. Scores are displayed as whole percentages with four ranges and a
separate Not scored choice. The shown/total count and Clear filters make the subset
explicit. Filtering preserves the publication's overall fit, ordering, evidence
and retrieval actions; a new analysis resets list filters.

Each requirement shows green up-arrow earned points and red down-arrow unearned
points toward the 100-point overall fit. The reference is full credit, not a change
from an earlier analysis. Shares use the original publication's weights and
contributions, including recency, and remain fixed through filtering. Missing earns
zero; full credit has zero shortfall; unavailable historical attribution is labelled.
Displayed points round to one decimal, so displayed totals may differ slightly.

The judge reads overall non-contact CV context and the job description alongside
retrieved candidates. Seniority considers stated role scope/ownership rather than
assuming a title proves every skill. Experience uses numeric years when specified,
otherwise a verified verbatim qualitative expectation such as production delivery.
The latter has depth/scope anchors, not fabricated tenure. Asked/Supported labels
compare the expectation and the judge's rationale. Context is untrusted and cannot
supply extra citation candidates. Context participates in request budgets/cache keys;
new extraction/judge versions require reanalysis for new judgments.

Domain scoring applies configured must-have weights, dimension weights, recency and
band/gate rules from `config/scoring_rubric.toml`. The model never supplies the fit
score. Incomplete analyses publish no score/band/ranking position. Keyword coverage
separately identifies exact, alias-only and missing technology names. It never
increases the evidence score by itself.

## Gaps, CV bullets, preparation and letters

Gaps are ordered by the published domain-calculated lift for match, seniority,
experience or evidence recency. Judge dimensions show their 0–4 current level;
recency shows the current percentage weight applied to older or undated evidence.
They show what evidence needs strengthening. Export
reads the same stored analysis. No separate model call recalculates the gap plan.

CV bullet drafts use evidence already present in the candidate's current CV. A
request selects a requirement with supporting evidence. Draft text/citations pass
schema and groundedness validation; unsupported content is refused or replaced by
the deterministic grounded template under the existing generation policy. Drafts
never raise fit. The source CV is not edited.

Preparation names likely probes, evidence to lead with, thin areas and interviewer
questions. Cover letters combine matched evidence with tone/gap-line preferences,
retain source citations and version history, and refuse when there is insufficient
matched must-have evidence. Exports preserve source references and provenance.
Prepare, Letter and shared API summaries project current chunks/verdicts; no legacy
requirements/claims tables or alternate score algorithm are involved.

## Ranking, comparison and Ask

Rank ready, publishable roles by the current stored score, with deciding requirements
and counts. Compare two roles using the same validated requirement/evidence views.
Incomplete roles stay out of rankings. There is no overall "should I apply" verdict.

Ask answers questions with resolving citations from stored documents/results. Models
with tool calling may use the bounded read-only agent loop and shared registry;
other models use the existing citation-validated question route. Tool results remain
untrusted, workspace scoped and bounded. Agent citations require a returned chunk
and a verbatim quote, with one repair then refusal. Tool steps are visible in the
current session and not persisted. The optional stdio MCP server exposes the same
registry; its client decides where returned text goes.

Ask displays processing as soon as a question is sent, receiving while the answer
streams, and updating while saved history reloads. Stop is available before the
first event; completion, failure and stop clear status. Late events from a stopped
request cannot clear or overwrite a newer request's processing state.

The shared Ask/MCP search and skill-experience tools still need full hybrid-search/
knowledge-graph wiring. This remaining retrieval limitation is explicit in BACKLOG.

## Provider and data controls

Ollama is the local default. OpenAI and Anthropic use independent provider modules;
completion and embeddings may use different providers. Profiles carry per-model
context/output, schema support, concurrency and batching policy, avoiding one small
model's limit constraining all models. API keys remain server-only. Hosted calls
require enabled egress, a configured key and the existing user acknowledgement;
construction and call-time gates apply. Every result/draft retains provider/model
and whether content left the machine.

Thread workers overlap I/O; CPU processes parse binary documents. Shared local model
slots and hosted rate headers bound calls across simultaneous jobs. Cache checks
avoid repeated CV reading, embedding probes and identical judgments. No quality or
latency claim follows from those structural changes; measurements belong only in
[evaluation.md](evaluation.md).

## Deliberately not features

Employer screening, multiple CVs per workspace, OCR, authentication/multi-tenancy,
public shared deployment, job-board ingestion, auto-apply, email integration, editing
the original CV, model-emitted fit scores and distributed queues are outside this
build. The product remains a private candidate tool.
