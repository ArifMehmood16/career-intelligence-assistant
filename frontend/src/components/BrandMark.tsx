/**
 * Product mark — a line of a CV, checked.
 * Original geometry; no third-party trademark or stock icon.
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      role="img"
      aria-label="Career Intelligence"
    >
      <rect width="32" height="32" rx="6" fill="currentColor" />
      {/* the check */}
      <path
        fill="none"
        stroke="var(--brand-mark-ink, hsl(var(--background)))"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.5 15.4 13.9 19.8 22.5 10.2"
      />
      {/* the line it was checked against */}
      <path
        fill="none"
        stroke="var(--brand-mark-ink, hsl(var(--background)))"
        strokeWidth="2.4"
        strokeLinecap="round"
        d="M10 23.8h12"
      />
    </svg>
  );
}
