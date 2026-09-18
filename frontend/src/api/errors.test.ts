/**
 * Phase 12.11 — map API error codes to actionable UI copy.
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import { describeApiError, KNOWN_ERROR_CODES } from "./errors";
import { ApiError } from "./client";

describe("describeApiError", () => {
  it("covers every documented contract error code", () => {
    expect([...KNOWN_ERROR_CODES].sort()).toEqual(
      [
        "analysis_incomplete",
        "cover_letter_not_found",
        "csrf_rejected",
        "cv_not_found",
        "cv_required",
        "document_too_large",
        "document_unreadable",
        "document_unsupported",
        "egress_not_acknowledged",
        "egress_not_permitted",
        "internal_error",
        "misconfigured",
        "provider_failed",
        "provider_unavailable",
        "rate_limited",
        "role_not_found",
        "span_not_found",
        "validation_failed",
      ].sort(),
    );
  });

  it("guides the operator when the Start proxy lacks API_BASE_URL", () => {
    const described = describeApiError(
      new ApiError("misconfigured", "API_BASE_URL is not set on the server.", {
        correlationId: "proxy",
        status: 500,
      }),
    );
    expect(described.known).toBe(true);
    expect(described.title).toMatch(/misconfigured/i);
    expect(described.nextStep).toMatch(/API_BASE_URL/i);
  });

  it("returns an actionable title and next step for known codes", () => {
    const described = describeApiError(
      new ApiError("cv_required", "Upload a CV before adding a role.", {
        correlationId: "c1",
        status: 409,
      }),
    );
    expect(described.title).toMatch(/cv/i);
    expect(described.nextStep).toMatch(/upload/i);
    expect(described.known).toBe(true);
  });

  it("fails visibly for unknown codes instead of swallowing them", () => {
    const described = describeApiError(
      new ApiError("totally_unknown", "weird", {
        correlationId: "c2",
        status: 500,
      }),
    );
    expect(described.known).toBe(false);
    expect(described.title).toMatch(/unexpected/i);
    expect(described.nextStep).toMatch(/c2|correlation/i);
    expect(described.message).toBe("weird");
  });

  it("handles non-ApiError failures visibly", () => {
    const described = describeApiError(new Error("network down"));
    expect(described.known).toBe(false);
    expect(described.message).toMatch(/network down/i);
  });
});
