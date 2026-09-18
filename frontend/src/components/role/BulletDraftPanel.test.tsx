/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BulletDraftPanel } from "./BulletDraftPanel";
import type { BulletDraft } from "@/types";

afterEach(() => {
  cleanup();
});

const draft: BulletDraft = {
  id: "draft-1",
  version: 1,
  createdAt: "2026-09-18T12:00:00Z",
  requirementId: "req-1",
  bullets: [
    {
      text: "- Migrated analytics pipelines onto Airflow DAGs.",
      spanIds: ["span-1"],
      evidence: [
        {
          spanId: "span-1",
          documentId: "doc-1",
          page: 1,
          paragraph: "Led Airflow DAG migrations for analytics pipelines.",
          highlight: "Airflow DAG migrations",
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

describe("BulletDraftPanel", () => {
  it("shows loading and error states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    const { rerender } = render(
      <BulletDraftPanel
        state="loading"
        draft={null}
        onRetry={onRetry}
        onCopy={vi.fn()}
        onCitation={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(
      <BulletDraftPanel
        state="error"
        draft={null}
        onRetry={onRetry}
        onCopy={vi.fn()}
        onCitation={vi.fn()}
        onDismiss={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/bullet draft could not be created/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("renders bullets, citations, provenance, template fallback, and copy", async () => {
    const user = userEvent.setup();
    const onCopy = vi.fn();
    const onCitation = vi.fn();
    const onDismiss = vi.fn();

    render(
      <BulletDraftPanel
        state="ready"
        draft={draft}
        onRetry={vi.fn()}
        onCopy={onCopy}
        onCitation={onCitation}
        onDismiss={onDismiss}
      />,
    );

    expect(screen.getByText(/draft bullet/i)).toBeInTheDocument();
    expect(screen.getByText(/template fallback/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Migrated analytics pipelines onto Airflow DAGs/),
    ).toBeInTheDocument();
    expect(screen.getByText(/hermetic/i)).toBeInTheDocument();
    expect(screen.getByText(/stayed local/i)).toBeInTheDocument();

    const chip = screen.getByRole("button", {
      name: /Airflow DAG migrations/i,
    });
    await user.click(chip);
    expect(onCitation).toHaveBeenCalledWith(draft.bullets[0]!.evidence[0]);

    await user.click(screen.getByRole("button", { name: /^Copy$/i }));
    expect(onCopy).toHaveBeenCalledWith(
      "- Migrated analytics pipelines onto Airflow DAGs.",
    );

    await user.click(
      within(screen.getByRole("region")).getByRole("button", {
        name: /dismiss/i,
      }),
    );
    expect(onDismiss).toHaveBeenCalled();
  });
});
