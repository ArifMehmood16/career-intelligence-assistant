import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  ApiError,
  createCoverLetterDraft,
  deleteRole,
  exportRoleArtefact,
  getCoverLetters,
  getGeneratedCoverLetters,
  getInterviewPack,
  getJob,
  getRole,
  getSpan,
  reanalyseRole,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { EvidencePanel } from "@/components/EvidencePanel";
import type { AsyncState } from "@/components/role/async-state";
import {
  LetterPanel,
  type LetterCitation,
  type LetterTone,
} from "@/components/role/LetterPanel";
import { numberLetterCitations } from "@/components/role/letterCitations";
import { PreparePanel } from "@/components/role/PreparePanel";
import { RoleDetailTabs } from "@/components/role/RoleDetailTabs";
import {
  isRoleDetailTabId,
  shouldFetchRoleTabResource,
  type RoleDetailTabId,
} from "@/components/role/role-detail-tabs";
import { RoleHeader, type RoleHeaderState } from "@/components/role/RoleHeader";
import { RoleFitContainer } from "@/components/role/verdicts/RoleFitContainer";
import type {
  CoverLetterDraft,
  Evidence,
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

  const [selected, setSelected] = useState<Requirement | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [letterTone, setLetterTone] = useState<LetterTone>("plain");
  const [includeGapLine, setIncludeGapLine] = useState(false);
  const [selectedLetter, setSelectedLetter] = useState<CoverLetterDraft | null>(
    null,
  );
  const [letterRefusal, setLetterRefusal] = useState<{
    message: string;
  } | null>(null);
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
      void queryClient.invalidateQueries({ queryKey: ["verdicts", roleId] });
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

  const activeLetterDraft: CoverLetterDraft | null =
    selectedLetter ??
    generatedLettersQuery.data?.[
      (generatedLettersQuery.data?.length ?? 0) - 1
    ] ??
    null;

  const letterCitationRefs = useMemo(
    () =>
      activeLetterDraft
        ? numberLetterCitations(activeLetterDraft.paragraphs)
        : [],
    [activeLetterDraft],
  );

  const letterSpanQueries = useQueries({
    queries: letterCitationRefs.map((item) => ({
      queryKey: ["span", item.spanId],
      queryFn: () => getSpan(item.spanId),
      enabled: fetchLetter && Boolean(item.spanId),
      retry: false,
    })),
  });

  const letterCitations: LetterCitation[] = letterCitationRefs.map(
    (item, index) => {
      const query = letterSpanQueries[index];
      const passage =
        query?.data?.highlight?.trim() ||
        query?.data?.paragraph?.trim() ||
        null;
      return {
        number: item.number,
        spanId: item.spanId,
        text: passage,
        loading: query?.isPending ?? false,
        error: query?.isError ?? false,
      };
    },
  );

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

  return (
    <div className="space-y-6">
      <RoleHeader
        role={roleQuery.data ?? null}
        loading={headerState === "loading"}
        state={headerState}
        failureCode={failureCode}
        failureReason={failureReason}
        observedAt={roleQuery.dataUpdatedAt}
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
          fit={<RoleFitContainer roleId={roleId} pane="fit" />}
          gaps={<RoleFitContainer roleId={roleId} pane="gaps" />}
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
              draft={activeLetterDraft}
              versions={generatedLettersQuery.data ?? []}
              refusal={letterRefusal}
              supportingDocuments={supportingLettersQuery.data ?? []}
              citations={letterCitations}
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
