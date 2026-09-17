import { ChevronDown, ChevronRight } from "lucide-react";
import type { KeyboardEvent } from "react";
import { StatusMark } from "@/components/StatusMark";
import type { AsyncState } from "@/components/role/FitBreakdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Requirement, RequirementStatus } from "@/types";

const GROUP_ORDER: RequirementStatus[] = ["missing", "partial", "met"];
const GROUP_LABEL: Record<RequirementStatus, string> = {
  missing: "Missing",
  partial: "Partial",
  met: "Met",
};

/** Force a layout for the state gallery; default follows the viewport. */
export type RequirementLayout = "responsive" | "table" | "cards";

export interface RequirementTableProps {
  state: AsyncState;
  requirements: Requirement[];
  collapsedGroups: RequirementStatus[];
  onToggleGroup: (status: RequirementStatus) => void;
  onSelect: (requirement: Requirement) => void;
  onRetry: () => void;
  layout?: RequirementLayout;
}

function excerpt(requirement: Requirement): string {
  if (!requirement.evidence) return "—";
  const text = requirement.evidence.highlight || requirement.evidence.paragraph;
  return text.length > 80 ? `${text.slice(0, 80)}…` : text;
}

function TypeBadge({ type }: { type: Requirement["type"] }) {
  return (
    <span className="inline-flex items-center rounded-none border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground">
      {type === "must" ? "Must" : "Desirable"}
    </span>
  );
}

export function RequirementTable({
  state,
  requirements,
  collapsedGroups,
  onToggleGroup,
  onSelect,
  onRetry,
  layout = "responsive",
}: RequirementTableProps) {
  const onRowKeyDown = (
    event: KeyboardEvent<HTMLElement>,
    requirement: Requirement,
  ) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(requirement);
    }
  };

  const groups = GROUP_ORDER.map((status) => ({
    status,
    items: requirements.filter((requirement) => requirement.status === status),
  }));

  const tableClass =
    layout === "table"
      ? "table w-full border-collapse text-left"
      : layout === "cards"
        ? "hidden"
        : "hidden w-full border-collapse text-left md:table";
  const cardsClass =
    layout === "cards"
      ? "space-y-4"
      : layout === "table"
        ? "hidden"
        : "space-y-4 md:hidden";

  return (
    <section
      aria-label="Requirements"
      className="rounded-md border border-border bg-surface p-5"
    >
      <h2 className="mb-4 text-sm font-semibold">Requirements</h2>

      {state === "loading" && (
        <div aria-busy="true" className="space-y-2">
          {[0, 1, 2, 3, 4].map((row) => (
            <div key={row} className="flex items-center gap-4">
              <Skeleton className="h-4 flex-1" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-40" />
            </div>
          ))}
        </div>
      )}

      {state === "error" && (
        <div className="space-y-3">
          <p className="text-muted-foreground">The requirements could not be loaded.</p>
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}

      {state === "empty" && (
        <p className="rounded-md border border-dashed border-border px-5 py-8 text-center text-muted-foreground">
          No requirements have been extracted for this role yet.
        </p>
      )}

      {state === "ready" && (
        <>
          {/* Table at 768px and above (or forced via layout) */}
          <table className={tableClass}>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="py-2 pr-4 font-medium text-muted-foreground">
                  Requirement
                </th>
                <th scope="col" className="py-2 pr-4 font-medium text-muted-foreground">
                  Type
                </th>
                <th scope="col" className="py-2 pr-4 font-medium text-muted-foreground">
                  Status
                </th>
                <th scope="col" className="py-2 font-medium text-muted-foreground">
                  Evidence
                </th>
              </tr>
            </thead>
            {groups.map((group) => {
              const collapsed = collapsedGroups.includes(group.status);
              return (
                <tbody key={group.status}>
                  <tr className="border-b border-border">
                    <th scope="colgroup" colSpan={4} className="py-2 font-medium">
                      <button
                        type="button"
                        aria-expanded={!collapsed}
                        onClick={() => onToggleGroup(group.status)}
                        className="inline-flex items-center gap-2 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {collapsed ? (
                          <ChevronRight className="size-4 text-muted-foreground" aria-hidden="true" />
                        ) : (
                          <ChevronDown className="size-4 text-muted-foreground" aria-hidden="true" />
                        )}
                        {GROUP_LABEL[group.status]}
                        <span className="font-mono text-muted-foreground">
                          {group.items.length}
                        </span>
                      </button>
                    </th>
                  </tr>
                  {!collapsed &&
                    group.items.map((requirement) => (
                      <tr
                        key={requirement.id}
                        tabIndex={0}
                        onClick={() => onSelect(requirement)}
                        onKeyDown={(event) => onRowKeyDown(event, requirement)}
                        className="cursor-pointer border-b border-border outline-none hover:bg-background focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <th scope="row" className="py-2 pr-4 font-normal">
                          {requirement.text}
                        </th>
                        <td className="py-2 pr-4">
                          <TypeBadge type={requirement.type} />
                        </td>
                        <td className="py-2 pr-4">
                          <StatusMark status={requirement.status} />
                        </td>
                        <td className="py-2 text-muted-foreground">{excerpt(requirement)}</td>
                      </tr>
                    ))}
                </tbody>
              );
            })}
          </table>

          {/* Stacked cards below 768px (or forced via layout) */}
          <div className={cardsClass}>
            {groups.map((group) => {
              const collapsed = collapsedGroups.includes(group.status);
              return (
                <div key={group.status}>
                  <button
                    type="button"
                    aria-expanded={!collapsed}
                    onClick={() => onToggleGroup(group.status)}
                    className="mb-2 inline-flex items-center gap-2 rounded-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {collapsed ? (
                      <ChevronRight className="size-4 text-muted-foreground" aria-hidden="true" />
                    ) : (
                      <ChevronDown className="size-4 text-muted-foreground" aria-hidden="true" />
                    )}
                    {GROUP_LABEL[group.status]}
                    <span className="font-mono text-muted-foreground">{group.items.length}</span>
                  </button>
                  {!collapsed && (
                    <ul className="space-y-2">
                      {group.items.map((requirement) => (
                        <li key={requirement.id}>
                          <button
                            type="button"
                            onClick={() => onSelect(requirement)}
                            className="block w-full rounded-md border border-border bg-background p-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            <span className="block font-medium">{requirement.text}</span>
                            <span className="mt-2 flex items-center gap-3">
                              <TypeBadge type={requirement.type} />
                              <StatusMark status={requirement.status} />
                            </span>
                            <span className="mt-2 block text-muted-foreground">
                              {excerpt(requirement)}
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
