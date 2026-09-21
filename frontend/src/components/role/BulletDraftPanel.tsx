/**
 * Phase 13.3 — evidence-grounded CV bullet draft surface.
 * Presentational: draft payload and callbacks come from the container.
 */
import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { BulletDraft, Evidence } from "@/types";

export interface BulletDraftPanelProps {
  state: AsyncState;
  draft: BulletDraft | null;
  onRetry: () => void;
  onCopy: (text: string) => void;
  onCitation: (evidence: Evidence) => void;
  onDismiss: () => void;
  copyError?: string | null;
}

function provenanceLine(draft: BulletDraft): string {
  const provider = draft.provenance.provider;
  const model = draft.provenance.model ?? "template";
  const locality = draft.provenance.leftMachine
    ? "left this machine"
    : "stayed local";
  return `${model} · ${provider} · ${locality}`;
}

export function BulletDraftPanel({
  state,
  draft,
  onRetry,
  onCopy,
  onCitation,
  onDismiss,
  copyError = null,
}: BulletDraftPanelProps) {
  if (state === "empty" || (state === "ready" && draft === null)) {
    return null;
  }

  return (
    <section
      aria-label="Bullet draft"
      role="region"
      className="rounded-md border border-border bg-surface p-5"
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-sm font-semibold">Draft bullet</h2>
          <p className="text-xs text-muted-foreground">
            Draft only — nothing is written back into your CV.
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={onDismiss}>
          Dismiss
        </Button>
      </div>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-3">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The bullet draft could not be created.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "ready" && draft !== null && (
        <div className="space-y-4">
          {draft.provenance.fallback === "template" ? (
            <p
              role="status"
              className="rounded-sm border border-border bg-background px-3 py-2 text-sm text-muted-foreground"
            >
              Template fallback — this draft was built from your claim text
              without a model rewrite.
            </p>
          ) : null}

          <ul className="space-y-4">
            {draft.bullets.map((bullet, index) => (
              <li key={`${draft.id}-${index}`} className="space-y-3">
                <p className="whitespace-pre-wrap font-mono text-sm leading-relaxed text-foreground">
                  {bullet.text}
                </p>
                {bullet.evidence.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {bullet.evidence.map((evidence) => (
                      <button
                        key={evidence.spanId}
                        type="button"
                        onClick={() => onCitation(evidence)}
                        className="rounded-md border border-border bg-background px-2 py-1 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {evidence.highlight || `p.${evidence.page}`}
                      </button>
                    ))}
                  </div>
                ) : null}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onCopy(bullet.text)}
                >
                  Copy
                </Button>
              </li>
            ))}
          </ul>

          {copyError ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{copyError}</p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const first = draft.bullets[0];
                  if (first) onCopy(first.text);
                }}
              >
                Retry copy
              </Button>
            </div>
          ) : null}

          <p className="font-mono text-[11px] text-muted-foreground">
            {provenanceLine(draft)}
          </p>
        </div>
      )}
    </section>
  );
}
