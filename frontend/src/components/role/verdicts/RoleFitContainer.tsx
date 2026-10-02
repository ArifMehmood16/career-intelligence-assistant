import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ApiError, getRoleVerdicts, getVerdictTrace } from "@/api/client";
import { BulletDraftContainer } from "@/components/role/BulletDraftContainer";

import { TraceDrawer, type TraceState } from "./TraceDrawer";
import { VerdictGapsPanel } from "./VerdictGapsPanel";
import { VerdictsPanel, type VerdictsState } from "./VerdictsPanel";

export interface RoleFitContainerProps {
  roleId: string;
  pane: "fit" | "gaps";
}

/** A role's Fit or Gaps tab, read from the verdict routes. */
export function RoleFitContainer({ roleId, pane }: RoleFitContainerProps) {
  const [traceFor, setTraceFor] = useState<string | null>(null);
  const [draftFor, setDraftFor] = useState<string | null>(null);
  const verdictsQuery = useQuery({
    queryKey: ["verdicts", roleId],
    queryFn: () => getRoleVerdicts(roleId),
    retry: false,
  });
  const traceQuery = useQuery({
    queryKey: ["verdict-trace", roleId, traceFor],
    queryFn: () => getVerdictTrace(roleId, traceFor!),
    enabled: traceFor !== null,
    retry: false,
  });

  const state: VerdictsState = verdictsQuery.isPending
    ? "loading"
    : verdictsQuery.isError
      ? verdictsQuery.error instanceof ApiError &&
        verdictsQuery.error.code === "analysis_incomplete"
        ? "incomplete"
        : "error"
      : "ready";
  const verdicts = verdictsQuery.data ?? null;
  const retry = () => {
    void verdictsQuery.refetch();
  };

  if (pane === "gaps") {
    return (
      <div className="space-y-6">
        <VerdictGapsPanel
          state={state}
          verdicts={verdicts}
          onRetry={retry}
          onDraftBullet={setDraftFor}
        />
        {draftFor !== null ? (
          <BulletDraftContainer
            key={draftFor}
            roleId={roleId}
            requirementId={draftFor}
            onDismiss={() => setDraftFor(null)}
          />
        ) : null}
      </div>
    );
  }

  const traceState: TraceState = traceQuery.isPending
    ? "loading"
    : traceQuery.isError
      ? "error"
      : "ready";
  return (
    <>
      <VerdictsPanel
        state={state}
        verdicts={verdicts}
        onRetry={retry}
        onShowTrace={setTraceFor}
      />
      <TraceDrawer
        open={traceFor !== null}
        state={traceState}
        verdict={
          verdicts?.verdicts.find((item) => item.requirementId === traceFor) ??
          null
        }
        trace={traceQuery.data ?? null}
        onOpenChange={(open) => {
          if (!open) setTraceFor(null);
        }}
        onRetry={() => {
          void traceQuery.refetch();
        }}
      />
    </>
  );
}
