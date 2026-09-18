/**
 * Original CIA monogram mark — Career Intelligence Assistant.
 * Geometric letterforms only; no third-party trademark or stock icon.
 */
export function CiaMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} role="img" aria-label="CIA">
      <rect width="32" height="32" rx="6" fill="currentColor" />
      {/* C */}
      <path
        fill="none"
        stroke="var(--cia-mark-ink, hsl(var(--background)))"
        strokeWidth="2.2"
        strokeLinecap="round"
        d="M12.5 10.2a6 6 0 1 0 0 11.6"
      />
      {/* I */}
      <path
        fill="none"
        stroke="var(--cia-mark-ink, hsl(var(--background)))"
        strokeWidth="2.2"
        strokeLinecap="round"
        d="M16.5 10.5v11"
      />
      {/* A */}
      <path
        fill="none"
        stroke="var(--cia-mark-ink, hsl(var(--background)))"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20 21.5l2.6-11 2.6 11M20.8 17.8h3.6"
      />
    </svg>
  );
}
