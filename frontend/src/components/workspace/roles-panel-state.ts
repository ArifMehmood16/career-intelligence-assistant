import type { RolesPanelState } from "@/components/workspace/RolesPanel";

export type QueryLoadStatus = "pending" | "error" | "success";

export function deriveRolesPanelState(input: {
  cvStatus: QueryLoadStatus;
  rolesStatus: QueryLoadStatus;
  hasCv: boolean;
  roleCount: number;
}): RolesPanelState {
  if (input.cvStatus === "pending" || input.rolesStatus === "pending") {
    return "loading";
  }
  if (input.cvStatus === "error" || input.rolesStatus === "error") {
    return "error";
  }
  if (!input.hasCv) {
    return "inert";
  }
  return input.roleCount === 0 ? "empty" : "ready";
}
