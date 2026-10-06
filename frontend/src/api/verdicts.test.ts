/**
 * PLAN 18.13 — the v2 verdicts and trace routes, and the agent's tool steps.
 * @vitest-environment node
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { getRoleVerdicts, getVerdictTrace, postMessageStream } from "./client";
import { ApiError } from "./client";
import { RECENCY_VERDICTS, VERDICTS } from "./__fixtures__/verdicts";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function stubFetch(handler: (input: RequestInfo | URL) => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => handler(input)),
  );
}

describe("getRoleVerdicts", () => {
  it("accepts a published recency gap without dropping verdicts", async () => {
    stubFetch(() => Response.json(RECENCY_VERDICTS));

    const result = await getRoleVerdicts("role-1");

    expect(result.gapPlan).toEqual(RECENCY_VERDICTS.gapPlan);
    expect(result.verdicts).toEqual(
      RECENCY_VERDICTS.verdicts.map((v) => ({
        ...v,
        scoreImpact: null,
        yearsExpected: null,
        seniorityExpected: null,
        experienceExpected: null,
      })),
    );
    expect(result.fitScore).toBe(RECENCY_VERDICTS.fitScore);
  });

  it("preserves published attribution and qualitative expectations", async () => {
    const verdict = {
      ...VERDICTS.verdicts[0],
      scoreImpact: { earned: 4, possible: 10, shortfall: 6 },
      yearsExpected: null,
      seniorityExpected: "senior",
      experienceExpected: "Production delivery",
    };
    stubFetch(() => Response.json({ ...VERDICTS, verdicts: [verdict] }));
    const result = await getRoleVerdicts("role-1");
    expect(result.verdicts[0]).toEqual(verdict);
  });

  it("still rejects an unknown gap dimension", async () => {
    stubFetch(() =>
      Response.json({
        ...RECENCY_VERDICTS,
        gapPlan: [{ ...RECENCY_VERDICTS.gapPlan[0], dimension: "unknown" }],
      }),
    );

    await expect(getRoleVerdicts("role-1")).rejects.toMatchObject({
      code: "internal_error",
      status: 200,
    });
  });

  it("returns the validated v2 fit", async () => {
    stubFetch((input) => {
      expect(String(input)).toBe("/api/roles/role-1/verdicts");
      return Response.json(VERDICTS);
    });

    const verdicts = await getRoleVerdicts("role-1");

    expect(verdicts.verdicts[0]?.experience?.score).toBe(2);
    expect(verdicts.verdicts[0]?.seniority).toBeNull();
    expect(verdicts.keywordCoverage.alias).toEqual(["Postgres"]);
  });

  it("raises the 409 a role without a v2 analysis returns", async () => {
    stubFetch(() =>
      Response.json(
        {
          error: {
            code: "analysis_incomplete",
            message: "No finished analysis.",
            correlationId: "c",
          },
        },
        { status: 409 },
      ),
    );

    await expect(getRoleVerdicts("role-1")).rejects.toMatchObject({
      code: "analysis_incomplete",
      status: 409,
    });
    await expect(getRoleVerdicts("role-1")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("getVerdictTrace", () => {
  it("returns the rounds and each leg's ranks", async () => {
    stubFetch((input) => {
      expect(String(input)).toBe("/api/roles/role-1/verdicts/r1/trace");
      return Response.json({
        requirementId: "r1",
        rounds: [
          {
            round: 0,
            queryText: "Has five or more years of Python.",
            hits: [
              {
                chunkId: "c1",
                fusedScore: 0.032,
                denseRank: 1,
                lexicalRank: null,
                exactRank: 1,
              },
            ],
          },
        ],
      });
    });

    const trace = await getVerdictTrace("role-1", "r1");

    expect(trace.rounds[0]?.hits[0]?.lexicalRank).toBeNull();
  });
});

describe("tool steps on the answer stream", () => {
  it("reports the agent's tool calls before the text", async () => {
    const encoder = new TextEncoder();
    const frames = [
      'event: meta\ndata: {"questionId":"q","messageId":"m","intent":"open_question","provider":"ollama","model":"qwen2.5:7b","leftMachine":false}\n\n',
      'event: tools\ndata: {"steps":[{"name":"search_evidence","arguments":{"query":"dbt"},"found":2,"failed":false}]}\n\n',
      'event: token\ndata: {"text":"Yes."}\n\n',
      'event: citations\ndata: {"citations":[]}\n\n',
      'event: done\ndata: {"kind":"answer"}\n\n',
    ];
    stubFetch(
      () =>
        new Response(
          new ReadableStream({
            start(controller) {
              for (const frame of frames) {
                controller.enqueue(encoder.encode(frame));
              }
              controller.close();
            },
          }),
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        ),
    );
    const seen: string[] = [];

    const result = await postMessageStream({
      content: "Where is dbt?",
      onEvent: (event) => seen.push(event.type),
    });

    expect(seen).toEqual(["meta", "tools", "token", "citations", "done"]);
    expect(result.toolSteps).toEqual([
      {
        name: "search_evidence",
        arguments: { query: "dbt" },
        found: 2,
        failed: false,
      },
    ]);
  });
});
