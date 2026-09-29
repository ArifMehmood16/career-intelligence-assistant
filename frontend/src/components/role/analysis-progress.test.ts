/**
 * Analysis progress copy and the clock between polls.
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import type { JobProgress } from "@/types";

import {
  currentTaskLine,
  formatClock,
  liveTimes,
  queueLine,
  remainingLine,
  taskLabel,
  tasksDoneLine,
} from "./analysis-progress";

const RUNNING: JobProgress = {
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

describe("analysis progress copy", () => {
  it("counts tasks done out of the total", () => {
    expect(tasksDoneLine(RUNNING)).toBe("4 of 7 tasks done");
  });

  it("names the running task and its counted units", () => {
    expect(currentTaskLine(RUNNING)).toBe(
      "Judging each requirement · 3 of 12 requirements",
    );
    expect(
      currentTaskLine({
        ...RUNNING,
        currentTask: "read_cv",
        tasks: RUNNING.tasks.map((t) =>
          t.key === "read_cv" ? { ...t, state: "running" } : t,
        ),
      }),
    ).toBe("Reading your CV");
  });

  it("labels every task a pipeline can run", () => {
    expect(taskLabel("read_advert")).toBe("Read the job description");
    expect(taskLabel("recheck")).toBe("Recheck thin evidence");
  });

  it("formats clock times with minutes and hours", () => {
    expect(formatClock(5)).toBe("0:05");
    expect(formatClock(83)).toBe("1:23");
    expect(formatClock(3723)).toBe("1:02:03");
  });

  it("says when the time left is an estimate, unknown or nearly up", () => {
    expect(remainingLine(130)).toBe("About 2:10 left");
    expect(remainingLine(null)).toBe("Estimating time left…");
    expect(remainingLine(0)).toBe("Finishing up…");
  });

  it("describes the queue", () => {
    expect(queueLine(0)).toBe("Starting soon");
    expect(queueLine(1)).toBe("Waiting · 1 analysis ahead");
    expect(queueLine(3)).toBe("Waiting · 3 analyses ahead");
  });
});

describe("the clock between polls", () => {
  it("counts elapsed time up and the estimate down from the snapshot", () => {
    expect(liveTimes(RUNNING, 10_000, 13_400)).toEqual({
      elapsedSeconds: 86,
      remainingSeconds: 127,
    });
  });

  it("never counts the estimate below zero or invents one", () => {
    expect(liveTimes(RUNNING, 0, 500_000).remainingSeconds).toBe(0);
    expect(
      liveTimes({ ...RUNNING, remainingSeconds: null }, 0, 5_000)
        .remainingSeconds,
    ).toBeNull();
    expect(
      liveTimes({ ...RUNNING, elapsedSeconds: null }, 0, 5_000).elapsedSeconds,
    ).toBeNull();
  });
});
