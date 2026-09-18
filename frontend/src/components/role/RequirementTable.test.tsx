/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RequirementTable } from "./RequirementTable";
import type { Requirement } from "@/types";

const requirement: Requirement = {
  id: "req-1",
  roleId: "role-1",
  text: "Production dbt experience",
  type: "must",
  status: "missing",
  evidence: null,
};

describe("RequirementTable states", () => {
  it("shows loading, error, and empty states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    const { rerender } = render(
      <RequirementTable
        state="loading"
        requirements={[]}
        collapsedGroups={[]}
        onToggleGroup={vi.fn()}
        onSelect={vi.fn()}
        onRetry={onRetry}
        layout="table"
      />,
    );
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(
      <RequirementTable
        state="error"
        requirements={[]}
        collapsedGroups={[]}
        onToggleGroup={vi.fn()}
        onSelect={vi.fn()}
        onRetry={onRetry}
        layout="table"
      />,
    );
    expect(
      screen.getByText(/requirements could not be loaded/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();

    rerender(
      <RequirementTable
        state="empty"
        requirements={[]}
        collapsedGroups={[]}
        onToggleGroup={vi.fn()}
        onSelect={vi.fn()}
        onRetry={onRetry}
        layout="table"
      />,
    );
    expect(
      screen.getByText(/no requirements have been extracted/i),
    ).toBeInTheDocument();
  });

  it("lets the user select a ready requirement", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <RequirementTable
        state="ready"
        requirements={[requirement]}
        collapsedGroups={[]}
        onToggleGroup={vi.fn()}
        onSelect={onSelect}
        onRetry={vi.fn()}
        layout="table"
      />,
    );
    await user.click(screen.getAllByText("Production dbt experience")[0]!);
    expect(onSelect).toHaveBeenCalledWith(requirement);
  });
});
