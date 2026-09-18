import { useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  getFitBreakdown,
  getRequirements,
  getRole,
  getSpan,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { EvidencePanel } from "@/components/EvidencePanel";
import { FitBreakdown, type AsyncState } from "@/components/role/FitBreakdown";
import { RequirementTable } from "@/components/role/RequirementTable";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import {
  isRoleDetailTabId,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";
import { RoleHeader } from "@/components/role/RoleHeader";
import type { Requirement, RequirementStatus } from "@/types";

export interface RoleDetailContainerProps {
  roleId: string;
}

function ComingSoon({ feature }: { feature: string }) {
  return (
    <p className="rounded-md border border-dashed border-border px-5 py-8 text-sm text-muted-foreground">
      {feature} will appear here in a later Phase 13 slice.
    </p>
  );
}

export function RoleDetailContainer({ roleId }: RoleDetailContainerProps) {
  const navigate = useNavigate({ from: "/roles/$id" });
  const search = useSearch({ from: "/roles/$id" });
  const activeTab: RoleDetailTabId =
    search.tab !== undefined && isRoleDetailTabId(search.tab)
      ? search.tab
      : "fit";

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

  const spanId = selected?.evidence?.spanId ?? null;
  const spanQuery = useQuery({
    queryKey: ["span", spanId],
    queryFn: () => getSpan(spanId!),
    enabled: panelOpen && Boolean(spanId),
    retry: false,
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

  const resolveState =
    !panelOpen || !spanId
      ? "ready"
      : spanQuery.isPending
        ? "loading"
        : spanQuery.isError
          ? "error"
          : "ready";

  const resolveError =
    spanQuery.error != null
      ? formatDescribedError(describeApiError(spanQuery.error))
      : null;

  const fitPane = (
    <div className="space-y-6">
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
        evidence={
          spanId ? (spanQuery.data ?? null) : (selected?.evidence ?? null)
        }
        resolveState={resolveState}
        resolveError={resolveError}
        onOpenChange={setPanelOpen}
      />
    </div>
  );

  return (
    <div className="space-y-6">
      <RoleHeader role={roleQuery.data ?? null} loading={roleQuery.isPending} />

      <RoleDetailTabs
        value={activeTab}
        onValueChange={(tab) => {
          void navigate({
            search: (prev) => ({ ...prev, tab }),
            replace: true,
          });
        }}
        fit={fitPane}
        gaps={<ComingSoon feature="Gaps" />}
        prepare={<ComingSoon feature="Prepare" />}
        letter={<ComingSoon feature="Letter" />}
      />
    </div>
  );
}
