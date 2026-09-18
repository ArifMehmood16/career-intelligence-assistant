/**
 * Phase 12.8 — GET /api/spans/{id} client.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getSpan } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function stubFetch(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Response,
) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
      handler(input, init),
    ),
  );
}

describe("getSpan", () => {
  it("returns Evidence for a known span id", async () => {
    stubFetch((input) => {
      expect(String(input)).toBe("/api/spans/span-1");
      return Response.json({
        spanId: "span-1",
        documentId: "cv-1",
        page: 1,
        paragraph: "Owned dbt models in production.",
        highlight: "dbt models",
      });
    });

    await expect(getSpan("span-1")).resolves.toEqual({
      spanId: "span-1",
      documentId: "cv-1",
      page: 1,
      paragraph: "Owned dbt models in production.",
      highlight: "dbt models",
    });
  });

  it("throws ApiError with span_not_found on 404", async () => {
    stubFetch(
      () =>
        new Response(
          JSON.stringify({
            error: {
              code: "span_not_found",
              message: "No span with that id.",
              correlationId: "corr-span",
            },
          }),
          { status: 404 },
        ),
    );

    await expect(getSpan("missing")).rejects.toMatchObject({
      name: "ApiError",
      code: "span_not_found",
      status: 404,
    } satisfies Partial<ApiError>);
  });
});
