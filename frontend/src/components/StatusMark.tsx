import type { RequirementStatus } from "@/types";

const LABELS: Record<RequirementStatus, string> = {
  met: "Met",
  partial: "Partial",
  missing: "Missing",
};

export interface StatusMarkProps {
  status: RequirementStatus;
}

/**
 * Glyph plus word, always both — status is never carried by colour alone.
 * filled disc = met, half disc = partial, hollow ring = missing.
 */
export function StatusMark({ status }: StatusMarkProps) {
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap">
      <span aria-hidden="true" className="inline-flex">
        {status === "met" && (
          <svg viewBox="0 0 12 12" className="size-3 text-met" role="presentation">
            <circle cx="6" cy="6" r="5" fill="currentColor" />
          </svg>
        )}
        {status === "partial" && (
          <svg viewBox="0 0 12 12" className="size-3 text-partial" role="presentation">
            <circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M6 1 A5 5 0 0 1 6 11 Z" fill="currentColor" />
          </svg>
        )}
        {status === "missing" && (
          <svg viewBox="0 0 12 12" className="size-3 text-missing" role="presentation">
            <circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        )}
      </span>
      <span>{LABELS[status]}</span>
    </span>
  );
}

export function statusLabel(status: RequirementStatus): string {
  return LABELS[status];
}
