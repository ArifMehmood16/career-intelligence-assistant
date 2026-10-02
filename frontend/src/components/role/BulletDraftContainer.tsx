import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { createBulletDraft, getSpan } from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import { EvidencePanel } from "@/components/EvidencePanel";
import { BulletDraftPanel } from "@/components/role/BulletDraftPanel";
import type { AsyncState } from "@/components/role/async-state";
import type { Evidence } from "@/types";

interface BulletDraftContainerProps {
  roleId: string;
  requirementId: string;
  onDismiss: () => void;
}

export function BulletDraftContainer({
  roleId,
  requirementId,
  onDismiss,
}: Readonly<BulletDraftContainerProps>) {
  const [copyError, setCopyError] = useState<string | null>(null);
  const [citation, setCitation] = useState<Evidence | null>(null);
  const { mutate, data, isPending, isError } = useMutation({
    mutationFn: (id: string) => createBulletDraft(roleId, id),
  });
  useEffect(() => {
    mutate(requirementId);
  }, [mutate, requirementId]);
  const span = useQuery({
    queryKey: ["span", citation?.spanId],
    queryFn: () => getSpan(citation!.spanId),
    enabled: citation !== null,
    retry: false,
  });
  let state: AsyncState = "empty";
  if (isPending) state = "loading";
  else if (isError) state = "error";
  else if (data) state = "ready";
  let resolveState: "loading" | "error" | "ready" = "ready";
  if (citation !== null && span.isPending) resolveState = "loading";
  if (span.isError) resolveState = "error";
  return (
    <>
      <BulletDraftPanel
        state={state}
        draft={data ?? null}
        copyError={copyError}
        onRetry={() => mutate(requirementId)}
        onDismiss={onDismiss}
        onCitation={setCitation}
        onCopy={(text) => {
          void navigator.clipboard.writeText(text).then(
            () => setCopyError(null),
            () => setCopyError("The draft could not be copied."),
          );
        }}
      />
      <EvidencePanel
        open={citation !== null}
        title="Cited CV evidence"
        status="partial"
        evidence={span.data ?? citation}
        resolveState={resolveState}
        resolveError={
          span.error ? formatDescribedError(describeApiError(span.error)) : null
        }
        onOpenChange={(open) => {
          if (!open) setCitation(null);
        }}
      />
    </>
  );
}
