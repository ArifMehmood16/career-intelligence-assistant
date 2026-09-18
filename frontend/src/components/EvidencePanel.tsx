import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { useRef } from "react";
import { StatusMark } from "@/components/StatusMark";
import type { Evidence, RequirementStatus } from "@/types";

export type EvidenceResolveState = "idle" | "loading" | "ready" | "error";

export interface EvidencePanelProps {
  open: boolean;
  title: string;
  /** Omitted for sources that have no requirement status, such as chat citations. */
  status?: RequirementStatus | null;
  evidence: Evidence | null;
  /** Span resolution against GET /api/spans/{id}. Defaults to ready. */
  resolveState?: EvidenceResolveState;
  resolveError?: string | null;
  onOpenChange: (open: boolean) => void;
}

/**
 * Shared evidence panel. Knows nothing about requirements or chat citations:
 * it renders a title, a status and an Evidence object.
 * Right-hand panel at 420px on desktop, bottom sheet below 768px.
 * Radix Dialog supplies the focus trap, Escape handling and focus return.
 */
export function EvidencePanel({
  open,
  title,
  status,
  evidence,
  resolveState = "ready",
  resolveError = null,
  onOpenChange,
}: EvidencePanelProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-foreground/20" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            headingRef.current?.focus();
          }}
          className="fixed z-50 flex flex-col gap-4 overflow-y-auto border-border bg-surface p-5 inset-x-0 bottom-0 max-h-[85vh] rounded-t-md border-t md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[420px] md:rounded-none md:border-t-0 md:border-l"
        >
          <div className="flex items-start justify-between gap-4">
            <DialogPrimitive.Title asChild>
              <h2
                ref={headingRef}
                tabIndex={-1}
                className="text-sm font-semibold outline-none"
              >
                {title}
              </h2>
            </DialogPrimitive.Title>
            <DialogPrimitive.Close
              className="rounded-sm p-1 text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Close evidence"
            >
              <X className="size-4" aria-hidden="true" />
            </DialogPrimitive.Close>
          </div>

          {status ? <StatusMark status={status} /> : null}

          {resolveState === "loading" ? (
            <p className="text-muted-foreground" aria-busy="true">
              Loading evidence…
            </p>
          ) : resolveState === "error" ? (
            <p className="text-muted-foreground" role="alert">
              {resolveError ??
                "This citation could not be resolved. The span id did not match a stored passage."}
            </p>
          ) : evidence ? (
            <div className="space-y-2">
              <p className="text-muted-foreground">
                CV page <span className="font-mono">{evidence.page}</span>
              </p>
              <blockquote className="border-l-2 border-border pl-3 font-mono text-[13px] leading-relaxed">
                <HighlightedParagraph
                  paragraph={evidence.paragraph}
                  highlight={evidence.highlight}
                />
              </blockquote>
            </div>
          ) : (
            <p className="text-muted-foreground">
              No supporting text was found in your CV for this. Nothing in the
              parsed document matches it, so there is no passage to show.
            </p>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function HighlightedParagraph({
  paragraph,
  highlight,
}: {
  paragraph: string;
  highlight: string;
}) {
  const index = highlight ? paragraph.indexOf(highlight) : -1;
  if (index === -1) return <>{paragraph}</>;

  return (
    <>
      {paragraph.slice(0, index)}
      <mark className="bg-highlight text-foreground">{highlight}</mark>
      {paragraph.slice(index + highlight.length)}
    </>
  );
}
