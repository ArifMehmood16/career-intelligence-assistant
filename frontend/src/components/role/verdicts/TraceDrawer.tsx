import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { RetrievalTrace, TraceRound, Verdict } from "@/types";

export type TraceState = "loading" | "error" | "ready";

export interface TraceDrawerProps {
  open: boolean;
  state: TraceState;
  verdict: Verdict | null;
  trace: RetrievalTrace | null;
  onOpenChange: (open: boolean) => void;
  onRetry: () => void;
}

function rank(value: number | null): string {
  return value === null ? "—" : String(value);
}

function RoundTable({
  round,
  cited,
}: {
  round: TraceRound;
  cited: ReadonlySet<string>;
}) {
  const caption =
    round.round === 0
      ? "Round 0: the requirement as the search query"
      : "Round 1: the judge's rewrite, in the judge's own words";
  return (
    <div className="space-y-2">
      <table aria-label={`Round ${round.round}`} className="w-full text-sm">
        <caption className="text-left">
          <span className="block font-medium">{caption}</span>
          <q className="block text-muted-foreground">{round.queryText}</q>
        </caption>
        <thead>
          <tr className="text-left text-muted-foreground">
            <th scope="col" className="py-1 pr-2">
              Chunk
            </th>
            <th scope="col" className="py-1 pr-2 text-right">
              Fused
            </th>
            <th scope="col" className="py-1 pr-2 text-right">
              Dense
            </th>
            <th scope="col" className="py-1 pr-2 text-right">
              Lexical
            </th>
            <th scope="col" className="py-1 pr-2 text-right">
              Exact
            </th>
            <th scope="col" className="py-1">
              <span className="sr-only">Cited</span>
            </th>
          </tr>
        </thead>
        <tbody className="font-mono tabular-nums">
          {round.hits.map((hit) => (
            <tr key={hit.chunkId} className="border-t border-border">
              <td className="py-1 pr-2 break-all">{hit.chunkId}</td>
              <td className="py-1 pr-2 text-right">
                {hit.fusedScore.toFixed(4)}
              </td>
              <td className="py-1 pr-2 text-right">{rank(hit.denseRank)}</td>
              <td className="py-1 pr-2 text-right">{rank(hit.lexicalRank)}</td>
              <td className="py-1 pr-2 text-right">{rank(hit.exactRank)}</td>
              <td className="py-1 font-sans">
                {cited.has(hit.chunkId) ? "Cited" : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The searches retrieval ran for one requirement and each leg's rank, fused by
 * reciprocal rank. Traces hold chunk ids and ranks, never chunk text.
 */
export function TraceDrawer({
  open,
  state,
  verdict,
  trace,
  onOpenChange,
  onRetry,
}: TraceDrawerProps) {
  const cited = new Set(verdict?.evidence.map((item) => item.chunkId) ?? []);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Retrieval trace</DialogTitle>
          <DialogDescription>{verdict?.statement ?? ""}</DialogDescription>
        </DialogHeader>
        {state === "loading" ? (
          <div className="space-y-2">
            <Skeleton className="h-5 w-64" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : state === "error" || trace === null ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              The trace could not be loaded.
            </p>
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            {trace.rounds.map((round) => (
              <RoundTable key={round.round} round={round} cited={cited} />
            ))}
            <p className="text-xs text-muted-foreground">
              A dash means that search leg did not return the chunk. Fused is
              the reciprocal-rank score the judge&apos;s candidates were ordered
              by.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
