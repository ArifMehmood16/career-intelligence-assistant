/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RoleHeader } from "./RoleHeader";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
    className?: string;
  }) => (
    <a href={props.to} className={props.className}>
      {children}
    </a>
  ),
}));

describe("RoleHeader states", () => {
  it("shows a skeleton while loading", () => {
    const { container } = render(<RoleHeader role={null} loading />);
    expect(
      container.querySelector(".animate-pulse, [class*='Skeleton']"),
    ).toBeTruthy();
  });

  it("shows role title, company, and score when ready", () => {
    render(
      <RoleHeader
        loading={false}
        role={{
          id: "role-1",
          title: "Analytics Engineer",
          company: "Acme",
          fitScore: 82,
          bandLabel: "Strong match",
          counts: { met: 1, partial: 0, missing: 0 },
          status: "ready",
          updatedAt: "2026-09-18T12:00:00Z",
        }}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Analytics Engineer" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("82")).toBeInTheDocument();
    expect(screen.getByText(/Strong match/)).toBeInTheDocument();
  });
});
