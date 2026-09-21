/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PreparePanel } from "./PreparePanel";
import type { InterviewPack } from "@/types";

afterEach(() => {
  cleanup();
});

const evidence = {
  spanId: "span-1",
  documentId: "doc-1",
  page: 1,
  paragraph: "Owned production dbt models for finance reporting.",
  highlight: "production dbt models",
};

const pack: InterviewPack = {
  roleId: "role-1",
  probes: [
    {
      requirementId: "req-1",
      question: "Tell me about your production dbt work.",
      status: "met",
    },
  ],
  leadWith: [
    {
      requirementId: "req-1",
      evidence,
      note: "Lead with the finance reporting models.",
    },
  ],
  thinAreas: [
    {
      requirementId: "req-2",
      requirementText: "Kubernetes administration",
      nearest: null,
    },
  ],
  askThem: [
    {
      question: "What does platform ownership look like for this team?",
      requirementId: null,
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

describe("PreparePanel", () => {
  it("shows loading, error, and empty states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    const { rerender } = render(
      <PreparePanel
        state="loading"
        pack={null}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onExport={vi.fn()}
      />,
    );
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(
      <PreparePanel
        state="error"
        pack={null}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onExport={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/interview pack could not be loaded/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();

    rerender(
      <PreparePanel
        state="empty"
        pack={null}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onExport={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/no interview pack is available/i),
    ).toBeInTheDocument();
  });

  it("renders four sections, clickable evidence, and export", async () => {
    const user = userEvent.setup();
    const onSelectEvidence = vi.fn();
    const onExport = vi.fn();

    render(
      <PreparePanel
        state="ready"
        pack={pack}
        onRetry={vi.fn()}
        onSelectEvidence={onSelectEvidence}
        onExport={onExport}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /what they will probe/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /evidence to lead with/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /where you are thin/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /what to ask them/i }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/Tell me about your production dbt work/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Kubernetes administration/)).toBeInTheDocument();
    expect(
      screen.getByText(/platform ownership look like/),
    ).toBeInTheDocument();

    const lead = screen.getByRole("region", {
      name: /evidence to lead with/i,
    });
    await user.click(
      within(lead).getByRole("button", { name: /production dbt models/i }),
    );
    expect(onSelectEvidence).toHaveBeenCalledWith(evidence);

    await user.click(screen.getByRole("button", { name: /export markdown/i }));
    expect(onExport).toHaveBeenCalled();
  });

  it("surfaces an export failure with a retryable control", async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();

    render(
      <PreparePanel
        state="ready"
        pack={pack}
        exportError="The interview pack could not be exported."
        onRetry={vi.fn()}
        onSelectEvidence={vi.fn()}
        onExport={onExport}
      />,
    );

    expect(
      screen.getByText(/interview pack could not be exported/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry export/i }));
    expect(onExport).toHaveBeenCalled();
  });
});
