import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BreakdownRow, Requirement } from "@/types";

export type AsyncState = "loading" | "error" | "empty" | "ready";

export interface FitBreakdownProps {
  state: AsyncState;
  rows: BreakdownRow[];
  requirementsById: Record<string, Requirement>;
  expandedRowIds: string[];
  onToggleRow: (id: string) => void;
  onRetry: () => void;
}

export function FitBreakdown({
  state,
  rows,
  requirementsById,
  expandedRowIds,
  onToggleRow,
  onRetry,
}: FitBreakdownProps) {
  return (
    <section
      aria-label="Fit breakdown"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-4 text-sm font-semibold">Breakdown</h2>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-4">
          {[0, 1, 2].map((row) => (
            <div key={row} className="space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-1 w-full" />
            </div>
          ))}
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The breakdown could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="text-muted-foreground">
          No breakdown is available for this role yet.
        </p>
      )}

      {state === "ready" && (
        <ul className="space-y-4">
          {rows.map((row) => {
            const expanded = expandedRowIds.includes(row.id);
            return (
              <li key={row.id}>
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => onToggleRow(row.id)}
                  className="flex w-full items-center gap-2 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {expanded ? (
                    <ChevronDown
                      className="size-4 text-muted-foreground"
                      aria-hidden="true"
                    />
                  ) : (
                    <ChevronRight
                      className="size-4 text-muted-foreground"
                      aria-hidden="true"
                    />
                  )}
                  <span className="flex-1">{row.label}</span>
                  <span className="font-mono">{row.value}</span>
                </button>
                <div
                  aria-hidden="true"
                  className="mt-2 h-1 w-full overflow-hidden rounded-sm bg-border"
                >
                  <svg
                    className="block h-1 w-full"
                    viewBox="0 0 100 4"
                    preserveAspectRatio="none"
                    role="presentation"
                  >
                    <rect
                      x="0"
                      y="0"
                      width={Math.max(0, Math.min(100, row.value))}
                      height="4"
                      className="fill-foreground"
                    />
                  </svg>
                </div>
                {expanded && (
                  <ul className="mt-2 space-y-1 pl-6">
                    {row.requirementIds.map((id) => (
                      <li key={id} className="text-muted-foreground">
                        {requirementsById[id]?.text ?? id}
                      </li>
                    ))}
                    {row.requirementIds.length === 0 && (
                      <li className="text-muted-foreground">
                        No requirements in this group.
                      </li>
                    )}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
