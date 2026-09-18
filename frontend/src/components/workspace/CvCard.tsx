import { FileText, Upload } from "lucide-react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CvDocument } from "@/types";

export type CvCardState = "empty" | "parsing" | "parsed" | "error";

export interface CvCardProps {
  state: CvCardState;
  document: CvDocument | null;
  errorMessage: string | null;
  onUpload: (filename: string) => void;
  onReplace: (filename: string) => void;
  onDelete: () => void;
  onRetry: () => void;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function CvCard({
  state,
  document: cv,
  errorMessage,
  onUpload,
  onReplace,
  onDelete,
  onRetry,
}: CvCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const pickFile = () => inputRef.current?.click();

  return (
    <section
      aria-label="CV"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-4 text-sm font-semibold">Your CV</h2>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          if (state === "parsed") onReplace(file.name);
          else onUpload(file.name);
          event.target.value = "";
        }}
      />

      {state === "empty" && (
        <div className="rounded-md border border-dashed border-border px-5 py-8 text-center">
          <Upload
            className="mx-auto size-5 text-muted-foreground"
            aria-hidden="true"
          />
          <p className="mt-3 text-sm text-muted-foreground">
            Upload your CV. PDF or DOCX, up to 10MB
          </p>
          <Button type="button" className="mt-4" onClick={pickFile}>
            Browse
          </Button>
        </div>
      )}

      {state === "parsing" && (
        <div aria-busy="true" className="space-y-3">
          <div className="flex items-start gap-3">
            <Skeleton className="size-8 rounded-md" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-28" />
            </div>
          </div>
          <Skeleton className="h-3 w-48" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
          </div>
          <p className="text-sm text-muted-foreground">Parsing…</p>
        </div>
      )}

      {state === "parsed" && cv && (
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <span className="flex size-8 items-center justify-center rounded-md border border-border bg-background">
              <FileText
                className="size-4 text-muted-foreground"
                aria-hidden="true"
              />
            </span>
            <div className="min-w-0">
              <p className="truncate font-mono text-sm">{cv.filename}</p>
              <p className="text-sm text-muted-foreground">
                <span className="font-mono">{cv.pageCount}</span> pages
              </p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Parsed {formatTimestamp(cv.parsedAt)}
          </p>
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={pickFile}
            >
              Replace
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onDelete}
            >
              Delete
            </Button>
          </div>
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {errorMessage ?? "That CV could not be parsed."}
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </section>
  );
}
