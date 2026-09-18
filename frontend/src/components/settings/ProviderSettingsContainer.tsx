import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  getProviderChoice,
  getProviders,
  setProviderChoice,
} from "@/api/client";
import { describeApiError, formatDescribedError } from "@/api/errors";
import {
  ProviderSettings,
  type PendingReindex,
  type ProviderSettingsState,
  type SelectorKind,
} from "@/components/settings/ProviderSettings";
import type { Provider, ProviderChoice } from "@/types";

function mutationErrorMessage(error: unknown): string | null {
  if (!error) return null;
  return formatDescribedError(describeApiError(error));
}

export function ProviderSettingsContainer() {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<{
    kind: SelectorKind;
    provider: Provider;
  } | null>(null);
  const [pendingReindex, setPendingReindex] = useState<PendingReindex | null>(
    null,
  );

  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
  });
  const choiceQuery = useQuery({
    queryKey: ["provider-choice"],
    queryFn: getProviderChoice,
  });

  const save = useMutation({
    mutationFn: setProviderChoice,
    onSuccess: (next) => {
      queryClient.setQueryData(["provider-choice"], next.choice);
      if (next.reindexJobId) {
        void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      }
    },
  });

  const providers = providersQuery.data ?? [];
  const choice = choiceQuery.data ?? null;

  const apply = (
    kind: SelectorKind,
    provider: Provider,
    model?: string,
    acknowledgedEgress = false,
  ) => {
    if (!choice) return;
    const nextModel = model ?? provider.models[0] ?? "";
    const next: ProviderChoice =
      kind === "answer"
        ? { ...choice, answerProviderId: provider.id, answerModel: nextModel }
        : { ...choice, indexProviderId: provider.id, indexModel: nextModel };
    const needsAck =
      acknowledgedEgress ||
      providers.find((item) => item.id === next.answerProviderId)?.kind ===
        "hosted" ||
      providers.find((item) => item.id === next.indexProviderId)?.kind ===
        "hosted";
    save.mutate({ choice: next, acknowledgedEgress: needsAck });
  };

  const queueOrApply = (
    kind: SelectorKind,
    provider: Provider,
    model?: string,
  ) => {
    if (!choice) return;
    const nextModel = model ?? provider.models[0] ?? "";
    const indexChanging =
      kind === "index" &&
      (provider.id !== choice.indexProviderId ||
        nextModel !== choice.indexModel);

    if (indexChanging) {
      setPendingReindex({
        kind,
        providerId: provider.id,
        model: nextModel,
      });
      return;
    }

    if (provider.kind === "hosted") {
      setPending({ kind, provider });
      return;
    }

    apply(kind, provider, nextModel);
  };

  const state: ProviderSettingsState =
    providersQuery.isPending || choiceQuery.isPending
      ? "loading"
      : providersQuery.isError || choiceQuery.isError || !choice
        ? "error"
        : "ready";

  return (
    <ProviderSettings
      state={state}
      providers={providers}
      answerProviderId={choice?.answerProviderId ?? ""}
      answerModel={choice?.answerModel ?? ""}
      indexProviderId={choice?.indexProviderId ?? ""}
      indexModel={choice?.indexModel ?? ""}
      pendingProvider={pending?.provider ?? null}
      pendingReindex={pendingReindex}
      saveError={mutationErrorMessage(save.error)}
      onSelect={(kind, providerId) => {
        const provider = providers.find((item) => item.id === providerId);
        if (!provider || !provider.available) return;
        queueOrApply(kind, provider);
      }}
      onModelChange={(kind, model) => {
        if (!choice) return;
        const currentId =
          kind === "answer" ? choice.answerProviderId : choice.indexProviderId;
        const provider = providers.find((item) => item.id === currentId);
        if (!provider) return;
        queueOrApply(kind, provider, model);
      }}
      onConfirmHosted={() => {
        if (pending) {
          apply(pending.kind, pending.provider, undefined, true);
        }
        setPending(null);
      }}
      onCancelHosted={() => setPending(null)}
      onConfirmReindex={() => {
        if (!pendingReindex) return;
        const provider = providers.find(
          (item) => item.id === pendingReindex.providerId,
        );
        if (!provider) {
          setPendingReindex(null);
          return;
        }
        if (provider.kind === "hosted") {
          setPending({ kind: pendingReindex.kind, provider });
          setPendingReindex(null);
          return;
        }
        apply(pendingReindex.kind, provider, pendingReindex.model);
        setPendingReindex(null);
      }}
      onCancelReindex={() => setPendingReindex(null)}
      onRetry={() => {
        save.reset();
        void providersQuery.refetch();
        void choiceQuery.refetch();
      }}
    />
  );
}
