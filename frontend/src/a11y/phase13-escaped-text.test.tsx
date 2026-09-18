/**
 * @vitest-environment jsdom
 *
 * Phase 13.10 — excerpts and generated text are escaped text, never HTML.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidencePanel } from "@/components/EvidencePanel";
import { BulletDraftPanel } from "@/components/role/BulletDraftPanel";
import { GapsPanel } from "@/components/role/GapsPanel";
import type { BulletDraft, GapItem } from "@/types";

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

  it("renders gap adjacent claims and bullet drafts as text", () => {
    const item: GapItem = {
      requirementId: "req-1",
      requirementText: scripty,
      type: "must",
      status: "partial",
      reason: "adjacent_claim_only",
      adjacentEvidence: {
        spanId: "span-1",
        documentId: "doc-1",
        page: 1,
        paragraph: xss,
        highlight: xss,
      },
      scoreDelta: 4,
      action: "evidence_it",
      canDraftBullet: true,
    };
    const draft: BulletDraft = {
      id: "d1",
      version: 1,
      createdAt: "2026-09-18T12:00:00Z",
      requirementId: "req-1",
      bullets: [
        {
          text: `- Shipped ${xss}`,
          spanIds: ["span-1"],
          evidence: [
            {
              spanId: "span-1",
              documentId: "doc-1",
              page: 1,
              paragraph: xss,
              highlight: xss,
            },
          ],
        },
      ],
      provenance: {
        provider: "hermetic",
        model: null,
        leftMachine: false,
        generatedAt: "2026-09-18T12:00:00Z",
        grounded: true,
        fallback: "template",
      },
    };

    render(
      <div>
        <GapsPanel
          state="ready"
          currentScore={50}
          items={[item]}
          onRetry={vi.fn()}
          onSelectEvidence={vi.fn()}
          onDraftBullet={vi.fn()}
        />
        <BulletDraftPanel
          state="ready"
          draft={draft}
          onRetry={vi.fn()}
          onCopy={vi.fn()}
          onCitation={vi.fn()}
          onDismiss={vi.fn()}
        />
      </div>,
    );

    expect(screen.getByText(scripty)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("img")).toBeNull();
    expect(window).not.toHaveProperty("__pwned");
  });
});
