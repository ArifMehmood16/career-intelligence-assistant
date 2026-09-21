import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addRole,
  deleteRole,
  getCv,
  getJob,
  getRoles,
  reanalyseRole,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { AddRoleDialog } from "@/components/workspace/AddRoleDialog";
import { deriveRolesPanelState } from "@/components/workspace/roles-panel-state";
import {
  RolesPanel,
  type RolesSortKey,
  type SortDirection,
} from "@/components/workspace/RolesPanel";
import type { Role } from "@/types";

const JOB_POLL_MS = 1500;

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

function mutationErrorMessage(error: unknown): string | null {
  if (!error) return null;
  return formatDescribedError(describeApiError(error));
}

export function RolesPanelContainer() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<RolesSortKey>("fit");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [roleJobs, setRoleJobs] = useState<Record<string, string>>({});
  const [failureReasons, setFailureReasons] = useState<Record<string, string>>(
    {},
  );

  const cvQuery = useQuery({ queryKey: ["cv"], queryFn: getCv });
  const rolesQuery = useQuery({
    queryKey: ["roles"],
    queryFn: getRoles,
    refetchInterval: (query) => {
      const rows = query.state.data ?? [];
      return rows.some((role) => role.status === "analysing")
        ? JOB_POLL_MS
        : false;
    },
  });

  const activeJobEntries = useMemo(
    () =>
      Object.entries(roleJobs).filter(([roleId]) => {
        const role = rolesQuery.data?.find((row) => row.id === roleId);
        return role?.status === "analysing" || role === undefined;
      }),
    [roleJobs, rolesQuery.data],
  );

  const activeJobId = activeJobEntries[0]?.[1];

  const jobQuery = useQuery({
    queryKey: ["jobs", activeJobId],
    queryFn: () => getJob(activeJobId!),
    enabled: Boolean(activeJobId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "queued" || state === "running" ? JOB_POLL_MS : false;
    },
  });

  useEffect(() => {
    const job = jobQuery.data;
    if (!job || !activeJobId) return;
    const roleId = activeJobEntries.find(([, id]) => id === activeJobId)?.[0];
    if (!roleId) return;

    if (job.state === "succeeded") {
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      setRoleJobs((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
      setFailureReasons((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
    }

    if (job.state === "failed") {
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      setFailureReasons((prev) => ({
        ...prev,
        [roleId]:
          job.error?.message ?? "Analysis failed. Try running it again.",
      }));
      setRoleJobs((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
    }
  }, [jobQuery.data, activeJobId, activeJobEntries, queryClient]);

  const create = useMutation({
    mutationFn: addRole,
    onSuccess: ({ role, jobId }) => {
      setDialogOpen(false);
      setRoleJobs((prev) => ({ ...prev, [role.id]: jobId }));
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
  });

  const reanalyse = useMutation({
    mutationFn: reanalyseRole,
    onSuccess: ({ jobId }, roleId) => {
      setRoleJobs((prev) => ({ ...prev, [roleId]: jobId }));
      setFailureReasons((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
    },
  });

  const remove = useMutation({
    mutationFn: deleteRole,
    onSuccess: (_result, roleId) => {
      setRoleJobs((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
      setFailureReasons((prev) => {
        const next = { ...prev };
        delete next[roleId];
        return next;
      });
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      void queryClient.invalidateQueries({ queryKey: ["ranking"] });
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

  const state = deriveRolesPanelState({
    cvStatus: cvQuery.isPending
      ? "pending"
      : cvQuery.isError
        ? "error"
        : "success",
    rolesStatus: rolesQuery.isPending
      ? "pending"
      : rolesQuery.isError
        ? "error"
        : "success",
    hasCv,
    roleCount: roles.length,
  });

  return (
    <RolesPanel
      state={state}
      roles={roles}
      sortKey={sortKey}
      sortDirection={sortDirection}
      failureReasons={failureReasons}
      onSort={(key) => {
        if (key === sortKey) {
          setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
          setSortKey(key);
          setSortDirection(key === "role" ? "asc" : "desc");
        }
      }}
      onRetry={() => {
        void cvQuery.refetch();
        void rolesQuery.refetch();
      }}
      onReanalyse={(roleId) => reanalyse.mutate(roleId)}
      onDelete={(roleId) => remove.mutate(roleId)}
      addRoleSlot={
        <AddRoleDialog
          open={dialogOpen}
          disabled={!hasCv}
          submitting={create.isPending}
          errorMessage={mutationErrorMessage(create.error)}
          onOpenChange={(open) => {
            if (!open) create.reset();
            setDialogOpen(open);
          }}
          onSubmit={(input) => create.mutate(input)}
        />
      }
    />
  );
}
