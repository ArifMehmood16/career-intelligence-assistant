import { ArrowDown, ArrowUp } from "lucide-react";
import type { KeyboardEvent, ReactNode } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Role } from "@/types";

export type RolesPanelState = "loading" | "error" | "empty" | "ready" | "inert";
export type RolesSortKey = "role" | "fit" | "met" | "partial" | "missing";
export type SortDirection = "asc" | "desc";
/** Force a layout for the state gallery; default follows the viewport. */
export type RolesLayout = "responsive" | "table" | "cards";
export type QueryLoadStatus = "pending" | "error" | "success";

export function deriveRolesPanelState(input: {
  cvStatus: QueryLoadStatus;
  rolesStatus: QueryLoadStatus;
  hasCv: boolean;
  roleCount: number;
}): RolesPanelState {
  if (input.cvStatus === "pending" || input.rolesStatus === "pending") {
    return "loading";
  }
  if (input.cvStatus === "error" || input.rolesStatus === "error") {
    return "error";
  }
  if (!input.hasCv) {
    return "inert";
  }
  return input.roleCount === 0 ? "empty" : "ready";
}

export interface RolesPanelProps {
  state: RolesPanelState;
  roles: Role[];
  sortKey: RolesSortKey;
  sortDirection: SortDirection;
  onSort: (key: RolesSortKey) => void;
  onRetry: () => void;
  onReanalyse?: (roleId: string) => void;
  failureReasons?: Record<string, string>;
  addRoleSlot: ReactNode;
  layout?: RolesLayout;
}

const COLUMNS: { key: RolesSortKey; label: string; numeric: boolean }[] = [
  { key: "role", label: "Role", numeric: false },
  { key: "fit", label: "Fit", numeric: false },
  { key: "met", label: "Met", numeric: true },
  { key: "partial", label: "Partial", numeric: true },
  { key: "missing", label: "Missing", numeric: true },
];

function FitCell({
  role,
  failureReason,
  onReanalyse,
}: {
  role: Role;
  failureReason?: string | undefined;
  onReanalyse?: ((roleId: string) => void) | undefined;
}) {
  if (role.status === "analysing") {
    return (
      <span role="status" aria-live="polite" className="text-muted-foreground">
        Analysing
      </span>
    );
  }
  if (role.status === "failed") {
    return (
      <div className="space-y-1">
        <span className="text-muted-foreground">Failed</span>
        {failureReason ? (
          <p className="text-sm text-muted-foreground">{failureReason}</p>
        ) : null}
        {onReanalyse ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onReanalyse(role.id);
            }}
          >
            Retry analysis
          </Button>
        ) : null}
      </div>
    );
  }
  return (
    <>
      <span className="font-mono">{role.fitScore}</span>
      <span className="text-muted-foreground"> / 100</span>
      <span className="ml-2 text-muted-foreground">{role.bandLabel}</span>
    </>
  );
}

export function RolesPanel({
  state,
  roles,
  sortKey,
  sortDirection,
  onSort,
  onRetry,
  onReanalyse,
  failureReasons = {},
  addRoleSlot,
  layout = "responsive",
}: RolesPanelProps) {
  const navigate = useNavigate();

  const tableClass =
    layout === "table"
      ? "block"
      : layout === "cards"
        ? "hidden"
        : "hidden min-[900px]:block";
  const cardsClass =
    layout === "cards"
      ? "block space-y-2"
      : layout === "table"
        ? "hidden"
        : "space-y-2 min-[900px]:hidden";

  const openRole = (id: string) => {
    void navigate({ to: "/roles/$id", params: { id } });
  };

  const onRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    id: string,
  ) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openRole(id);
    }
  };

  return (
    <section
      aria-label="Roles"
      className="rounded-md border border-border bg-surface p-5"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">Roles</h2>
        {addRoleSlot}
      </div>

      {state === "inert" && (
        <p className="rounded-md border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground">
          Add your CV first. Fit scores need something to compare against.
        </p>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Roles could not be loaded.
          </p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="rounded-md border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground">
          No roles yet. Add a job description to see how your CV compares.
        </p>
      )}

      {state === "loading" && (
        <div aria-busy="true" className="space-y-2">
          {[0, 1, 2, 3].map((row) => (
            <div key={row} className="flex items-center gap-4">
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-10" />
              <Skeleton className="h-4 w-10" />
              <Skeleton className="h-4 w-10" />
            </div>
          ))}
        </div>
      )}

      {state === "ready" && (
        <>
          <div className={tableClass}>
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-border">
                  {COLUMNS.map((column) => {
                    const active = sortKey === column.key;
                    return (
                      <th
                        key={column.key}
                        scope="col"
                        aria-sort={
                          active
                            ? sortDirection === "asc"
                              ? "ascending"
                              : "descending"
                            : "none"
                        }
                        className={
                          column.numeric
                            ? "py-2 text-right font-medium text-muted-foreground"
                            : "py-2 font-medium text-muted-foreground"
                        }
                      >
                        <button
                          type="button"
                          onClick={() => onSort(column.key)}
                          className={`inline-flex items-center gap-1 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                            column.numeric ? "justify-end" : ""
                          }`}
                        >
                          {column.label}
                          {active &&
                            (sortDirection === "asc" ? (
                              <ArrowUp className="size-3" aria-hidden="true" />
                            ) : (
                              <ArrowDown
                                className="size-3"
                                aria-hidden="true"
                              />
                            ))}
                        </button>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {roles.map((role) => (
                  <tr
                    key={role.id}
                    tabIndex={0}
                    onClick={() => openRole(role.id)}
                    onKeyDown={(event) => onRowKeyDown(event, role.id)}
                    className="cursor-pointer border-b border-border outline-none hover:bg-background focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <th scope="row" className="py-2 pr-4 font-normal">
                      <Link
                        to="/roles/$id"
                        params={{ id: role.id }}
                        tabIndex={-1}
                        className="font-medium outline-none"
                      >
                        {role.title}
                      </Link>
                      <span className="block text-muted-foreground">
                        {role.company}
                      </span>
                    </th>
                    <td className="py-2 pr-4">
                      <FitCell
                        role={role}
                        failureReason={failureReasons[role.id]}
                        onReanalyse={onReanalyse}
                      />
                    </td>
                    <td className="py-2 text-right font-mono">
                      {role.status === "ready" ? role.counts.met : "—"}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {role.status === "ready" ? role.counts.partial : "—"}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {role.status === "ready" ? role.counts.missing : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className={cardsClass}>
            {roles.map((role) => (
              <li key={role.id}>
                <Link
                  to="/roles/$id"
                  params={{ id: role.id }}
                  className="block rounded-md border border-border bg-background p-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="block font-medium">{role.title}</span>
                  <span className="block text-muted-foreground">
                    {role.company}
                  </span>
                  <span className="mt-2 block">
                    <FitCell
                      role={role}
                      failureReason={failureReasons[role.id]}
                      onReanalyse={onReanalyse}
                    />
                  </span>
                  {role.status === "ready" ? (
                    <span className="mt-1 block text-muted-foreground">
                      Met{" "}
                      <span className="font-mono text-foreground">
                        {role.counts.met}
                      </span>{" "}
                      · Partial{" "}
                      <span className="font-mono text-foreground">
                        {role.counts.partial}
                      </span>{" "}
                      · Missing{" "}
                      <span className="font-mono text-foreground">
                        {role.counts.missing}
                      </span>
                    </span>
                  ) : null}
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
