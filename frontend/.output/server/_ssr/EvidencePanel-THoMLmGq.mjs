import { n as __toESM } from "../_runtime.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime, d as DialogContent, h as DialogTitle, l as Dialog, m as DialogPortal, p as DialogOverlay, u as DialogClose } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { t as X } from "../_libs/lucide-react.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/EvidencePanel-THoMLmGq.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var LABELS = {
	met: "Met",
	partial: "Partial",
	missing: "Missing"
};
/**
* Glyph plus word, always both — status is never carried by colour alone.
* filled disc = met, half disc = partial, hollow ring = missing.
*/
function StatusMark({ status }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
		className: "inline-flex items-center gap-2 whitespace-nowrap",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			"aria-hidden": "true",
			className: "inline-flex",
			children: [
				status === "met" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
					viewBox: "0 0 12 12",
					className: "size-3 text-met",
					role: "presentation",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
						cx: "6",
						cy: "6",
						r: "5",
						fill: "currentColor"
					})
				}),
				status === "partial" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
					viewBox: "0 0 12 12",
					className: "size-3 text-partial",
					role: "presentation",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
						cx: "6",
						cy: "6",
						r: "5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: "1.5"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
						d: "M6 1 A5 5 0 0 1 6 11 Z",
						fill: "currentColor"
					})]
				}),
				status === "missing" && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
					viewBox: "0 0 12 12",
					className: "size-3 text-missing",
					role: "presentation",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
						cx: "6",
						cy: "6",
						r: "5",
						fill: "none",
						stroke: "currentColor",
						strokeWidth: "1.5"
					})
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: LABELS[status] })]
	});
}
/**
* Shared evidence panel. Knows nothing about requirements or chat citations:
* it renders a title, a status and an Evidence object.
* Right-hand panel at 420px on desktop, bottom sheet below 768px.
* Radix Dialog supplies the focus trap, Escape handling and focus return.
*/
function EvidencePanel({ open, title, status, evidence, onOpenChange }) {
	const headingRef = (0, import_react.useRef)(null);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dialog, {
		open,
		onOpenChange,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogPortal, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogOverlay, { className: "fixed inset-0 z-50 bg-foreground/20" }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, {
			"aria-describedby": void 0,
			onOpenAutoFocus: (event) => {
				event.preventDefault();
				headingRef.current?.focus();
			},
			className: "fixed z-50 flex flex-col gap-4 overflow-y-auto border-border bg-surface p-5 inset-x-0 bottom-0 max-h-[85vh] rounded-t-md border-t md:inset-y-0 md:right-0 md:left-auto md:max-h-none md:w-[420px] md:rounded-none md:border-t-0 md:border-l",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex items-start justify-between gap-4",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, {
						asChild: true,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
							ref: headingRef,
							tabIndex: -1,
							className: "text-sm font-semibold outline-none",
							children: title
						})
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogClose, {
						className: "rounded-sm p-1 text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
						"aria-label": "Close evidence",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(X, {
							className: "size-4",
							"aria-hidden": "true"
						})
					})]
				}),
				status ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(StatusMark, { status }) : null,
				evidence ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "space-y-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
						className: "text-muted-foreground",
						children: ["CV page ", /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
							className: "font-mono",
							children: evidence.page
						})]
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("blockquote", {
						className: "border-l-2 border-border pl-3 font-mono text-[13px] leading-relaxed",
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HighlightedParagraph, {
							paragraph: evidence.paragraph,
							highlight: evidence.highlight
						})
					})]
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "text-muted-foreground",
					children: "No supporting text was found in your CV for this. Nothing in the parsed document matches it, so there is no passage to show."
				})
			]
		})] })
	});
}
function HighlightedParagraph({ paragraph, highlight }) {
	const index = highlight ? paragraph.indexOf(highlight) : -1;
	if (index === -1) return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(import_jsx_runtime.Fragment, { children: paragraph });
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
		paragraph.slice(0, index),
		/* @__PURE__ */ (0, import_jsx_runtime.jsx)("mark", {
			className: "bg-highlight text-foreground",
			children: highlight
		}),
		paragraph.slice(index + highlight.length)
	] });
}
//#endregion
export { StatusMark as n, EvidencePanel as t };
