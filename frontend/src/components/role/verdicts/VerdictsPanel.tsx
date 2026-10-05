import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { RoleVerdicts } from "@/types";

import { KeywordCoveragePanel } from "./KeywordCoveragePanel";
import { RequirementsPanel } from "./RequirementsPanel";
import { bandLabel } from "./verdict-copy";

export type VerdictsState = "loading" | "error" | "incomplete" | "ready";

export interface VerdictsPanelProps {
  state: VerdictsState;
  verdicts: RoleVerdicts | null;
  onRetry: () => void;
  onShowTrace: (requirementId: string) => void;
}

/**
 * A role's fit: the score from domain code, the judge's three
 * dimensions with the quotes behind them, and keyword coverage beside the score.
 */
export function VerdictsPanel({
  state,
  verdicts,
  onRetry,
  onShowTrace,
}: VerdictsPanelProps) {
  if (state === "loading") {
    return (
      <div className="space-y-3" aria-busy="true">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  if (state === "error") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          The verdicts could not be loaded.
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
        This role has no finished analysis, so there is no fit to show. This is
        not a fit judgement.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <section aria-label="Fit" className="space-y-1">
        <p>
          <span className="font-mono text-xl">
            {Math.round(verdicts.fitScore)}
          </span>
          <span className="text-muted-foreground">
            {" "}
            / 100 · {bandLabel(verdicts.band)}
          </span>
        </p>
        {verdicts.gated ? (
          <p className="text-sm text-muted-foreground">
            A must-have scored low on match, so the band is capped at partial.
          </p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          The score is arithmetic over the judge&apos;s verdicts (
          {verdicts.rubricVersion}); the model never gives it.
          {verdicts.leftMachine
            ? " A hosted model judged part of this analysis."
            : " Every model call stayed on this machine."}
        </p>
      </section>

      <KeywordCoveragePanel coverage={verdicts.keywordCoverage} />

      <RequirementsPanel
        key={verdicts.analysisId}
        verdicts={verdicts.verdicts}
        onShowTrace={onShowTrace}
      />
    </div>
  );
}
