/**
 * Analysis progress copy, and the clock that runs between polls.
 *
 * The server sends a snapshot: tasks done of total, elapsed seconds and an
 * estimate of the time left. Between polls the page counts elapsed time up and
 * the estimate down from the moment that snapshot arrived.
 */
import type { AnalysisTaskKey, JobProgress } from "@/types";

interface TaskCopy {
  label: string;
  active: string;
  unit?: [singular: string, plural: string];
}

const REQUIREMENTS: [string, string] = ["requirement", "requirements"];

const TASKS: Record<AnalysisTaskKey, TaskCopy> = {
  prepare: {
    label: "Prepare the documents",
    active: "Preparing the documents",
  },
  read_advert: {
    label: "Read the job description",
    active: "Reading the job description",
  },
  read_cv: { label: "Read your CV", active: "Reading your CV" },
  search: {
    label: "Search your CV for evidence",
    active: "Searching your CV for evidence",
    unit: REQUIREMENTS,
  },
  judge: {
    label: "Judge each requirement",
    active: "Judging each requirement",
    unit: REQUIREMENTS,
  },
  recheck: {
    label: "Recheck thin evidence",
    active: "Rechecking thin evidence",
    unit: ["recheck", "rechecks"],
  },
  score: { label: "Score the fit", active: "Scoring the fit" },
};

export function taskLabel(key: AnalysisTaskKey): string {
  return TASKS[key]?.label ?? key;
}

export function unitsLine(
  key: AnalysisTaskKey,
  done: number,
  total: number | null,
): string | null {
  const unit = TASKS[key]?.unit;
  if (!unit || total === null) return null;
  return `${done} of ${total} ${total === 1 ? unit[0] : unit[1]}`;
}

export function tasksDoneLine(progress: JobProgress): string {
  return `${progress.tasksDone} of ${progress.tasksTotal} tasks done`;
}

export function currentTaskLine(progress: JobProgress): string | null {
  const tasks = progress.tasks.filter((t) => t.state === "running");
  if (tasks.length === 0) return null;
  return tasks
    .map((task) => {
      const active = TASKS[task.key]?.active ?? task.key;
      const units = unitsLine(task.key, task.unitsDone, task.unitsTotal);
      return units ? `${active} · ${units}` : active;
    })
    .join(" · ");
}

export function callsLine(progress: JobProgress): string | null {
  if (progress.modelCallsRemaining === undefined) return null;
  const model = progress.modelCallsRemaining;
  const embedding = progress.embeddingCallsRemaining ?? 0;
  const qualifier = progress.callEstimateComplete ? "About" : "At least";
  const planned = progress.callEstimateComplete ? "" : "planned ";
  const models = `${model} ${planned}LLM ${model === 1 ? "call" : "calls"}`;
  const embeddings =
    embedding > 0
      ? ` + ${embedding} embedding ${embedding === 1 ? "call" : "calls"}`
      : "";
  return `${qualifier} ${models}${embeddings} left`;
}

export function formatClock(totalSeconds: number): string {
  const whole = Math.max(0, Math.round(totalSeconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const seconds = String(whole % 60).padStart(2, "0");
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}`
    : `${minutes}:${seconds}`;
}

export function remainingLine(seconds: number | null): string {
  if (seconds === null) return "Estimating time left…";
  if (seconds <= 0) return "Finishing up…";
  return `About ${formatClock(seconds)} left`;
}

export function queueLine(ahead: number): string {
  if (ahead <= 0) return "Starting soon";
  return `Waiting · ${ahead} ${ahead === 1 ? "analysis" : "analyses"} ahead`;
}

export interface LiveTimes {
  elapsedSeconds: number | null;
  remainingSeconds: number | null;
}

/** Times now, from a snapshot observed at `observedAt` (both epoch ms). */
export function liveTimes(
  progress: JobProgress,
  observedAt: number,
  now: number,
): LiveTimes {
  const passed = Math.max(0, now - observedAt) / 1000;
  return {
    elapsedSeconds:
      progress.elapsedSeconds === null
        ? null
        : Math.round(progress.elapsedSeconds + passed),
    remainingSeconds:
      progress.remainingSeconds === null
        ? null
        : Math.max(0, Math.round(progress.remainingSeconds - passed)),
  };
}
