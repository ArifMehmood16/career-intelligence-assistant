import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getFitBreakdown, getRequirements, getRole } from "@/api/client";
import { EvidencePanel } from "@/components/EvidencePanel";
import { FitBreakdown, type AsyncState } from "@/components/role/FitBreakdown";
import { RequirementTable } from "@/components/role/RequirementTable";
import { RoleHeader } from "@/components/role/RoleHeader";
import type { Requirement, RequirementStatus } from "@/types";

export interface RoleDetailContainerProps {
  roleId: string;
}

export function RoleDetailContainer({ roleId }: RoleDetailContainerProps) {
  const [expandedRowIds, setExpandedRowIds] = useState<string[]>([]);
  // The gaps are the point of this screen: Missing is open, the rest collapsed.
  const [collapsedGroups, setCollapsedGroups] = useState<RequirementStatus[]>([
    "partial",
    "met",
  ]);
  const [selected, setSelected] = useState<Requirement | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);

  const roleQuery = useQuery({
    queryKey: ["role", roleId],
    queryFn: () => getRole(roleId),
  });
  const breakdownQuery = useQuery({
    queryKey: ["breakdown", roleId],
    queryFn: () => getFitBreakdown(roleId),
  });
  const requirementsQuery = useQuery({
    queryKey: ["requirements", roleId],
    queryFn: () => getRequirements(roleId),
  });

  const requirements = useMemo(
    () => requirementsQuery.data ?? [],
    [requirementsQuery.data],
  );
  const requirementsById = useMemo(
    () => Object.fromEntries(requirements.map((item) => [item.id, item])),
    [requirements],
  );

  const breakdownRows = breakdownQuery.data ?? [];

  const breakdownState: AsyncState = breakdownQuery.isPending
    ? "loading"
    : breakdownQuery.isError
      ? "error"
      : breakdownRows.length === 0
        ? "empty"
        : "ready";

  const requirementsState: AsyncState = requirementsQuery.isPending
    ? "loading"
    : requirementsQuery.isError
      ? "error"
      : requirements.length === 0
        ? "empty"
        : "ready";

  return (
    <div className="space-y-6">
      <RoleHeader role={roleQuery.data ?? null} loading={roleQuery.isPending} />

      <FitBreakdown
        state={breakdownState}
        rows={breakdownRows}
        requirementsById={requirementsById}
        expandedRowIds={expandedRowIds}
        onToggleRow={(id) =>
          setExpandedRowIds((current) =>
            current.includes(id)
              ? current.filter((item) => item !== id)
              : [...current, id],
          )
        }
        onRetry={() => {
          void breakdownQuery.refetch();
        }}
      />

      <RequirementTable
        state={requirementsState}
        requirements={requirements}
        collapsedGroups={collapsedGroups}
        onToggleGroup={(status) =>
          setCollapsedGroups((current) =>
            current.includes(status)
              ? current.filter((item) => item !== status)
              : [...current, status],
          )
        }
        onSelect={(requirement) => {
          setSelected(requirement);
          setPanelOpen(true);
        }}
        onRetry={() => {
          void requirementsQuery.refetch();
        }}
      />

      <EvidencePanel
        open={panelOpen}
        title={selected?.text ?? ""}
        status={selected?.status ?? "missing"}
        evidence={selected?.evidence ?? null}
        onOpenChange={setPanelOpen}
      />
    </div>
  );
}
