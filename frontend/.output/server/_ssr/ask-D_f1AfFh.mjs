import { n as __toESM } from "../_runtime.mjs";
import { a as getMessages, d as sendMessage, s as getProviders } from "./client-Dl4tIPLr.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { t as ChatView } from "./ChatView-CDi5wssh.mjs";
import { t as EvidencePanel } from "./EvidencePanel-THoMLmGq.mjs";
import { i as useQueryClient, n as useQuery, t as useMutation } from "../_libs/tanstack__react-query.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/ask-D_f1AfFh.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var TOKEN_MS = 28;
function ChatContainer() {
	const queryClient = useQueryClient();
	const [draft, setDraft] = (0, import_react.useState)("");
	const [streamingId, setStreamingId] = (0, import_react.useState)(null);
	const [streamingText, setStreamingText] = (0, import_react.useState)("");
	const [citation, setCitation] = (0, import_react.useState)(null);
	const [panelOpen, setPanelOpen] = (0, import_react.useState)(false);
	const timerRef = (0, import_react.useRef)(null);
	const messagesQuery = useQuery({
		queryKey: ["messages"],
		queryFn: getMessages
	});
	const providersQuery = useQuery({
		queryKey: ["providers"],
		queryFn: getProviders
	});
	const stopStream = () => {
		if (timerRef.current) clearInterval(timerRef.current);
		timerRef.current = null;
		setStreamingId(null);
		setStreamingText("");
	};
	(0, import_react.useEffect)(() => () => stopStream(), []);
	const send = useMutation({
		mutationFn: sendMessage,
		onSuccess: (next) => {
			queryClient.setQueryData(["messages"], next);
			const last = next[next.length - 1];
			if (!last || last.author !== "assistant") return;
			const tokens = last.content.split(/(\s+)/);
			let index = 0;
			setStreamingId(last.id);
			setStreamingText("");
			timerRef.current = setInterval(() => {
				index += 1;
				setStreamingText(tokens.slice(0, index).join(""));
				if (index >= tokens.length) stopStream();
			}, TOKEN_MS);
		}
	});
	const providerNameById = (0, import_react.useMemo)(() => Object.fromEntries((providersQuery.data ?? []).map((item) => [item.id, item.name])), [providersQuery.data]);
	const state = messagesQuery.isPending ? "loading" : messagesQuery.isError ? "error" : "ready";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex h-full min-h-0 flex-col",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatView, {
			state,
			messages: messagesQuery.data ?? [],
			streamingId,
			streamingText,
			draft,
			sending: send.isPending,
			providerNameById,
			onDraftChange: setDraft,
			onSend: () => {
				const content = draft.trim();
				if (!content || send.isPending) return;
				setDraft("");
				send.mutate(content);
			},
			onStop: stopStream,
			onCitation: (next) => {
				setCitation(next);
				setPanelOpen(true);
			},
			onRetry: () => {
				messagesQuery.refetch();
			}
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(EvidencePanel, {
			open: panelOpen,
			title: citation?.label ?? "",
			status: null,
			evidence: citation?.evidence ?? null,
			onOpenChange: setPanelOpen
		})]
	});
}
function AskPage() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-h-[calc(100vh-8.5rem)] flex-col gap-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
			className: "text-xl",
			children: "Ask"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "flex min-h-0 flex-1 flex-col",
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatContainer, {})
		})]
	});
}
//#endregion
export { AskPage as component };
