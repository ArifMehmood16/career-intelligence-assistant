/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ComparePanel } from "./ComparePanel";
import type { Comparison, Role } from "@/types";

afterEach(() => {
  cleanup();
});

const roleA: Role = {
  id: "role-a",
  title: "Analytics Engineer",
  company: "Northwind",
  fitScore: 78,
  bandLabel: "Strong",
  counts: { met: 5, partial: 1, missing: 1 },
  status: "ready",
  updatedAt: "2026-09-18T12:00:00Z",
};

const roleB: Role = {
  ...roleA,
  id: "role-b",
  title: "Platform Engineer",
  company: "Kestrel",
  fitScore: 61,
  bandLabel: "Partial",
};

const comparison: Comparison = {
  a: roleA,
  b: roleB,
  shared: [
    {
      text: "SQL fluency",
      aStatus: "met",
      bStatus: "partial",
    },
  ],
  onlyInA: [
    {
      id: "req-a1",
      roleId: "role-a",
      text: "Production dbt",
      type: "must",
      status: "met",
      evidence: null,
    },
  ],
  onlyInB: [
    {
      id: "req-b1",
      roleId: "role-b",
      text: "Kubernetes",
      type: "must",
      status: "missing",
      evidence: null,
    },
  ],
  differentiator: "Production dbt is met only for Analytics Engineer",
};

describe("ComparePanel", () => {
  it("requires two distinct roles before comparing", async () => {
    const user = userEvent.setup();
    const onCompare = vi.fn();

    render(
      <ComparePanel
        roles={[roleA, roleB]}
        roleAId={roleA.id}
        roleBId={roleA.id}
        state="empty"
        comparison={null}
        onRoleAChange={vi.fn()}
        onRoleBChange={vi.fn()}
        onCompare={onCompare}
        onRetry={vi.fn()}
        onOpenGaps={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /^Compare$/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /^Compare$/i }));
    expect(onCompare).not.toHaveBeenCalled();
  });

  it("renders shared, unique, differentiator, and gap links", async () => {
    const user = userEvent.setup();
    const onOpenGaps = vi.fn();

    render(
      <ComparePanel
        roles={[roleA, roleB]}
        roleAId={roleA.id}
        roleBId={roleB.id}
        state="ready"
        comparison={comparison}
        onRoleAChange={vi.fn()}
        onRoleBChange={vi.fn()}
        onCompare={vi.fn()}
        onRetry={vi.fn()}
        onOpenGaps={onOpenGaps}
      />,
    );

    expect(screen.getByText(/SQL fluency/)).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Only in Analytics Engineer/i }),
    ).toBeInTheDocument();
    const onlyA = screen.getByRole("heading", {
      name: /Only in Analytics Engineer/i,
    }).parentElement;
    expect(onlyA).toHaveTextContent(/Production dbt/);
    const onlyB = screen.getByRole("heading", {
      name: /Only in Platform Engineer/i,
    }).parentElement;
    expect(onlyB).toHaveTextContent(/Kubernetes/);
    expect(
      screen.getByText(/Production dbt is met only for Analytics Engineer/),
    ).toBeInTheDocument();

    const gaps = screen.getByRole("region", { name: /comparison result/i });
    await user.click(
      within(gaps).getByRole("button", {
        name: /gaps for analytics engineer/i,
      }),
    );
    expect(onOpenGaps).toHaveBeenCalledWith(roleA.id);
  });
});
