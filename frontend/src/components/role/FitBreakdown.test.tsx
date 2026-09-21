/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FitBreakdown } from "./FitBreakdown";

describe("FitBreakdown states", () => {
  it("shows loading skeletons", () => {
    const { container } = render(
      <FitBreakdown
        state="loading"
        rows={[]}
        requirementsById={{}}
        expandedRowIds={[]}
        onToggleRow={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
  });

  it("shows an actionable error state", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <FitBreakdown
        state="error"
        rows={[]}
        requirementsById={{}}
        expandedRowIds={[]}
        onToggleRow={vi.fn()}
        onRetry={onRetry}
      />,
    );
    expect(
      screen.getByText(/breakdown could not be loaded/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("shows empty copy when there are no rows", () => {
    render(
      <FitBreakdown
        state="empty"
        rows={[]}
        requirementsById={{}}
        expandedRowIds={[]}
        onToggleRow={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText(/no breakdown is available/i)).toBeInTheDocument();
  });

  it("renders ready rows with scores", () => {
    render(
      <FitBreakdown
        state="ready"
        rows={[
          {
            id: "must",
            label: "Must-have match",
            value: 0.8,
            requirementIds: [],
          },
        ]}
        requirementsById={{}}
        expandedRowIds={[]}
        onToggleRow={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Must-have match")).toBeInTheDocument();
  });

  it("renders the prose fit summary above the component rows", () => {
    render(
      <FitBreakdown
        state="ready"
        summary="The strongest match is “Production dbt experience”. The biggest gap is “CUDA kernel authoring”."
        rows={[
          {
            id: "must",
            label: "Must-have match",
            value: 0.8,
            requirementIds: [],
          },
        ]}
        requirementsById={{}}
        expandedRowIds={[]}
        onToggleRow={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/strongest match is “Production dbt experience”/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/biggest gap is “CUDA kernel authoring”/),
    ).toBeInTheDocument();
  });
});
