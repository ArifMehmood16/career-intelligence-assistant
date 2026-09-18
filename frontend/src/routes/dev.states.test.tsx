/**
 * @vitest-environment jsdom
 *
 * Phase 13.8 — every /dev/states section title is listed and the page mounts.
 */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => () => ({}),
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
  useNavigate: () => vi.fn(),
}));

import { DEV_STATE_SECTION_TITLES, DevStatesPage } from "./dev.states";

afterEach(() => {
  cleanup();
});

describe("/dev/states gallery", () => {
  it("renders every documented section title from props alone", () => {
    render(<DevStatesPage />);

    const missing: string[] = [];
    for (const title of DEV_STATE_SECTION_TITLES) {
      if (screen.queryByText(title, { selector: "h2" }) === null) {
        missing.push(title);
      }
    }
    expect(missing).toEqual([]);
  });
});
