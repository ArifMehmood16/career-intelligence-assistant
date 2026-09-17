import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { getProviderChoice, getProviders } from "@/api/client";
import { AppShell } from "@/components/AppShell";

export function AppShellContainer({ children }: { children: ReactNode }) {
  const providersQuery = useQuery({ queryKey: ["providers"], queryFn: getProviders });
  const choiceQuery = useQuery({ queryKey: ["provider-choice"], queryFn: getProviderChoice });

  const choice = choiceQuery.data ?? null;
  const activeProvider =
    providersQuery.data?.find((provider) => provider.id === choice?.answerProviderId) ?? null;

  return (
    <AppShell activeProvider={activeProvider} activeModel={choice?.answerModel ?? null}>
      {children}
    </AppShell>
  );
}
