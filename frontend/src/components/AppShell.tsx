import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { CiaMark } from "@/components/CiaMark";
import { ProviderBadge } from "@/components/ProviderBadge";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Provider } from "@/types";

export interface AppShellProps {
  activeProvider: Provider | null;
  activeModel: string | null;
  children: ReactNode;
}

const navLinks = [
  { to: "/", label: "Workspace" },
  { to: "/ask", label: "Ask" },
  { to: "/settings", label: "Settings" },
] as const;

const linkFocus =
  "outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md";

export function AppShell({
  activeProvider,
  activeModel,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link
            to="/"
            aria-label="CIA — Career Intelligence Assistant"
            className={`inline-flex items-center gap-2 text-sm font-semibold tracking-tight ${linkFocus}`}
          >
            <CiaMark className="size-6 shrink-0 text-foreground" />
            <span>CIA</span>
            <span className="hidden font-normal text-muted-foreground sm:inline">
              Career Intelligence
            </span>
          </Link>

          <nav className="order-3 flex w-full flex-wrap items-center gap-1 sm:order-none sm:w-auto">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                activeOptions={{ exact: link.to === "/" }}
                className={`px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-background data-[status=active]:text-foreground ${linkFocus}`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {activeProvider && activeModel ? (
              <ProviderBadge provider={activeProvider} model={activeModel} />
            ) : (
              <span className="text-xs text-muted-foreground">No provider</span>
            )}
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        {children}
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-6xl px-4 py-3 text-xs text-muted-foreground sm:px-6">
          <Link
            to="/dev/states"
            className={`hover:text-foreground ${linkFocus}`}
          >
            Component states
          </Link>
        </div>
      </footer>
    </div>
  );
}
