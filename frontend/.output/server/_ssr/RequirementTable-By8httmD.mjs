import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { n as Skeleton, t as Button } from "./skeleton-C6lgllgE.mjs";
import { l as ChevronRight, u as ChevronDown } from "../_libs/lucide-react.mjs";
import { n as StatusMark } from "./EvidencePanel-THoMLmGq.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/RequirementTable-By8httmD.js
var import_jsx_runtime = require_jsx_runtime();
var GROUP_ORDER = [
	"missing",
	"partial",
	"met"
];
var GROUP_LABEL = {
	missing: "Missing",
	partial: "Partial",
	met: "Met"
};
function excerpt(requirement) {
	if (!requirement.evidence) return "—";
	const text = requirement.evidence.highlight || requirement.evidence.paragraph;
	return text.length > 80 ? `${text.slice(0, 80)}…` : text;
}
function TypeBadge({ type }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: "inline-flex items-center rounded-none border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground",
		children: type === "must" ? "Must" : "Desirable"
	});
}
function RequirementTable({ state, requirements, collapsedGroups, onToggleGroup, onSelect, onRetry, layout = "responsive" }) {
	const onRowKeyDown = (event, requirement) => {
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			onSelect(requirement);
		}
	};
	const groups = GROUP_ORDER.map((status) => ({
		status,
		items: requirements.filter((requirement) => requirement.status === status)
	}));
	const tableClass = layout === "table" ? "table w-full border-collapse text-left" : layout === "cards" ? "hidden" : "hidden w-full border-collapse text-left md:table";
	const cardsClass = layout === "cards" ? "space-y-4" : layout === "table" ? "hidden" : "space-y-4 md:hidden";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Requirements",
		className: "rounded-md border border-border bg-surface p-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "mb-4 text-sm font-semibold",
				children: "Requirements"
			}),
			state === "loading" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				"aria-busy": "true",
				className: "space-y-2",
				children: [
					0,
					1,
					2,
					3,
					4
				].map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 flex-1" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-20" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-20" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-40" })
					]
				}, row))
			}),
			state === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-muted-foreground",
					children: "The requirements could not be loaded."
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: onRetry,
					children: "Retry"
				})]
			}),
			state === "empty" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "rounded-md border border-dashed border-border px-5 py-8 text-center text-muted-foreground",
				children: "No requirements have been extracted for this role yet."
			}),
			state === "ready" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
				className: tableClass,
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
					className: "border-b border-border",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
							scope: "col",
							className: "py-2 pr-4 font-medium text-muted-foreground",
							children: "Requirement"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
							scope: "col",
							className: "py-2 pr-4 font-medium text-muted-foreground",
							children: "Type"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
							scope: "col",
							className: "py-2 pr-4 font-medium text-muted-foreground",
							children: "Status"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
							scope: "col",
							className: "py-2 font-medium text-muted-foreground",
							children: "Evidence"
						})
					]
				}) }), groups.map((group) => {
					const collapsed = collapsedGroups.includes(group.status);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tbody", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("tr", {
						className: "border-b border-border",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
							scope: "colgroup",
							colSpan: 4,
							className: "py-2 font-medium",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
								type: "button",
								"aria-expanded": !collapsed,
								onClick: () => onToggleGroup(group.status),
								className: "inline-flex items-center gap-2 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
								children: [
									collapsed ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronRight, {
										className: "size-4 text-muted-foreground",
										"aria-hidden": "true"
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronDown, {
										className: "size-4 text-muted-foreground",
										"aria-hidden": "true"
									}),
									GROUP_LABEL[group.status],
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-mono text-muted-foreground",
										children: group.items.length
									})
								]
							})
						})
					}), !collapsed && group.items.map((requirement) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						tabIndex: 0,
						onClick: () => onSelect(requirement),
						onKeyDown: (event) => onRowKeyDown(event, requirement),
						className: "cursor-pointer border-b border-border outline-none hover:bg-background focus-visible:ring-2 focus-visible:ring-ring",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								scope: "row",
								className: "py-2 pr-4 font-normal",
								children: requirement.text
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-4",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TypeBadge, { type: requirement.type })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-4",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusMark, { status: requirement.status })
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 text-muted-foreground",
								children: excerpt(requirement)
							})
						]
					}, requirement.id))] }, group.status);
				})]
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: cardsClass,
				children: groups.map((group) => {
					const collapsed = collapsedGroups.includes(group.status);
					return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
						type: "button",
						"aria-expanded": !collapsed,
						onClick: () => onToggleGroup(group.status),
						className: "mb-2 inline-flex items-center gap-2 rounded-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring",
						children: [
							collapsed ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronRight, {
								className: "size-4 text-muted-foreground",
								"aria-hidden": "true"
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChevronDown, {
								className: "size-4 text-muted-foreground",
								"aria-hidden": "true"
							}),
							GROUP_LABEL[group.status],
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono text-muted-foreground",
								children: group.items.length
							})
						]
					}), !collapsed && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
						className: "space-y-2",
						children: group.items.map((requirement) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
							type: "button",
							onClick: () => onSelect(requirement),
							className: "block w-full rounded-md border border-border bg-background p-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring",
							children: [
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "block font-medium",
									children: requirement.text
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
									className: "mt-2 flex items-center gap-3",
									children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TypeBadge, { type: requirement.type }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusMark, { status: requirement.status })]
								}),
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "mt-2 block text-muted-foreground",
									children: excerpt(requirement)
								})
							]
						}) }, requirement.id))
					})] }, group.status);
				})
			})] })
		]
	});
}
//#endregion
export { RequirementTable as t };
