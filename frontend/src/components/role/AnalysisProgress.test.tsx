/**
 * @vitest-environment jsdom
 */
import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnalysisJob, JobProgress } from "@/types";

import { AnalysisProgress } from "./AnalysisProgress";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

const PROGRESS: JobProgress = {
  tasksDone: 4,
  tasksTotal: 7,
  fraction: (4 + 3 / 12) / 7,
  currentTask: "judge",
  elapsedSeconds: 83,
  remainingSeconds: 130,
  queuePosition: null,
  tasks: [
    { key: "prepare", state: "done", unitsDone: 0, unitsTotal: null },
    { key: "read_cv", state: "done", unitsDone: 0, unitsTotal: null },
    { key: "read_advert", state: "done", unitsDone: 0, unitsTotal: null },
    { key: "search", state: "done", unitsDone: 12, unitsTotal: 12 },
    { key: "judge", state: "running", unitsDone: 3, unitsTotal: 12 },
    { key: "recheck", state: "pending", unitsDone: 0, unitsTotal: null },
    { key: "score", state: "pending", unitsDone: 0, unitsTotal: null },
  ],
};

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    id: "job-1",
    kind: "role_analysis",
    state: "running",
    stage: "mapping",
    startedAt: "2026-09-29T12:00:00Z",
    finishedAt: null,
    error: null,
    progress: PROGRESS,
    ...overrides,
  };
}

describe("AnalysisProgress", () => {
  it.each(["judge", "recheck"] as const)(
    "explains batch completion while %s has zero finished requirements",
    (key) => {
      render(
        <AnalysisProgress
          job={job({
            progress: {
              ...PROGRESS,
              currentTask: key,
              tasks: PROGRESS.tasks.map((task) =>
                task.key === key
                  ? { ...task, state: "running", unitsDone: 0, unitsTotal: 12 }
                  : { ...task, state: "done" },
              ),
            },
          })}
          observedAt={0}
          now={0}
        />,
      );
      expect(
        screen.getByText("Requirement counts update when a batch finishes."),
      ).toBeInTheDocument();
      expect(
        screen.getAllByRole("listitem")[key === "judge" ? 4 : 5],
      ).toHaveTextContent("0 of 12");
    },
  );

  it("stops stale running task glyphs when the job has failed", () => {
    const { container } = render(
      <AnalysisProgress
        job={job({ state: "failed" })}
        observedAt={0}
        now={0}
      />,
    );
    expect(screen.getAllByRole("listitem")[4]).toHaveTextContent(
      "Stopped here",
    );
    expect(container.querySelector(".motion-safe\\:animate-spin")).toBeNull();
    expect(
      screen.queryByText("Requirement counts update when a batch finishes."),
    ).toBeNull();
  });

  it("shows tasks done of total, the running task and both times", () => {
    render(<AnalysisProgress job={job()} observedAt={0} now={0} />);

    expect(screen.getByText("4 of 7 tasks done")).toBeInTheDocument();
    expect(
      screen.getByText("Judging each requirement · 3 of 12 requirements"),
    ).toBeInTheDocument();
    expect(screen.getByText(/1:23 elapsed/)).toBeInTheDocument();
    expect(screen.getByText(/About 2:10 left/)).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Analysis progress" });
    expect(bar).toHaveAttribute("aria-valuenow", "61");
    expect(bar).toHaveAttribute("aria-valuetext", "4 of 7 tasks done");
  });

  it("lists every task with its state in words, not only a glyph", () => {
    render(<AnalysisProgress job={job()} observedAt={0} now={0} />);

    const list = screen.getByRole("list", { name: "Analysis tasks" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(7);
    expect(items[0]).toHaveTextContent("Prepare the documents");
    expect(items[0]).toHaveTextContent("done");
    expect(items[3]).toHaveTextContent("12 of 12 requirements");
    expect(items[4]).toHaveTextContent("Judge each requirement");
    expect(items[4]).toHaveTextContent("in progress");
    expect(items[6]).toHaveTextContent("not started");
  });

  it("keeps the compact view to the summary, bar and times", () => {
    render(
      <AnalysisProgress job={job()} observedAt={0} now={0} variant="compact" />,
    );

    expect(screen.queryByRole("list", { name: "Analysis tasks" })).toBeNull();
    expect(screen.getByText("4 of 7 tasks done")).toBeInTheDocument();
  });

  it("shows a queued job's place and says when time left is unknown", () => {
    render(
      <AnalysisProgress
        job={job({
          state: "queued",
          startedAt: null,
          progress: {
            ...PROGRESS,
            tasksDone: 0,
            fraction: 0,
            currentTask: null,
            elapsedSeconds: null,
            remainingSeconds: null,
            queuePosition: 1,
            tasks: PROGRESS.tasks.map((t) => ({ ...t, state: "pending" })),
          },
        })}
        observedAt={0}
        now={0}
      />,
    );

    expect(screen.getByText("Waiting · 1 analysis ahead")).toBeInTheDocument();
    expect(screen.getByText("Estimating time left…")).toBeInTheDocument();
    expect(screen.queryByText(/elapsed/)).toBeNull();
  });

  it("marks the task a failed analysis stopped in", () => {
    render(
      <AnalysisProgress
        job={job({
          state: "failed",
          progress: {
            ...PROGRESS,
            currentTask: null,
            remainingSeconds: null,
            tasks: PROGRESS.tasks.map((t) =>
              t.key === "judge" ? { ...t, state: "failed" } : t,
            ),
          },
        })}
        observedAt={0}
        now={0}
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(items[4]).toHaveTextContent("Stopped here");
  });

  it("counts the clock between polls", () => {
    vi.useFakeTimers();
    vi.setSystemTime(10_000);
    render(<AnalysisProgress job={job()} observedAt={10_000} />);
    expect(screen.getByText(/1:23 elapsed/)).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(2_000);
    });

    expect(screen.getByText(/1:25 elapsed/)).toBeInTheDocument();
    expect(screen.getByText(/About 2:08 left/)).toBeInTheDocument();
  });

  it("falls back to a plain status when the server sends no progress", () => {
    render(
      <AnalysisProgress job={job({ progress: null })} observedAt={0} now={0} />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Analysing");
  });
});
