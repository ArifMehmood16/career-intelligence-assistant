/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

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

afterEach(() => {
  cleanup();
});

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

  it("shows not-found instead of an indefinite skeleton", () => {
    const { container } = render(
      <RoleHeader role={null} loading={false} state="not-found" />,
    );
    expect(screen.getByText(/role not found/i)).toBeInTheDocument();
    expect(container.querySelector(".animate-pulse")).toBeNull();
  });

  it("shows analysing without a fit score", () => {
    render(
      <RoleHeader
        loading={false}
        state="analysing"
        role={{
          id: "role-1",
          title: "Analytics Engineer",
          company: "Acme",
          fitScore: 0,
          bandLabel: "Not scored yet",
          counts: { met: 0, partial: 0, missing: 0 },
          status: "analysing",
          updatedAt: "2026-09-18T12:00:00Z",
        }}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Analytics Engineer" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/analysing/i);
    expect(screen.queryByText("82")).toBeNull();
  });

  it("shows failed analysis with a retry action", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <RoleHeader
        loading={false}
        state="failed"
        onRetry={onRetry}
        role={{
          id: "role-1",
          title: "Analytics Engineer",
          company: "Acme",
          fitScore: 0,
          bandLabel: "Not scored yet",
          counts: { met: 0, partial: 0, missing: 0 },
          status: "failed",
          updatedAt: "2026-09-18T12:00:00Z",
        }}
      />,
    );
    expect(screen.getByText(/analysis failed/i)).toBeInTheDocument();
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry analysis/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("shows incomplete analysis without a fit score", () => {
    render(
      <RoleHeader
        loading={false}
        state="failed"
        failureCode="assessment_incomplete"
        role={{
          id: "role-1",
          title: "Analytics Engineer",
          company: "Acme",
          fitScore: 4,
          bandLabel: "Limited match",
          counts: { met: 0, partial: 0, missing: 0 },
          status: "failed",
          updatedAt: "2026-09-18T12:00:00Z",
        }}
      />,
    );
    expect(screen.getByText(/analysis incomplete/i)).toBeInTheDocument();
    expect(screen.getByText(/not a fit judgement/i)).toBeInTheDocument();
    expect(screen.queryByText("4")).toBeNull();
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
    expect(screen.queryByText(/limited match/i)).not.toBeInTheDocument();
  });

  it("shows a retryable load error instead of a skeleton", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { container } = render(
      <RoleHeader
        role={null}
        loading={false}
        state="error"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText(/role could not be loaded/i)).toBeInTheDocument();
    expect(container.querySelector(".animate-pulse")).toBeNull();
    await user.click(screen.getByRole("button", { name: /^retry$/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("asks for confirmation before deleting the open role", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(
      <RoleHeader
        loading={false}
        state="ready"
        onDelete={onDelete}
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

    await user.click(
      screen.getByRole("button", { name: /delete analytics engineer/i }),
    );
    expect(confirmSpy).toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();

    confirmSpy.mockReturnValue(true);
    await user.click(
      screen.getByRole("button", { name: /delete analytics engineer/i }),
    );
    expect(onDelete).toHaveBeenCalledTimes(1);
    confirmSpy.mockRestore();
  });
});
