export interface CvDocument {
  id: string;
  filename: string;
  pageCount: number;
  parsedAt: string;
}

export interface Evidence {
  spanId: string;
  documentId: string;
  page: number;
  paragraph: string;
  /** Must be an exact substring of `paragraph`. */
  highlight: string;
}

export type RoleStatus = "analysing" | "ready" | "failed";

export interface Role {
  id: string;
  title: string;
  company: string;
  fitScore: number;
  bandLabel: string;
  counts: { met: number; partial: number; missing: number };
  status: RoleStatus;
  updatedAt: string;
}

export type RequirementType = "must" | "desirable";
export type RequirementStatus = "met" | "partial" | "missing";

export interface Requirement {
  id: string;
  roleId: string;
  text: string;
  type: RequirementType;
  status: RequirementStatus;
  evidence: Evidence | null;
}

export interface BreakdownRow {
  id: "must" | "desirable" | "recency";
  label: string;
  value: number;
  requirementIds: string[];
}

export interface Citation {
  id: string;
  label: string;
  evidence: Evidence;
}

export interface ChatMessage {
  id: string;
  conversationId?: string;
  author: "user" | "assistant";
  content: string;
  kind: "question" | "answer" | "insufficient";
  citations: Citation[];
  model: string | null;
  provider: string | null;
  leftMachine: boolean;
  createdAt?: string;
}

export interface Provider {
  id: string;
  name: string;
  kind: "local" | "hosted";
  models: string[];
  available: boolean;
  unavailableReason: string | null;
}

export interface ProviderChoice {
  answerProviderId: string;
  answerModel: string;
  indexProviderId: string;
  indexModel: string;
}

export type AnalysisJobKind = "role_analysis" | "cv_parse" | "reindex";
export type AnalysisJobState = "queued" | "running" | "succeeded" | "failed";
export type AnalysisJobStage =
  | "parsing"
  | "extracting_requirements"
  | "extracting_claims"
  | "mapping"
  | "scoring";

export interface AnalysisJobError {
  code: string;
  message: string;
}

export interface AnalysisJob {
  id: string;
  kind: AnalysisJobKind;
  state: AnalysisJobState;
  stage: AnalysisJobStage | null;
  startedAt: string | null;
  finishedAt: string | null;
  error: AnalysisJobError | null;
}

export type GapItemReason =
  | "no_related_claim"
  | "adjacent_claim_only"
  | "evidence_too_old"
  | "evidence_thin";

export type GapItemAction = "evidence_it" | "learn_it" | "accept_it";

export interface GapItem {
  requirementId: string;
  requirementText: string;
  type: RequirementType;
  status: "partial" | "missing";
  reason: GapItemReason;
  adjacentEvidence: Evidence | null;
  scoreDelta: number;
  action: GapItemAction;
  canDraftBullet: boolean;
}

export interface GapPlan {
  roleId: string;
  currentScore: number;
  items: GapItem[];
}

export interface DraftProvenance {
  provider: string;
  model: string | null;
  leftMachine: boolean;
  generatedAt: string;
  grounded: boolean;
  fallback: "none" | "regenerated" | "template";
}

export interface InterviewProbe {
  requirementId: string;
  question: string;
  status: RequirementStatus;
}

export interface InterviewLeadWith {
  requirementId: string;
  evidence: Evidence;
  note: string;
}

export interface InterviewThinArea {
  requirementId: string;
  requirementText: string;
  nearest: Evidence | null;
}

export interface InterviewAskThem {
  question: string;
  requirementId: string | null;
}

export interface InterviewPack {
  roleId: string;
  probes: InterviewProbe[];
  leadWith: InterviewLeadWith[];
  thinAreas: InterviewThinArea[];
  askThem: InterviewAskThem[];
  provenance: DraftProvenance;
}

export interface BulletLine {
  text: string;
  spanIds: string[];
  evidence: Evidence[];
}

export interface BulletDraft {
  id: string;
  version: number;
  createdAt: string;
  requirementId: string;
  bullets: BulletLine[];
  provenance: DraftProvenance;
}

export interface CoverLetterParagraph {
  text: string;
  requirementIds: string[];
  spanIds: string[];
}

export interface CoverLetterDraft {
  id: string;
  version: number;
  createdAt: string;
  roleId: string;
  paragraphs: CoverLetterParagraph[];
  omittedReason: string | null;
  provenance: DraftProvenance;
}

export interface RankedRole {
  role: Role;
  rank: number;
  tied: boolean;
  because: string[];
}

export interface ComparisonSharedRequirement {
  text: string;
  aStatus: RequirementStatus;
  bStatus: RequirementStatus;
}

export interface Comparison {
  a: Role;
  b: Role;
  shared: ComparisonSharedRequirement[];
  onlyInA: Requirement[];
  onlyInB: Requirement[];
  differentiator: string;
}

export interface SupportingDocument {
  id: string;
  kind: "cover_letter";
  filename: string;
  mediaType: string;
  byteLength: number;
  pageCount: number;
  parsedAt: string;
  createdAt: string;
}
