import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  createBulletDraft,
  createCoverLetterDraft,
  deleteRole,
  exportRoleArtefact,
  getCoverLetters,
  getFitBreakdown,
  getGapPlan,
  getGeneratedCoverLetters,
  getInterviewPack,
  getJob,
  getRequirements,
  getRole,
  getSpan,
  reanalyseRole,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { EvidencePanel } from "@/components/EvidencePanel";
import { BulletDraftPanel } from "@/components/role/BulletDraftPanel";
import { FitBreakdown, type AsyncState } from "@/components/role/FitBreakdown";
import { GapsPanel } from "@/components/role/GapsPanel";
import { LetterPanel, type LetterTone } from "@/components/role/LetterPanel";
import { PreparePanel } from "@/components/role/PreparePanel";
import { RequirementTable } from "@/components/role/RequirementTable";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import {
  isRoleDetailTabId,
  shouldFetchRoleTabResource,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";
import { RoleHeader, type RoleHeaderState } from "@/components/role/RoleHeader";
import type {
  CoverLetterDraft,
  Evidence,
  GapItem,
  Requirement,
  RequirementStatus,
} from "@/types";

export interface RoleDetailContainerProps {
  roleId: string;
}

export function RoleDetailContainer({ roleId }: RoleDetailContainerProps) {
  const navigate = useNavigate({ from: "/roles/$id" });
  const search = useSearch({ from: "/roles/$id" });
  const queryClient = useQueryClient();
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
  const [letterTone, setLetterTone] = useState<LetterTone>("plain");
  const [includeGapLine, setIncludeGapLine] = useState(false);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetterDraft | null>(
    null,
  );
  const [letterRefusal, setLetterRefusal] = useState<{
    message: string;
  } | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [letterExportError, setLetterExportError] = useState<string | null>(
    null,
  );
  const [prepareExportError, setPrepareExportError] = useState<string | null>(
    null,
  );
  const [analysisJobId, setAnalysisJobId] = useState<string | null>(null);
  const [failureCode, setFailureCode] = useState<string | null>(null);
  const [failureReason, setFailureReason] = useState<string | null>(null);

  const roleQuery = useQuery({
    queryKey: ["role", roleId],
    queryFn: () => getRole(roleId),
    refetchInterval: (query) =>
      query.state.data?.status === "analysing" ? 1500 : false,
    retry: false,
  });
  const jobQuery = useQuery({
    queryKey: ["jobs", analysisJobId],
    queryFn: () => getJob(analysisJobId!),
    enabled: Boolean(analysisJobId),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "queued" || state === "running" ? 1500 : false;
    },
  });

  useEffect(() => {
    const job = jobQuery.data;
    if (!job || !analysisJobId) return;
    if (job.state === "succeeded") {
      setAnalysisJobId(null);
      setFailureCode(null);
      setFailureReason(null);
      void queryClient.invalidateQueries({ queryKey: ["role", roleId] });
      return;
    }
    if (job.state === "failed") {
      setFailureCode(job.error?.code ?? "analysis_failed");
      setFailureReason(job.error?.message ?? null);
      setAnalysisJobId(null);
      void queryClient.invalidateQueries({ queryKey: ["role", roleId] });
    }
  }, [jobQuery.data, analysisJobId, queryClient, roleId]);
  const roleStatus = roleQuery.data?.status;
  const fetchFit = shouldFetchRoleTabResource({
    roleStatus,
    activeTab,
    resourceTab: "fit",
  });
  const fetchGaps = shouldFetchRoleTabResource({
    roleStatus,
    activeTab,
    resourceTab: "gaps",
  });
  const fetchPrepare = shouldFetchRoleTabResource({
    roleStatus,
    activeTab,
    resourceTab: "prepare",
  });
  const fetchLetter = shouldFetchRoleTabResource({
    roleStatus,
    activeTab,
    resourceTab: "letter",
  });
  const breakdownQuery = useQuery({
    queryKey: ["breakdown", roleId],
    queryFn: () => getFitBreakdown(roleId),
    enabled: fetchFit,
  });
  const requirementsQuery = useQuery({
    queryKey: ["requirements", roleId],
    queryFn: () => getRequirements(roleId),
    enabled: fetchFit,
  });
  const gapPlanQuery = useQuery({
    queryKey: ["gap-plan", roleId],
    queryFn: () => getGapPlan(roleId),
    enabled: fetchGaps,
  });
  const interviewPackQuery = useQuery({
    queryKey: ["interview-pack", roleId],
    queryFn: () => getInterviewPack(roleId),
    enabled: fetchPrepare,
  });
  const generatedLettersQuery = useQuery({
    queryKey: ["generated-cover-letters", roleId],
    queryFn: () => getGeneratedCoverLetters(roleId),
    enabled: fetchLetter,
  });
  const supportingLettersQuery = useQuery({
    queryKey: ["cover-letters"],
    queryFn: () => getCoverLetters(),
    enabled: fetchLetter,
  });

  const reanalyse = useMutation({
    mutationFn: () => reanalyseRole(roleId),
    onSuccess: ({ jobId }) => {
      setAnalysisJobId(jobId);
      setFailureCode(null);
      setFailureReason(null);
      void queryClient.invalidateQueries({ queryKey: ["role", roleId] });
    },
  });

  const remove = useMutation({
    mutationFn: () => deleteRole(roleId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["roles"] });
      void queryClient.invalidateQueries({ queryKey: ["ranking"] });
      void navigate({ to: "/" });
    },
  });

  const headerState: RoleHeaderState = roleQuery.isPending
    ? "loading"
    : roleQuery.isError
      ? roleQuery.error instanceof ApiError &&
        roleQuery.error.code === "role_not_found"
        ? "not-found"
        : "error"
      : roleQuery.data?.status === "analysing"
        ? "analysing"
        : roleQuery.data?.status === "failed"
          ? "failed"
          : roleQuery.data
            ? "ready"
            : "not-found";

  const bulletMutation = useMutation({
    mutationFn: (requirementId: string) =>
      createBulletDraft(roleId, requirementId),
  });

  const letterMutation = useMutation({
    mutationFn: () =>
      createCoverLetterDraft(roleId, {
        tone: letterTone,
        includeGapLine,
      }),
    onSuccess: (draft) => {
      setLetterRefusal(null);
      setSelectedLetter(draft);
      void queryClient.invalidateQueries({
        queryKey: ["generated-cover-letters", roleId],
      });
    },
    onError: (error) => {
      if (
        error instanceof ApiError &&
        error.code === "insufficient_matched_requirements"
      ) {
        setSelectedLetter(null);
        setLetterRefusal({ message: error.message });
        return;
      }
      setLetterRefusal(null);
    },
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

  const pack = interviewPackQuery.data ?? null;
  const prepareState: AsyncState = interviewPackQuery.isPending
    ? "loading"
    : interviewPackQuery.isError
      ? "error"
      : pack === null ||
          (pack.probes.length === 0 &&
            pack.leadWith.length === 0 &&
            pack.thinAreas.length === 0 &&
            pack.askThem.length === 0)
        ? "empty"
        : "ready";

  const downloadMarkdown = async (filename: string, body: string) => {
    const blob = new Blob([body], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

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
    setCopyError(null);
    bulletMutation.mutate(requirementId);
  };

  const fitPane = (
    <div className="space-y-6">
      <FitBreakdown
        state={breakdownState}
        summary={roleQuery.data?.fitSummary ?? null}
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
        copyError={copyError}
        onRetry={() => {
          if (draftRequirementId) {
            bulletMutation.mutate(draftRequirementId);
          }
        }}
        onCopy={(text) => {
          void navigator.clipboard.writeText(text).then(
            () => setCopyError(null),
            () => setCopyError("The draft could not be copied."),
          );
        }}
        onCitation={(evidence) => {
          openEvidence("Cited span", "partial", evidence);
        }}
        onDismiss={() => {
          setDraftVisible(false);
          bulletMutation.reset();
          setDraftRequirementId(null);
          setCopyError(null);
        }}
      />
    </div>
  );

  return (
    <div className="space-y-6">
      <RoleHeader
        role={roleQuery.data ?? null}
        loading={headerState === "loading"}
        state={headerState}
        failureCode={failureCode}
        failureReason={failureReason}
        onRetry={() => {
          if (headerState === "failed") {
            reanalyse.mutate();
            return;
          }
          void roleQuery.refetch();
        }}
        onDelete={() => remove.mutate()}
      />

      {headerState === "ready" ? (
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
          prepare={
            <PreparePanel
              state={prepareState}
              pack={pack}
              exportError={prepareExportError}
              onRetry={() => {
                void interviewPackQuery.refetch();
              }}
              onSelectEvidence={(evidence) => {
                openEvidence("Interview evidence", "met", evidence);
              }}
              onExport={() => {
                void exportRoleArtefact(roleId, "interview-pack")
                  .then((body) => {
                    setPrepareExportError(null);
                    return downloadMarkdown(
                      `interview-pack-${roleId}.md`,
                      body,
                    );
                  })
                  .catch(() => {
                    setPrepareExportError(
                      "The interview pack could not be exported.",
                    );
                  });
              }}
            />
          }
          letter={
            <LetterPanel
              tone={letterTone}
              includeGapLine={includeGapLine}
              generating={letterMutation.isPending}
              draft={
                selectedLetter ??
                generatedLettersQuery.data?.[
                  (generatedLettersQuery.data?.length ?? 0) - 1
                ] ??
                null
              }
              versions={generatedLettersQuery.data ?? []}
              refusal={letterRefusal}
              supportingDocuments={supportingLettersQuery.data ?? []}
              generatedState={
                generatedLettersQuery.isPending
                  ? "loading"
                  : generatedLettersQuery.isError
                    ? "error"
                    : "ready"
              }
              supportingState={
                supportingLettersQuery.isPending
                  ? "loading"
                  : supportingLettersQuery.isError
                    ? "error"
                    : "ready"
              }
              onRetryGenerated={() => {
                void generatedLettersQuery.refetch();
              }}
              onRetrySupporting={() => {
                void supportingLettersQuery.refetch();
              }}
              exportError={letterExportError}
              onToneChange={setLetterTone}
              onIncludeGapLineChange={setIncludeGapLine}
              onGenerate={() => {
                setLetterRefusal(null);
                letterMutation.mutate();
              }}
              onSelectVersion={(version) => {
                setLetterRefusal(null);
                setSelectedLetter(version);
              }}
              onExport={(draft) => {
                void exportRoleArtefact(roleId, "cover-letter", {
                  version: draft.version,
                })
                  .then((body) => {
                    setLetterExportError(null);
                    return downloadMarkdown(`cover-letter-${roleId}.md`, body);
                  })
                  .catch(() => {
                    setLetterExportError(
                      "The cover letter could not be exported.",
                    );
                  });
              }}
              onCitation={(citationSpanId) => {
                openEvidence("Cited span", "met", {
                  spanId: citationSpanId,
                  documentId: "",
                  page: 1,
                  paragraph: "",
                  highlight: "",
                });
              }}
              onOpenGaps={() => {
                void navigate({
                  search: (prev) => ({ ...prev, tab: "gaps" }),
                  replace: true,
                });
              }}
            />
          }
        />
      ) : null}

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
