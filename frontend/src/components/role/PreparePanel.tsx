/**
 * Phase 13.4 — interview preparation pack.
 * Presentational: pack and callbacks come from the container.
 */
import type { ReactNode } from "react";

import { StatusMark } from "@/components/StatusMark";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Evidence, InterviewPack } from "@/types";

export interface PreparePanelProps {
  state: AsyncState;
  pack: InterviewPack | null;
  onRetry: () => void;
  onSelectEvidence: (evidence: Evidence) => void;
  onExport: () => void;
  exportError?: string | null;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="space-y-3">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export function PreparePanel({
  state,
  pack,
  onRetry,
  onSelectEvidence,
  onExport,
  exportError = null,
}: PreparePanelProps) {
  return (
    <section
      aria-label="Prepare"
      className="rounded-md border border-border bg-surface p-5"
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-sm font-semibold">Interview pack</h2>
        {state === "ready" ? (
          <div className="space-y-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onExport}
            >
              Export Markdown
            </Button>
            {exportError ? (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">{exportError}</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={onExport}
                >
                  Retry export
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-4">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="space-y-2">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-12 w-full" />
            </div>
          ))}
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The interview pack could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="text-muted-foreground">
          No interview pack is available for this role yet.
        </p>
      )}

      {state === "ready" && pack !== null && (
        <div className="space-y-8">
          <Section title="What they will probe">
            {pack.probes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No probes listed.</p>
            ) : (
              <ul className="space-y-3">
                {pack.probes.map((probe) => (
                  <li
                    key={probe.requirementId}
                    className="space-y-1 border-b border-border pb-3 last:border-b-0 last:pb-0"
                  >
                    <StatusMark status={probe.status} />
                    <p className="text-sm text-foreground">{probe.question}</p>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Evidence to lead with">
            {pack.leadWith.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No met must-haves to lead with.
              </p>
            ) : (
              <ul className="space-y-3">
                {pack.leadWith.map((lead) => (
                  <li key={lead.requirementId} className="space-y-2">
                    <p className="text-sm text-muted-foreground">{lead.note}</p>
                    <button
                      type="button"
                      onClick={() => onSelectEvidence(lead.evidence)}
                      className="w-full rounded-sm border border-border bg-background px-3 py-2 text-left font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      {lead.evidence.highlight || lead.evidence.paragraph}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="Where you are thin">
            {pack.thinAreas.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No thin must-haves for this role.
              </p>
            ) : (
              <ul className="space-y-3">
                {pack.thinAreas.map((thin) => (
                  <li key={thin.requirementId} className="space-y-2">
                    <p className="text-sm font-medium text-foreground">
                      {thin.requirementText}
                    </p>
                    {thin.nearest ? (
                      <button
                        type="button"
                        onClick={() => onSelectEvidence(thin.nearest!)}
                        className="w-full rounded-sm border border-border bg-background px-3 py-2 text-left font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        Nearest:{" "}
                        {thin.nearest.highlight || thin.nearest.paragraph}
                      </button>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        No nearest claim in the CV.
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Section>

          <Section title="What to ask them">
            {pack.askThem.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No interviewer questions generated.
              </p>
            ) : (
              <ul className="space-y-2">
                {pack.askThem.map((ask, index) => (
                  <li
                    key={`${ask.requirementId ?? "ask"}-${index}`}
                    className="text-sm text-foreground"
                  >
                    {ask.question}
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      )}
    </section>
  );
}
