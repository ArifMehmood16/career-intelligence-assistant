/**
 * Phase 12.7 — analysis job client helpers.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { getJob, reanalyseRole } from "./client";

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

describe("getJob", () => {
  it("returns a validated AnalysisJob and normalises string errors", async () => {
    stubFetch((input) => {
      expect(String(input)).toBe("/api/jobs/job-1");
      return Response.json({
        id: "job-1",
        kind: "role_analysis",
        state: "failed",
        stage: null,
        startedAt: "2026-09-18T12:00:00Z",
        finishedAt: "2026-09-18T12:01:00Z",
        error: "Provider timed out.",
      });
    });

    await expect(getJob("job-1")).resolves.toEqual({
      id: "job-1",
      kind: "role_analysis",
      state: "failed",
      stage: null,
      startedAt: "2026-09-18T12:00:00Z",
      finishedAt: "2026-09-18T12:01:00Z",
      error: { code: "analysis_failed", message: "Provider timed out." },
    });
  });

  it("keeps object-shaped errors from the contract", async () => {
    stubFetch(() =>
      Response.json({
        id: "job-2",
        kind: "role_analysis",
        state: "running",
        stage: "mapping",
        startedAt: "2026-09-18T12:00:00Z",
        finishedAt: null,
        error: null,
      }),
    );

    await expect(getJob("job-2")).resolves.toMatchObject({
      state: "running",
      stage: "mapping",
      error: null,
    });
  });
});

describe("reanalyseRole", () => {
  it("posts reanalyse and returns the new jobId", async () => {
    stubFetch((input, init) => {
      expect(String(input)).toBe("/api/roles/role-1/reanalyse");
      expect(init?.method).toBe("POST");
      return Response.json({ jobId: "job-9" }, { status: 202 });
    });

    await expect(reanalyseRole("role-1")).resolves.toEqual({ jobId: "job-9" });
  });
});
