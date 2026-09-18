/**
 * Phase 13.1 — role detail tabs are keyboard-navigable and label each pane.
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RoleDetailTabs } from "./RoleDetailTabs";
import { ROLE_DETAIL_TABS } from "./role-detail-tabs";

afterEach(() => {
  cleanup();
});

describe("RoleDetailTabs", () => {
  it("exposes Fit, Gaps, Prepare and Letter tabs", () => {
    const { container } = render(
      <RoleDetailTabs
        value="fit"
        onValueChange={vi.fn()}
        fit={<p>Fit body</p>}
        gaps={<p>Gaps body</p>}
        prepare={<p>Prepare body</p>}
        letter={<p>Letter body</p>}
      />,
    );

    const tablist = within(container).getByRole("tablist", {
      name: "Role detail sections",
    });
    for (const tab of ROLE_DETAIL_TABS) {
      expect(
        within(tablist).getByRole("tab", { name: tab.label }),
      ).toBeInTheDocument();
    }
    expect(screen.getByText("Fit body")).toBeInTheDocument();
  });

  it("notifies when a tab trigger is clicked", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    const { container } = render(
      <RoleDetailTabs
        value="fit"
        onValueChange={onValueChange}
        fit={<p>Fit body</p>}
        gaps={<p>Gaps body</p>}
        prepare={<p>Prepare body</p>}
        letter={<p>Letter body</p>}
      />,
    );

    const tablist = within(container).getByRole("tablist", {
      name: "Role detail sections",
    });
    await user.click(within(tablist).getByRole("tab", { name: "Gaps" }));
    expect(onValueChange).toHaveBeenCalledWith("gaps");
  });

  it("moves focus across tabs with the keyboard", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <RoleDetailTabs
        value="fit"
        onValueChange={vi.fn()}
        fit={<p>Fit body</p>}
        gaps={<p>Gaps body</p>}
        prepare={<p>Prepare body</p>}
        letter={<p>Letter body</p>}
      />,
    );

    const tablist = within(container).getByRole("tablist", {
      name: "Role detail sections",
    });
    const fit = within(tablist).getByRole("tab", { name: "Fit" });
    const gaps = within(tablist).getByRole("tab", { name: "Gaps" });
    fit.focus();
    await user.keyboard("{ArrowRight}");
    expect(gaps).toHaveFocus();
  });
});
