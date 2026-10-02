/**
 * PLAN 18.13 — what retrieval showed the judge for one requirement.
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TRACE, VERDICTS } from "@/api/__fixtures__/verdicts";

import { TraceDrawer } from "./TraceDrawer";
import { VerdictGapsPanel } from "./VerdictGapsPanel";

afterEach(() => {
  cleanup();
});

function drawer(props: Partial<Parameters<typeof TraceDrawer>[0]> = {}) {
  return render(
    <TraceDrawer
      open
      state="ready"
      verdict={VERDICTS.verdicts[0]!}
      trace={TRACE}
      onOpenChange={vi.fn()}
      onRetry={vi.fn()}
      {...props}
    />,
  );
}

describe("TraceDrawer", () => {
  it("shows each search round with every leg's rank and marks cited chunks", () => {
    drawer();

    const dialog = screen.getByRole("dialog", { name: /retrieval trace/i });
    const first = within(dialog).getByRole("table", { name: /round 0/i });
    const rows = within(first).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("c1");
    expect(rows[1]).toHaveTextContent("Cited");
    expect(rows[2]).toHaveTextContent("c2");
    expect(rows[2]).not.toHaveTextContent("Cited");
    expect(rows[2]).toHaveTextContent("—");
    expect(
      within(dialog).getByText(/the judge's own words/i),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText("Python data tooling in production"),
    ).toBeInTheDocument();
  });

  it("shows a skeleton while the trace loads", () => {
    drawer({ state: "loading", trace: null });

    expect(
      screen.getByRole("dialog").querySelector(".animate-pulse"),
    ).toBeTruthy();
  });

  it("offers a retry when the trace could not load", async () => {
    const onRetry = vi.fn();
    drawer({ state: "error", trace: null, onRetry });

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});

describe("VerdictGapsPanel", () => {
  it("orders the gaps by what closing them would add", () => {
    render(<VerdictGapsPanel state="ready" verdicts={VERDICTS} onRetry={vi.fn()} />);

    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Has five or more years of Python.");
    expect(items[0]).toHaveTextContent("Experience");
    expect(items[0]).toHaveTextContent("2 / 4");
    expect(items[0]).toHaveTextContent("+6.5");
  });

  it("says when nothing is left to close", () => {
    render(
      <VerdictGapsPanel
        state="ready"
        verdicts={{ ...VERDICTS, gapPlan: [] }}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText(/no gaps/i)).toBeInTheDocument();
  });

  it("has loading, error and incomplete states", () => {
    const { rerender, container } = render(
      <VerdictGapsPanel state="loading" verdicts={null} onRetry={vi.fn()} />,
    );
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
    rerender(<VerdictGapsPanel state="error" verdicts={null} onRetry={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    rerender(
      <VerdictGapsPanel state="incomplete" verdicts={null} onRetry={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      /no finished analysis/i,
    );
  });
});
