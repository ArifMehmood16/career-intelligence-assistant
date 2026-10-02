import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { RoleVerdicts } from "@/types";

import { DIMENSION_LABEL, MAX_SCORE } from "./verdict-copy";
import type { VerdictsState } from "./VerdictsPanel";

export interface VerdictGapsPanelProps {
  state: VerdictsState;
  verdicts: RoleVerdicts | null;
  onRetry: () => void;
  onDraftBullet?: (requirementId: string) => void;
}

/** A role's gaps: the dimension to raise and what closing it would add. */
export function VerdictGapsPanel({
  state,
  verdicts,
  onRetry,
  onDraftBullet,
}: Readonly<VerdictGapsPanelProps>) {
  if (state === "loading") {
    return <Skeleton className="h-24 w-full" />;
  }
  if (state === "error") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          The gaps could not be loaded.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </div>
    );
  }
  if (state === "incomplete" || verdicts === null) {
    return (
      <p role="status" className="text-sm text-muted-foreground">
        This role has no finished analysis, so there are no gaps to show.
      </p>
    );
  }
  if (verdicts.gapPlan.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No gaps: every requirement scored as stated.
      </p>
    );
  }
  const statements = new Map(
    verdicts.verdicts.map((item) => [item.requirementId, item.statement]),
  );
  const draftable = new Set(
    verdicts.verdicts
      .filter(
        (item) =>
          item.verdict === "partial" &&
          item.evidence.length > 0 &&
          item.unmetConditions.length > 0,
      )
      .map((item) => item.requirementId),
  );
  return (
    <section aria-labelledby="verdict-gaps-heading" className="space-y-3">
      <h2 id="verdict-gaps-heading" className="text-base font-medium">
        Gaps, by what closing each would add to the fit
      </h2>
      <ol className="space-y-2">
        {verdicts.gapPlan.map((gap) => (
          <li
            key={`${gap.requirementId}-${gap.dimension}`}
            className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-border p-3"
          >
            <span>
              <span className="block">
                {statements.get(gap.requirementId) ?? gap.requirementId}
              </span>
              <span className="text-sm text-muted-foreground">
                {gap.dimension === "recency"
                  ? `Evidence recency · current weight ${Math.round(gap.current * 100)}%`
                  : `${DIMENSION_LABEL[gap.dimension]} · now ${gap.current} / ${MAX_SCORE}`}
              </span>
            </span>
            <span className="font-mono tabular-nums">
              +{gap.delta.toFixed(1)}
            </span>
            {onDraftBullet && draftable.has(gap.requirementId) ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onDraftBullet(gap.requirementId)}
              >
                Draft a CV bullet
              </Button>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
