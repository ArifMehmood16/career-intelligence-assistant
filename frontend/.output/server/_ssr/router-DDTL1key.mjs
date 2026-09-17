import { n as __toESM } from "../_runtime.mjs";
import { o as getProviderChoice, s as getProviders } from "./client-Dl4tIPLr.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { a as Moon, r as Sun } from "../_libs/lucide-react.mjs";
import { n as useQuery, r as QueryClientProvider } from "../_libs/tanstack__react-query.mjs";
import { t as QueryClient } from "../_libs/tanstack__query-core.mjs";
import { t as ProviderBadge } from "./ProviderBadge-BehfGqHZ.mjs";
import { _ as useRouter, c as HeadContent, d as Outlet, f as lazyRouteComponent, h as Link, m as createRootRouteWithContext, p as createFileRoute, s as Scripts, u as createRouter } from "../_libs/@tanstack/react-router+[...].mjs";
import { t as Route$5 } from "./roles._id-BU4vZl1c.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/router-DDTL1key.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
var styles_default = "/assets/styles-CzKtKIAh.css";
var STORAGE_KEY = "ci-theme";
function ThemeToggle() {
	const [theme, setTheme] = (0, import_react.useState)("light");
	(0, import_react.useEffect)(() => {
		const stored = window.localStorage.getItem(STORAGE_KEY);
		const initial = stored === "dark" || stored === "light" ? stored : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
		setTheme(initial);
	}, []);
	(0, import_react.useEffect)(() => {
		document.documentElement.classList.toggle("dark", theme === "dark");
		window.localStorage.setItem(STORAGE_KEY, theme);
	}, [theme]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
		type: "button",
		"aria-label": theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
		onClick: () => setTheme(theme === "dark" ? "light" : "dark"),
		className: "inline-flex size-8 items-center justify-center rounded-md border border-border bg-surface text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
		children: theme === "dark" ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Sun, {
			className: "size-4",
			"aria-hidden": "true"
		}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Moon, {
			className: "size-4",
			"aria-hidden": "true"
		})
	});
}
var navLinks = [
	{
		to: "/",
		label: "Workspace"
	},
	{
		to: "/ask",
		label: "Ask"
	},
	{
		to: "/settings",
		label: "Settings"
	}
];
var linkFocus = "outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md";
function AppShell({ activeProvider, activeModel, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex min-h-screen flex-col bg-background text-foreground",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("header", {
				className: "border-b border-border bg-surface",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Link, {
							to: "/",
							className: `text-sm font-semibold tracking-tight ${linkFocus}`,
							children: "Career Intelligence"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("nav", {
							className: "order-3 flex w-full flex-wrap items-center gap-1 sm:order-none sm:w-auto",
							children: navLinks.map((link) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Link, {
								to: link.to,
								activeOptions: { exact: link.to === "/" },
								className: `px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-background data-[status=active]:text-foreground ${linkFocus}`,
								children: link.label
							}, link.to))
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "flex items-center gap-2",
							children: [activeProvider && activeModel ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderBadge, {
								provider: activeProvider,
								model: activeModel
							}) : /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
								className: "text-xs text-muted-foreground",
								children: "No provider"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ThemeToggle, {})]
						})
					]
				})
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("main", {
				className: "mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6",
				children
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("footer", {
				className: "border-t border-border",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mx-auto w-full max-w-6xl px-4 py-3 text-xs text-muted-foreground sm:px-6",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Link, {
						to: "/dev/states",
						className: `hover:text-foreground ${linkFocus}`,
						children: "Component states"
					})
				})
			})
		]
	});
}
function AppShellContainer({ children }) {
	const providersQuery = useQuery({
		queryKey: ["providers"],
		queryFn: getProviders
	});
	const choice = useQuery({
		queryKey: ["provider-choice"],
		queryFn: getProviderChoice
	}).data ?? null;
	const activeProvider = providersQuery.data?.find((provider) => provider.id === choice?.answerProviderId) ?? null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShell, {
		activeProvider,
		activeModel: choice?.answerModel ?? null,
		children
	});
}
function reportLovableError(error, context = {}) {
	if (typeof window === "undefined") return;
	window.__lovableEvents?.captureException?.(error, {
		source: "react_error_boundary",
		route: window.location.pathname,
		...context
	}, {
		mechanism: "react_error_boundary",
		handled: false,
		severity: "error"
	});
	const message = error instanceof Response ? `Response ${error.status}${error.url ? ` at ${error.url}` : ""}` : error instanceof Error ? error.message : String(error);
	const stack = error instanceof Error ? error.stack : void 0;
	window.__lovableReportRuntimeError?.({
		message,
		...stack !== void 0 && { stack },
		filename: window.location.pathname
	});
}
function NotFoundComponent() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex min-h-screen items-center justify-center bg-background px-4",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "max-w-md text-center",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-7xl font-bold text-foreground",
					children: "404"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", {
					className: "mt-4 text-xl font-semibold text-foreground",
					children: "Page not found"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 text-sm text-muted-foreground",
					children: "The page you're looking for doesn't exist or has been moved."
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
					className: "mt-6",
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Link, {
						to: "/",
						className: "inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 outline-none focus-visible:ring-2 focus-visible:ring-ring",
						children: "Go home"
					})
				})
			]
		})
	});
}
function ErrorComponent({ error, reset }) {
	console.error(error);
	const router = useRouter();
	(0, import_react.useEffect)(() => {
		reportLovableError(error, { boundary: "tanstack_root_error_component" });
	}, [error]);
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
		className: "flex min-h-screen items-center justify-center bg-background px-4",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "max-w-md text-center",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
					className: "text-xl font-semibold tracking-tight text-foreground",
					children: "This page didn't load"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
					className: "mt-2 text-sm text-muted-foreground",
					children: "Something went wrong on our end. You can try refreshing or head back home."
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "mt-6 flex flex-wrap justify-center gap-2",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						onClick: () => {
							router.invalidate();
							reset();
						},
						className: "inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 outline-none focus-visible:ring-2 focus-visible:ring-ring",
						children: "Try again"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("a", {
						href: "/",
						className: "inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent outline-none focus-visible:ring-2 focus-visible:ring-ring",
						children: "Go home"
					})]
				})
			]
		})
	});
}
var Route$4 = createRootRouteWithContext()({
	head: () => ({
		meta: [
			{ charSet: "utf-8" },
			{
				name: "viewport",
				content: "width=device-width, initial-scale=1"
			},
			{ title: "Career Intelligence" },
			{
				name: "description",
				content: "Match a CV against job descriptions and ask questions about the fit."
			},
			{
				property: "og:title",
				content: "Career Intelligence"
			},
			{
				property: "og:description",
				content: "Match a CV against job descriptions and ask questions about the fit."
			},
			{
				property: "og:type",
				content: "website"
			},
			{
				name: "twitter:card",
				content: "summary_large_image"
			}
		],
		links: [
			{
				rel: "stylesheet",
				href: styles_default
			},
			{
				rel: "preconnect",
				href: "https://fonts.googleapis.com"
			},
			{
				rel: "preconnect",
				href: "https://fonts.gstatic.com",
				crossOrigin: "anonymous"
			},
			{
				rel: "stylesheet",
				href: "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap"
			},
			{
				rel: "icon",
				href: "/favicon.ico",
				type: "image/x-icon"
			}
		]
	}),
	shellComponent: RootShell,
	component: RootComponent,
	notFoundComponent: NotFoundComponent,
	errorComponent: ErrorComponent
});
function RootShell({ children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("html", {
		lang: "en",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("head", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(HeadContent, {}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("body", { children: [children, /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Scripts, {})] })]
	});
}
function RootComponent() {
	const { queryClient } = Route$4.useRouteContext();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(QueryClientProvider, {
		client: queryClient,
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShellContainer, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Outlet, {}) })
	});
}
var $$splitComponentImporter$3 = () => import("./routes-E97j2pX7.mjs");
var Route$3 = createFileRoute("/")({
	head: () => ({ meta: [
		{ title: "Workspace — Career Intelligence" },
		{
			name: "description",
			content: "Match your CV against saved job descriptions and see where the evidence sits."
		},
		{
			property: "og:title",
			content: "Workspace — Career Intelligence"
		},
		{
			property: "og:description",
			content: "Match your CV against saved job descriptions and see where the evidence sits."
		},
		{
			property: "og:type",
			content: "website"
		},
		{
			name: "twitter:card",
			content: "summary_large_image"
		}
	] }),
	component: lazyRouteComponent($$splitComponentImporter$3, "component")
});
var $$splitComponentImporter$2 = () => import("./ask-D_f1AfFh.mjs");
var Route$2 = createFileRoute("/ask")({
	head: () => ({ meta: [
		{ title: "Ask — Career Intelligence" },
		{
			name: "description",
			content: "Ask questions about your CV and role fit, answered with citations."
		},
		{
			property: "og:title",
			content: "Ask — Career Intelligence"
		},
		{
			property: "og:description",
			content: "Ask questions about your CV and role fit, answered with citations."
		},
		{
			property: "og:type",
			content: "website"
		},
		{
			name: "twitter:card",
			content: "summary_large_image"
		}
	] }),
	component: lazyRouteComponent($$splitComponentImporter$2, "component")
});
var $$splitComponentImporter$1 = () => import("./settings-D7LPuBSx.mjs");
var Route$1 = createFileRoute("/settings")({
	head: () => ({ meta: [
		{ title: "Settings — Career Intelligence" },
		{
			name: "description",
			content: "Choose the answering and indexing providers used for CV analysis."
		},
		{
			property: "og:title",
			content: "Settings — Career Intelligence"
		},
		{
			property: "og:description",
			content: "Choose the answering and indexing providers used for CV analysis."
		},
		{
			property: "og:type",
			content: "website"
		},
		{
			name: "twitter:card",
			content: "summary_large_image"
		}
	] }),
	component: lazyRouteComponent($$splitComponentImporter$1, "component")
});
var $$splitComponentImporter = () => import("./dev.states-DexWWbuM.mjs");
var Route = createFileRoute("/dev/states")({
	head: () => ({ meta: [
		{ title: "Component states — Career Intelligence" },
		{
			name: "description",
			content: "Gallery of every component state rendered from props alone."
		},
		{
			property: "og:title",
			content: "Component states — Career Intelligence"
		},
		{
			property: "og:description",
			content: "Gallery of every component state rendered from props alone."
		},
		{
			property: "og:type",
			content: "website"
		},
		{
			name: "twitter:card",
			content: "summary_large_image"
		}
	] }),
	component: lazyRouteComponent($$splitComponentImporter, "component")
});
var rootRouteChildren = {
	IndexRoute: Route$3.update({
		id: "/",
		path: "/",
		getParentRoute: () => Route$4
	}),
	AskRoute: Route$2.update({
		id: "/ask",
		path: "/ask",
		getParentRoute: () => Route$4
	}),
	SettingsRoute: Route$1.update({
		id: "/settings",
		path: "/settings",
		getParentRoute: () => Route$4
	}),
	DevStatesRoute: Route.update({
		id: "/dev/states",
		path: "/dev/states",
		getParentRoute: () => Route$4
	}),
	RolesIdRoute: Route$5.update({
		id: "/roles/$id",
		path: "/roles/$id",
		getParentRoute: () => Route$4
	})
};
var routeTree = Route$4._addFileChildren(rootRouteChildren)._addFileTypes();
var getRouter = () => {
	const queryClient = new QueryClient();
	return createRouter({
		routeTree,
		context: { queryClient },
		scrollRestoration: true,
		defaultPreloadStaleTime: 0
	});
};
//#endregion
export { getRouter };
