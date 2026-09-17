import { n as __toESM } from "../_runtime.mjs";
import { c as getRequirements, i as getFitBreakdown, l as getRole } from "./client-Dl4tIPLr.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { n as Skeleton, t as Button } from "./skeleton-C6lgllgE.mjs";
import { l as ChevronRight, m as ArrowLeft, u as ChevronDown } from "../_libs/lucide-react.mjs";
import { t as EvidencePanel } from "./EvidencePanel-THoMLmGq.mjs";
import { n as useQuery } from "../_libs/tanstack__react-query.mjs";
import { t as RequirementTable } from "./RequirementTable-By8httmD.mjs";
import { h as Link } from "../_libs/@tanstack/react-router+[...].mjs";
import { t as Route } from "./roles._id-BU4vZl1c.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/roles._id-CrKSyoex.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function FitBreakdown({ state, rows, requirementsById, expandedRowIds, onToggleRow, onRetry }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Fit breakdown",
		className: "rounded-md border border-border bg-surface p-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "mb-4 text-sm font-semibold",
				children: "Breakdown"
			}),
			state === "loading" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				"aria-busy": "true",
				className: "space-y-4",
				children: [
					0,
					1,
					2
				].map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-48" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-1 w-full" })]
				}, row))
			}),
			state === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-muted-foreground",
					children: "The breakdown could not be loaded."
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: onRetry,
					children: "Retry"
				})]
			}),
			state === "empty" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-muted-foreground",
				children: "No breakdown is available for this role yet."
			}),
			state === "ready" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "space-y-4",
				children: rows.map((row) => {
					const expanded = expandedRowIds.includes(row.id);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("li", { children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							type: "button",
							"aria-expanded": expanded,
							onClick: () => onToggleRow(row.id),
							className: "flex w-full items-center gap-2 rounded-sm text-left outline-none focus-visible:ring-2 focus-visible:ring-ring",
							children: [
								expanded ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronDown, {
									className: "size-4 text-muted-foreground",
									"aria-hidden": "true"
								}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronRight, {
									className: "size-4 text-muted-foreground",
									"aria-hidden": "true"
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "flex-1",
									children: row.label
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono",
									children: row.value
								})
							]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							"aria-hidden": "true",
							className: "mt-2 h-1 w-full overflow-hidden rounded-sm bg-border",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
								className: "block h-1 w-full",
								viewBox: "0 0 100 4",
								preserveAspectRatio: "none",
								role: "presentation",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
									x: "0",
									y: "0",
									width: Math.max(0, Math.min(100, row.value)),
									height: "4",
									className: "fill-foreground"
								})
							})
						}),
						expanded && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("ul", {
							className: "mt-2 space-y-1 pl-6",
							children: [row.requirementIds.map((id) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
								className: "text-muted-foreground",
								children: requirementsById[id]?.text ?? id
							}, id)), row.requirementIds.length === 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", {
								className: "text-muted-foreground",
								children: "No requirements in this group."
							})]
						})
					] }, row.id);
				})
			})
		]
	});
}
function RoleHeader({ role, loading }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
		className: "sticky top-0 z-30 -mx-4 border-b border-border bg-background px-4 py-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Link, {
			to: "/",
			className: "inline-flex items-center gap-1 rounded-sm text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArrowLeft, {
				className: "size-3.5",
				"aria-hidden": "true"
			}), "Workspace"]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "mt-1 flex flex-wrap items-baseline justify-between gap-2",
			children: loading || !role ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-6 w-64" }) : /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "text-xl",
				children: role.title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-muted-foreground",
				children: role.company
			})] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "font-mono text-xl",
				children: role.fitScore
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
				className: "text-muted-foreground",
				children: [" / 100 · ", role.bandLabel]
			})] })] })
		})]
	});
}
function RoleDetailContainer({ roleId }) {
	const [expandedRowIds, setExpandedRowIds] = (0, import_react.useState)([]);
	const [collapsedGroups, setCollapsedGroups] = (0, import_react.useState)(["partial", "met"]);
	const [selected, setSelected] = (0, import_react.useState)(null);
	const [panelOpen, setPanelOpen] = (0, import_react.useState)(false);
	const roleQuery = useQuery({
		queryKey: ["role", roleId],
		queryFn: () => getRole(roleId)
	});
	const breakdownQuery = useQuery({
		queryKey: ["breakdown", roleId],
		queryFn: () => getFitBreakdown(roleId)
	});
	const requirementsQuery = useQuery({
		queryKey: ["requirements", roleId],
		queryFn: () => getRequirements(roleId)
	});
	const requirements = (0, import_react.useMemo)(() => requirementsQuery.data ?? [], [requirementsQuery.data]);
	const requirementsById = (0, import_react.useMemo)(() => Object.fromEntries(requirements.map((item) => [item.id, item])), [requirements]);
	const breakdownRows = breakdownQuery.data ?? [];
	const breakdownState = breakdownQuery.isPending ? "loading" : breakdownQuery.isError ? "error" : breakdownRows.length === 0 ? "empty" : "ready";
	const requirementsState = requirementsQuery.isPending ? "loading" : requirementsQuery.isError ? "error" : requirements.length === 0 ? "empty" : "ready";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RoleHeader, {
				role: roleQuery.data ?? null,
				loading: roleQuery.isPending
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(FitBreakdown, {
				state: breakdownState,
				rows: breakdownRows,
				requirementsById,
				expandedRowIds,
				onToggleRow: (id) => setExpandedRowIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]),
				onRetry: () => {
					breakdownQuery.refetch();
				}
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(RequirementTable, {
				state: requirementsState,
				requirements,
				collapsedGroups,
				onToggleGroup: (status) => setCollapsedGroups((current) => current.includes(status) ? current.filter((item) => item !== status) : [...current, status]),
				onSelect: (requirement) => {
					setSelected(requirement);
					setPanelOpen(true);
				},
				onRetry: () => {
					requirementsQuery.refetch();
				}
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(EvidencePanel, {
				open: panelOpen,
				title: selected?.text ?? "",
				status: selected?.status ?? "missing",
				evidence: selected?.evidence ?? null,
				onOpenChange: setPanelOpen
			})
		]
	});
}
function RolePage() {
	const { id } = Route.useParams();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RoleDetailContainer, { roleId: id });
}
//#endregion
export { RolePage as component };
