import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getProviderChoice,
  getProviders,
  setProviderChoice,
} from "@/api/client";
import {
  ProviderSettings,
  type ProviderSettingsState,
  type SelectorKind,
} from "@/components/settings/ProviderSettings";
import type { Provider, ProviderChoice } from "@/types";

export function ProviderSettingsContainer() {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<{
    kind: SelectorKind;
    provider: Provider;
  } | null>(null);

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
      queryClient.setQueryData(["provider-choice"], next);
    },
  });

  const providers = providersQuery.data ?? [];
  const choice = choiceQuery.data ?? null;

  const apply = (kind: SelectorKind, provider: Provider, model?: string) => {
    if (!choice) return;
    const nextModel = model ?? provider.models[0] ?? "";
    const next: ProviderChoice =
      kind === "answer"
        ? { ...choice, answerProviderId: provider.id, answerModel: nextModel }
        : { ...choice, indexProviderId: provider.id, indexModel: nextModel };
    save.mutate(next);
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
      onSelect={(kind, providerId) => {
        const provider = providers.find((item) => item.id === providerId);
        if (!provider || !provider.available) return;
        if (provider.kind === "hosted") {
          setPending({ kind, provider });
          return;
        }
        apply(kind, provider);
      }}
      onModelChange={(kind, model) => {
        if (!choice) return;
        const currentId =
          kind === "answer" ? choice.answerProviderId : choice.indexProviderId;
        const provider = providers.find((item) => item.id === currentId);
        if (!provider) return;
        apply(kind, provider, model);
      }}
      onConfirmHosted={() => {
        if (pending) apply(pending.kind, pending.provider);
        setPending(null);
      }}
      onCancelHosted={() => setPending(null)}
      onRetry={() => {
        void providersQuery.refetch();
        void choiceQuery.refetch();
      }}
    />
  );
}
