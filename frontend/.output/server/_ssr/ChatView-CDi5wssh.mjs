import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { n as Skeleton, t as Button } from "./skeleton-C6lgllgE.mjs";
import { t as Textarea } from "./textarea-N-uEoc1Y.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/ChatView-CDi5wssh.js
var import_jsx_runtime = require_jsx_runtime();
var STARTER_PROMPTS = [
	"What am I missing for this role?",
	"Compare my fit across all roles",
	"What will they probe in interview?"
];
function ChatView({ state, messages, streamingId, streamingText, draft, sending, providerNameById, onDraftChange, onSend, onStop, onCitation, onRetry }) {
	const empty = state === "ready" && messages.length === 0;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto flex h-full w-full max-w-[760px] flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-1 flex-col gap-5 pb-4",
			children: [
				state === "loading" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-16 w-full" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Skeleton, { className: "h-24 w-full" })] }) : null,
				state === "error" ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "card-surface space-y-3",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "That conversation could not be loaded." }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "button",
						variant: "outline",
						size: "sm",
						onClick: onRetry,
						children: "Retry"
					})]
				}) : null,
				state === "ready" ? messages.map((message) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(MessageBubble, {
					message,
					streaming: message.id === streamingId,
					streamingText,
					providerNameById,
					onCitation
				}, message.id)) : null
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "sticky bottom-0 space-y-3 border-t border-border bg-background pt-3 pb-4",
			children: [empty ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-2",
				children: STARTER_PROMPTS.map((prompt) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					onClick: () => onDraftChange(prompt),
					className: "rounded-md border border-border bg-surface px-3 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
					children: prompt
				}, prompt))
			}) : null, /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex items-end gap-2",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
					rows: 2,
					value: draft,
					placeholder: "Ask about your CV and the roles you saved",
					onChange: (event) => onDraftChange(event.target.value),
					onKeyDown: (event) => {
						if (event.key === "Enter" && !event.shiftKey) {
							event.preventDefault();
							onSend();
						}
					}
				}), streamingId ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					onClick: onStop,
					children: "Stop"
				}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					onClick: onSend,
					disabled: sending || !draft.trim(),
					children: "Send"
				})]
			})]
		})]
	});
}
function MessageBubble({ message, streaming, streamingText, providerNameById, onCitation }) {
	if (message.author === "user") return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex justify-end",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
			className: "max-w-[85%] rounded-md border border-border bg-surface px-3 py-2",
			children: message.content
		})
	});
	const insufficient = message.kind === "insufficient";
	const body = streaming ? streamingText : message.content;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: insufficient ? "space-y-3 rounded-md border border-border border-l-2 bg-surface px-3 py-3" : "space-y-3 rounded-md border border-border bg-surface px-3 py-3",
		children: [
			insufficient ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "text-xs font-medium",
				children: "Not enough evidence"
			}) : null,
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "whitespace-pre-wrap",
				children: [body, streaming ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					"aria-hidden": "true",
					className: "ml-0.5 inline-block h-4 w-[7px] translate-y-[2px] bg-foreground"
				}) : null]
			}),
			insufficient && !streaming ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: "Next step: add the detail to your CV, or ask about something the parsed document covers." }) : null,
			!streaming && message.citations.length > 0 ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-2",
				children: message.citations.map((citation) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					onClick: () => onCitation(citation),
					className: "rounded-md border border-border bg-background px-2 py-1 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring",
					children: citation.label
				}, citation.id))
			}) : null,
			!streaming && message.model ? /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "font-mono text-[11px] text-muted-foreground",
				children: [
					message.model,
					" ",
					message.provider ? providerNameById[message.provider] ?? message.provider : "unknown provider"
				]
			}) : null
		]
	});
}
//#endregion
export { ChatView as t };
