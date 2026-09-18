/**
 * Phase 12.11 — map stable API error codes to actionable UI states.
 * Switch on `code`, never on `message` (api-contract).
 */
import { ApiError } from "./client";

export const KNOWN_ERROR_CODES = [
  "validation_failed",
  "cv_required",
  "document_too_large",
  "document_unsupported",
  "document_unreadable",
  "role_not_found",
  "cv_not_found",
  "cover_letter_not_found",
  "span_not_found",
  "analysis_incomplete",
  "provider_unavailable",
  "egress_not_permitted",
  "egress_not_acknowledged",
  "provider_failed",
  "rate_limited",
  "internal_error",
  "misconfigured",
  "csrf_rejected",
] as const;

export type KnownErrorCode = (typeof KNOWN_ERROR_CODES)[number];

export interface DescribedApiError {
  code: string;
  known: boolean;
  title: string;
  message: string;
  nextStep: string;
  correlationId: string | null;
}

const GUIDANCE: Record<KnownErrorCode, { title: string; nextStep: string }> = {
  validation_failed: {
    title: "That request was not valid",
    nextStep: "Check the fields and try again.",
  },
  cv_required: {
    title: "A CV is required",
    nextStep: "Upload a CV on the workspace, then try again.",
  },
  document_too_large: {
    title: "That file is too large",
    nextStep: "Use a smaller PDF, DOCX, or plain-text file (up to 10MB).",
  },
  document_unsupported: {
    title: "That file type is not supported",
    nextStep: "Upload a PDF, DOCX, or plain-text document.",
  },
  document_unreadable: {
    title: "That document could not be read",
    nextStep:
      "Try a text-based PDF or DOCX. Scanned images and encrypted files are not accepted yet.",
  },
  role_not_found: {
    title: "Role not found",
    nextStep: "Return to the workspace and open a role from the list.",
  },
  cv_not_found: {
    title: "CV not found",
    nextStep: "Upload a CV on the workspace.",
  },
  cover_letter_not_found: {
    title: "Cover letter not found",
    nextStep: "Refresh the list and try again, or upload it again.",
  },
  span_not_found: {
    title: "Citation could not be resolved",
    nextStep:
      "This is a product bug worth reporting — a citation pointed at a missing span.",
  },
  analysis_incomplete: {
    title: "Analysis is still running",
    nextStep: "Wait for the role to finish analysing, then open it again.",
  },
  provider_unavailable: {
    title: "That provider is not available",
    nextStep:
      "Pick another provider in Settings, or fix the reason shown there.",
  },
  egress_not_permitted: {
    title: "Hosted providers are turned off",
    nextStep:
      "Choose a local provider, or ask the operator to enable hosted providers.",
  },
  egress_not_acknowledged: {
    title: "Hosted use was not confirmed",
    nextStep: "Confirm that documents may leave this machine, then try again.",
  },
  provider_failed: {
    title: "The model provider failed",
    nextStep: "Retry in a moment, or switch provider in Settings.",
  },
  rate_limited: {
    title: "Too many requests",
    nextStep: "Wait a short while, then try again.",
  },
  internal_error: {
    title: "Something went wrong",
    nextStep: "Retry. If it keeps failing, note the correlation id below.",
  },
  misconfigured: {
    title: "The web server is misconfigured",
    nextStep:
      "API_BASE_URL must be set for the Start proxy (make run loads config/app.env). Restart the web process.",
  },
  csrf_rejected: {
    title: "That request was blocked",
    nextStep:
      "Reload from the app origin (default http://localhost:3000) and try again.",
  },
};

function isKnownCode(code: string): code is KnownErrorCode {
  return (KNOWN_ERROR_CODES as readonly string[]).includes(code);
}

export function describeApiError(error: unknown): DescribedApiError {
  if (error instanceof ApiError) {
    if (isKnownCode(error.code)) {
      const guidance = GUIDANCE[error.code];
      return {
        code: error.code,
        known: true,
        title: guidance.title,
        message: error.message,
        nextStep: guidance.nextStep,
        correlationId: error.correlationId,
      };
    }
    return {
      code: error.code,
      known: false,
      title: "Unexpected error",
      message: error.message,
      nextStep: `This code is not in the contract table. Note correlation id ${error.correlationId}.`,
      correlationId: error.correlationId,
    };
  }

  if (error instanceof Error) {
    return {
      code: "internal_error",
      known: false,
      title: "Unexpected error",
      message: error.message,
      nextStep: "Retry. If it keeps failing, check the network connection.",
      correlationId: null,
    };
  }

  return {
    code: "internal_error",
    known: false,
    title: "Unexpected error",
    message: "Request failed.",
    nextStep: "Retry. If it keeps failing, check the network connection.",
    correlationId: null,
  };
}

export function formatDescribedError(described: DescribedApiError): string {
  const parts = [described.message || described.title, described.nextStep];
  if (described.correlationId) {
    parts.push(`Reference: ${described.correlationId}`);
  }
  return parts.join(" ");
}
