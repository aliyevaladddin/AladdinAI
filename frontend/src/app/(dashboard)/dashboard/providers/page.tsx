// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Legacy /dashboard/providers route.
 * Redirects to /dashboard/settings?tab=providers (2026-06-01).
 */
export default function ProvidersRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/dashboard/settings?tab=providers");
  }, [router]);

  return (
    <div className="h-full flex items-center justify-center">
      <div style={{ color: "var(--fg-3)", fontSize: 13 }}>
        Redirecting to Settings…
      </div>
    </div>
  );
}
