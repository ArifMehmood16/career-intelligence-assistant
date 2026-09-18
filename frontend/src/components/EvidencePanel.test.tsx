/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EvidencePanel } from "./EvidencePanel";

describe("EvidencePanel resolve states", () => {
  it("shows a loading state while a span is resolving", () => {
    render(
      <EvidencePanel
        open
        title="5+ years of SQL"
        status="met"
        evidence={null}
        resolveState="loading"
        onOpenChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/loading evidence/i)).toBeInTheDocument();
  });

  it("surfaces an unresolvable span as a visible error, not an empty panel", () => {
    render(
      <EvidencePanel
        open
        title="5+ years of SQL"
        status="met"
        evidence={null}
        resolveState="error"
        resolveError="This citation could not be resolved (span_not_found)."
        onOpenChange={vi.fn()}
      />,
    );

    expect(screen.getByText(/could not be resolved/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/no supporting text was found/i),
    ).not.toBeInTheDocument();
  });
});
