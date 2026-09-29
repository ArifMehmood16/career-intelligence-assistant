/**
 * Phase 12.7 — analysis job client helpers.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { getJob, getRoles, reanalyseRole } from "./client";

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
        error:
          "assessment_incomplete: Analysis did not assess every scoreable requirement.",
      });
    });

    await expect(getJob("job-1")).resolves.toEqual({
      id: "job-1",
      kind: "role_analysis",
      state: "failed",
      stage: null,
      startedAt: "2026-09-18T12:00:00Z",
      finishedAt: "2026-09-18T12:01:00Z",
      error: {
        code: "assessment_incomplete",
        message: "Analysis did not assess every scoreable requirement.",
      },
    });
  });

  it("keeps object-shaped errors from the contract", async () => {
    stubFetch(() =>
      Response.json({
        id: "job-2",
        kind: "role_analysis",
        state: "failed",
        stage: "scoring",
        startedAt: "2026-09-18T12:00:00Z",
        finishedAt: "2026-09-18T12:01:00Z",
        error: {
          code: "extraction_incomplete",
          message: "Claim extraction did not classify every part of the CV.",
        },
      }),
    );

    await expect(getJob("job-2")).resolves.toMatchObject({
      state: "failed",
      stage: "scoring",
      error: {
        code: "extraction_incomplete",
        message: "Claim extraction did not classify every part of the CV.",
      },
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

const PROGRESS = {
  tasksDone: 1,
  tasksTotal: 5,
  fraction: 0.2,
  currentTask: "read_advert",
  elapsedSeconds: 4,
  remainingSeconds: null,
  queuePosition: null,
  tasks: [
    { key: "prepare", state: "done", unitsDone: 0, unitsTotal: null },
    { key: "read_advert", state: "running", unitsDone: 0, unitsTotal: null },
    { key: "read_cv", state: "pending", unitsDone: 0, unitsTotal: null },
    { key: "match", state: "pending", unitsDone: 0, unitsTotal: null },
    { key: "score", state: "pending", unitsDone: 0, unitsTotal: null },
  ],
};

const RUNNING_JOB = {
  id: "job-3",
  kind: "role_analysis",
  state: "running",
  stage: "extracting_requirements",
  startedAt: "2026-09-29T12:00:00Z",
  finishedAt: null,
  error: null,
  progress: PROGRESS,
};

describe("analysis progress on the wire", () => {
  it("keeps a job's progress snapshot", async () => {
    stubFetch(() => Response.json(RUNNING_JOB));

    await expect(getJob("job-3")).resolves.toMatchObject({
      progress: PROGRESS,
    });
  });

  it("maps each role's active job, and leaves it out when absent", async () => {
    const role = {
      id: "role-1",
      title: "AE",
      company: "Acme",
      fitScore: 0,
      bandLabel: "Not scored yet",
      counts: { met: 0, partial: 0, missing: 0 },
      status: "analysing",
      updatedAt: "2026-09-29T12:00:00Z",
    };
    stubFetch(() =>
      Response.json([
        { ...role, activeJob: RUNNING_JOB },
        { ...role, id: "role-2", status: "ready", activeJob: null },
        { ...role, id: "role-3", status: "ready" },
      ]),
    );

    const [running, ready, older] = await getRoles();

    expect(running?.activeJob).toMatchObject({
      id: "job-3",
      progress: PROGRESS,
    });
    expect(ready?.activeJob).toBeNull();
    expect(older).not.toHaveProperty("activeJob");
  });
});
