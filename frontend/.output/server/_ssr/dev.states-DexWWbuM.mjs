import { n as __toESM } from "../_runtime.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { t as Button } from "./skeleton-C6lgllgE.mjs";
import { t as ChatView } from "./ChatView-CDi5wssh.mjs";
import { t as EvidencePanel } from "./EvidencePanel-THoMLmGq.mjs";
import { t as ProviderBadge } from "./ProviderBadge-BehfGqHZ.mjs";
import { t as RequirementTable } from "./RequirementTable-By8httmD.mjs";
import { t as ProviderSettings } from "./ProviderSettings-BG0WJIVk.mjs";
import { n as RolesPanel, t as CvCard } from "./RolesPanel-BehcnrAy.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/dev.states-DexWWbuM.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var noop = () => void 0;
var sampleCv = {
	id: "cv-demo",
	filename: "a-mehmood-cv.pdf",
	pageCount: 3,
	parsedAt: "2026-09-12T09:41:00.000Z"
};
var sampleRoles = [
	{
		id: "role-northwind",
		title: "Senior Data Analyst",
		company: "Northwind Analytics",
		fitScore: 82,
		bandLabel: "Strong match",
		counts: {
			met: 6,
			partial: 2,
			missing: 1
		}
	},
	{
		id: "role-kestrel",
		title: "Analytics Engineer",
		company: "Kestrel Systems",
		fitScore: 61,
		bandLabel: "Partial match",
		counts: {
			met: 4,
			partial: 3,
			missing: 3
		}
	},
	{
		id: "role-halden",
		title: "Machine Learning Engineer",
		company: "Halden Data Group",
		fitScore: 34,
		bandLabel: "Limited match",
		counts: {
			met: 2,
			partial: 2,
			missing: 5
		}
	}
];
var matchedEvidence = {
	documentId: "cv-demo",
	page: 1,
	paragraph: "Between 2021 and 2024 I owned the reporting layer for a retail analytics platform, writing and tuning complex SQL across a 4TB Postgres warehouse and cutting the nightly batch window from six hours to ninety minutes.",
	highlight: "writing and tuning complex SQL across a 4TB Postgres warehouse"
};
var sampleRequirements = [
	{
		id: "req-missing",
		roleId: "role-kestrel",
		text: "Hands-on Terraform for infrastructure as code",
		type: "must",
		status: "missing",
		evidence: null
	},
	{
		id: "req-partial",
		roleId: "role-kestrel",
		text: "Owns a production dbt project end to end",
		type: "must",
		status: "partial",
		evidence: {
			documentId: "cv-demo",
			page: 2,
			paragraph: "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on.",
			highlight: "covering roughly a third of the reporting tables"
		}
	},
	{
		id: "req-met",
		roleId: "role-kestrel",
		text: "5+ years of advanced SQL in a production warehouse",
		type: "must",
		status: "met",
		evidence: matchedEvidence
	}
];
var answeredMessage = {
	id: "msg-answered",
	author: "assistant",
	content: "Two must-have requirements have no supporting evidence in the CV: infrastructure as code with Terraform, and full ownership of a production dbt project.",
	kind: "answer",
	citations: [{
		id: "cit-1",
		label: "CV p.2",
		evidence: {
			documentId: "cv-demo",
			page: 2,
			paragraph: "Later I introduced dbt for a subset of the warehouse models, covering roughly a third of the reporting tables before I moved on.",
			highlight: "covering roughly a third of the reporting tables"
		}
	}, {
		id: "cit-2",
		label: "Senior Data Analyst — Northwind",
		evidence: matchedEvidence
	}],
	model: "built-in-offline",
	provider: "builtin"
};
var insufficientMessage = {
	id: "msg-insufficient",
	author: "assistant",
	content: "The CV does not contain enough information to answer that. No salary expectations or compensation history appear in the parsed document.",
	kind: "insufficient",
	citations: [],
	model: "built-in-offline",
	provider: "builtin"
};
var streamingMessage = {
	id: "msg-streaming",
	author: "assistant",
	content: "The strongest evidence for this role is the warehouse SQL work.",
	kind: "answer",
	citations: [],
	model: "built-in-offline",
	provider: "builtin"
};
var providerLocal = {
	id: "builtin",
	name: "Built-in offline mode",
	kind: "local",
	models: ["built-in-offline"],
	available: true,
	unavailableReason: null
};
var providerLocalUnavailable = {
	id: "local-server",
	name: "Local model server",
	kind: "local",
	models: ["llama3.1:8b", "qwen2.5:14b"],
	available: false,
	unavailableReason: "Local model server not reachable at http://localhost:11434."
};
var providerOpenAi = {
	id: "openai",
	name: "OpenAI",
	kind: "hosted",
	models: ["gpt-4.1", "gpt-4.1-mini"],
	available: false,
	unavailableReason: "No API key configured on the server."
};
var providerAnthropic = {
	id: "anthropic",
	name: "Anthropic",
	kind: "hosted",
	models: ["claude-sonnet-4", "claude-haiku-4"],
	available: false,
	unavailableReason: "External providers are turned off for this deployment."
};
var providerAnthropicAvailable = {
	...providerAnthropic,
	available: true,
	unavailableReason: null
};
var allProviders = [
	providerLocal,
	providerLocalUnavailable,
	providerOpenAi,
	providerAnthropic
];
var providerNameById = Object.fromEntries(allProviders.map((provider) => [provider.id, provider.name]));
var chatNoops = {
	onDraftChange: noop,
	onSend: noop,
	onStop: noop,
	onCitation: noop,
	onRetry: noop
};
function Section({ title, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "space-y-3 border-b border-border pb-8",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
			className: "text-base font-semibold",
			children: title
		}), children]
	});
}
function DevStatesPage() {
	const [evidenceKind, setEvidenceKind] = (0, import_react.useState)("matched");
	const [egressOpen, setEgressOpen] = (0, import_react.useState)(true);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto max-w-[900px] space-y-8",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
				className: "text-xl",
				children: "Component states"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-muted-foreground",
				children: "Every presentational component rendered from props alone. No data fetching."
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "CV card: empty",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCard, {
					state: "empty",
					document: null,
					errorMessage: null,
					onUpload: noop,
					onReplace: noop,
					onDelete: noop,
					onRetry: noop
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "CV card: parsing",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCard, {
					state: "parsing",
					document: null,
					errorMessage: null,
					onUpload: noop,
					onReplace: noop,
					onDelete: noop,
					onRetry: noop
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "CV card: parsed",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCard, {
					state: "parsed",
					document: sampleCv,
					errorMessage: null,
					onUpload: noop,
					onReplace: noop,
					onDelete: noop,
					onRetry: noop
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "CV card: error",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCard, {
					state: "error",
					document: null,
					errorMessage: "That file type is not supported.",
					onUpload: noop,
					onReplace: noop,
					onDelete: noop,
					onRetry: noop
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Roles table: loading",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
					state: "loading",
					roles: [],
					sortKey: "fit",
					sortDirection: "desc",
					onSort: noop,
					onRetry: noop,
					addRoleSlot: null,
					layout: "table"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Roles table: empty",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
					state: "empty",
					roles: [],
					sortKey: "fit",
					sortDirection: "desc",
					onSort: noop,
					onRetry: noop,
					addRoleSlot: null,
					layout: "table"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Roles table: error",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
					state: "error",
					roles: [],
					sortKey: "fit",
					sortDirection: "desc",
					onSort: noop,
					onRetry: noop,
					addRoleSlot: null,
					layout: "table"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Roles table: populated",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
					state: "ready",
					roles: sampleRoles,
					sortKey: "fit",
					sortDirection: "desc",
					onSort: noop,
					onRetry: noop,
					addRoleSlot: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "button",
						size: "sm",
						children: "Add role"
					}),
					layout: "table"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Roles stacked cards: populated",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
					state: "ready",
					roles: sampleRoles,
					sortKey: "fit",
					sortDirection: "desc",
					onSort: noop,
					onRetry: noop,
					addRoleSlot: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
						type: "button",
						size: "sm",
						children: "Add role"
					}),
					layout: "cards"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Requirement table: all three status groups",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RequirementTable, {
					state: "ready",
					requirements: sampleRequirements,
					collapsedGroups: [],
					onToggleGroup: noop,
					onSelect: noop,
					onRetry: noop,
					layout: "table"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Requirement table: mobile card variant",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RequirementTable, {
					state: "ready",
					requirements: sampleRequirements,
					collapsedGroups: [],
					onToggleGroup: noop,
					onSelect: noop,
					onRetry: noop,
					layout: "cards"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Evidence panel: matched requirement",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: () => setEvidenceKind("matched"),
					children: "Open matched evidence"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Evidence panel: missing requirement",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: () => setEvidenceKind("missing"),
					children: "Open missing evidence"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(EvidencePanel, {
				open: evidenceKind !== null,
				title: evidenceKind === "missing" ? "Hands-on Terraform for infrastructure as code" : "5+ years of advanced SQL in a production warehouse",
				status: evidenceKind === "missing" ? "missing" : "met",
				evidence: evidenceKind === "missing" ? null : matchedEvidence,
				onOpenChange: (open) => {
					if (!open) setEvidenceKind(null);
				}
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Chat: empty with starter chips",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "h-[420px]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatView, {
						state: "ready",
						messages: [],
						streamingId: null,
						streamingText: "",
						draft: "",
						sending: false,
						providerNameById,
						...chatNoops
					})
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Chat: streaming",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "h-[420px]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatView, {
						state: "ready",
						messages: [{
							id: "msg-user",
							author: "user",
							content: "Where is the strongest evidence for this role?",
							kind: "answer",
							citations: [],
							model: null,
							provider: null
						}, streamingMessage],
						streamingId: "msg-streaming",
						streamingText: "The strongest evidence for this role",
						draft: "",
						sending: false,
						providerNameById,
						...chatNoops
					})
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Chat: answered with citations",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "h-[420px]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatView, {
						state: "ready",
						messages: [{
							id: "msg-user-2",
							author: "user",
							content: "Where does my CV fall short for Kestrel?",
							kind: "answer",
							citations: [],
							model: null,
							provider: null
						}, answeredMessage],
						streamingId: null,
						streamingText: "",
						draft: "",
						sending: false,
						providerNameById,
						...chatNoops
					})
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Chat: insufficient evidence",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "h-[320px]",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ChatView, {
						state: "ready",
						messages: [insufficientMessage],
						streamingId: null,
						streamingText: "",
						draft: "",
						sending: false,
						providerNameById,
						...chatNoops
					})
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Provider cards: available, selected, and each unavailable reason",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSettings, {
					state: "ready",
					providers: allProviders,
					answerProviderId: "builtin",
					answerModel: "built-in-offline",
					indexProviderId: "builtin",
					indexModel: "built-in-offline",
					pendingProvider: null,
					onSelect: noop,
					onModelChange: noop,
					onConfirmHosted: noop,
					onCancelHosted: noop,
					onRetry: noop
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Section, {
				title: "Egress dialog: open",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
					type: "button",
					variant: "outline",
					size: "sm",
					onClick: () => setEgressOpen(true),
					children: "Re-open egress dialog"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSettings, {
					state: "ready",
					providers: [providerLocal, providerAnthropicAvailable],
					answerProviderId: "builtin",
					answerModel: "built-in-offline",
					indexProviderId: "builtin",
					indexModel: "built-in-offline",
					pendingProvider: egressOpen ? providerAnthropicAvailable : null,
					onSelect: noop,
					onModelChange: noop,
					onConfirmHosted: () => setEgressOpen(false),
					onCancelHosted: () => setEgressOpen(false),
					onRetry: noop
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Provider badge: local",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderBadge, {
					provider: providerLocal,
					model: "built-in-offline"
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Section, {
				title: "Provider badge: hosted",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderBadge, {
					provider: providerAnthropicAvailable,
					model: "claude-sonnet-4"
				})
			})
		]
	});
}
//#endregion
export { DevStatesPage as component };
