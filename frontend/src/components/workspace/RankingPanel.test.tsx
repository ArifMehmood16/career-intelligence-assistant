/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RankingPanel } from "./RankingPanel";
import type { RankedRole } from "@/types";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    ...props
  }: {
    children: React.ReactNode;
    to: string;
    params?: Record<string, string>;
    className?: string;
  }) => {
    const id = props.params?.["id"];
    const href = id !== undefined ? props.to.replace("$id", id) : props.to;
    return (
      <a href={href} className={props.className}>
        {children}
      </a>
    );
  },
}));

afterEach(() => {
  cleanup();
});

const roleA = {
  id: "role-a",
  title: "Analytics Engineer",
  company: "Northwind",
  fitScore: 78,
  bandLabel: "Strong",
  counts: { met: 5, partial: 1, missing: 1 },
  status: "ready" as const,
  updatedAt: "2026-09-18T12:00:00Z",
};

const roleB = {
  ...roleA,
  id: "role-b",
  title: "Platform Engineer",
  company: "Kestrel",
  fitScore: 78,
  bandLabel: "Strong",
};

const ranked: RankedRole[] = [
  {
    role: roleA,
    rank: 1,
    tied: true,
    because: ["Production dbt experience"],
  },
  {
    role: roleB,
    rank: 1,
    tied: true,
    because: ["Kubernetes administration"],
  },
];

describe("RankingPanel", () => {
  it("shows loading, error, and empty states", () => {
    const { rerender } = render(
      <RankingPanel state="loading" ranked={[]} onRetry={() => undefined} />,
    );
    expect(document.querySelector("[aria-busy='true']")).not.toBeNull();

    rerender(
      <RankingPanel state="error" ranked={[]} onRetry={() => undefined} />,
    );
    expect(
      screen.getByText(/ranking could not be loaded/i),
    ).toBeInTheDocument();

    rerender(
      <RankingPanel state="empty" ranked={[]} onRetry={() => undefined} />,
    );
    expect(
      screen.getByText(/add at least one ready role/i),
    ).toBeInTheDocument();
  });

  it("lists ranks with named reasons and marks ties", () => {
    render(
      <RankingPanel state="ready" ranked={ranked} onRetry={() => undefined} />,
    );

    const list = screen.getByRole("list", { name: /role ranking/i });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(2);

    expect(items[0]).toHaveTextContent(/#1/);
    expect(items[0]).toHaveTextContent(/tied/i);
    expect(items[0]).toHaveTextContent(/Analytics Engineer/);
    expect(items[0]).toHaveTextContent(/Production dbt experience/);

    expect(items[1]).toHaveTextContent(/#1/);
    expect(items[1]).toHaveTextContent(/tied/i);
    expect(items[1]).toHaveTextContent(/Platform Engineer/);
    expect(items[1]).toHaveTextContent(/Kubernetes administration/);

    expect(
      screen.getByRole("link", { name: /Analytics Engineer/i }),
    ).toHaveAttribute("href", "/roles/role-a");
  });
});
