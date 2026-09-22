/**
 * Phase 13.2 — ordered gap plan for a role.
 * Presentational: data and callbacks come from the container.
 */
import { StatusMark } from "@/components/StatusMark";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  GapItem,
  GapItemAction,
  GapItemReason,
  RequirementType,
} from "@/types";

export interface GapsPanelProps {
  state: AsyncState;
  currentScore: number;
  items: GapItem[];
  onRetry: () => void;
  onSelectEvidence: (item: GapItem) => void;
  onDraftBullet: (item: GapItem) => void;
}

const REASON_LABEL: Record<GapItemReason, string> = {
  no_related_claim: "Nothing in the CV addresses it",
  adjacent_claim_only: "An adjacent claim does not match",
  evidence_too_old: "Evidence is older than the recency window",
  evidence_thin: "Evidence is present but thin",
};

const ACTION_LABEL: Record<GapItemAction, string> = {
  evidence_it: "Evidence it",
  learn_it: "Learn it",
  accept_it: "Accept it",
};

function formatScore(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function liftCopy(item: GapItem, currentScore: number): string {
  const kind = item.type === "must" ? "must-have" : "desirable";
  const from = formatScore(currentScore);
  const to = formatScore(currentScore + item.scoreDelta);
  return `If this ${kind} were met, the fit score would rise from ${from} → ${to} / 100.`;
}

function TypeBadge({ type }: { type: RequirementType }) {
  return (
    <span className="inline-flex items-center rounded-none border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">
      {type === "must" ? "Must" : "Desirable"}
    </span>
  );
}

function adjacentExcerpt(item: GapItem): string {
  if (!item.adjacentEvidence) return "";
  const text =
    item.adjacentEvidence.highlight || item.adjacentEvidence.paragraph;
  return text.length > 100 ? `${text.slice(0, 100)}…` : text;
}

export function GapsPanel({
  state,
  currentScore,
  items,
  onRetry,
  onSelectEvidence,
  onDraftBullet,
}: GapsPanelProps) {
  return (
    <section
      aria-label="Gaps"
      className="rounded-md border border-border bg-surface p-5"
    >
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold">Gap plan</h2>
        {state === "ready" || state === "empty" ? (
          <p className="font-mono text-sm text-muted-foreground">
            Current score{" "}
            <span className="text-foreground tabular-nums">
              {formatScore(currentScore)}
            </span>
          </p>
        ) : null}
      </div>
      {state === "ready" ? (
        <p className="mb-4 text-sm text-muted-foreground">
          Ordered by how many points the fit score would gain if you closed
          the gap. Missing or partial is the mapping; must or desirable is how
          the job listed it. The lift is the same arithmetic as the Fit tab,
          not a model guess.
        </p>
      ) : null}

      {state === "loading" && (
        <div aria-busy="true" className="space-y-4">
          {[0, 1, 2].map((row) => (
            <div key={row} className="space-y-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The gap plan could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="text-muted-foreground">
          No missing or partial requirements for this role.
        </p>
      )}

      {state === "ready" && (
        <ol aria-label="Gap plan" className="space-y-4">
          {items.map((item) => (
            <li
              key={item.requirementId}
              className="space-y-3 border-b border-border pb-4 last:border-b-0 last:pb-0"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusMark status={item.status} />
                    <TypeBadge type={item.type} />
                    <span className="font-mono text-sm tabular-nums text-foreground">
                      +{formatScore(item.scoreDelta)} if met
                    </span>
                  </div>
                  <p className="text-sm font-medium text-foreground">
                    {item.requirementText}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {liftCopy(item, currentScore)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {REASON_LABEL[item.reason]}
                  </p>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Suggested action: {ACTION_LABEL[item.action]}
                  </p>
                </div>
                {item.canDraftBullet ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => onDraftBullet(item)}
                  >
                    Draft a bullet
                  </Button>
                ) : null}
              </div>

              {item.adjacentEvidence ? (
                <button
                  type="button"
                  aria-label="Adjacent evidence"
                  onClick={() => onSelectEvidence(item)}
                  className="w-full rounded-sm border border-border bg-background px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <p className="mb-1 text-xs text-muted-foreground">
                    Nearest adjacent claim
                  </p>
                  <p className="font-mono text-xs leading-relaxed text-foreground">
                    {adjacentExcerpt(item)}
                  </p>
                </button>
              ) : (
                <p className="text-xs text-muted-foreground">
                  No adjacent claim in the CV.
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
