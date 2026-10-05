import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import type { Verdict, VerdictLabel } from "@/types";

import { VerdictCard } from "./VerdictCard";

const SCORE_RANGES = {
  "0-24": [0, 24],
  "25-49": [25, 49],
  "50-74": [50, 74],
  "75-100": [75, 100],
} as const;

type ScoreFilter = "all" | "unscored" | keyof typeof SCORE_RANGES;

export interface RequirementFilters {
  status: "all" | VerdictLabel;
  score: ScoreFilter;
}

const ALL: Readonly<RequirementFilters> = { status: "all", score: "all" };
const SELECT_STYLE =
  "h-9 rounded-md border border-border bg-background px-2 text-sm";

function scoreMatches(score: number | null, filter: ScoreFilter): boolean {
  if (filter === "all") return true;
  if (score === null) return filter === "unscored";
  if (filter === "unscored") return false;
  const percent = Math.round(score * 100);
  const [minimum, maximum] = SCORE_RANGES[filter];
  return percent >= minimum && percent <= maximum;
}

interface RequirementsPanelProps {
  verdicts: readonly Verdict[];
  onShowTrace: (requirementId: string) => void;
  initialFilters?: Readonly<RequirementFilters>;
}

/** Filter the stored publication locally; its fit and evidence are unchanged. */
export function RequirementsPanel({
  verdicts,
  onShowTrace,
  initialFilters = ALL,
}: Readonly<RequirementsPanelProps>) {
  const id = useId();
  const [filters, setFilters] = useState(initialFilters);
  const visible = verdicts.filter(
    (verdict) =>
      (filters.status === "all" || verdict.verdict === filters.status) &&
      scoreMatches(verdict.requirementScore, filters.score),
  );

  return (
    <section aria-labelledby={`${id}-heading`} className="space-y-3">
      <h2 id={`${id}-heading`} className="text-base font-medium">
        Requirements
      </h2>
      {verdicts.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No requirements were found in this job description.
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label htmlFor={`${id}-status`}>Match status</Label>
              <select
                id={`${id}-status`}
                value={filters.status}
                className={SELECT_STYLE}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    status: event.target.value as RequirementFilters["status"],
                  })
                }
              >
                <option value="all">All statuses</option>
                <option value="met">Met</option>
                <option value="partial">Partial</option>
                <option value="missing">Missing</option>
              </select>
            </div>
            <div className="space-y-1">
              <Label htmlFor={`${id}-score`}>Requirement score</Label>
              <select
                id={`${id}-score`}
                value={filters.score}
                className={SELECT_STYLE}
                onChange={(event) =>
                  setFilters({
                    ...filters,
                    score: event.target.value as ScoreFilter,
                  })
                }
              >
                <option value="all">All scores</option>
                {Object.keys(SCORE_RANGES).map((range) => (
                  <option key={range} value={range}>
                    {range.replace("-", "–")}%
                  </option>
                ))}
                <option value="unscored">Not scored</option>
              </select>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={filters.status === "all" && filters.score === "all"}
              onClick={() => setFilters(ALL)}
            >
              Clear filters
            </Button>
          </div>
          <p
            role="status"
            aria-live="polite"
            className="text-sm text-muted-foreground"
          >
            Showing {visible.length} of {verdicts.length} requirements
          </p>
          {visible.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No requirements match these filters.
            </p>
          ) : (
            visible.map((verdict) => (
              <VerdictCard
                key={verdict.requirementId}
                verdict={verdict}
                onShowTrace={onShowTrace}
              />
            ))
          )}
        </>
      )}
    </section>
  );
}
