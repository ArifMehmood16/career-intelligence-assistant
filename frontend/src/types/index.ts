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
  /** Present on GET /roles/{id} once analysis is ready; omitted from list rows. */
  fitSummary?: string | null;
  /** The queued or running analysis, with its progress. */
  activeJob?: AnalysisJob | null;
  /** The pipeline that produced the published analysis; null before one exists. */
  analysisPipeline?: AnalysisPipeline | null;
}

export type AnalysisPipeline = "v2";

export type RequirementType = "must" | "desirable";
export type RequirementStatus = "met" | "partial" | "missing";

export interface RelatednessSignals {
  lexical: boolean;
  lexicalOverlap: number;
  embedding: boolean;
  embeddingSimilarity: number;
  adjudication: boolean | null;
  related: boolean;
}

export interface Requirement {
  id: string;
  roleId: string;
  text: string;
  type: RequirementType;
  status: RequirementStatus;
  evidence: Evidence | null;
  signals?: RelatednessSignals | null | undefined;
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
  /** The agent's tool calls for a fresh answer. Not stored, so absent in history. */
  toolSteps?: ToolStep[];
}

export interface ToolStep {
  name: string;
  arguments: Record<string, string>;
  found: number;
  failed: boolean;
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

export type AnalysisTaskKey =
  | "prepare"
  | "read_advert"
  | "read_cv"
  | "search"
  | "judge"
  | "recheck"
  | "score";

export type AnalysisTaskState =
  "pending" | "running" | "done" | "skipped" | "failed";

export interface AnalysisTask {
  key: AnalysisTaskKey;
  state: AnalysisTaskState;
  unitsDone: number;
  unitsTotal: number | null;
  modelCallsDone?: number | undefined;
  modelCallsTotal?: number | null | undefined;
  embeddingCallsDone?: number | undefined;
  embeddingCallsTotal?: number | null | undefined;
}

/** Server snapshot; `remainingSeconds` is an estimate and null until it can be made. */
export interface JobProgress {
  tasksDone: number;
  tasksTotal: number;
  fraction: number;
  currentTask: AnalysisTaskKey | null;
  elapsedSeconds: number | null;
  remainingSeconds: number | null;
  queuePosition: number | null;
  tasks: AnalysisTask[];
  modelCallsDone?: number | undefined;
  modelCallsRemaining?: number | undefined;
  embeddingCallsDone?: number | undefined;
  embeddingCallsRemaining?: number | undefined;
  callEstimateComplete?: boolean | undefined;
}

export interface AnalysisJob {
  id: string;
  kind: AnalysisJobKind;
  state: AnalysisJobState;
  stage: AnalysisJobStage | null;
  startedAt: string | null;
  finishedAt: string | null;
  error: AnalysisJobError | null;
  /** Absent from the in-memory store and older servers. */
  progress?: JobProgress | null;
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

/* ---- Pipeline v2 verdicts (PLAN 18.10 routes, 18.13 views) ---- */

export type VerdictLabel = "met" | "partial" | "missing";
export type JudgeDimension = "match" | "seniority" | "experience";

/** A judge score on the 0–4 anchors, and the judge's own reason for it. */
export interface DimensionScore {
  score: number;
  rationale: string;
}

export interface VerdictEvidence {
  chunkId: string;
  documentId: string;
  /** Verbatim from the chunk; checked by the server before it was stored. */
  quote: string;
}

export interface Verdict {
  requirementId: string;
  quote: string;
  statement: string;
  mustHave: boolean;
  verdict: VerdictLabel;
  requirementScore: number | null;
  match: DimensionScore;
  seniority: DimensionScore | null;
  experience: DimensionScore | null;
  unmetConditions: string[];
  contradiction: boolean;
  adjustments: string[];
  evidence: VerdictEvidence[];
  provider: string;
  model: string;
}

export interface KeywordCoverage {
  exact: string[];
  alias: string[];
  missing: string[];
}

export interface V2Gap {
  requirementId: string;
  dimension: JudgeDimension;
  current: number;
  delta: number;
}

export interface RoleVerdicts {
  roleId: string;
  analysisId: string;
  fitScore: number;
  band: string;
  gated: boolean;
  rubricVersion: string;
  leftMachine: boolean;
  verdicts: Verdict[];
  keywordCoverage: KeywordCoverage;
  gapPlan: V2Gap[];
}

export interface TraceHit {
  chunkId: string;
  fusedScore: number;
  denseRank: number | null;
  lexicalRank: number | null;
  exactRank: number | null;
}

export interface TraceRound {
  round: number;
  queryText: string;
  hits: TraceHit[];
}

export interface RetrievalTrace {
  requirementId: string;
  rounds: TraceRound[];
}
