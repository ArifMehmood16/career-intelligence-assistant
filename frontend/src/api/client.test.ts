/**
 * Phase 12.3 — real HTTP client: request(), ApiError, zod validation.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  addRole,
  deleteRole,
  exportRoleArtefact,
  getCv,
  getProviders,
  getRoles,
  request,
} from "./client";

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

describe("request", () => {
  it("returns validated JSON for a successful GET", async () => {
    stubFetch(() =>
      Response.json([
        {
          id: "role-1",
          title: "AE",
          company: "Acme",
          fitScore: 80,
          bandLabel: "Strong match",
          counts: { met: 2, partial: 1, missing: 0 },
          status: "ready",
          updatedAt: "2026-09-18T12:00:00Z",
        },
      ]),
    );

    const roles = await getRoles();
    expect(roles).toEqual([
      {
        id: "role-1",
        title: "AE",
        company: "Acme",
        fitScore: 80,
        bandLabel: "Strong match",
        counts: { met: 2, partial: 1, missing: 0 },
        status: "ready",
        updatedAt: "2026-09-18T12:00:00Z",
      },
    ]);
    expect(fetch).toHaveBeenCalledWith(
      "/api/roles",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
  });

  it("maps RoleCreated with jobId from the API", async () => {
    stubFetch(() =>
      Response.json(
        {
          role: {
            id: "role-1",
            title: "AE",
            company: "Acme",
            fitScore: 0,
            bandLabel: "Not scored yet",
            counts: { met: 0, partial: 0, missing: 0 },
            status: "analysing",
            updatedAt: "2026-09-18T12:00:00Z",
          },
          jobId: "job-1",
        },
        { status: 202 },
      ),
    );

    await expect(
      addRole({ title: "AE", company: "Acme", description: "Need dbt" }),
    ).resolves.toMatchObject({
      role: { id: "role-1", status: "analysing" },
      jobId: "job-1",
    });
  });

  it("throws ApiError with code and correlationId from the envelope", async () => {
    stubFetch(
      () =>
        new Response(
          JSON.stringify({
            error: {
              code: "cv_required",
              message: "Upload a CV before adding a role.",
              correlationId: "corr-1",
            },
          }),
          {
            status: 409,
            headers: {
              "Content-Type": "application/json",
              "X-Correlation-Id": "corr-1",
            },
          },
        ),
    );

    await expect(
      addRole({ title: "AE", company: "Acme", description: "Need dbt" }),
    ).rejects.toMatchObject({
      name: "ApiError",
      code: "cv_required",
      correlationId: "corr-1",
      status: 409,
    });
    await expect(
      addRole({ title: "AE", company: "Acme", description: "Need dbt" }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("rejects responses that fail zod validation", async () => {
    stubFetch(() => Response.json([{ id: "role-1", title: 99 }]));

    await expect(getRoles()).rejects.toThrow(/invalid/i);
  });

  it("treats a JSON null CV body as null", async () => {
    stubFetch(() => new Response("null", { status: 200 }));
    await expect(getCv()).resolves.toBeNull();
  });
});

describe("getProviders", () => {
  it("keeps the existing Provider shape from a richer API payload", async () => {
    stubFetch(() =>
      Response.json([
        {
          id: "hermetic",
          name: "Hermetic",
          kind: "local",
          models: ["rules-v1"],
          available: true,
          unavailableReason: null,
          supports: { completion: true, embedding: true },
          capabilities: {
            structuredOutput: true,
            contextWindow: 8192,
            maxOutputTokens: 1024,
            embeddingDimensions: null,
          },
        },
      ]),
    );

    await expect(getProviders()).resolves.toEqual([
      {
        id: "hermetic",
        name: "Hermetic",
        kind: "local",
        models: ["rules-v1"],
        available: true,
        unavailableReason: null,
      },
    ]);
  });
});

describe("request helper", () => {
  it("sets Accept application/json by default", async () => {
    stubFetch((_input, init) => {
      const headers = new Headers(init?.headers);
      expect(headers.get("Accept")).toBe("application/json");
      return Response.json(null);
    });
    await request("/api/cv", { schema: null });
  });
});

describe("deleteRole", () => {
  it("hard-deletes a role by id", async () => {
    stubFetch((input, init) => {
      expect(String(input)).toBe("/api/roles/role-1");
      expect(init?.method).toBe("DELETE");
      return new Response(null, { status: 204 });
    });

    await expect(deleteRole("role-1")).resolves.toBeUndefined();
  });
});

describe("exportRoleArtefact", () => {
  it("pins markdown export to the selected draft version", async () => {
    stubFetch((input) => {
      const url = String(input);
      expect(url).toBe("/api/roles/role-1/export/cover-letter.md?version=1");
      return new Response("Version one letter\n", {
        status: 200,
        headers: { "Content-Type": "text/markdown; charset=utf-8" },
      });
    });

    await expect(
      exportRoleArtefact("role-1", "cover-letter", { version: 1 }),
    ).resolves.toBe("Version one letter\n");
  });
});
