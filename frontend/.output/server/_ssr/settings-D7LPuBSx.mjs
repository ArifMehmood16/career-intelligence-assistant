import { n as __toESM } from "../_runtime.mjs";
import { f as setProviderChoice, o as getProviderChoice, s as getProviders } from "./client-Dl4tIPLr.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { i as useQueryClient, n as useQuery, t as useMutation } from "../_libs/tanstack__react-query.mjs";
import { t as ProviderSettings } from "./ProviderSettings-BG0WJIVk.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/settings-D7LPuBSx.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function ProviderSettingsContainer() {
	const queryClient = useQueryClient();
	const [pending, setPending] = (0, import_react.useState)(null);
	const providersQuery = useQuery({
		queryKey: ["providers"],
		queryFn: getProviders
	});
	const choiceQuery = useQuery({
		queryKey: ["provider-choice"],
		queryFn: getProviderChoice
	});
	const save = useMutation({
		mutationFn: setProviderChoice,
		onSuccess: (next) => {
			queryClient.setQueryData(["provider-choice"], next);
		}
	});
	const providers = providersQuery.data ?? [];
	const choice = choiceQuery.data ?? null;
	const apply = (kind, provider, model) => {
		if (!choice) return;
		const nextModel = model ?? provider.models[0] ?? "";
		const next = kind === "answer" ? {
			...choice,
			answerProviderId: provider.id,
			answerModel: nextModel
		} : {
			...choice,
			indexProviderId: provider.id,
			indexModel: nextModel
		};
		save.mutate(next);
	};
	const state = providersQuery.isPending || choiceQuery.isPending ? "loading" : providersQuery.isError || choiceQuery.isError || !choice ? "error" : "ready";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSettings, {
		state,
		providers,
		answerProviderId: choice?.answerProviderId ?? "",
		answerModel: choice?.answerModel ?? "",
		indexProviderId: choice?.indexProviderId ?? "",
		indexModel: choice?.indexModel ?? "",
		pendingProvider: pending?.provider ?? null,
		onSelect: (kind, providerId) => {
			const provider = providers.find((item) => item.id === providerId);
			if (!provider || !provider.available) return;
			if (provider.kind === "hosted") {
				setPending({
					kind,
					provider
				});
				return;
			}
			apply(kind, provider);
		},
		onModelChange: (kind, model) => {
			if (!choice) return;
			const currentId = kind === "answer" ? choice.answerProviderId : choice.indexProviderId;
			const provider = providers.find((item) => item.id === currentId);
			if (!provider) return;
			apply(kind, provider, model);
		},
		onConfirmHosted: () => {
			if (pending) apply(pending.kind, pending.provider);
			setPending(null);
		},
		onCancelHosted: () => setPending(null),
		onRetry: () => {
			providersQuery.refetch();
			choiceQuery.refetch();
		}
	});
}
function SettingsPage() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
			className: "text-xl",
			children: "Settings"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ProviderSettingsContainer, {})]
	});
}
//#endregion
export { SettingsPage as component };
