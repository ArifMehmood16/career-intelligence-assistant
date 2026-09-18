import { useQuery } from "@tanstack/react-query";

import { getRanking } from "@/api/client";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { RankingPanel } from "@/components/workspace/RankingPanel";

export function RankingPanelContainer() {
  const rankingQuery = useQuery({
    queryKey: ["ranking"],
    queryFn: getRanking,
  });

  const ranked = rankingQuery.data ?? [];
  const state: AsyncState = rankingQuery.isPending
    ? "loading"
    : rankingQuery.isError
      ? "error"
      : ranked.length === 0
        ? "empty"
        : "ready";

  return (
    <RankingPanel
      state={state}
      ranked={ranked}
      onRetry={() => {
        void rankingQuery.refetch();
      }}
    />
  );
}
