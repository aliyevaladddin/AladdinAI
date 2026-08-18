"use client";

/**
 * Training tab in Settings — Self-Forging golden set and harness.
 * Reuses the ForgingPage component but renders it inline.
 */
import dynamic from "next/dynamic";

const ForgingPage = dynamic(
  () => import("@/app/(dashboard)/dashboard/forging/page"),
  { ssr: false },
);

export function TrainingSettings() {
  return <ForgingPage />;
}
