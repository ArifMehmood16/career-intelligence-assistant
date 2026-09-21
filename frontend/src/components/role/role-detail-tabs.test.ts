import { describe, expect, it } from "vitest";

import { shouldFetchRoleTabResource } from "./role-detail-tabs";

describe("shouldFetchRoleTabResource", () => {
  it("does not fetch tab resources until the role is ready and the tab is active", () => {
    expect(
      shouldFetchRoleTabResource({
        roleStatus: "analysing",
        activeTab: "fit",
        resourceTab: "fit",
      }),
    ).toBe(false);
    expect(
      shouldFetchRoleTabResource({
        roleStatus: "failed",
        activeTab: "gaps",
        resourceTab: "gaps",
      }),
    ).toBe(false);
    expect(
      shouldFetchRoleTabResource({
        roleStatus: "ready",
        activeTab: "fit",
        resourceTab: "letter",
      }),
    ).toBe(false);
    expect(
      shouldFetchRoleTabResource({
        roleStatus: "ready",
        activeTab: "letter",
        resourceTab: "letter",
      }),
    ).toBe(true);
  });
});
