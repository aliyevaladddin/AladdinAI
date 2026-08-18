"use client";

/**
 * Observability tab in Settings — shows the global agent traces view.
 * Reuses the TracesPage component but renders it inline (no page-level layout).
 */
import dynamic from "next/dynamic";

const TracesPage = dynamic(
  () => import("@/app/(dashboard)/dashboard/traces/page"),
  { ssr: false },
);

export function ObservabilitySettings() {
  return <TracesPage />;
}
