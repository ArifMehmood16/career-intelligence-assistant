/**
 * Phase 13.7 — side-by-side role comparison.
 * Presentational: role picks and comparison payload come from the container.
 */
import { StatusMark } from "@/components/StatusMark";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import type { Comparison, Role } from "@/types";

export interface ComparePanelProps {
  roles: Role[];
  roleAId: string;
  roleBId: string;
  state: AsyncState;
  comparison: Comparison | null;
  onRoleAChange: (roleId: string) => void;
  onRoleBChange: (roleId: string) => void;
  onCompare: () => void;
  onRetry: () => void;
  onOpenGaps: (roleId: string) => void;
}

export function ComparePanel({
  roles,
  roleAId,
  roleBId,
  state,
  comparison,
  onRoleAChange,
  onRoleBChange,
  onCompare,
  onRetry,
  onOpenGaps,
}: ComparePanelProps) {
  const canCompare =
    roleAId !== "" &&
    roleBId !== "" &&
    roleAId !== roleBId &&
    roles.length >= 2;

  return (
    <section
      aria-label="Compare"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-2 text-sm font-semibold">Compare</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Two roles side by side — shared requirements, unique ones, and the
        differentiator.
      </p>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="compare-role-a">Role A</Label>
          <select
            id="compare-role-a"
            value={roleAId}
            onChange={(event) => onRoleAChange(event.target.value)}
            className="h-9 rounded-md border border-border bg-background px-2 text-sm"
          >
            <option value="">Select a role</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title} — {role.company}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="compare-role-b">Role B</Label>
          <select
            id="compare-role-b"
            value={roleBId}
            onChange={(event) => onRoleBChange(event.target.value)}
            className="h-9 rounded-md border border-border bg-background px-2 text-sm"
          >
            <option value="">Select a role</option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.title} — {role.company}
              </option>
            ))}
          </select>
        </div>
        <Button type="button" onClick={onCompare} disabled={!canCompare}>
          Compare
        </Button>
      </div>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-3">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">
            The comparison could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="text-muted-foreground">
          Choose two different ready roles and compare them.
        </p>
      )}

      {state === "ready" && comparison !== null && (
        <div role="region" aria-label="Comparison result" className="space-y-6">
          <div className="flex flex-wrap gap-4 text-sm">
            <p>
              <span className="font-medium">{comparison.a.title}</span>
              <span className="text-muted-foreground">
                {" "}
                · {comparison.a.company} ·{" "}
              </span>
              <span className="font-mono">{comparison.a.fitScore}</span>
            </p>
            <p>
              <span className="font-medium">{comparison.b.title}</span>
              <span className="text-muted-foreground">
                {" "}
                · {comparison.b.company} ·{" "}
              </span>
              <span className="font-mono">{comparison.b.fitScore}</span>
            </p>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Shared requirements</h3>
            {comparison.shared.length === 0 ? (
              <p className="text-sm text-muted-foreground">None shared.</p>
            ) : (
              <ul className="space-y-2">
                {comparison.shared.map((item) => (
                  <li
                    key={item.text}
                    className="flex flex-wrap items-center gap-3 text-sm"
                  >
                    <span className="min-w-0 flex-1">{item.text}</span>
                    <StatusMark status={item.aStatus} />
                    <StatusMark status={item.bStatus} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Only in {comparison.a.title}
              </h3>
              <ul className="space-y-1 text-sm">
                {comparison.onlyInA.map((req) => (
                  <li key={req.id}>{req.text}</li>
                ))}
              </ul>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                Only in {comparison.b.title}
              </h3>
              <ul className="space-y-1 text-sm">
                {comparison.onlyInB.map((req) => (
                  <li key={req.id}>{req.text}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold">Differentiator</h3>
            <p className="text-sm text-foreground">
              {comparison.differentiator}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenGaps(comparison.a.id)}
            >
              Gaps for {comparison.a.title}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenGaps(comparison.b.id)}
            >
              Gaps for {comparison.b.title}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
