import { ArrowUpRight, Square } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Provider } from "@/types";

export interface ProviderBadgeProps {
  provider: Provider;
  model: string;
}

/**
 * Single shared badge for every place a provider is shown.
 * local  — outlined, neutral border, filled square glyph
 * hosted — solid accent fill, outward-arrow glyph
 * The glyph distinguishes the two without relying on colour.
 */
export function ProviderBadge({ provider, model }: ProviderBadgeProps) {
  const isHosted = provider.kind === "hosted";

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={
              isHosted
                ? "inline-flex items-center gap-1.5 rounded-md bg-accent px-2 py-1 text-xs font-medium text-accent-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
                : "inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-xs font-medium text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
            }
          >
            {isHosted ? (
              <ArrowUpRight className="size-3.5" aria-hidden="true" />
            ) : (
              <Square className="size-3 fill-current" aria-hidden="true" />
            )}
            <span>{provider.name}</span>
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <span className="font-mono text-xs">
            {provider.name} · {model}
          </span>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
