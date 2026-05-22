"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { Toaster } from "sonner";

import { AppShell } from "@/components/shell/AppShell";
import { ActivityBar } from "@/components/shell/ActivityBar";
import { StatusBar } from "@/components/shell/StatusBar";
import { DASHBOARD_PRIMARY, DASHBOARD_FOOTER } from "@/components/shell/dashboard-nav";
import { DashboardTitlebarRight } from "@/components/shell/DashboardTitlebarRight";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <AppShell>
        <div
          className="h-full w-full flex items-center justify-center"
          style={{ color: "var(--fg-3)", fontSize: 13 }}
        >
          Loading…
        </div>
      </AppShell>
    );
  }

  return (
    <>
      <AppShell
        titlebarRight={<DashboardTitlebarRight />}
        activity={
          <ActivityBar
            items={DASHBOARD_PRIMARY}
            footer={DASHBOARD_FOOTER}
            dividerAfter={5}
          />
        }
        status={<StatusBar />}
      >
        <main className="h-full overflow-y-auto px-8 py-6">{children}</main>
      </AppShell>
      <Toaster theme="dark" richColors position="top-right" />
    </>
  );
}
