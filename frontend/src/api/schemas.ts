/** Zod schemas mirroring the shared frontend types (wire camelCase). */
import { z } from "zod";

export const evidenceSchema = z.object({
  spanId: z.string(),
  documentId: z.string(),
  page: z.number().int(),
  paragraph: z.string(),
  highlight: z.string(),
});

export const cvDocumentSchema = z
  .object({
    id: z.string(),
    filename: z.string(),
    pageCount: z.number().int(),
    parsedAt: z.string(),
  })
  .passthrough();

export const roleCountsSchema = z.object({
  met: z.number().int(),
  partial: z.number().int(),
  missing: z.number().int(),
});

export const roleSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    company: z.string(),
    fitScore: z.number(),
    bandLabel: z.string(),
    counts: roleCountsSchema,
    status: z.enum(["analysing", "ready", "failed"]),
    updatedAt: z.string(),
  })
  .passthrough();

export const roleCreatedSchema = z.object({
  role: roleSchema,
  jobId: z.string(),
});

export const requirementSchema = z.object({
  id: z.string(),
  roleId: z.string(),
  text: z.string(),
  type: z.enum(["must", "desirable"]),
  status: z.enum(["met", "partial", "missing"]),
  evidence: evidenceSchema.nullable(),
});

export const breakdownRowSchema = z.object({
  id: z.enum(["must", "desirable", "recency"]),
  label: z.string(),
  value: z.number(),
  requirementIds: z.array(z.string()),
});

export const citationSchema = z.object({
  id: z.string(),
  label: z.string(),
  evidence: evidenceSchema.nullable().optional(),
});

export const chatMessageSchema = z.object({
  id: z.string(),
  conversationId: z.string().optional(),
  author: z.enum(["user", "assistant"]),
  content: z.string(),
  kind: z.enum(["question", "answer", "insufficient"]),
  citations: z.array(citationSchema),
  model: z.string().nullable(),
  provider: z.string().nullable(),
  leftMachine: z.boolean(),
  createdAt: z.string().optional(),
});

export const providerSchema = z
  .object({
    id: z.string(),
    name: z.string(),
    kind: z.enum(["local", "hosted"]),
    models: z.array(z.string()),
    available: z.boolean(),
    unavailableReason: z.string().nullable(),
  })
  .passthrough();

export const providerChoiceSchema = z.object({
  answerProviderId: z.string(),
  answerModel: z.string(),
  indexProviderId: z.string(),
  indexModel: z.string(),
});

export const providerChoiceUpdateResponseSchema = providerChoiceSchema.extend({
  reindex: z
    .object({
      jobId: z.string(),
    })
    .nullable()
    .optional(),
});

export const analysisJobSchema = z
  .object({
    id: z.string(),
    kind: z.enum(["role_analysis", "cv_parse", "reindex"]),
    state: z.enum(["queued", "running", "succeeded", "failed"]),
    stage: z
      .enum([
        "parsing",
        "extracting_requirements",
        "extracting_claims",
        "mapping",
        "scoring",
      ])
      .nullable(),
    startedAt: z.string().nullable(),
    finishedAt: z.string().nullable(),
    error: z
      .union([
        z.string(),
        z.object({ code: z.string(), message: z.string() }),
        z.null(),
      ])
      .optional(),
  })
  .passthrough();

export const reanalyseResponseSchema = z.object({
  jobId: z.string(),
});

export const supportingDocumentSchema = z.object({
  id: z.string(),
  kind: z.literal("cover_letter"),
  filename: z.string(),
  mediaType: z.string(),
  byteLength: z.number().int(),
  pageCount: z.number().int(),
  parsedAt: z.string(),
  createdAt: z.string(),
});

export const gapItemSchema = z.object({
  requirementId: z.string(),
  requirementText: z.string(),
  type: z.enum(["must", "desirable"]),
  status: z.enum(["partial", "missing"]),
  reason: z.enum([
    "no_related_claim",
    "adjacent_claim_only",
    "evidence_too_old",
    "evidence_thin",
  ]),
  adjacentEvidence: evidenceSchema.nullable(),
  scoreDelta: z.number(),
  action: z.enum(["evidence_it", "learn_it", "accept_it"]),
  canDraftBullet: z.boolean(),
});

export const gapPlanSchema = z.object({
  roleId: z.string(),
  currentScore: z.number(),
  items: z.array(gapItemSchema),
});

export const draftProvenanceSchema = z.object({
  provider: z.string(),
  model: z.string().nullable(),
  leftMachine: z.boolean(),
  generatedAt: z.string(),
  grounded: z.boolean(),
  fallback: z.enum(["none", "regenerated", "template"]),
});

export const bulletLineSchema = z.object({
  text: z.string(),
  spanIds: z.array(z.string()),
  evidence: z.array(evidenceSchema),
});

export const bulletDraftSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  createdAt: z.string(),
  requirementId: z.string(),
  bullets: z.array(bulletLineSchema),
  provenance: draftProvenanceSchema,
});

export const interviewProbeSchema = z.object({
  requirementId: z.string(),
  question: z.string(),
  status: z.enum(["met", "partial", "missing"]),
});

export const interviewLeadWithSchema = z.object({
  requirementId: z.string(),
  evidence: evidenceSchema,
  note: z.string(),
});

export const interviewThinAreaSchema = z.object({
  requirementId: z.string(),
  requirementText: z.string(),
  nearest: evidenceSchema.nullable(),
});

export const interviewAskThemSchema = z.object({
  question: z.string(),
  requirementId: z.string().nullable(),
});

export const interviewPackSchema = z.object({
  roleId: z.string(),
  probes: z.array(interviewProbeSchema),
  leadWith: z.array(interviewLeadWithSchema),
  thinAreas: z.array(interviewThinAreaSchema),
  askThem: z.array(interviewAskThemSchema),
  provenance: draftProvenanceSchema,
});

export const coverLetterParagraphSchema = z.object({
  text: z.string(),
  requirementIds: z.array(z.string()),
  spanIds: z.array(z.string()),
});

export const coverLetterDraftSchema = z.object({
  id: z.string(),
  version: z.number().int(),
  createdAt: z.string(),
  roleId: z.string(),
  paragraphs: z.array(coverLetterParagraphSchema),
  omittedReason: z.string().nullable(),
  provenance: draftProvenanceSchema,
});

export const rankedRoleSchema = z.object({
  role: roleSchema,
  rank: z.number().int(),
  tied: z.boolean(),
  because: z.array(z.string()),
});

export const comparisonSharedSchema = z.object({
  text: z.string(),
  aStatus: z.enum(["met", "partial", "missing"]),
  bStatus: z.enum(["met", "partial", "missing"]),
});

export const comparisonSchema = z.object({
  a: roleSchema,
  b: roleSchema,
  shared: z.array(comparisonSharedSchema),
  onlyInA: z.array(requirementSchema),
  onlyInB: z.array(requirementSchema),
  differentiator: z.string(),
});

export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    correlationId: z.string(),
  }),
});
