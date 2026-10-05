"""HTTP wire models — camelCase on the wire, snake_case in Python."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Shared base for every request/response schema exposed under ``/api``."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )


class ErrorBody(ApiModel):
    code: str
    message: str
    correlation_id: str


class ErrorEnvelope(ApiModel):
    error: ErrorBody


class ReadyResponse(ApiModel):
    database: str
    migrations: str
    completion_provider: str
    embedding_provider: str
    hosted_egress: bool


class CvPasteRequest(ApiModel):
    text: str
    filename: str = "pasted.txt"


class SupportingDocumentResponse(ApiModel):
    id: str
    kind: str
    filename: str
    media_type: str
    byte_length: int
    page_count: int
    parsed_at: str
    created_at: str


class CvDocumentResponse(ApiModel):
    id: str
    filename: str
    page_count: int
    parsed_at: str


class ReanalysisInfo(ApiModel):
    job_ids: list[str]


class CvUploadResponse(CvDocumentResponse):
    reanalysis: ReanalysisInfo


class EvidenceResponse(ApiModel):
    span_id: str
    document_id: str
    page: int
    paragraph: str
    highlight: str


class RoleCounts(ApiModel):
    met: int
    partial: int
    missing: int


class JobErrorBody(ApiModel):
    code: str
    message: str


class JobTaskWire(ApiModel):
    key: str
    state: str
    units_done: int
    units_total: int | None
    model_calls_done: int = 0
    model_calls_total: int | None = None
    embedding_calls_done: int = 0
    embedding_calls_total: int | None = None


class JobProgressWire(ApiModel):
    """Tasks done of total, and times in whole seconds; remaining is an estimate."""

    tasks_done: int
    tasks_total: int
    fraction: float
    current_task: str | None
    elapsed_seconds: int | None
    remaining_seconds: int | None
    queue_position: int | None
    tasks: list[JobTaskWire]
    model_calls_done: int = 0
    model_calls_remaining: int = 0
    embedding_calls_done: int = 0
    embedding_calls_remaining: int = 0
    call_estimate_complete: bool = False


class AnalysisJobResponse(ApiModel):
    id: str
    kind: str
    state: str
    stage: str | None
    started_at: str | None
    finished_at: str | None
    error: JobErrorBody | None
    progress: JobProgressWire | None = None


class RoleResponse(ApiModel):
    id: str
    title: str
    company: str
    fit_score: int
    band_label: str
    counts: RoleCounts
    status: str
    updated_at: str
    fit_summary: str | None = None
    active_job: AnalysisJobResponse | None = None
    analysis_pipeline: str | None = None


class RoleCreateRequest(ApiModel):
    title: str
    company: str
    description: str


class RoleCreatedResponse(ApiModel):
    role: RoleResponse
    job_id: str


class ReanalyseResponse(ApiModel):
    job_id: str


class RelatednessSignalsWire(ApiModel):
    lexical: bool
    lexical_overlap: int
    embedding: bool
    embedding_similarity: float
    adjudication: bool | None
    related: bool


class RequirementWire(ApiModel):
    id: str
    role_id: str
    text: str
    type: str
    status: str
    evidence: EvidenceResponse | None
    signals: RelatednessSignalsWire | None = None


class BreakdownRowWire(ApiModel):
    id: str
    label: str
    value: float
    requirement_ids: list[str]


class GapItemWire(ApiModel):
    requirement_id: str
    requirement_text: str
    type: str
    status: str
    reason: str
    adjacent_evidence: EvidenceResponse | None
    score_delta: float
    action: str
    can_draft_bullet: bool


class GapPlanWire(ApiModel):
    role_id: str
    current_score: float
    items: list[GapItemWire]


class DraftProvenanceWire(ApiModel):
    provider: str
    model: str | None
    left_machine: bool
    generated_at: str
    grounded: bool
    fallback: str


class InterviewPackWire(ApiModel):
    role_id: str
    probes: list[dict[str, object]]
    lead_with: list[dict[str, object]]
    thin_areas: list[dict[str, object]]
    ask_them: list[dict[str, object]]
    provenance: DraftProvenanceWire


class BulletDraftWire(ApiModel):
    id: str
    version: int
    created_at: str
    requirement_id: str
    bullets: list[dict[str, object]]
    provenance: DraftProvenanceWire


class CoverLetterDraftWire(ApiModel):
    id: str
    version: int
    created_at: str
    role_id: str
    paragraphs: list[dict[str, object]]
    omitted_reason: str | None
    provenance: DraftProvenanceWire


class BulletRequest(ApiModel):
    requirement_id: str


class CoverLetterRequest(ApiModel):
    tone: str = "plain"
    include_gap_line: bool = False


class MessageCreateRequest(ApiModel):
    content: str
    client_request_id: str
    role_id: str | None = None


class CitationWire(ApiModel):
    id: str
    label: str
    evidence: EvidenceResponse | None = None


class ToolStepWire(ApiModel):
    name: str
    arguments: dict[str, str]
    found: int
    failed: bool


class ChatMessageWire(ApiModel):
    id: str
    conversation_id: str
    author: str
    content: str
    kind: str
    citations: list[CitationWire]
    model: str | None
    provider: str | None
    left_machine: bool
    created_at: str
    # The agent's tool calls for a fresh answer; not stored, so empty in history.
    tool_steps: list[ToolStepWire] = Field(default_factory=list)


class RankedRoleWire(ApiModel):
    role: RoleResponse
    rank: int
    tied: bool
    because: list[str]


class ComparisonWire(ApiModel):
    a: RoleResponse
    b: RoleResponse
    shared: list[dict[str, object]]
    only_in_a: list[RequirementWire]
    only_in_b: list[RequirementWire]
    differentiator: str


class ProviderSupportsModel(ApiModel):
    completion: bool
    embedding: bool


class ProviderCapabilitiesModel(ApiModel):
    structured_output: bool
    context_window: int | None
    max_output_tokens: int | None
    embedding_dimensions: int | None


class ProviderResponse(ApiModel):
    id: str
    name: str
    kind: str
    models: list[str]
    available: bool
    unavailable_reason: str | None
    supports: ProviderSupportsModel
    capabilities: ProviderCapabilitiesModel


class ProviderChoiceResponse(ApiModel):
    answer_provider_id: str
    answer_model: str
    index_provider_id: str
    index_model: str


class DimensionScoreWire(ApiModel):
    score: int
    rationale: str


class VerdictEvidenceWire(ApiModel):
    chunk_id: str
    document_id: str
    quote: str


class VerdictWire(ApiModel):
    requirement_id: str
    quote: str
    statement: str
    must_have: bool
    verdict: str
    requirement_score: float | None
    match: DimensionScoreWire
    seniority: DimensionScoreWire | None
    experience: DimensionScoreWire | None
    unmet_conditions: list[str]
    contradiction: bool
    adjustments: list[str]
    evidence: list[VerdictEvidenceWire]
    provider: str
    model: str


class KeywordCoverageWire(ApiModel):
    exact: list[str]
    alias: list[str]
    missing: list[str]


class V2GapWire(ApiModel):
    requirement_id: str
    dimension: str
    current: float
    delta: float


class RoleVerdictsWire(ApiModel):
    role_id: str
    analysis_id: str
    fit_score: float
    band: str
    gated: bool
    rubric_version: str
    left_machine: bool
    verdicts: list[VerdictWire]
    keyword_coverage: KeywordCoverageWire
    gap_plan: list[V2GapWire]


class TraceHitWire(ApiModel):
    chunk_id: str
    fused_score: float
    dense_rank: int | None
    lexical_rank: int | None
    exact_rank: int | None


class TraceRoundWire(ApiModel):
    round: int
    query_text: str
    hits: list[TraceHitWire]


class RetrievalTraceWire(ApiModel):
    requirement_id: str
    rounds: list[TraceRoundWire]


class ProviderChoiceUpdateRequest(ApiModel):
    answer_provider_id: str
    answer_model: str
    index_provider_id: str
    index_model: str
    acknowledged_egress: bool
