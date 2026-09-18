/**
 * HTTP client — same-origin `/api/**` via the Start proxy.
 * No fixtures. Every JSON response is validated with zod.
 */
import type {
  AnalysisJob,
  BreakdownRow,
  ChatMessage,
  CvDocument,
  Evidence,
  Provider,
  ProviderChoice,
  Requirement,
  Role,
  SupportingDocument,
} from "@/types";
import {
  analysisJobSchema,
  breakdownRowSchema,
  chatMessageSchema,
  cvDocumentSchema,
  errorEnvelopeSchema,
  evidenceSchema,
  providerChoiceSchema,
  providerSchema,
  reanalyseResponseSchema,
  requirementSchema,
  roleCreatedSchema,
  roleSchema,
  supportingDocumentSchema,
} from "./schemas";
import type { z } from "zod";

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

export function setProviderChoice(
  choice: ProviderChoice,
): Promise<ProviderChoice> {
  return request("/api/settings/providers", {
    method: "PUT",
    body: {
      ...choice,
      // Hosted confirmation is enforced in the settings UI before this runs.
      acknowledgedEgress: true,
    },
    schema: providerChoiceSchema,
  });
}
