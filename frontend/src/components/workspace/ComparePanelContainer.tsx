import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { getComparison, getRoles } from "@/api/client";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { ComparePanel } from "@/components/workspace/ComparePanel";

export function ComparePanelContainer() {
  const navigate = useNavigate();
  const [roleAId, setRoleAId] = useState("");
  const [roleBId, setRoleBId] = useState("");
  const [requested, setRequested] = useState(false);

  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: getRoles,
  });

  const compareQuery = useQuery({
    queryKey: ["compare", roleAId, roleBId],
    queryFn: () => getComparison(roleAId, roleBId),
    enabled:
      requested && roleAId !== "" && roleBId !== "" && roleAId !== roleBId,
  });

  const roles = rolesQuery.data ?? [];
  const rolesState: AsyncState = rolesQuery.isPending
    ? "loading"
    : rolesQuery.isError
      ? "error"
      : "ready";
  const state: AsyncState = !requested
    ? "empty"
    : compareQuery.isPending
      ? "loading"
      : compareQuery.isError
        ? "error"
        : compareQuery.data
          ? "ready"
          : "empty";

  return (
    <ComparePanel
      roles={roles.filter((role) => role.status === "ready")}
      roleAId={roleAId}
      roleBId={roleBId}
      state={state}
      rolesState={rolesState}
      comparison={compareQuery.data ?? null}
      onRoleAChange={(id) => {
        setRequested(false);
        setRoleAId(id);
      }}
      onRoleBChange={(id) => {
        setRequested(false);
        setRoleBId(id);
      }}
      onCompare={() => {
        if (requested) {
          void compareQuery.refetch();
        } else {
          setRequested(true);
        }
      }}
      onRetry={() => {
        void compareQuery.refetch();
      }}
      onRetryRoles={() => {
        void rolesQuery.refetch();
      }}
      onOpenGaps={(roleId) => {
        void navigate({
          to: "/roles/$id",
          params: { id: roleId },
          search: { tab: "gaps" },
        });
      }}
    />
  );
}
