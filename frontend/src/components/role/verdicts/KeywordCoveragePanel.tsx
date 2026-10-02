import { TriangleAlert } from "lucide-react";

import type { KeywordCoverage } from "@/types";

export interface KeywordCoveragePanelProps {
  coverage: KeywordCoverage;
}

function Terms({ terms }: { terms: string[] }) {
  if (terms.length === 0) {
    return <p className="text-sm text-muted-foreground">None</p>;
  }
  return (
    <ul className="flex flex-wrap gap-1.5">
      {terms.map((term) => (
        <li
          key={term}
          className="rounded-md border border-border px-2 py-0.5 font-mono text-xs"
        >
          {term}
        </li>
      ))}
    </ul>
  );
}

/**
 * The advert's technology terms against the CV's wording. Shown beside the fit
 * score, never added to it: the judge has already seen them (ADR 014).
 */
export function KeywordCoveragePanel({ coverage }: KeywordCoveragePanelProps) {
  const total =
    coverage.exact.length + coverage.alias.length + coverage.missing.length;
  return (
    <section aria-labelledby="coverage-heading" className="space-y-3">
      <h2 id="coverage-heading" className="text-base font-medium">
        Keyword coverage
      </h2>
      {total === 0 ? (
        <p className="text-sm text-muted-foreground">
          The job description names no specific technologies.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <div
            role="group"
            aria-label="In your CV as written"
            className="space-y-1.5"
          >
            <h3 className="text-sm">In your CV as written</h3>
            <Terms terms={coverage.exact} />
          </div>
          <div
            role="group"
            aria-label="Only under another name"
            className="space-y-1.5"
          >
            <h3 className="inline-flex items-center gap-1 text-sm">
              <TriangleAlert aria-hidden="true" className="size-3.5" />
              Only under another name
            </h3>
            <Terms terms={coverage.alias} />
            {coverage.alias.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                An applicant-tracking system may miss these. Consider using the
                advert&apos;s wording where it is true.
              </p>
            ) : null}
          </div>
          <div role="group" aria-label="Not found" className="space-y-1.5">
            <h3 className="text-sm">Not found</h3>
            <Terms terms={coverage.missing} />
          </div>
        </div>
      )}
    </section>
  );
}
