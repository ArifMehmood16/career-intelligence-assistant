import { ArrowLeft } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Role } from "@/types";

export type RoleHeaderState =
  "loading" | "ready" | "not-found" | "failed" | "analysing" | "error";

export interface RoleHeaderProps {
  role: Role | null;
  loading: boolean;
  state?: RoleHeaderState;
  onRetry?: () => void;
  onDelete?: () => void;
}

export function RoleHeader({
  role,
  loading,
  state,
  onRetry,
  onDelete,
}: RoleHeaderProps) {
  const resolved: RoleHeaderState =
    state ?? (loading || !role ? "loading" : "ready");

  const deleteControl =
    onDelete && role ? (
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={`Delete ${role.title}`}
        onClick={() => {
          const confirmed = window.confirm(
            `Delete ${role.title}? Its analysis, drafts and mappings will be removed.`,
          );
          if (confirmed) onDelete();
        }}
      >
        Delete
      </Button>
    ) : null;

  return (
    <header className="sticky top-0 z-30 -mx-4 border-b border-border bg-background px-4 py-3">
      <Link
        to="/"
        className="inline-flex items-center gap-1 rounded-sm text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-3.5" aria-hidden="true" />
        Workspace
      </Link>
      <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
        {resolved === "loading" ? (
          <Skeleton className="h-6 w-64" />
        ) : resolved === "not-found" ? (
          <p className="text-sm text-muted-foreground">Role not found.</p>
        ) : resolved === "error" ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              The role could not be loaded.
            </p>
            {onRetry ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onRetry}
              >
                Retry
              </Button>
            ) : null}
          </div>
        ) : resolved === "analysing" && role ? (
          <>
            <div>
              <h1 className="text-xl">{role.title}</h1>
              <p className="text-muted-foreground">{role.company}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <p
                role="status"
                aria-live="polite"
                className="text-muted-foreground"
              >
                Analysing
              </p>
              {deleteControl}
            </div>
          </>
        ) : resolved === "failed" && role ? (
          <>
            <div>
              <h1 className="text-xl">{role.title}</h1>
              <p className="text-muted-foreground">{role.company}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Analysis failed.
                </p>
                {onRetry ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={onRetry}
                  >
                    Retry analysis
                  </Button>
                ) : null}
              </div>
              {deleteControl}
            </div>
          </>
        ) : role ? (
          <>
            <div>
              <h1 className="text-xl">{role.title}</h1>
              <p className="text-muted-foreground">{role.company}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <p>
                <span className="font-mono text-xl">{role.fitScore}</span>
                <span className="text-muted-foreground">
                  {" "}
                  / 100 · {role.bandLabel}
                </span>
              </p>
              {deleteControl}
            </div>
          </>
        ) : (
          <Skeleton className="h-6 w-64" />
        )}
      </div>
    </header>
  );
}
