import { TriangleAlert } from "lucide-react";
import { useId } from "react";

import { StatusMark } from "@/components/StatusMark";
import { Button } from "@/components/ui/button";
import type { DimensionScore, JudgeDimension, Verdict } from "@/types";

import {
  adjustmentLabel,
  anchorLabel,
  DIMENSION_LABEL,
  MAX_SCORE,
  NOT_STATED,
} from "./verdict-copy";

export interface VerdictCardProps {
  verdict: Verdict;
  onShowTrace: (requirementId: string) => void;
}

function Meter({ score }: { score: number }) {
  return (
    <span aria-hidden="true" className="inline-flex gap-0.5">
      {Array.from({ length: MAX_SCORE }, (_, index) => (
        <span
          key={index}
          className={
            index < score
              ? "h-2 w-4 rounded-sm bg-foreground"
              : "h-2 w-4 rounded-sm bg-muted"
          }
        />
      ))}
    </span>
  );
}

function Dimension({
  dimension,
  score,
}: {
  dimension: JudgeDimension;
  score: DimensionScore | null;
}) {
  const label = DIMENSION_LABEL[dimension];
  return (
    <div role="group" aria-label={label} className="space-y-0.5">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <span className="w-24 font-medium">{label}</span>
        {score === null ? (
          <span className="text-muted-foreground">
            {dimension === "match" ? "" : NOT_STATED[dimension]}
          </span>
        ) : (
          <>
            <Meter score={score.score} />
            <span className="font-mono tabular-nums">
              {score.score} / {MAX_SCORE}
            </span>
            <span className="text-muted-foreground">
              {anchorLabel(dimension, score.score)}
            </span>
          </>
        )}
      </p>
      {score !== null && score.rationale ? (
        <p className="pl-26 text-sm text-muted-foreground">
          <span className="sr-only">The judge&apos;s reason: </span>
          {score.rationale}
        </p>
      ) : null}
    </div>
  );
}

/** One requirement as the judge scored it and the server checked it. */
export function VerdictCard({ verdict, onShowTrace }: VerdictCardProps) {
  const headingId = useId();
  return (
    <article
      aria-labelledby={headingId}
      className="space-y-3 rounded-md border border-border p-4"
    >
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <h3 id={headingId} className="font-medium">
            {verdict.statement}
          </h3>
          <p className="text-sm text-muted-foreground">
            From the advert: <q>{verdict.quote}</q>
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {verdict.mustHave ? (
            <span className="rounded-none border border-border px-1.5 py-0.5 text-[11px]">
              Must-have
            </span>
          ) : null}
          <StatusMark status={verdict.verdict} />
        </div>
      </header>

      <p className="text-sm font-mono tabular-nums">
        Requirement score:{" "}
        {verdict.requirementScore === null
          ? "Not scored"
          : `${Math.round(verdict.requirementScore * 100)}%`}
      </p>

      <div className="space-y-2">
        <Dimension dimension="match" score={verdict.match} />
        <Dimension dimension="seniority" score={verdict.seniority} />
        <Dimension dimension="experience" score={verdict.experience} />
      </div>

      {verdict.evidence.length > 0 ? (
        <div className="space-y-1">
          <p className="text-sm font-medium">Evidence, quoted from your CV</p>
          {verdict.evidence.map((item) => (
            <blockquote
              key={`${item.chunkId}-${item.quote}`}
              className="border-l-2 border-border pl-3 text-sm"
            >
              {item.quote}
            </blockquote>
          ))}
        </div>
      ) : null}

      {verdict.unmetConditions.length > 0 ? (
        <div className="space-y-1">
          <p className="text-sm font-medium">Not shown by the evidence</p>
          <ul className="list-disc pl-5 text-sm">
            {verdict.unmetConditions.map((condition) => (
              <li key={condition}>{condition}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {verdict.contradiction ? (
        <p className="inline-flex items-center gap-1 text-sm">
          <TriangleAlert aria-hidden="true" className="size-3.5" />
          The CV says the candidate lacks this.
        </p>
      ) : null}

      {verdict.adjustments.length > 0 ? (
        <ul className="space-y-0.5 text-sm text-muted-foreground">
          {verdict.adjustments.map((code) => (
            <li key={code}>{adjustmentLabel(code)}</li>
          ))}
        </ul>
      ) : null}

      <footer className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-mono text-[11px] text-muted-foreground">
          Judged by {verdict.model} · {verdict.provider}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onShowTrace(verdict.requirementId)}
        >
          Show retrieval trace
        </Button>
      </footer>
    </article>
  );
}
