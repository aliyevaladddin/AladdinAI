import { AppShell } from "@/components/shell/AppShell";

/**
 * Minimal chrome for public/auth surfaces.
 * Shows the lamp + wordmark in the titlebar but no activity bar or
 * status bar — those are reserved for the authenticated workspace.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <div className="min-h-full w-full flex items-center justify-center px-4 py-12">
        {children}
      </div>
    </AppShell>
  );
}
