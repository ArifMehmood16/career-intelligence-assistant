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

const BASE_VERDICT = VERDICTS.verdicts[0]!;
describe("Published score contribution", () => {
  it.each([
    ["met", 10, 0],
    ["partial", 4, 6],
    ["missing", 0, 10],
  ] as const)(
    "shows earned and unearned points for %s",
    (verdict, earned, shortfall) => {
      panel({
        verdicts: {
          ...VERDICTS,
          verdicts: [
            {
              ...BASE_VERDICT,
              verdict,
              scoreImpact: { earned, possible: 10, shortfall },
            },
          ],
        },
      });
      expect(
        screen.getByText(`+${earned.toFixed(1)} earned points`),
      ).toBeInTheDocument();
      expect(
        screen.getByText(`−${shortfall.toFixed(1)} unearned points`),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/10.0 possible points toward overall fit/),
      ).toBeInTheDocument();
    },
  );

  it("does not invent attribution for an older result", () => {
    panel();
    expect(
      screen.getByText("Score contribution unavailable"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/earned points/)).not.toBeInTheDocument();
  });
});
const FILTER_VERDICTS: RoleVerdicts = {
  ...VERDICTS,
  verdicts: [
    BASE_VERDICT,
    {
      ...BASE_VERDICT,
      requirementId: "met",
      statement: "Met requirement",
      verdict: "met",
      requirementScore: 1,
    },
    {
      ...BASE_VERDICT,
      requirementId: "missing",
      statement: "Missing requirement",
      verdict: "missing",
      requirementScore: 0,
    },
    {
      ...BASE_VERDICT,
      requirementId: "unscored",
      statement: "Unscored requirement",
      requirementScore: null,
    },
  ],
};

describe("Requirement filters", () => {
  it.each([
    ["0-24", ["Score 0", "Score 24"]],
    ["25-49", ["Score 25", "Score 49"]],
    ["50-74", ["Score 50", "Score 74"]],
    ["75-100", ["Score 75", "Score 100"]],
  ])(
    "filters %s using the displayed score boundaries",
    async (range, names) => {
      const scores = [0, 0.24, 0.245, 0.49, 0.5, 0.74, 0.75, 1];
      panel({
        verdicts: {
          ...VERDICTS,
          verdicts: scores.map((score) => ({
            ...BASE_VERDICT,
            requirementId: `score-${score}`,
            statement: `Score ${Math.round(score * 100)}`,
            requirementScore: score,
          })),
        },
      });
      await userEvent.selectOptions(
        screen.getByRole("combobox", { name: "Requirement score" }),
        range,
      );
      expect(
        screen
          .getAllByRole("article")
          .map((card) => within(card).getByRole("heading").textContent),
      ).toEqual(names);
    },
  );

  it("combines status and score without changing fit or trace actions", async () => {
    const onShowTrace = vi.fn();
    panel({ verdicts: FILTER_VERDICTS, onShowTrace });
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Match status" }),
      "partial",
    );
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Requirement score" }),
      "50-74",
    );
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Showing 1 of 4 requirements",
    );
    expect(screen.getByText("71")).toBeInTheDocument();
    expect(screen.getByText("Requirement score: 50%")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Show retrieval trace" }),
    );
    expect(onShowTrace).toHaveBeenCalledWith("r1");
  });

  it("keeps zero scores distinct from unscored requirements", async () => {
    panel({ verdicts: FILTER_VERDICTS });
    const score = screen.getByRole("combobox", { name: "Requirement score" });
    await userEvent.selectOptions(score, "0-24");
    expect(screen.getByRole("article")).toHaveAccessibleName(
      "Missing requirement",
    );
    expect(screen.getByText("Requirement score: 0%")).toBeInTheDocument();
    await userEvent.selectOptions(score, "unscored");
    expect(screen.getByRole("article")).toHaveAccessibleName(
      "Unscored requirement",
    );
    expect(
      screen.getByText("Requirement score: Not scored"),
    ).toBeInTheDocument();
  });

  it("explains empty filter results and clears both filters", async () => {
    panel({ verdicts: FILTER_VERDICTS });
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Match status" }),
      "met",
    );
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Requirement score" }),
      "0-24",
    );
    expect(screen.queryByRole("article")).toBeNull();
    expect(
      screen.getByText("No requirements match these filters."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/No requirements were found/)).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Clear filters" }),
    );
    expect(screen.getAllByRole("article")).toHaveLength(4);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Showing 4 of 4 requirements",
    );
  });

  it("resets filters when a new analysis publication arrives", async () => {
    const props = {
      state: "ready" as const,
      verdicts: FILTER_VERDICTS,
      onRetry: vi.fn(),
      onShowTrace: vi.fn(),
    };
    const { rerender } = render(<VerdictsPanel {...props} />);
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Match status" }),
      "missing",
    );
    rerender(
      <VerdictsPanel
        {...props}
        verdicts={{ ...FILTER_VERDICTS, analysisId: "new-analysis" }}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Match status" })).toHaveValue(
      "all",
    );
    expect(screen.getAllByRole("article")).toHaveLength(4);
  });
});

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
