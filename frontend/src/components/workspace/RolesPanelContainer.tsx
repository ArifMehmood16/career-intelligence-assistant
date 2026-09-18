import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addRole, getCv, getRoles } from "@/api/client";
import { AddRoleDialog } from "@/components/workspace/AddRoleDialog";
import {
  RolesPanel,
  type RolesPanelState,
  type RolesSortKey,
  type SortDirection,
} from "@/components/workspace/RolesPanel";
import type { Role } from "@/types";

function compare(a: Role, b: Role, key: RolesSortKey): number {
  switch (key) {
    case "role":
      return a.title.localeCompare(b.title);
    case "fit":
      return a.fitScore - b.fitScore;
    case "met":
      return a.counts.met - b.counts.met;
    case "partial":
      return a.counts.partial - b.counts.partial;
    case "missing":
      return a.counts.missing - b.counts.missing;
  }
}

export function RolesPanelContainer() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<RolesSortKey>("fit");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [dialogOpen, setDialogOpen] = useState(false);

  const cvQuery = useQuery({ queryKey: ["cv"], queryFn: getCv });
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: getRoles });

  const create = useMutation({
    mutationFn: addRole,
    onSuccess: () => {
      setDialogOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
  });

  const roles = useMemo(() => {
    const list = [...(rolesQuery.data ?? [])];
    list.sort((a, b) =>
      sortDirection === "asc" ? compare(a, b, sortKey) : compare(b, a, sortKey),
    );
    return list;
  }, [rolesQuery.data, sortKey, sortDirection]);

  const hasCv = Boolean(cvQuery.data);

  const state: RolesPanelState =
    cvQuery.isPending || rolesQuery.isPending
      ? "loading"
      : !hasCv
        ? "inert"
        : rolesQuery.isError
          ? "error"
          : roles.length === 0
            ? "empty"
            : "ready";

  return (
    <RolesPanel
      state={state}
      roles={roles}
      sortKey={sortKey}
      sortDirection={sortDirection}
      onSort={(key) => {
        if (key === sortKey) {
          setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
          setSortKey(key);
          setSortDirection(key === "role" ? "asc" : "desc");
        }
      }}
      onRetry={() => {
        void rolesQuery.refetch();
      }}
      addRoleSlot={
        <AddRoleDialog
          open={dialogOpen}
          disabled={!hasCv}
          submitting={create.isPending}
          onOpenChange={setDialogOpen}
          onSubmit={(input) => create.mutate(input)}
        />
      }
    />
  );
}
