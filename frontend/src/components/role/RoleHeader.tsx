import { ArrowLeft } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";
import type { Role } from "@/types";

export interface RoleHeaderProps {
  role: Role | null;
  loading: boolean;
}

export function RoleHeader({ role, loading }: RoleHeaderProps) {
  return (
    <header className="sticky top-0 z-30 -mx-4 border-b border-border bg-background px-4 py-3">
      <Link
        to="/"
        className="inline-flex items-center gap-1 rounded-sm text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-3.5" aria-hidden="true" />
        Workspace
      </Link>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-2">
        {loading || !role ? (
          <Skeleton className="h-6 w-64" />
        ) : (
          <>
            <div>
              <h1 className="text-xl">{role.title}</h1>
              <p className="text-muted-foreground">{role.company}</p>
            </div>
            <p>
              <span className="font-mono text-xl">{role.fitScore}</span>
              <span className="text-muted-foreground">
                {" "}
                / 100 · {role.bandLabel}
              </span>
            </p>
          </>
        )}
      </div>
    </header>
  );
}
