import { FileText, Upload } from "lucide-react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import type { SupportingDocument } from "@/types";

export type CoverLettersCardState = "loading" | "ready" | "error";

export interface CoverLettersCardProps {
  state: CoverLettersCardState;
  documents: SupportingDocument[];
  errorMessage: string | null;
  uploading: boolean;
  onUpload: (file: File) => void;
  onDelete: (id: string) => void;
  onRetry: () => void;
}

export function CoverLettersCard({
  state,
  documents,
  errorMessage,
  uploading,
  onUpload,
  onDelete,
  onRetry,
}: CoverLettersCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <section
      aria-label="Cover letters"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-2 text-sm font-semibold">Supporting cover letters</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Optional. These help answer questions about your drafts, but they are
        never used as evidence for fit scores or requirement mappings.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt,application/pdf,text/plain"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          onUpload(file);
          event.target.value = "";
        }}
      />

      {state === "error" ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {errorMessage ?? "Cover letters could not be loaded."}
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.length === 0 && state === "ready" && (
            <p className="text-sm text-muted-foreground">
              No supporting cover letters uploaded yet.
            </p>
          )}
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <FileText
                    className="size-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <span className="truncate font-mono text-sm">
                    {doc.filename}
                  </span>
                </span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const confirmed = window.confirm(
                      `Delete ${doc.filename}? It will no longer be available for questions.`,
                    );
                    if (confirmed) onDelete(doc.id);
                  }}
                >
                  Delete
                </Button>
              </li>
            ))}
          </ul>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={uploading || state === "loading"}
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="size-4" aria-hidden="true" />
            {uploading ? "Uploading…" : "Upload cover letter"}
          </Button>
        </div>
      )}
    </section>
  );
}
