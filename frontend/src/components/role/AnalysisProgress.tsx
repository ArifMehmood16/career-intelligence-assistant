import { Check, Circle, LoaderCircle, Minus, X } from "lucide-react";
import { useEffect, useState } from "react";

import {
  currentTaskLine,
  callsLine,
  formatClock,
  liveTimes,
  queueLine,
  remainingLine,
  taskLabel,
  tasksDoneLine,
  unitsLine,
} from "@/components/role/analysis-progress";
import type { AnalysisJob, AnalysisTask, AnalysisTaskState } from "@/types";

export interface AnalysisProgressProps {
  job: AnalysisJob;
  /** Epoch ms when this snapshot of the job arrived. */
  observedAt: number;
  /** "compact" leaves out the task list, for a table cell or a header. */
  variant?: "compact" | "full";
  /** A fixed clock for tests and the state gallery; otherwise it ticks. */
  now?: number;
}

const STATE_WORDS: Record<AnalysisTaskState, string> = {
  done: "done",
  running: "in progress",
  pending: "not started",
  skipped: "Skipped, nothing to recheck",
  failed: "Stopped here",
};

function useNow(ticking: boolean, fixed: number | undefined): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (fixed !== undefined || !ticking) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [ticking, fixed]);
  return fixed ?? now;
}

function TaskGlyph({ state }: { state: AnalysisTaskState }) {
  const className = "size-3.5 shrink-0";
  switch (state) {
    case "done":
      return <Check aria-hidden="true" className={`${className} text-met`} />;
    case "running":
      return (
        <LoaderCircle
          aria-hidden="true"
          className={`${className} motion-safe:animate-spin`}
        />
      );
    case "skipped":
      return (
        <Minus
          aria-hidden="true"
          className={`${className} text-muted-foreground`}
        />
      );
    case "failed":
      return (
        <X aria-hidden="true" className={`${className} text-destructive`} />
      );
    default:
      return (
        <Circle
          aria-hidden="true"
          className={`${className} text-muted-foreground`}
        />
      );
  }
}

function TaskRow({ task }: { task: AnalysisTask }) {
  const units = unitsLine(task.key, task.unitsDone, task.unitsTotal);
  const shown = task.state === "skipped" || task.state === "failed";
  return (
    <li className="flex items-center gap-2">
      <TaskGlyph state={task.state} />
      <span className={task.state === "pending" ? "text-muted-foreground" : ""}>
        {taskLabel(task.key)}
      </span>
      {units ? (
        <span className="text-muted-foreground tabular-nums">{units}</span>
      ) : null}
      <span className={shown ? "text-muted-foreground" : "sr-only"}>
        {shown ? STATE_WORDS[task.state] : `, ${STATE_WORDS[task.state]}`}
      </span>
    </li>
  );
}

/** Tasks done of total, the running task, elapsed time and the estimate left. */
export function AnalysisProgress({
  job,
  observedAt,
  variant = "full",
  now: fixedNow,
}: AnalysisProgressProps) {
  const ticking = job.state === "queued" || job.state === "running";
  const now = useNow(ticking, fixedNow);
  const progress = job.progress;
  if (!progress) {
    return (
      <span role="status" aria-live="polite" className="text-muted-foreground">
        Analysing
      </span>
    );
  }
  const times = liveTimes(progress, observedAt, now);
  const percent = Math.round(progress.fraction * 100);
  const summary =
    job.state === "queued"
      ? queueLine(progress.queuePosition ?? 0)
      : tasksDoneLine(progress);
  const current = currentTaskLine(progress);
  const calls = callsLine(progress);
  const showTime = ticking;

  return (
    <div className="min-w-48 space-y-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm">
        <span role="status" aria-live="polite">
          {summary}
        </span>
        {showTime ? (
          <span className="text-muted-foreground tabular-nums">
            {times.elapsedSeconds === null
              ? ""
              : `${formatClock(times.elapsedSeconds)} elapsed · `}
            {remainingLine(times.remainingSeconds)}
          </span>
        ) : null}
      </div>
      <div
        role="progressbar"
        aria-label="Analysis progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={tasksDoneLine(progress)}
        className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
      >
        <svg
          className="block h-1.5 w-full"
          viewBox="0 0 100 4"
          preserveAspectRatio="none"
          role="presentation"
        >
          <rect
            x="0"
            y="0"
            width={percent}
            height="4"
            className="fill-primary"
          />
        </svg>
      </div>
      {current ? (
        <p className="text-sm text-muted-foreground">{current}</p>
      ) : null}
      {showTime && calls ? (
        <p className="text-sm text-muted-foreground tabular-nums">{calls}</p>
      ) : null}
      {variant === "full" && showTime && calls ? (
        <p className="text-xs text-muted-foreground">
          Calls run in parallel where possible. Cached work is skipped; repairs
          can add calls.
        </p>
      ) : null}
      {variant === "full" ? (
        <ol aria-label="Analysis tasks" className="space-y-1 pt-1 text-sm">
          {progress.tasks.map((task) => (
            <TaskRow key={task.key} task={task} />
          ))}
        </ol>
      ) : null}
    </div>
  );
}
