import type { RoleStatus } from "@/types";

/** Role detail tab ids — shared by route search validation and the tabs UI. */
export const ROLE_DETAIL_TABS = [
  { id: "fit", label: "Fit" },
  { id: "gaps", label: "Gaps" },
  { id: "prepare", label: "Prepare" },
  { id: "letter", label: "Letter" },
] as const;

export type RoleDetailTabId = (typeof ROLE_DETAIL_TABS)[number]["id"];

export function isRoleDetailTabId(value: string): value is RoleDetailTabId {
  return ROLE_DETAIL_TABS.some((tab) => tab.id === value);
}

export function shouldFetchRoleTabResource(options: {
  roleStatus: RoleStatus | undefined;
  activeTab: RoleDetailTabId;
  resourceTab: RoleDetailTabId;
}): boolean {
  return (
    options.roleStatus === "ready" && options.activeTab === options.resourceTab
  );
}
