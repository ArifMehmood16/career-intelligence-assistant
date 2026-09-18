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

export interface Role {
  id: string;
  title: string;
  company: string;
  fitScore: number;
  bandLabel: string;
  counts: { met: number; partial: number; missing: number };
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
