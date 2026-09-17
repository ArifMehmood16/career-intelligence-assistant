import { n as __toESM } from "../_runtime.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { n as Skeleton, t as Button } from "./skeleton-C6lgllgE.mjs";
import { f as ArrowUp, h as ArrowDown, n as Upload, o as FileText } from "../_libs/lucide-react.mjs";
import { g as useNavigate, h as Link } from "../_libs/@tanstack/react-router+[...].mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/RolesPanel-BehcnrAy.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function formatTimestamp(iso) {
	const date = new Date(iso);
	return new Intl.DateTimeFormat("en-GB", {
		dateStyle: "medium",
		timeStyle: "short"
	}).format(date);
}
function CvCard({ state, document: cv, errorMessage, onUpload, onReplace, onDelete, onRetry }) {
	const inputRef = (0, import_react.useRef)(null);
	const pickFile = () => inputRef.current?.click();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "CV",
		className: "rounded-md border border-border bg-surface p-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
				className: "mb-4 text-sm font-semibold",
				children: "Your CV"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
				ref: inputRef,
				type: "file",
				accept: ".pdf,.docx",
				className: "hidden",
				onChange: (event) => {
					const file = event.target.files?.[0];
					if (!file) return;
					if (state === "parsed") onReplace(file.name);
					else onUpload(file.name);
					event.target.value = "";
				}
			}),
			state === "empty" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "rounded-md border border-dashed border-border px-5 py-8 text-center",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Upload, {
						className: "mx-auto size-5 text-muted-foreground",
						"aria-hidden": "true"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-3 text-sm text-muted-foreground",
						children: "Upload your CV. PDF or DOCX, up to 10MB"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "button",
						className: "mt-4",
						onClick: pickFile,
						children: "Browse"
					})
				]
			}),
			state === "parsing" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				"aria-busy": "true",
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "size-8 rounded-md" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex-1 space-y-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-40" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-3 w-28" })]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-3 w-48" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2 pt-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-8 w-20" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-8 w-20" })]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-sm text-muted-foreground",
						children: "Parsing…"
					})
				]
			}),
			state === "parsed" && cv && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex items-start gap-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "flex size-8 items-center justify-center rounded-md border border-border bg-background",
							children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(FileText, {
								className: "size-4 text-muted-foreground",
								"aria-hidden": "true"
							})
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "min-w-0",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "truncate font-mono text-sm",
								children: cv.filename
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
								className: "text-sm text-muted-foreground",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono",
									children: cv.pageCount
								}), " pages"]
							})]
						})]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-sm text-muted-foreground",
						children: ["Parsed ", formatTimestamp(cv.parsedAt)]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
						className: "flex gap-2 pt-1",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							type: "button",
							variant: "outline",
							size: "sm",
							onClick: pickFile,
							children: "Replace"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							type: "button",
							variant: "outline",
							size: "sm",
							onClick: onDelete,
							children: "Delete"
						})]
					})
				]
			}),
			state === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: errorMessage ?? "That CV could not be parsed."
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: onRetry,
					children: "Retry"
				})]
			})
		]
	});
}
var COLUMNS = [
	{
		key: "role",
		label: "Role",
		numeric: false
	},
	{
		key: "fit",
		label: "Fit",
		numeric: false
	},
	{
		key: "met",
		label: "Met",
		numeric: true
	},
	{
		key: "partial",
		label: "Partial",
		numeric: true
	},
	{
		key: "missing",
		label: "Missing",
		numeric: true
	}
];
function RolesPanel({ state, roles, sortKey, sortDirection, onSort, onRetry, addRoleSlot, layout = "responsive" }) {
	const navigate = useNavigate();
	const tableClass = layout === "table" ? "block" : layout === "cards" ? "hidden" : "hidden min-[900px]:block";
	const cardsClass = layout === "cards" ? "block space-y-2" : layout === "table" ? "hidden" : "space-y-2 min-[900px]:hidden";
	const openRole = (id) => {
		navigate({
			to: "/roles/$id",
			params: { id }
		});
	};
	const onRowKeyDown = (event, id) => {
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			openRole(id);
		}
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		"aria-label": "Roles",
		className: "rounded-md border border-border bg-surface p-5",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "mb-4 flex items-center justify-between gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "text-sm font-semibold",
					children: "Roles"
				}), addRoleSlot]
			}),
			state === "inert" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "rounded-md border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground",
				children: "Add your CV first. Fit scores need something to compare against."
			}),
			state === "error" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "space-y-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-sm text-muted-foreground",
					children: "Roles could not be loaded."
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: onRetry,
					children: "Retry"
				})]
			}),
			state === "empty" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "rounded-md border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground",
				children: "No roles yet. Add a job description to see how your CV compares."
			}),
			state === "loading" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				"aria-busy": "true",
				className: "space-y-2",
				children: [
					0,
					1,
					2,
					3
				].map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-center gap-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 flex-1" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-24" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-10" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-10" }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-4 w-10" })
					]
				}, row))
			}),
			state === "ready" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: tableClass,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
					className: "w-full border-collapse text-left",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tr", {
						className: "border-b border-border",
						children: COLUMNS.map((column) => {
							const active = sortKey === column.key;
							return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								scope: "col",
								"aria-sort": active ? sortDirection === "asc" ? "ascending" : "descending" : "none",
								className: column.numeric ? "py-2 text-right font-medium text-muted-foreground" : "py-2 font-medium text-muted-foreground",
								children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
									type: "button",
									onClick: () => onSort(column.key),
									className: `inline-flex items-center gap-1 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${column.numeric ? "justify-end" : ""}`,
									children: [column.label, active && (sortDirection === "asc" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArrowUp, {
										className: "size-3",
										"aria-hidden": "true"
									}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArrowDown, {
										className: "size-3",
										"aria-hidden": "true"
									}))]
								})
							}, column.key);
						})
					}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: roles.map((role) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						tabIndex: 0,
						onClick: () => openRole(role.id),
						onKeyDown: (event) => onRowKeyDown(event, role.id),
						className: "cursor-pointer border-b border-border outline-none hover:bg-background focus-visible:ring-2 focus-visible:ring-ring",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("th", {
								scope: "row",
								className: "py-2 pr-4 font-normal",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Link, {
									to: "/roles/$id",
									params: { id: role.id },
									tabIndex: -1,
									className: "font-medium outline-none",
									children: role.title
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "block text-muted-foreground",
									children: role.company
								})]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("td", {
								className: "py-2 pr-4",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "font-mono",
										children: role.fitScore
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "text-muted-foreground",
										children: " / 100"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "ml-2 text-muted-foreground",
										children: role.bandLabel
									})
								]
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 text-right font-mono",
								children: role.counts.met
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 text-right font-mono",
								children: role.counts.partial
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 text-right font-mono",
								children: role.counts.missing
							})
						]
					}, role.id)) })]
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: cardsClass,
				children: roles.map((role) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Link, {
					to: "/roles/$id",
					params: { id: role.id },
					className: "block rounded-md border border-border bg-background p-4 outline-none focus-visible:ring-2 focus-visible:ring-ring",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "block font-medium",
							children: role.title
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "block text-muted-foreground",
							children: role.company
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "mt-2 block",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "font-mono",
								children: role.fitScore
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
								className: "text-muted-foreground",
								children: [" / 100 · ", role.bandLabel]
							})]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
							className: "mt-1 block text-muted-foreground",
							children: [
								"Met ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-foreground",
									children: role.counts.met
								}),
								" · Partial ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-foreground",
									children: role.counts.partial
								}),
								" · Missing ",
								/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
									className: "font-mono text-foreground",
									children: role.counts.missing
								})
							]
						})
					]
				}) }, role.id))
			})] })
		]
	});
}
//#endregion
export { RolesPanel as n, CvCard as t };
