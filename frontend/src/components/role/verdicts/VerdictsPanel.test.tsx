/**
 * PLAN 18.13 — a role's fit: dimension scores with quotes, coverage, states.
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VERDICTS } from "@/api/__fixtures__/verdicts";
import type { RoleVerdicts } from "@/types";

import { KeywordCoveragePanel } from "./KeywordCoveragePanel";
import { VerdictsPanel } from "./VerdictsPanel";

afterEach(() => {
  cleanup();
});

function panel(
  props: Partial<Parameters<typeof VerdictsPanel>[0]> = {},
): ReturnType<typeof render> {
  return render(
    <VerdictsPanel
      state="ready"
      verdicts={VERDICTS}
      onRetry={vi.fn()}
      onShowTrace={vi.fn()}
      {...props}
    />,
  );
}

describe("VerdictsPanel states", () => {
  it("shows a skeleton while loading", () => {
    const { container } = panel({ state: "loading", verdicts: null });
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("offers a retry when the verdicts could not load", async () => {
    const onRetry = vi.fn();
    panel({ state: "error", verdicts: null, onRetry });

    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("says so when there is no finished analysis, and is not a score", () => {
    panel({ state: "incomplete", verdicts: null });

    expect(screen.getByRole("status")).toHaveTextContent(
      /no finished analysis/i,
    );
    expect(screen.queryByText(/\/ 100/)).toBeNull();
  });

  it("says so when the job description had no requirements", () => {
    panel({ verdicts: { ...VERDICTS, verdicts: [], gapPlan: [] } });

    expect(
      screen.getByText(/no requirements were found in this job description/i),
    ).toBeInTheDocument();
  });
});

describe("VerdictsPanel ready", () => {
  it("shows the fit, the band and why the band is capped", () => {
    panel();

    expect(screen.getByText("71")).toBeInTheDocument();
    expect(screen.getByText(/Partial match/)).toBeInTheDocument();
    expect(screen.getByText(/band is capped at partial/i)).toBeInTheDocument();
  });

  it("shows each dimension's score, its anchor and the judge's reason", () => {
    panel();

    const card = screen.getByRole("article", {
      name: "Has five or more years of Python.",
    });
    const match = within(card).getByRole("group", { name: "Match" });
    expect(match).toHaveTextContent("3 / 4");
    expect(match).toHaveTextContent("The requirement as stated");
    expect(match).toHaveTextContent("Python in two roles.");
    expect(
      within(card).getByRole("group", { name: "Seniority" }),
    ).toHaveTextContent("The advert states no level.");
    expect(
      within(card).getByRole("group", { name: "Experience" }),
    ).toHaveTextContent("At least half the years");
  });

  it("quotes the evidence verbatim and lists what the evidence does not show", () => {
    panel();

    const card = screen.getByRole("article", {
      name: "Has five or more years of Python.",
    });
    expect(
      within(card).getByText("Wrote Python utilities"),
    ).toBeInTheDocument();
    expect(within(card).getByText("5+ years of Python")).toBeInTheDocument();
    expect(within(card).getByText("five years")).toBeInTheDocument();
    expect(within(card).getByText("Must-have")).toBeInTheDocument();
  });

  it("names every rule the server applied and a contradiction", () => {
    const changed: RoleVerdicts = {
      ...VERDICTS,
      verdicts: [
        {
          ...VERDICTS.verdicts[0]!,
          contradiction: true,
          adjustments: ["match_capped_contradiction"],
        },
      ],
    };
    panel({ verdicts: changed });

    expect(
      screen.getByText("Match capped at 2: the CV contradicts it."),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/the CV says the candidate lacks this/i),
    ).toBeInTheDocument();
  });

  it("opens the retrieval trace for a requirement", async () => {
    const onShowTrace = vi.fn();
    panel({ onShowTrace });

    await userEvent.click(
      screen.getByRole("button", { name: /retrieval trace/i }),
    );

    expect(onShowTrace).toHaveBeenCalledWith("r1");
  });
});

describe("KeywordCoveragePanel", () => {
  it("flags terms found only under another name", () => {
    render(<KeywordCoveragePanel coverage={VERDICTS.keywordCoverage} />);

    const alias = screen.getByRole("group", { name: /another name/i });
    expect(alias).toHaveTextContent("Postgres");
    expect(alias).toHaveTextContent(/applicant-tracking system may miss/i);
    expect(
      screen.getByRole("group", { name: /as written/i }),
    ).toHaveTextContent("Python");
    expect(screen.getByRole("group", { name: /not found/i })).toHaveTextContent(
      "Kafka",
    );
  });

  it("says when the advert names no technologies", () => {
    render(
      <KeywordCoveragePanel coverage={{ exact: [], alias: [], missing: [] }} />,
    );

    expect(
      screen.getByText(/names no specific technologies/i),
    ).toBeInTheDocument();
  });
});
