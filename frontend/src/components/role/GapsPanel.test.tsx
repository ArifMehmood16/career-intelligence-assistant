/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GapsPanel } from "./GapsPanel";
import type { GapItem } from "@/types";

afterEach(() => {
  cleanup();
});

const evidence = {
  spanId: "span-1",
  documentId: "doc-1",
  page: 1,
  paragraph: "Led Airflow DAG migrations for analytics pipelines.",
  highlight: "Airflow DAG migrations",
};

function gap(overrides: Partial<GapItem> = {}): GapItem {
  return {
    requirementId: "req-1",
    requirementText: "Production Airflow experience",
    type: "must",
    status: "partial",
    reason: "adjacent_claim_only",
    adjacentEvidence: evidence,
    scoreDelta: 9,
    action: "evidence_it",
    canDraftBullet: true,
    ...overrides,
  };
}

describe("GapsPanel", () => {
  it("shows loading, error, and empty states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    const { rerender } = render(
      <GapsPanel
        state="loading"
        currentScore={0}
        items={[]}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onDraftBullet={vi.fn()}
      />,
    );
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(
      <GapsPanel
        state="error"
        currentScore={0}
        items={[]}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onDraftBullet={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/gap plan could not be loaded/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();

    rerender(
      <GapsPanel
        state="empty"
        currentScore={72}
        items={[]}
        onRetry={onRetry}
        onSelectEvidence={vi.fn()}
        onDraftBullet={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/no missing or partial requirements/i),
    ).toBeInTheDocument();
  });

  it("lists gaps with reason, score delta, action, and draft when allowed", async () => {
    const user = userEvent.setup();
    const onSelectEvidence = vi.fn();
    const onDraftBullet = vi.fn();
    const items = [
      gap({
        requirementId: "req-high",
        requirementText: "dbt in production",
        scoreDelta: 12,
        canDraftBullet: true,
      }),
      gap({
        requirementId: "req-low",
        requirementText: "Kubernetes administration",
        type: "desirable",
        status: "missing",
        reason: "no_related_claim",
        adjacentEvidence: null,
        scoreDelta: 2,
        action: "learn_it",
        canDraftBullet: false,
      }),
    ];

    render(
      <GapsPanel
        state="ready"
        currentScore={61}
        items={items}
        onRetry={vi.fn()}
        onSelectEvidence={onSelectEvidence}
        onDraftBullet={onDraftBullet}
      />,
    );

    expect(screen.getByText(/current score/i)).toHaveTextContent("61");
    const list = screen.getByRole("list", { name: /gap plan/i });
    const rows = within(list).getAllByRole("listitem");
    const first = rows[0];
    const second = rows[1];
    expect(first).toBeDefined();
    expect(second).toBeDefined();
    if (!first || !second) {
      throw new Error("expected two gap rows");
    }
    expect(first).toHaveTextContent("dbt in production");
    expect(first).toHaveTextContent(/\+12/);
    expect(first).toHaveTextContent(/adjacent claim does not match/i);
    expect(first).toHaveTextContent(/evidence it/i);

    await user.click(
      within(first).getByRole("button", { name: /adjacent evidence/i }),
    );
    expect(onSelectEvidence).toHaveBeenCalledWith(items[0]);

    await user.click(
      within(first).getByRole("button", { name: /draft a bullet/i }),
    );
    expect(onDraftBullet).toHaveBeenCalledWith(items[0]);

    expect(
      within(second).queryByRole("button", { name: /draft a bullet/i }),
    ).toBeNull();
    expect(second).toHaveTextContent(/nothing in the cv addresses it/i);
    expect(second).toHaveTextContent(/learn it/i);
  });
});
