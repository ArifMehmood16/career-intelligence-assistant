/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RolesPanel } from "./RolesPanel";
import type { Role } from "@/types";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
    params?: Record<string, string>;
    className?: string;
    tabIndex?: number;
  }) => (
    <a href={props.to} className={props.className} tabIndex={props.tabIndex}>
      {children}
    </a>
  ),
  useNavigate: () => vi.fn(),
}));

const analysingRole: Role = {
  id: "role-a",
  title: "Analytics Engineer",
  company: "Acme",
  fitScore: 0,
  bandLabel: "Not scored yet",
  counts: { met: 0, partial: 0, missing: 0 },
  status: "analysing",
  updatedAt: "2026-09-18T12:00:00Z",
};

const failedRole: Role = {
  ...analysingRole,
  id: "role-f",
  title: "Failed Role",
  status: "failed",
};

describe("RolesPanel analysis status", () => {
  it("shows Analysing instead of a score while status is analysing", () => {
    render(
      <RolesPanel
        state="ready"
        roles={[analysingRole]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        addRoleSlot={null}
        layout="table"
      />,
    );

    expect(screen.getAllByText("Analysing").length).toBeGreaterThan(0);
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
  });

  it("shows Failed with reason and a Retry control", async () => {
    const user = userEvent.setup();
    const onReanalyse = vi.fn();

    render(
      <RolesPanel
        state="ready"
        roles={[failedRole]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        onReanalyse={onReanalyse}
        failureReasons={{ "role-f": "Provider timed out." }}
        addRoleSlot={null}
        layout="table"
      />,
    );

    expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Provider timed out.").length).toBeGreaterThan(
      0,
    );
    await user.click(
      screen.getAllByRole("button", { name: "Retry analysis" })[0]!,
    );
    expect(onReanalyse).toHaveBeenCalledWith("role-f");
  });
});
