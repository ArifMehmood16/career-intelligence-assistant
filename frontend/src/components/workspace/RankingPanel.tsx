/**
 * Phase 13.6 — workspace ranking with named reasons and ties.
 * Presentational: ranked rows and retry come from the container.
 */
import { Link } from "@tanstack/react-router";

import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { RankedRole } from "@/types";

export interface RankingPanelProps {
  state: AsyncState;
  ranked: RankedRole[];
  onRetry: () => void;
}

export function RankingPanel({ state, ranked, onRetry }: RankingPanelProps) {
  return (
    <section
      aria-label="Ranking"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-2 text-sm font-semibold">Ranking</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Ordered from stored fit scores. Ties stay ties — the reason is named.
      </p>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-3">
          {[0, 1, 2].map((row) => (
            <Skeleton key={row} className="h-14 w-full" />
          ))}
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The ranking could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="text-muted-foreground">
          Add at least one ready role to see a ranking.
        </p>
      )}

      {state === "ready" && (
        <ol aria-label="Role ranking" className="space-y-3">
          {ranked.map((item) => (
            <li
              key={item.role.id}
              className="rounded-sm border border-border bg-background px-3 py-3"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="font-mono text-sm tabular-nums">
                    #{item.rank}
                  </span>
                  {item.tied ? (
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      Tied
                    </span>
                  ) : null}
                  <Link
                    to="/roles/$id"
                    params={{ id: item.role.id }}
                    className="text-sm font-medium text-foreground underline-offset-2 hover:underline"
                  >
                    {item.role.title}
                  </Link>
                  <span className="text-sm text-muted-foreground">
                    {item.role.company}
                  </span>
                </div>
                <span className="font-mono text-sm tabular-nums">
                  {item.role.fitScore}
                </span>
              </div>
              {item.because.length > 0 ? (
                <p className="mt-2 text-sm text-muted-foreground">
                  Because: {item.because.join("; ")}
                </p>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  Because: score only — no named differentiator.
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
