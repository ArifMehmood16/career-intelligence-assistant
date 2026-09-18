"""HTTP wire models — camelCase on the wire, snake_case in Python."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
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


class RoleResponse(ApiModel):
    id: str
    title: str
    company: str
    fit_score: int
    band_label: str
    counts: RoleCounts
    status: str
    updated_at: str


class RoleCreateRequest(ApiModel):
    title: str
    company: str
    description: str


class RoleCreatedResponse(ApiModel):
    role: RoleResponse
    job_id: str


class ReanalyseResponse(ApiModel):
    job_id: str


class AnalysisJobResponse(ApiModel):
    id: str
    kind: str
    state: str
    stage: str | None
    started_at: str | None
    finished_at: str | None
    error: str | None


class RequirementWire(ApiModel):
    id: str
    role_id: str
    text: str
    type: str
    status: str
    evidence: EvidenceResponse | None


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


class ProviderChoiceUpdateRequest(ApiModel):
    answer_provider_id: str
    answer_model: str
    index_provider_id: str
    index_model: str
    acknowledged_egress: bool
