/**
 * Phase 13.5 — cover letter draft controls, versions, refusal, supporting docs.
 * Presentational: data and callbacks come from the container.
 */
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { CoverLetterDraft, SupportingDocument } from "@/types";

export type LetterTone = "plain" | "warm";

export interface LetterRefusal {
  message: string;
}

export interface LetterPanelProps {
  tone: LetterTone;
  includeGapLine: boolean;
  generating: boolean;
  draft: CoverLetterDraft | null;
  versions: CoverLetterDraft[];
  refusal: LetterRefusal | null;
  supportingDocuments: SupportingDocument[];
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
  onToneChange,
  onIncludeGapLineChange,
  onGenerate,
  onSelectVersion,
  onExport,
  onCitation,
  onOpenGaps,
}: LetterPanelProps) {
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
        <section
          aria-label="Generated letter"
          className="rounded-md border border-border bg-surface p-5"
        >
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Version {draft.version}</h3>
              <p className="font-mono text-[11px] text-muted-foreground">
                {draft.provenance.model ?? "template"} ·{" "}
                {draft.provenance.provider} ·{" "}
                {draft.provenance.leftMachine
                  ? "left this machine"
                  : "stayed local"}
              </p>
            </div>
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
          </div>

          <div className="space-y-4">
            {draft.paragraphs.map((paragraph, index) => (
              <div key={`${draft.id}-p-${index}`} className="space-y-2">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {paragraph.text}
                </p>
                {paragraph.spanIds.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {paragraph.spanIds.map((spanId) => (
                      <button
                        key={`${index}-${spanId}`}
                        type="button"
                        onClick={() => onCitation(spanId)}
                        className="rounded-md border border-border bg-background px-2 py-1 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {spanId}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {versions.length > 0 ? (
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
        {supportingDocuments.length === 0 ? (
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
