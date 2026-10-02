/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RolesPanel } from "./RolesPanel";
import { deriveRolesPanelState } from "./roles-panel-state";
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

afterEach(() => {
  cleanup();
});

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

describe("RolesPanel screen states", () => {
  const panelProps = {
    roles: [] as Role[],
    sortKey: "fit" as const,
    sortDirection: "desc" as const,
    onSort: vi.fn(),
    onRetry: vi.fn(),
    addRoleSlot: null,
    layout: "table" as const,
  };

  it("shows inert, empty, loading and error states", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(
      <RolesPanel {...panelProps} state="inert" onRetry={onRetry} />,
    );
    expect(screen.getByText(/add your cv first/i)).toBeInTheDocument();

    rerender(<RolesPanel {...panelProps} state="empty" onRetry={onRetry} />);
    expect(screen.getByText(/no roles yet/i)).toBeInTheDocument();

    rerender(<RolesPanel {...panelProps} state="loading" onRetry={onRetry} />);
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(<RolesPanel {...panelProps} state="error" onRetry={onRetry} />);
    expect(screen.getByText(/roles could not be loaded/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("treats a failed CV query as error, not as add-your-CV inert", () => {
    expect(
      deriveRolesPanelState({
        cvStatus: "error",
        rolesStatus: "success",
        hasCv: false,
        roleCount: 0,
      }),
    ).toBe("error");
    expect(
      deriveRolesPanelState({
        cvStatus: "success",
        rolesStatus: "error",
        hasCv: true,
        roleCount: 0,
      }),
    ).toBe("error");
    expect(
      deriveRolesPanelState({
        cvStatus: "success",
        rolesStatus: "success",
        hasCv: false,
        roleCount: 0,
      }),
    ).toBe("inert");
  });
});

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

  it("shows each analysing role's progress when the server sends it", () => {
    const running: Role = {
      ...analysingRole,
      activeJob: {
        id: "job-a",
        kind: "role_analysis",
        state: "running",
        stage: "extracting_claims",
        startedAt: "2026-09-18T12:00:00Z",
        finishedAt: null,
        error: null,
        progress: {
          tasksDone: 2,
          tasksTotal: 5,
          fraction: 0.4,
          currentTask: "read_cv",
          elapsedSeconds: 42,
          remainingSeconds: 75,
          queuePosition: null,
          tasks: [
            { key: "prepare", state: "done", unitsDone: 0, unitsTotal: null },
            {
              key: "read_advert",
              state: "done",
              unitsDone: 0,
              unitsTotal: null,
            },
            {
              key: "read_cv",
              state: "running",
              unitsDone: 0,
              unitsTotal: null,
            },
            { key: "search", state: "pending", unitsDone: 0, unitsTotal: null },
            { key: "score", state: "pending", unitsDone: 0, unitsTotal: null },
          ],
        },
      },
    };

    render(
      <RolesPanel
        state="ready"
        roles={[running]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        addRoleSlot={null}
        layout="table"
        observedAt={Date.now()}
      />,
    );

    const table = within(screen.getByRole("table"));
    expect(table.getByText("2 of 5 tasks done")).toBeInTheDocument();
    expect(table.getByText("Reading your CV")).toBeInTheDocument();
    expect(
      table.getByText(/0:4\d elapsed · About 1:\d\d left/),
    ).toBeInTheDocument();
    expect(
      table.getByRole("progressbar", { name: "Analysis progress" }),
    ).toHaveAttribute("aria-valuenow", "40");
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
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
    await user.click(
      screen.getAllByRole("button", { name: "Retry analysis" })[0]!,
    );
    expect(onReanalyse).toHaveBeenCalledWith("role-f");
  });

  it("shows Analysis incomplete without a fit score", () => {
    render(
      <RolesPanel
        state="ready"
        roles={[
          {
            ...failedRole,
            fitScore: 4,
            bandLabel: "Limited match",
          },
        ]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        failureCodes={{ "role-f": "assessment_incomplete" }}
        addRoleSlot={null}
        layout="table"
      />,
    );

    expect(screen.getAllByText("Analysis incomplete").length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText(/not a fit judgement/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText("4")).toBeNull();
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
    expect(screen.queryByText(/limited match/i)).not.toBeInTheDocument();
  });

  it("asks for confirmation before deleting a role and does not open it", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const readyRole: Role = {
      ...analysingRole,
      id: "role-1",
      status: "ready",
      fitScore: 82,
      bandLabel: "Strong match",
      counts: { met: 1, partial: 0, missing: 0 },
    };

    render(
      <RolesPanel
        state="ready"
        roles={[readyRole]}
        sortKey="fit"
        sortDirection="desc"
        onSort={vi.fn()}
        onRetry={vi.fn()}
        onDelete={onDelete}
        addRoleSlot={null}
        layout="table"
      />,
    );

    const table = screen.getByRole("table");
    await user.click(
      within(table).getByRole("button", { name: /delete analytics engineer/i }),
    );
    expect(confirmSpy).toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();

    confirmSpy.mockReturnValue(true);
    await user.click(
      within(table).getByRole("button", { name: /delete analytics engineer/i }),
    );
    expect(onDelete).toHaveBeenCalledWith("role-1");
    confirmSpy.mockRestore();
  });
});
