import { n as __toESM } from "../_runtime.mjs";
import { t as cn } from "./utils-C_uf36nf.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { i as Square, p as ArrowUpRight } from "../_libs/lucide-react.mjs";
import { a as Trigger, i as Root3, n as Portal, r as Provider, t as Content2 } from "../_libs/radix-ui__react-tooltip.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/ProviderBadge-BehfGqHZ.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var TooltipProvider = Provider;
var Tooltip = Root3;
var TooltipTrigger = Trigger;
var TooltipContent = import_react.forwardRef(({ className, sideOffset = 4, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Portal, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Content2, {
	ref,
	sideOffset,
	className: cn("z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-(--radix-tooltip-content-transform-origin)", className),
	...props
}) }));
TooltipContent.displayName = Content2.displayName;
/**
* Single shared badge for every place a provider is shown.
* local  — outlined, neutral border, filled square glyph
* hosted — solid accent fill, outward-arrow glyph
* The glyph distinguishes the two without relying on colour.
*/
function ProviderBadge({ provider, model }) {
	const isHosted = provider.kind === "hosted";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipProvider, {
		delayDuration: 150,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Tooltip, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipTrigger, {
			asChild: true,
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("button", {
				type: "button",
				className: isHosted ? "inline-flex items-center gap-1.5 rounded-md bg-accent px-2 py-1 text-xs font-medium text-accent-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring" : "inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-2 py-1 text-xs font-medium text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
				children: [isHosted ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ArrowUpRight, {
					className: "size-3.5",
					"aria-hidden": "true"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Square, {
					className: "size-3 fill-current",
					"aria-hidden": "true"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: provider.name })]
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", {
			className: "font-mono text-xs",
			children: [
				provider.name,
				" · ",
				model
			]
		}) })] })
	});
}
//#endregion
export { ProviderBadge as t };
