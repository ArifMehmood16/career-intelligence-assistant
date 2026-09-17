globalThis.__nitro_main__ = import.meta.url;
import { i as HTTPError, n as defineLazyEventHandler, t as H3Core } from "./_libs/h3+rou3+srvx.mjs";
import { t as HookableCore } from "./_libs/hookable.mjs";
import { r as FastResponse } from "./_libs/h3-v2+rou3+srvx.mjs";
//#region #nitro-vite-setup
function lazyService(loader) {
	let promise, mod;
	return { fetch(req) {
		if (mod) return mod.fetch(req);
		if (!promise) promise = loader().then((_mod) => mod = _mod.default || _mod);
		return promise.then((mod) => mod.fetch(req));
	} };
}
var services = { ["ssr"]: lazyService(() => import("./_ssr/ssr.mjs")) };
globalThis.__nitro_vite_envs__ = services;
//#endregion
//#region #nitro/virtual/public-assets-data
var public_assets_data_default = {
	"/.gitkeep": {
		"type": "text/plain; charset=utf-8",
		"etag": "\"0-2jmj7l5rSw0yVb/vlWAYkK/YBwk\"",
		"mtime": "2026-09-17T15:43:09.518Z",
		"size": 0,
		"path": "../public/.gitkeep"
	},
	"/favicon.ico": {
		"type": "image/vnd.microsoft.icon",
		"etag": "\"4f95-3RXc3p2mhEAs1WBwaIvE0Y0uu0Y\"",
		"mtime": "2026-09-17T22:10:20.684Z",
		"size": 20373,
		"path": "../public/favicon.ico"
	},
	"/robots.txt": {
		"type": "text/plain; charset=utf-8",
		"etag": "\"a0-CKGXSIe7TSsqDTmGm/nY1t/o5d0\"",
		"mtime": "2026-09-17T22:10:20.684Z",
		"size": 160,
		"path": "../public/robots.txt"
	},
	"/assets/ChatView-C0p_Lu6R.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"d04-WpcBlHPjjKcbfZrZpOeDQbDO4B8\"",
		"mtime": "2026-09-17T22:10:20.552Z",
		"size": 3332,
		"path": "../public/assets/ChatView-C0p_Lu6R.js"
	},
	"/assets/EvidencePanel-CyB3WAAS.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"baf-UGzKtM6zL1ImL3ifQpQloYvNWGU\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 2991,
		"path": "../public/assets/EvidencePanel-CyB3WAAS.js"
	},
	"/assets/RequirementTable-B9fPDU3u.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"1413-r8bn1SjEJMDr/gJSE8zeXNc+HaE\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 5139,
		"path": "../public/assets/RequirementTable-B9fPDU3u.js"
	},
	"/assets/RolesPanel-CMgknA4d.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"20f8-9S1TiGxERjeV6DRFYuQ8c5t+xOQ\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 8440,
		"path": "../public/assets/RolesPanel-CMgknA4d.js"
	},
	"/assets/ask-7CHZy8-A.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"6c9-MrdyGDWGeKqR7RnmWzKkHbchl24\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 1737,
		"path": "../public/assets/ask-7CHZy8-A.js"
	},
	"/assets/chevron-down-CpUt-K8A.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"75-4J6wCf2UsOpjmEQlF3cYSLv9Cwg\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 117,
		"path": "../public/assets/chevron-down-CpUt-K8A.js"
	},
	"/assets/ProviderSettings-_-u1JSQh.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"8738-lGoM8oifeOCkh056rEEG3M91g74\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 34616,
		"path": "../public/assets/ProviderSettings-_-u1JSQh.js"
	},
	"/assets/dist-C6FnTXtP.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"2bf4-hS2UGe4pKDJt46QtHLODvP5jzHQ\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 11252,
		"path": "../public/assets/dist-C6FnTXtP.js"
	},
	"/assets/dist-obgms1bA.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"5b85-Wv1i0Dh+BC5CYlBXz7BvFW2LYyg\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 23429,
		"path": "../public/assets/dist-obgms1bA.js"
	},
	"/assets/roles._id-DZiFKAjN.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"125a-ip3TGVepD5cDthCGES2dm2Mk6ac\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 4698,
		"path": "../public/assets/roles._id-DZiFKAjN.js"
	},
	"/assets/dev.states-Bgly9IBt.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"242c-PFok90/10cf5wqO+nMZZNoWH1NQ\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 9260,
		"path": "../public/assets/dev.states-Bgly9IBt.js"
	},
	"/assets/settings-BZa5iDfB.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"5c2-yQcLHybAS7YT3i95JQ/ZtxO4ZJQ\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 1474,
		"path": "../public/assets/settings-BZa5iDfB.js"
	},
	"/assets/textarea-BHm-2brR.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"1db-riIz/Wu8HISvOwVraKL9tqQtgwc\"",
		"mtime": "2026-09-17T22:10:20.554Z",
		"size": 475,
		"path": "../public/assets/textarea-BHm-2brR.js"
	},
	"/assets/routes-P4Wov8ov.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"299f-drZm6/YK5TUmnqq+QVe6rMdlDXQ\"",
		"mtime": "2026-09-17T22:10:20.553Z",
		"size": 10655,
		"path": "../public/assets/routes-P4Wov8ov.js"
	},
	"/assets/useMutation-B7Fz57Ms.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"921-0d7ZffoohDS1ms6jZNtcOUElnAk\"",
		"mtime": "2026-09-17T22:10:20.554Z",
		"size": 2337,
		"path": "../public/assets/useMutation-B7Fz57Ms.js"
	},
	"/assets/styles-CzKtKIAh.css": {
		"type": "text/css; charset=utf-8",
		"etag": "\"71e3-I6DQNX6bWIvEE8Ym/HerDG2PBbU\"",
		"mtime": "2026-09-17T22:10:20.554Z",
		"size": 29155,
		"path": "../public/assets/styles-CzKtKIAh.css"
	},
	"/assets/x-DxdKPCWZ.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"8f-tYfLte0zuneaCFooVnV2h8gv1E8\"",
		"mtime": "2026-09-17T22:10:20.554Z",
		"size": 143,
		"path": "../public/assets/x-DxdKPCWZ.js"
	},
	"/assets/utils-D5IoqmBG.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"e1e6-FV5U2yfsdd3oqalo9yHZLNpJ6WY\"",
		"mtime": "2026-09-17T22:10:20.554Z",
		"size": 57830,
		"path": "../public/assets/utils-D5IoqmBG.js"
	},
	"/assets/index-CvTr7tqW.js": {
		"type": "text/javascript; charset=utf-8",
		"etag": "\"68544-Sxafjyk/lrjARvI66gao6wNWP0o\"",
		"mtime": "2026-09-17T22:10:20.552Z",
		"size": 427332,
		"path": "../public/assets/index-CvTr7tqW.js"
	}
};
//#endregion
//#region #nitro/virtual/public-assets
var publicAssetBases = {};
function isPublicAssetURL(id = "") {
	if (public_assets_data_default[id]) return true;
	for (const base in publicAssetBases) if (id.startsWith(base)) return true;
	return false;
}
//#endregion
//#region node_modules/nitro/dist/runtime/internal/route-rules.mjs
var headers = ((m) => function headersRouteRule(event) {
	for (const [key, value] of Object.entries(m.options || {})) event.res.headers.set(key, value);
});
//#endregion
//#region #nitro/virtual/routing
var findRouteRules = /* @__PURE__ */ (() => {
	const $0 = [{
		name: "headers",
		route: "/assets/**",
		handler: headers,
		options: { "cache-control": "public, max-age=31536000, immutable" }
	}];
	return (m, p) => {
		let r = [];
		if (p.charCodeAt(p.length - 1) === 47) p = p.slice(0, -1) || "/";
		let s = p.split("/");
		if (s.length > 1) {
			if (s[1] === "assets") r.unshift({
				data: $0,
				params: { "_": s.slice(2).join("/") }
			});
		}
		return r;
	};
})();
var _lazy_7GRlFI = defineLazyEventHandler(() => import("./_chunks/ssr-renderer.mjs"));
var findRoute = /* @__PURE__ */ (() => {
	const data = {
		route: "/**",
		handler: _lazy_7GRlFI
	};
	return ((_m, p) => {
		return {
			data,
			params: { "_": p.slice(1) }
		};
	});
})();
[].filter(Boolean);
//#endregion
//#region node_modules/nitro/dist/runtime/internal/error/prod.mjs
var errorHandler = (error, event) => {
	const res = defaultHandler(error, event);
	return new FastResponse(typeof res.body === "string" ? res.body : JSON.stringify(res.body, null, 2), res);
};
function defaultHandler(error, event) {
	const unhandled = error.unhandled ?? !HTTPError.isError(error);
	const { status = 500, statusText = "" } = unhandled ? {} : error;
	if (status === 404) {
		const url = event.url || new URL(event.req.url);
		const baseURL = "/";
		if (/^\/[^/]/.test(baseURL) && !url.pathname.startsWith(baseURL)) return {
			status: 302,
			headers: new Headers({ location: `${baseURL}${url.pathname.slice(1)}${url.search}` })
		};
	}
	const headers = new Headers(unhandled ? {} : error.headers);
	headers.set("content-type", "application/json; charset=utf-8");
	return {
		status,
		statusText,
		headers,
		body: {
			error: true,
			...unhandled ? {
				status,
				unhandled: true
			} : typeof error.toJSON === "function" ? error.toJSON() : {
				status,
				statusText,
				message: error.message
			}
		}
	};
}
//#endregion
//#region #nitro/virtual/error-handler
var errorHandlers = [errorHandler];
async function error_handler_default(error, event) {
	for (const handler of errorHandlers) try {
		const response = await handler(error, event, { defaultHandler });
		if (response) return response;
	} catch (error) {
		console.error(error);
	}
}
//#endregion
//#region #nitro/virtual/app
function createNitroApp() {
	const captureError = (error, errorCtx) => {
		if (errorCtx?.event) {
			const errors = errorCtx.event.req.context?.nitro?.errors;
			if (errors) errors.push({
				error,
				context: errorCtx
			});
		}
	};
	const h3App = createH3App({ onError(error, event) {
		return error_handler_default(error, event);
	} });
	let appHandler = (req) => {
		req.context ||= {};
		req.context.nitro = req.context.nitro || { errors: [] };
		return h3App.fetch(req);
	};
	return {
		fetch: appHandler,
		h3: h3App,
		hooks: void 0,
		captureError
	};
}
function createH3App(config) {
	const h3App = new H3Core(config);
	h3App["~findRoute"] = (event) => findRoute(event.req.method, event.url.pathname);
	h3App["~getMiddleware"] = (event, route) => {
		const pathname = event.url.pathname;
		const method = event.req.method;
		const middleware = [];
		const routeRules = getRouteRules(method, pathname);
		event.context.routeRules = routeRules?.routeRules;
		if (routeRules?.routeRuleMiddleware.length) middleware.push(...routeRules.routeRuleMiddleware);
		if (route?.data?.middleware?.length) middleware.push(...route.data.middleware);
		return middleware;
	};
	return h3App;
}
//#endregion
//#region node_modules/nitro/dist/runtime/internal/app.mjs
var APP_ID = "default";
function useNitroApp() {
	let instance = useNitroApp._instance;
	if (instance) return instance;
	instance = useNitroApp._instance = createNitroApp();
	globalThis.__nitro__ = globalThis.__nitro__ || {};
	globalThis.__nitro__[APP_ID] = instance;
	return instance;
}
function useNitroHooks() {
	const nitroApp = useNitroApp();
	const hooks = nitroApp.hooks;
	if (hooks) return hooks;
	return nitroApp.hooks = new HookableCore();
}
function getRouteRules(method, pathname) {
	const m = findRouteRules(method, pathname);
	if (!m?.length) return { routeRuleMiddleware: [] };
	const routeRules = {};
	for (const layer of m) for (const rule of layer.data) {
		const currentRule = routeRules[rule.name];
		if (currentRule) {
			if (rule.options === false) {
				delete routeRules[rule.name];
				continue;
			}
			if (typeof currentRule.options === "object" && typeof rule.options === "object") currentRule.options = {
				...currentRule.options,
				...rule.options
			};
			else currentRule.options = rule.options;
			currentRule.route = rule.route;
			currentRule.params = {
				...currentRule.params,
				...layer.params
			};
		} else if (rule.options !== false) routeRules[rule.name] = {
			...rule,
			params: layer.params
		};
	}
	const middleware = [];
	const orderedRules = Object.values(routeRules).sort((a, b) => (a.handler?.order || 0) - (b.handler?.order || 0));
	for (const rule of orderedRules) {
		if (rule.options === false || !rule.handler) continue;
		middleware.push(rule.handler(rule));
	}
	return {
		routeRules,
		routeRuleMiddleware: middleware
	};
}
//#endregion
//#region node_modules/nitro/dist/presets/cloudflare/runtime/_module-handler.mjs
function createHandler(hooks) {
	const nitroApp = useNitroApp();
	const nitroHooks = useNitroHooks();
	return {
		async fetch(request, env, context) {
			globalThis.__env__ = env;
			augmentReq(request, {
				env,
				context
			});
			const ctxExt = {};
			const url = new URL(request.url);
			if (hooks.fetch) {
				const res = await hooks.fetch(request, env, context, url, ctxExt);
				if (res) return res;
			}
			return await nitroApp.fetch(request);
		},
		scheduled(controller, env, context) {
			globalThis.__env__ = env;
			context.waitUntil(nitroHooks.callHook("cloudflare:scheduled", {
				controller,
				env,
				context
			}) || Promise.resolve());
		},
		email(message, env, context) {
			globalThis.__env__ = env;
			context.waitUntil(nitroHooks.callHook("cloudflare:email", {
				message,
				event: message,
				env,
				context
			}) || Promise.resolve());
		},
		queue(batch, env, context) {
			globalThis.__env__ = env;
			context.waitUntil(nitroHooks.callHook("cloudflare:queue", {
				batch,
				event: batch,
				env,
				context
			}) || Promise.resolve());
		},
		tail(traces, env, context) {
			globalThis.__env__ = env;
			context.waitUntil(nitroHooks.callHook("cloudflare:tail", {
				traces,
				env,
				context
			}) || Promise.resolve());
		},
		trace(traces, env, context) {
			globalThis.__env__ = env;
			context.waitUntil(nitroHooks.callHook("cloudflare:trace", {
				traces,
				env,
				context
			}) || Promise.resolve());
		}
	};
}
function augmentReq(cfReq, ctx) {
	const req = cfReq;
	req.ip = cfReq.headers.get("cf-connecting-ip") || void 0;
	req.runtime ??= { name: "cloudflare" };
	req.runtime.cloudflare = {
		...req.runtime.cloudflare,
		...ctx
	};
	req.waitUntil = ctx.context?.waitUntil.bind(ctx.context);
}
//#endregion
//#region node_modules/nitro/dist/presets/cloudflare/runtime/cloudflare-module.mjs
var cloudflare_module_default = createHandler({ fetch(cfRequest, env, context, url) {
	if (env.ASSETS && isPublicAssetURL(url.pathname)) return env.ASSETS.fetch(cfRequest);
} });
//#endregion
export { cloudflare_module_default as default };
