/**
 * @vitest-environment jsdom
 *
 * Phase 13.10 — excerpts and generated text are escaped text, never HTML.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidencePanel } from "@/components/EvidencePanel";
import { VerdictsPanel } from "@/components/role/verdicts/VerdictsPanel";
import { VerdictGapsPanel } from "@/components/role/verdicts/VerdictGapsPanel";
import { VERDICTS } from "@/api/__fixtures__/verdicts";
import type { RoleVerdicts } from "@/types";

afterEach(() => {
  cleanup();
});

const xss = '<img src=x onerror="alert(1)">';
const scripty = "<script>window.__pwned=1</script>";

describe("Phase 13.10 escaped text", () => {
  it("renders evidence excerpts as text nodes, not HTML", () => {
    render(
      <EvidencePanel
        open={true}
        title="Requirement"
        status="met"
        evidence={{
          spanId: "span-1",
          documentId: "doc-1",
          page: 1,
          paragraph: `Lead with ${xss} in production.`,
          highlight: xss,
        }}
        onOpenChange={vi.fn()}
      />,
    );

    expect(
      screen.getByText(new RegExp(xss.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))),
    ).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
  });

  it("renders verdict evidence and gap statements as escaped text", () => {
    const verdicts: RoleVerdicts = {
      ...VERDICTS,
      verdicts: VERDICTS.verdicts.map((item) => ({
        ...item,
        quote: xss,
        statement: scripty,
        match: { ...item.match, rationale: scripty },
        evidence: [{ chunkId: "c1", documentId: "cv-1", quote: xss }],
      })),
    };
    render(
      <div>
        <VerdictsPanel
          state="ready"
          verdicts={verdicts}
          onRetry={vi.fn()}
          onShowTrace={vi.fn()}
        />
        <VerdictGapsPanel state="ready" verdicts={verdicts} onRetry={vi.fn()} />
      </div>,
    );
    expect(screen.getAllByText(scripty).length).toBeGreaterThan(0);
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
    expect(window).not.toHaveProperty("__pwned");
  });
});
