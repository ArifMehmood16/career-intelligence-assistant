/**
 * PLAN 18.13 — the v2 fit reads the verdict routes; a trace loads on demand.
 * @vitest-environment jsdom
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TRACE, VERDICTS } from "@/api/__fixtures__/verdicts";

import { V2RoleFitContainer } from "./V2RoleFitContainer";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function wrap(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  );
}

function stubRoutes(verdicts: () => Response) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      return url.endsWith("/trace") ? Response.json(TRACE) : verdicts();
    }),
  );
  return calls;
}

describe("V2RoleFitContainer", () => {
  it("shows the verdicts and loads a trace only when asked", async () => {
    const calls = stubRoutes(() => Response.json(VERDICTS));
    wrap(<V2RoleFitContainer roleId="role-1" pane="fit" />);

    expect(
      await screen.findByRole("article", {
        name: "Has five or more years of Python.",
      }),
    ).toBeInTheDocument();
    expect(calls).toEqual(["/api/roles/role-1/verdicts"]);

    await userEvent.click(
      screen.getByRole("button", { name: /retrieval trace/i }),
    );

    expect(
      await screen.findByRole("table", { name: /round 0/i }),
    ).toBeInTheDocument();
    expect(calls).toContain("/api/roles/role-1/verdicts/r1/trace");
  });

  it("treats a 409 as no finished v2 analysis, not as an error", async () => {
    stubRoutes(() =>
      Response.json(
        {
          error: {
            code: "analysis_incomplete",
            message: "No v2 analysis.",
            correlationId: "c",
          },
        },
        { status: 409 },
      ),
    );
    wrap(<V2RoleFitContainer roleId="role-1" pane="fit" />);

    expect(await screen.findByRole("status")).toHaveTextContent(
      /no finished v2 analysis/i,
    );
  });

  it("reads the gaps from the same verdicts", async () => {
    stubRoutes(() => Response.json(VERDICTS));
    wrap(<V2RoleFitContainer roleId="role-1" pane="gaps" />);

    expect(await screen.findByText("+6.5")).toBeInTheDocument();
  });
});
