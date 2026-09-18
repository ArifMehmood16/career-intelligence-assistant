import { useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createBulletDraft,
  getFitBreakdown,
  getGapPlan,
  getRequirements,
  getRole,
  getSpan,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { EvidencePanel } from "@/components/EvidencePanel";
import { BulletDraftPanel } from "@/components/role/BulletDraftPanel";
import { FitBreakdown, type AsyncState } from "@/components/role/FitBreakdown";
import { GapsPanel } from "@/components/role/GapsPanel";
import { RequirementTable } from "@/components/role/RequirementTable";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import {
  isRoleDetailTabId,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";
import { RoleHeader } from "@/components/role/RoleHeader";
import type {
  Evidence,
  GapItem,
  Requirement,
  RequirementStatus,
} from "@/types";

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
  const [draftVisible, setDraftVisible] = useState(false);
  const [draftRequirementId, setDraftRequirementId] = useState<string | null>(
    null,
  );

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
  const gapPlanQuery = useQuery({
    queryKey: ["gap-plan", roleId],
    queryFn: () => getGapPlan(roleId),
  });

  const bulletMutation = useMutation({
    mutationFn: (requirementId: string) =>
      createBulletDraft(roleId, requirementId),
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

  const gapItems = gapPlanQuery.data?.items ?? [];
  const gapsState: AsyncState = gapPlanQuery.isPending
    ? "loading"
    : gapPlanQuery.isError
      ? "error"
      : gapItems.length === 0
        ? "empty"
        : "ready";

  const draftState: AsyncState = !draftVisible
    ? "empty"
    : bulletMutation.isPending
      ? "loading"
      : bulletMutation.isError
        ? "error"
        : bulletMutation.data
          ? "ready"
          : "empty";

  const openEvidence = (
    title: string,
    status: RequirementStatus,
    evidence: Evidence,
  ) => {
    setSelected({
      id: evidence.spanId,
      roleId,
      text: title,
      type: "must",
      status,
      evidence,
    });
    setPanelOpen(true);
  };

  const openGapEvidence = (item: GapItem) => {
    if (!item.adjacentEvidence) return;
    openEvidence(item.requirementText, item.status, item.adjacentEvidence);
  };

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

  const requestBulletDraft = (requirementId: string) => {
    setDraftRequirementId(requirementId);
    setDraftVisible(true);
    bulletMutation.mutate(requirementId);
  };

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
    </div>
  );

  const gapsPane = (
    <div className="space-y-6">
      <GapsPanel
        state={gapsState}
        currentScore={gapPlanQuery.data?.currentScore ?? 0}
        items={gapItems}
        onRetry={() => {
          void gapPlanQuery.refetch();
        }}
        onSelectEvidence={openGapEvidence}
        onDraftBullet={(item) => {
          requestBulletDraft(item.requirementId);
        }}
      />
      <BulletDraftPanel
        state={draftState}
        draft={bulletMutation.data ?? null}
        onRetry={() => {
          if (draftRequirementId) {
            bulletMutation.mutate(draftRequirementId);
          }
        }}
        onCopy={(text) => {
          void navigator.clipboard.writeText(text);
        }}
        onCitation={(evidence) => {
          openEvidence("Cited span", "partial", evidence);
        }}
        onDismiss={() => {
          setDraftVisible(false);
          bulletMutation.reset();
          setDraftRequirementId(null);
        }}
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
        gaps={gapsPane}
        prepare={<ComingSoon feature="Prepare" />}
        letter={<ComingSoon feature="Letter" />}
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
}
