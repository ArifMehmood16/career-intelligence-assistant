/**
 * Phase 13.5 — cover letter draft controls, versions, refusal, supporting docs.
 * Presentational: data and callbacks come from the container.
 */
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import type { AsyncState } from "@/components/role/FitBreakdown";
import {
  citationNumberBySpanId,
  numberLetterCitations,
} from "@/components/role/letterCitations";
import type { CoverLetterDraft, SupportingDocument } from "@/types";

export type LetterTone = "plain" | "warm";

export interface LetterRefusal {
  message: string;
}

export interface LetterCitation {
  number: number;
  spanId: string;
  /** Resolved passage text; null while loading. */
  text: string | null;
  loading?: boolean;
  error?: boolean;
}

export interface LetterPanelProps {
  tone: LetterTone;
  includeGapLine: boolean;
  generating: boolean;
  draft: CoverLetterDraft | null;
  versions: CoverLetterDraft[];
  refusal: LetterRefusal | null;
  supportingDocuments: SupportingDocument[];
  /** Numbered glossary entries for the active draft. */
  citations?: LetterCitation[];
  generatedState?: AsyncState;
  supportingState?: AsyncState;
  onRetryGenerated?: () => void;
  onRetrySupporting?: () => void;
  exportError?: string | null;
  onToneChange: (tone: LetterTone) => void;
  onIncludeGapLineChange: (include: boolean) => void;
  onGenerate: () => void;
  onSelectVersion: (draft: CoverLetterDraft) => void;
  onExport: (draft: CoverLetterDraft) => void;
  onCitation: (spanId: string) => void;
  onOpenGaps: () => void;
}

export function LetterPanel({
  tone,
  includeGapLine,
  generating,
  draft,
  versions,
  refusal,
  supportingDocuments,
  citations = [],
  generatedState = "ready",
  supportingState = "ready",
  onRetryGenerated,
  onRetrySupporting,
  exportError = null,
  onToneChange,
  onIncludeGapLineChange,
  onGenerate,
  onSelectVersion,
  onExport,
  onCitation,
  onOpenGaps,
}: LetterPanelProps) {
  const [activeNumber, setActiveNumber] = useState<number | null>(null);

  const numberBySpan = useMemo(() => {
    if (citations.length > 0) {
      return new Map(citations.map((item) => [item.spanId, item.number]));
    }
    if (!draft) return new Map<string, number>();
    return citationNumberBySpanId(numberLetterCitations(draft.paragraphs));
  }, [citations, draft]);

  const glossary = useMemo((): LetterCitation[] => {
    if (citations.length > 0) return citations;
    if (!draft) return [];
    return numberLetterCitations(draft.paragraphs).map((item) => ({
      number: item.number,
      spanId: item.spanId,
      text: null,
    }));
  }, [citations, draft]);

  useEffect(() => {
    setActiveNumber(null);
  }, [draft?.id]);

  const selectCitation = (spanId: string) => {
    const number = numberBySpan.get(spanId) ?? null;
    setActiveNumber(number);
    onCitation(spanId);
  };

  return (
    <div className="space-y-6">
      <section
        aria-label="Letter controls"
        className="rounded-md border border-border bg-surface p-5"
      >
        <h2 className="mb-4 text-sm font-semibold">Cover letter draft</h2>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Tone</Label>
            <RadioGroup
              value={tone}
              onValueChange={(value) => {
                if (value === "plain" || value === "warm") {
                  onToneChange(value);
                }
              }}
              className="flex flex-wrap gap-4"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem value="plain" id="tone-plain" />
                <Label htmlFor="tone-plain" className="font-normal">
                  Plain
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem value="warm" id="tone-warm" />
                <Label htmlFor="tone-warm" className="font-normal">
                  Warm
                </Label>
              </div>
            </RadioGroup>
          </div>

          <div className="flex items-center gap-2">
            <input
              id="include-gap-line"
              type="checkbox"
              checked={includeGapLine}
              onChange={(event) => onIncludeGapLineChange(event.target.checked)}
              className="size-4 rounded-sm border border-border"
            />
            <Label htmlFor="include-gap-line" className="font-normal">
              Include an honest line about the largest gap
            </Label>
          </div>

          <Button type="button" onClick={onGenerate} disabled={generating}>
            {generating ? "Generating…" : "Generate letter"}
          </Button>
        </div>

        {refusal ? (
          <div
            role="status"
            className="mt-4 space-y-3 rounded-sm border border-border bg-background px-3 py-3"
          >
            <p className="text-sm text-foreground">{refusal.message}</p>
            <p className="text-sm text-muted-foreground">
              Next step: close the gaps that matter most, then try again.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onOpenGaps}
            >
              Open Gaps
            </Button>
          </div>
        ) : null}
      </section>

      {draft ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)] lg:items-start">
          <section
            aria-label="Generated letter"
            className="rounded-md border border-border bg-surface p-5"
          >
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">
                  Version {draft.version}
                </h3>
                <p className="font-mono text-[11px] text-muted-foreground">
                  {draft.provenance.model ?? "template"} ·{" "}
                  {draft.provenance.provider} ·{" "}
                  {draft.provenance.leftMachine
                    ? "left this machine"
                    : "stayed local"}
                </p>
              </div>
              <div className="space-y-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    onExport(draft);
                  }}
                >
                  Export Markdown
                </Button>
                {exportError ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      {exportError}
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        onExport(draft);
                      }}
                    >
                      Retry export
                    </Button>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="space-y-4">
              {draft.paragraphs.map((paragraph, index) => {
                const numbers = [
                  ...new Set(
                    paragraph.spanIds
                      .map((spanId) => numberBySpan.get(spanId))
                      .filter((value): value is number => value != null),
                  ),
                ];
                return (
                  <div key={`${draft.id}-p-${index}`} className="space-y-2">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                      {paragraph.text}
                      {numbers.length > 0 ? (
                        <span className="ml-1 inline-flex flex-wrap gap-1 align-super">
                          {numbers.map((number) => (
                            <button
                              key={`${index}-${number}`}
                              type="button"
                              aria-label={`Citation ${number}`}
                              aria-pressed={activeNumber === number}
                              onClick={() => {
                                const match = glossary.find(
                                  (item) => item.number === number,
                                );
                                if (match) selectCitation(match.spanId);
                                else {
                                  const spanId = paragraph.spanIds.find(
                                    (id) => numberBySpan.get(id) === number,
                                  );
                                  if (spanId) selectCitation(spanId);
                                }
                              }}
                              className={
                                activeNumber === number
                                  ? "rounded-sm border border-foreground bg-foreground px-1.5 py-0.5 text-[11px] font-medium text-background outline-none focus-visible:ring-2 focus-visible:ring-ring"
                                  : "rounded-sm border border-border bg-background px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground outline-none hover:border-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                              }
                            >
                              [{number}]
                            </button>
                          ))}
                        </span>
                      ) : null}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          <aside
            aria-label="Citation glossary"
            className="rounded-md border border-border bg-surface p-5 lg:sticky lg:top-4"
          >
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold">Citations</h3>
              <p className="text-[11px] text-muted-foreground">
                Source passages
              </p>
            </div>
            {glossary.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No cited passages for this version.
              </p>
            ) : (
              <ol className="space-y-3">
                {glossary.map((citation) => {
                  const selected = activeNumber === citation.number;
                  return (
                    <li key={citation.spanId}>
                      <button
                        type="button"
                        aria-label={`Citation ${citation.number} details`}
                        aria-pressed={selected}
                        onClick={() => selectCitation(citation.spanId)}
                        className={
                          selected
                            ? "w-full rounded-md border border-foreground bg-background px-3 py-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            : "w-full rounded-md border border-border bg-background px-3 py-3 text-left outline-none hover:border-foreground focus-visible:ring-2 focus-visible:ring-ring"
                        }
                      >
                        <span className="mb-1 block text-xs font-semibold text-foreground">
                          [{citation.number}]
                        </span>
                        {citation.loading ? (
                          <span className="block text-sm text-muted-foreground">
                            Loading passage…
                          </span>
                        ) : citation.error ? (
                          <span className="block text-sm text-muted-foreground">
                            This citation could not be resolved.
                          </span>
                        ) : (
                          <span className="block whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                            {citation.text?.trim() || "Passage unavailable."}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ol>
            )}
          </aside>
        </div>
      ) : null}

      {generatedState === "loading" ? (
        <section
          aria-label="Version history"
          className="rounded-md border border-border bg-surface p-5"
        >
          <div aria-busy="true" className="space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-9 w-24" />
          </div>
        </section>
      ) : generatedState === "error" ? (
        <section
          aria-label="Version history"
          className="rounded-md border border-border bg-surface p-5"
        >
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Generated letters could not be loaded.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetryGenerated}
            >
              Retry generated letters
            </Button>
          </div>
        </section>
      ) : versions.length > 0 ? (
        <section
          aria-label="Version history"
          className="rounded-md border border-border bg-surface p-5"
        >
          <h3 className="mb-3 text-sm font-semibold">Version history</h3>
          <ul className="flex flex-wrap gap-2">
            {versions.map((version) => (
              <li key={version.id}>
                <Button
                  type="button"
                  size="sm"
                  variant={draft?.id === version.id ? "default" : "outline"}
                  onClick={() => onSelectVersion(version)}
                >
                  Version {version.version}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section
        aria-label="Supporting cover letters"
        className="rounded-md border border-dashed border-border bg-surface p-5"
      >
        <h3 className="mb-2 text-sm font-semibold">
          Uploaded supporting letters
        </h3>
        <p className="mb-3 text-sm text-muted-foreground">
          Shown separately as supporting documents, never as generated versions.
        </p>
        {supportingState === "loading" ? (
          <div aria-busy="true" className="space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-1/3" />
          </div>
        ) : supportingState === "error" ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Supporting letters could not be loaded.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onRetrySupporting}
            >
              Retry supporting letters
            </Button>
          </div>
        ) : supportingDocuments.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No supporting cover letters uploaded on the workspace.
          </p>
        ) : (
          <ul className="space-y-2">
            {supportingDocuments.map((doc) => (
              <li key={doc.id} className="font-mono text-sm text-foreground">
                {doc.filename}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
