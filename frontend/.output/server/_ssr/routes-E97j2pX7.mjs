import { n as __toESM } from "../_runtime.mjs";
import { n as deleteCv, p as uploadCv, r as getCv, t as addRole, u as getRoles } from "./client-Dl4tIPLr.mjs";
import { t as cva } from "../_libs/class-variance-authority+clsx.mjs";
import { t as cn } from "./utils-C_uf36nf.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { P as require_jsx_runtime, d as DialogContent$1, f as DialogDescription$1, g as DialogTrigger$1, h as DialogTitle$1, l as Dialog$1, m as DialogPortal$1, p as DialogOverlay$1, u as DialogClose } from "../_libs/@radix-ui/react-alert-dialog+[...].mjs";
import { t as Button } from "./skeleton-C6lgllgE.mjs";
import { t as Textarea } from "./textarea-N-uEoc1Y.mjs";
import { t as X } from "../_libs/lucide-react.mjs";
import { i as useQueryClient, n as useQuery, t as useMutation } from "../_libs/tanstack__react-query.mjs";
import { n as RolesPanel, t as CvCard } from "./RolesPanel-BehcnrAy.mjs";
import { i as Trigger, n as List, r as Root2, t as Content } from "../_libs/radix-ui__react-tabs.mjs";
import { t as Root } from "../_libs/radix-ui__react-label.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-E97j2pX7.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function CvCardContainer() {
	const queryClient = useQueryClient();
	const cvQuery = useQuery({
		queryKey: ["cv"],
		queryFn: getCv
	});
	const invalidate = () => {
		queryClient.invalidateQueries({ queryKey: ["cv"] });
	};
	const upload = useMutation({
		mutationFn: uploadCv,
		onSuccess: invalidate
	});
	const remove = useMutation({
		mutationFn: deleteCv,
		onSuccess: invalidate
	});
	const failed = cvQuery.isError || upload.isError || remove.isError;
	const busy = cvQuery.isPending || upload.isPending || remove.isPending;
	const state = failed ? "error" : busy ? "parsing" : cvQuery.data ? "parsed" : "empty";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCard, {
		state,
		document: cvQuery.data ?? null,
		errorMessage: failed ? "That CV could not be parsed. Try uploading it again." : null,
		onUpload: (filename) => upload.mutate(filename),
		onReplace: (filename) => upload.mutate(filename),
		onDelete: () => remove.mutate(),
		onRetry: () => {
			upload.reset();
			remove.reset();
			cvQuery.refetch();
		}
	});
}
var Dialog = Dialog$1;
var DialogTrigger = DialogTrigger$1;
var DialogPortal = DialogPortal$1;
var DialogOverlay = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogOverlay$1, {
	ref,
	className: cn("fixed inset-0 z-50 bg-foreground/20", className),
	...props
}));
DialogOverlay.displayName = DialogOverlay$1.displayName;
var DialogContent = import_react.forwardRef(({ className, children, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogPortal, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogOverlay, {}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent$1, {
	ref,
	className: cn("fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-background p-6 sm:rounded-lg", className),
	...props,
	children: [children, /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogClose, {
		className: "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background cursor-pointer transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(X, { className: "h-4 w-4" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
			className: "sr-only",
			children: "Close"
		})]
	})]
})] }));
DialogContent.displayName = DialogContent$1.displayName;
var DialogHeader = ({ className, ...props }) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
	className: cn("flex flex-col space-y-1.5 text-center sm:text-left", className),
	...props
});
DialogHeader.displayName = "DialogHeader";
var DialogFooter = ({ className, ...props }) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
	className: cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className),
	...props
});
DialogFooter.displayName = "DialogFooter";
var DialogTitle = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle$1, {
	ref,
	className: cn("text-lg font-semibold leading-none tracking-tight", className),
	...props
}));
DialogTitle.displayName = DialogTitle$1.displayName;
var DialogDescription = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription$1, {
	ref,
	className: cn("text-sm text-muted-foreground", className),
	...props
}));
DialogDescription.displayName = DialogDescription$1.displayName;
var Tabs = Root2;
var TabsList = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(List, {
	ref,
	className: cn("inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground", className),
	...props
}));
TabsList.displayName = List.displayName;
var TabsTrigger = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Trigger, {
	ref,
	className: cn("inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background cursor-pointer transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 disabled:cursor-not-allowed data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow", className),
	...props
}));
TabsTrigger.displayName = Trigger.displayName;
var TabsContent = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Content, {
	ref,
	className: cn("mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2", className),
	...props
}));
TabsContent.displayName = Content.displayName;
var Input = import_react.forwardRef(({ className, type, ...props }, ref) => {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
		type,
		className: cn("flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm", className),
		ref,
		...props
	});
});
Input.displayName = "Input";
var labelVariants = cva("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70");
var Label = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Root, {
	ref,
	className: cn(labelVariants(), className),
	...props
}));
Label.displayName = Root.displayName;
function AddRoleDialog({ open, disabled, submitting, onOpenChange, onSubmit }) {
	const [title, setTitle] = (0, import_react.useState)("");
	const [company, setCompany] = (0, import_react.useState)("");
	const [description, setDescription] = (0, import_react.useState)("");
	const [filename, setFilename] = (0, import_react.useState)("");
	const reset = () => {
		setTitle("");
		setCompany("");
		setDescription("");
		setFilename("");
	};
	const submit = (source) => {
		if (!title.trim() || !company.trim()) return;
		onSubmit({
			title: title.trim(),
			company: company.trim(),
			description: source === "file" ? filename : description.trim()
		});
		reset();
	};
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Dialog, {
		open,
		onOpenChange: (next) => {
			if (!next) reset();
			onOpenChange(next);
		},
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTrigger, {
			asChild: true,
			children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
				type: "button",
				size: "sm",
				disabled,
				children: "Add role"
			})
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogContent, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(DialogHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogTitle, { children: "Add role" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogDescription, { children: "Upload a job description file or paste the text." })] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-3",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
						htmlFor: "role-title",
						children: "Role title"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						id: "role-title",
						value: title,
						onChange: (event) => setTitle(event.target.value),
						placeholder: "Senior Data Analyst"
					})]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "grid gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
						htmlFor: "role-company",
						children: "Company"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
						id: "role-company",
						value: company,
						onChange: (event) => setCompany(event.target.value),
						placeholder: "Northwind Analytics"
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Tabs, {
				defaultValue: "upload",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TabsList, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TabsTrigger, {
						value: "upload",
						children: "Upload file"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TabsTrigger, {
						value: "paste",
						children: "Paste text"
					})] }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TabsContent, {
						value: "upload",
						className: "mt-3 space-y-3",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "grid gap-1.5",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
									htmlFor: "role-file",
									children: "Job description file"
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
									id: "role-file",
									type: "file",
									accept: ".pdf,.docx,.txt",
									onChange: (event) => setFilename(event.target.files?.[0]?.name ?? "")
								})]
							}),
							filename ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
								className: "font-mono text-sm text-muted-foreground",
								children: filename
							}) : null,
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogFooter, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
								type: "button",
								onClick: () => submit("file"),
								disabled: submitting || !title.trim() || !company.trim() || !filename,
								children: submitting ? "Adding…" : "Add role"
							}) })
						]
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(TabsContent, {
						value: "paste",
						className: "mt-3 space-y-3",
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "grid gap-1.5",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
								htmlFor: "role-text",
								children: "Job description"
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Textarea, {
								id: "role-text",
								rows: 8,
								value: description,
								onChange: (event) => setDescription(event.target.value),
								placeholder: "Paste the job description here"
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(DialogFooter, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Button, {
							type: "button",
							onClick: () => submit("text"),
							disabled: submitting || !title.trim() || !company.trim() || !description.trim(),
							children: submitting ? "Adding…" : "Add role"
						}) })]
					})
				]
			})
		] })]
	});
}
function compare(a, b, key) {
	switch (key) {
		case "role": return a.title.localeCompare(b.title);
		case "fit": return a.fitScore - b.fitScore;
		case "met": return a.counts.met - b.counts.met;
		case "partial": return a.counts.partial - b.counts.partial;
		case "missing": return a.counts.missing - b.counts.missing;
	}
}
function RolesPanelContainer() {
	const queryClient = useQueryClient();
	const [sortKey, setSortKey] = (0, import_react.useState)("fit");
	const [sortDirection, setSortDirection] = (0, import_react.useState)("desc");
	const [dialogOpen, setDialogOpen] = (0, import_react.useState)(false);
	const cvQuery = useQuery({
		queryKey: ["cv"],
		queryFn: getCv
	});
	const rolesQuery = useQuery({
		queryKey: ["roles"],
		queryFn: getRoles
	});
	const create = useMutation({
		mutationFn: addRole,
		onSuccess: () => {
			setDialogOpen(false);
			queryClient.invalidateQueries({ queryKey: ["roles"] });
		}
	});
	const roles = (0, import_react.useMemo)(() => {
		const list = [...rolesQuery.data ?? []];
		list.sort((a, b) => sortDirection === "asc" ? compare(a, b, sortKey) : compare(b, a, sortKey));
		return list;
	}, [
		rolesQuery.data,
		sortKey,
		sortDirection
	]);
	const hasCv = Boolean(cvQuery.data);
	const state = cvQuery.isPending || rolesQuery.isPending ? "loading" : !hasCv ? "inert" : rolesQuery.isError ? "error" : roles.length === 0 ? "empty" : "ready";
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanel, {
		state,
		roles,
		sortKey,
		sortDirection,
		onSort: (key) => {
			if (key === sortKey) setSortDirection(sortDirection === "asc" ? "desc" : "asc");
			else {
				setSortKey(key);
				setSortDirection(key === "role" ? "asc" : "desc");
			}
		},
		onRetry: () => {
			rolesQuery.refetch();
		},
		addRoleSlot: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AddRoleDialog, {
			open: dialogOpen,
			disabled: !hasCv,
			submitting: create.isPending,
			onOpenChange: setDialogOpen,
			onSubmit: (input) => create.mutate(input)
		})
	});
}
function WorkspacePage() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "space-y-6",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
			className: "text-xl",
			children: "Workspace"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex flex-col gap-6 min-[900px]:flex-row min-[900px]:items-start",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-[900px]:w-[380px] min-[900px]:shrink-0",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CvCardContainer, {})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "min-w-0 flex-1",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(RolesPanelContainer, {})
			})]
		})]
	});
}
//#endregion
export { WorkspacePage as component };
