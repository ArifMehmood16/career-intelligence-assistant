/**
 * HTTP client — same-origin `/api/**` via the Start proxy.
 * No fixtures. Every JSON response is validated with zod.
 */
import type {
  AnalysisJob,
  BreakdownRow,
  BulletDraft,
  ChatMessage,
  Citation,
  Comparison,
  CoverLetterDraft,
  CvDocument,
  Evidence,
  GapPlan,
  InterviewPack,
  Provider,
  ProviderChoice,
  RankedRole,
  Requirement,
  Role,
  SupportingDocument,
} from "@/types";
import {
  analysisJobSchema,
  breakdownRowSchema,
  bulletDraftSchema,
  chatMessageSchema,
  citationSchema,
  comparisonSchema,
  coverLetterDraftSchema,
  cvDocumentSchema,
  errorEnvelopeSchema,
  evidenceSchema,
  gapPlanSchema,
  interviewPackSchema,
  providerChoiceSchema,
  providerChoiceUpdateResponseSchema,
  providerSchema,
  rankedRoleSchema,
  reanalyseResponseSchema,
  requirementSchema,
  roleCreatedSchema,
  roleSchema,
  supportingDocumentSchema,
} from "./schemas";
import { z } from "zod";

export class ApiError extends Error {
  readonly code: string;
  readonly correlationId: string;
  readonly status: number;

  constructor(
    code: string,
    message: string,
    options: { correlationId: string; status: number },
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.correlationId = options.correlationId;
    this.status = options.status;
  }
}

type Schema<T> = z.ZodType<T> | null;

export async function request<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: HeadersInit;
    schema: Schema<T>;
    signal?: AbortSignal;
  },
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const init: RequestInit = {
    method: options.method ?? "GET",
    headers,
    credentials: "same-origin",
  };
  if (options.body !== undefined) {
    if (options.body instanceof FormData) {
      init.body = options.body;
    } else {
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      init.body =
        typeof options.body === "string"
          ? options.body
          : JSON.stringify(options.body);
    }
  }
  if (options.signal !== undefined) {
    init.signal = options.signal;
  }

  const response = await fetch(path, init);

  const correlationHeader = response.headers.get("X-Correlation-Id") ?? "";

  if (!response.ok) {
    let code = "internal_error";
    let message = "Request failed.";
    let correlationId = correlationHeader || "unknown";
    try {
      const payload: unknown = await response.json();
      const parsed = errorEnvelopeSchema.safeParse(payload);
      if (parsed.success) {
        code = parsed.data.error.code;
        message = parsed.data.error.message;
        correlationId = parsed.data.error.correlationId || correlationId;
      }
    } catch {
      // keep defaults
    }
    throw new ApiError(code, message, {
      correlationId,
      status: response.status,
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const rawText = await response.text();
  if (rawText === "" || rawText === "null") {
    if (options.schema === null) {
      return null as T;
    }
    // Explicit JSON null for optional resources (GET /api/cv).
    if (rawText === "null") {
      return null as T;
    }
  }

  let json: unknown;
  try {
    json = rawText === "" ? null : JSON.parse(rawText);
  } catch {
    throw new ApiError("internal_error", "Response was not valid JSON.", {
      correlationId: correlationHeader || "unknown",
      status: response.status,
    });
  }

  if (options.schema === null) {
    return json as T;
  }

  const parsed = options.schema.safeParse(json);
  if (!parsed.success) {
    throw new ApiError(
      "internal_error",
      `Response failed validation: ${parsed.error.message}`,
      {
        correlationId: correlationHeader || "unknown",
        status: response.status,
      },
    );
  }
  return parsed.data;
}

function mapRole(raw: z.infer<typeof roleSchema>): Role {
  return {
    id: raw.id,
    title: raw.title,
    company: raw.company,
    fitScore: raw.fitScore,
    bandLabel: raw.bandLabel,
    counts: raw.counts,
    status: raw.status,
    updatedAt: raw.updatedAt,
    fitSummary: raw.fitSummary ?? null,
  };
}

function mapProvider(raw: z.infer<typeof providerSchema>): Provider {
  return {
    id: raw.id,
    name: raw.name,
    kind: raw.kind,
    models: raw.models,
    available: raw.available,
    unavailableReason: raw.unavailableReason,
  };
}

function mapMessage(raw: z.infer<typeof chatMessageSchema>): ChatMessage {
  const message: ChatMessage = {
    id: raw.id,
    author: raw.author,
    content: raw.content,
    kind: raw.kind,
    citations: raw.citations.map((citation) => ({
      id: citation.id,
      label: citation.label,
      evidence: citation.evidence ?? {
        spanId: citation.id,
        documentId: "",
        page: 1,
        paragraph: citation.label,
        highlight: citation.label,
      },
    })),
    model: raw.model,
    provider: raw.provider,
    leftMachine: raw.leftMachine,
  };
  if (raw.conversationId !== undefined) {
    message.conversationId = raw.conversationId;
  }
  if (raw.createdAt !== undefined) {
    message.createdAt = raw.createdAt;
  }
  return message;
}

export function getCv(): Promise<CvDocument | null> {
  return request("/api/cv", { schema: cvDocumentSchema.nullable() });
}

export function uploadCv(file: File): Promise<CvDocument> {
  const form = new FormData();
  form.append("file", file, file.name);
  return request("/api/cv", {
    method: "POST",
    body: form,
    schema: cvDocumentSchema,
  }).then((raw) => ({
    id: raw.id,
    filename: raw.filename,
    pageCount: raw.pageCount,
    parsedAt: raw.parsedAt,
  }));
}

export function deleteCv(): Promise<void> {
  return request("/api/cv", { method: "DELETE", schema: null });
}

export function getCoverLetters(): Promise<SupportingDocument[]> {
  return request("/api/cover-letters", {
    schema: supportingDocumentSchema.array(),
  });
}

export function uploadCoverLetter(file: File): Promise<SupportingDocument> {
  const form = new FormData();
  form.append("file", file, file.name);
  return request("/api/cover-letters", {
    method: "POST",
    body: form,
    schema: supportingDocumentSchema,
  });
}

export function deleteCoverLetter(documentId: string): Promise<void> {
  return request(`/api/cover-letters/${documentId}`, {
    method: "DELETE",
    schema: null,
  });
}

export async function getRoles(): Promise<Role[]> {
  const rows = await request("/api/roles", {
    schema: roleSchema.array(),
  });
  return rows.map(mapRole);
}

export async function getRanking(): Promise<RankedRole[]> {
  const rows = await request("/api/ranking", {
    schema: rankedRoleSchema.array(),
  });
  return rows.map((row) => ({
    role: mapRole(row.role),
    rank: row.rank,
    tied: row.tied,
    because: row.because,
  }));
}

export async function getComparison(
  roleAId: string,
  roleBId: string,
): Promise<Comparison> {
  const params = new URLSearchParams({ a: roleAId, b: roleBId });
  const row = await request(`/api/compare?${params.toString()}`, {
    schema: comparisonSchema,
  });
  return {
    a: mapRole(row.a),
    b: mapRole(row.b),
    shared: row.shared,
    onlyInA: row.onlyInA,
    onlyInB: row.onlyInB,
    differentiator: row.differentiator,
  };
}

export function deleteRole(roleId: string): Promise<void> {
  return request(`/api/roles/${roleId}`, { method: "DELETE", schema: null });
}

export async function getRole(id: string): Promise<Role | null> {
  try {
    const row = await request(`/api/roles/${id}`, { schema: roleSchema });
    return mapRole(row);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export function getRequirements(roleId: string): Promise<Requirement[]> {
  return request(`/api/roles/${roleId}/requirements`, {
    schema: requirementSchema.array(),
  });
}

export function getFitBreakdown(roleId: string): Promise<BreakdownRow[]> {
  return request(`/api/roles/${roleId}/breakdown`, {
    schema: breakdownRowSchema.array(),
  });
}

export function getGapPlan(roleId: string): Promise<GapPlan> {
  return request(`/api/roles/${roleId}/gap-plan`, {
    schema: gapPlanSchema,
  });
}

export function createBulletDraft(
  roleId: string,
  requirementId: string,
): Promise<BulletDraft> {
  return request(`/api/roles/${roleId}/bullets`, {
    method: "POST",
    body: { requirementId },
    schema: bulletDraftSchema,
  });
}

export function getInterviewPack(roleId: string): Promise<InterviewPack> {
  return request(`/api/roles/${roleId}/interview-pack`, {
    schema: interviewPackSchema,
  });
}

export function getGeneratedCoverLetters(
  roleId: string,
): Promise<CoverLetterDraft[]> {
  return request(`/api/roles/${roleId}/cover-letters`, {
    schema: coverLetterDraftSchema.array(),
  });
}

export function createCoverLetterDraft(
  roleId: string,
  input: { tone: "plain" | "warm"; includeGapLine: boolean },
): Promise<CoverLetterDraft> {
  return request(`/api/roles/${roleId}/cover-letter`, {
    method: "POST",
    body: {
      tone: input.tone,
      includeGapLine: input.includeGapLine,
    },
    schema: coverLetterDraftSchema,
  });
}

export type ExportArtefact =
  "gap-plan" | "interview-pack" | "cover-letter" | "bullets";

/** Download Markdown for a role artefact; returns the raw text. */
export async function exportRoleArtefact(
  roleId: string,
  artefact: ExportArtefact,
  options?: { version?: number },
): Promise<string> {
  const params = new URLSearchParams();
  if (options?.version !== undefined) {
    params.set("version", String(options.version));
  }
  const query = params.size > 0 ? `?${params.toString()}` : "";
  const response = await fetch(
    `/api/roles/${roleId}/export/${artefact}.md${query}`,
    {
      method: "GET",
      headers: { Accept: "text/markdown, text/plain, */*" },
      credentials: "same-origin",
    },
  );
  if (!response.ok) {
    let code = "internal_error";
    let message = "Export failed.";
    let correlationId = response.headers.get("X-Correlation-Id") ?? "unknown";
    try {
      const payload: unknown = await response.json();
      const parsed = errorEnvelopeSchema.safeParse(payload);
      if (parsed.success) {
        code = parsed.data.error.code;
        message = parsed.data.error.message;
        correlationId = parsed.data.error.correlationId || correlationId;
      }
    } catch {
      // keep defaults
    }
    throw new ApiError(code, message, {
      correlationId,
      status: response.status,
    });
  }
  return response.text();
}

export function getSpan(spanId: string): Promise<Evidence> {
  return request(`/api/spans/${spanId}`, { schema: evidenceSchema });
}

export async function addRole(input: {
  title: string;
  company: string;
  description: string;
}): Promise<{ role: Role; jobId: string }> {
  const created = await request("/api/roles", {
    method: "POST",
    body: input,
    schema: roleCreatedSchema,
  });
  return { role: mapRole(created.role), jobId: created.jobId };
}

export async function getJob(jobId: string): Promise<AnalysisJob> {
  const raw = await request(`/api/jobs/${jobId}`, {
    schema: analysisJobSchema,
  });
  const error =
    raw.error == null
      ? null
      : typeof raw.error === "string"
        ? { code: "analysis_failed", message: raw.error }
        : raw.error;
  return {
    id: raw.id,
    kind: raw.kind,
    state: raw.state,
    stage: raw.stage,
    startedAt: raw.startedAt,
    finishedAt: raw.finishedAt,
    error,
  };
}

export function reanalyseRole(roleId: string): Promise<{ jobId: string }> {
  return request(`/api/roles/${roleId}/reanalyse`, {
    method: "POST",
    schema: reanalyseResponseSchema,
  });
}

export async function getMessages(): Promise<ChatMessage[]> {
  const rows = await request("/api/messages", {
    schema: chatMessageSchema.array(),
  });
  return rows.map(mapMessage);
}

export type MessageStreamEvent =
  | {
      type: "meta";
      questionId: string;
      messageId: string;
      intent: string;
      provider: string;
      model: string | null;
      leftMachine: boolean;
    }
  | { type: "token"; text: string }
  | { type: "citations"; citations: Citation[] }
  | { type: "done"; kind: "answer" | "insufficient" }
  | { type: "error"; code: string; message: string };

export interface MessageStreamResult {
  messageId: string | null;
  questionId: string | null;
  text: string;
  kind: "answer" | "insufficient" | null;
  citations: Citation[];
  provider: string | null;
  model: string | null;
  leftMachine: boolean;
  clientRequestId: string;
}

export async function postMessageStream(options: {
  content: string;
  roleId?: string;
  clientRequestId?: string;
  signal?: AbortSignal;
  onEvent: (event: MessageStreamEvent) => void;
}): Promise<MessageStreamResult> {
  const clientRequestId = options.clientRequestId ?? crypto.randomUUID();
  const headers = new Headers({
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  });
  const body: Record<string, string> = {
    content: options.content,
    clientRequestId,
  };
  if (options.roleId !== undefined) {
    body["roleId"] = options.roleId;
  }

  const init: RequestInit = {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    credentials: "same-origin",
  };
  if (options.signal !== undefined) {
    init.signal = options.signal;
  }

  const response = await fetch("/api/messages", init);
  const correlationHeader = response.headers.get("X-Correlation-Id") ?? "";

  if (!response.ok) {
    let code = "internal_error";
    let message = "Request failed.";
    let correlationId = correlationHeader || "unknown";
    try {
      const payload: unknown = await response.json();
      const parsed = errorEnvelopeSchema.safeParse(payload);
      if (parsed.success) {
        code = parsed.data.error.code;
        message = parsed.data.error.message;
        correlationId = parsed.data.error.correlationId || correlationId;
      }
    } catch {
      // keep defaults
    }
    throw new ApiError(code, message, {
      correlationId,
      status: response.status,
    });
  }

  if (!response.body) {
    throw new ApiError("internal_error", "Stream response had no body.", {
      correlationId: correlationHeader || "unknown",
      status: response.status,
    });
  }

  const result: MessageStreamResult = {
    messageId: null,
    questionId: null,
    text: "",
    kind: null,
    citations: [],
    provider: null,
    model: null,
    leftMachine: false,
    clientRequestId,
  };

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleBlock = (block: string) => {
    const lines = block.split(/\r?\n/);
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length === 0) return;
    const raw = dataLines.join("\n");
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return;
    }

    if (eventName === "meta") {
      const event: MessageStreamEvent = {
        type: "meta",
        questionId: String(data["questionId"] ?? ""),
        messageId: String(data["messageId"] ?? ""),
        intent: String(data["intent"] ?? ""),
        provider: String(data["provider"] ?? ""),
        model: data["model"] == null ? null : String(data["model"]),
        leftMachine: Boolean(data["leftMachine"]),
      };
      result.messageId = event.messageId;
      result.questionId = event.questionId;
      result.provider = event.provider;
      result.model = event.model;
      result.leftMachine = event.leftMachine;
      options.onEvent(event);
      return;
    }

    if (eventName === "token") {
      const text = String(data["text"] ?? "");
      result.text += text;
      options.onEvent({ type: "token", text });
      return;
    }

    if (eventName === "citations") {
      const parsed = z.array(citationSchema).safeParse(data["citations"] ?? []);
      const citations = parsed.success
        ? parsed.data.map((citation) => ({
            id: citation.id,
            label: citation.label,
            evidence: citation.evidence ?? {
              spanId: citation.id,
              documentId: "",
              page: 1,
              paragraph: citation.label,
              highlight: citation.label,
            },
          }))
        : [];
      result.citations = citations;
      options.onEvent({ type: "citations", citations });
      return;
    }

    if (eventName === "done") {
      const kind = data["kind"] === "insufficient" ? "insufficient" : "answer";
      result.kind = kind;
      options.onEvent({ type: "done", kind });
      return;
    }

    if (eventName === "error") {
      const code = String(data["code"] ?? "provider_failed");
      const message = String(data["message"] ?? "Provider failed.");
      options.onEvent({ type: "error", code, message });
      throw new ApiError(code, message, {
        correlationId: correlationHeader || "unknown",
        status: 502,
      });
    }
  };

  while (true) {
    if (options.signal?.aborted) {
      await reader.cancel();
      throw new DOMException("The operation was aborted.", "AbortError");
    }
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split(/\n\n/);
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      if (block.trim()) handleBlock(block);
    }
  }
  if (buffer.trim()) {
    handleBlock(buffer);
  }

  return result;
}

export async function sendMessage(content: string): Promise<ChatMessage[]> {
  await request("/api/messages", {
    method: "POST",
    headers: { Accept: "application/json" },
    body: {
      content,
      clientRequestId: crypto.randomUUID(),
    },
    schema: chatMessageSchema,
  });
  return getMessages();
}

export async function deleteMessages(): Promise<void> {
  await request("/api/messages", { method: "DELETE", schema: null });
}

export async function getProviders(): Promise<Provider[]> {
  const rows = await request("/api/providers", {
    schema: providerSchema.array(),
  });
  return rows.map(mapProvider);
}

export function getProviderChoice(): Promise<ProviderChoice> {
  return request("/api/settings/providers", {
    schema: providerChoiceSchema,
  });
}

export async function setProviderChoice(input: {
  choice: ProviderChoice;
  acknowledgedEgress: boolean;
}): Promise<{ choice: ProviderChoice; reindexJobId: string | null }> {
  const raw = await request("/api/settings/providers", {
    method: "PUT",
    body: {
      ...input.choice,
      acknowledgedEgress: input.acknowledgedEgress,
    },
    schema: providerChoiceUpdateResponseSchema,
  });
  return {
    choice: {
      answerProviderId: raw.answerProviderId,
      answerModel: raw.answerModel,
      indexProviderId: raw.indexProviderId,
      indexModel: raw.indexModel,
    },
    reindexJobId: raw.reindex?.jobId ?? null,
  };
}
