// NOTICE: This file is protected under RCF-PL
"use client";

import { Check, Loader2, AlertTriangle } from "lucide-react";
import type { InstallStep } from "./types";

// [RCF:PROTECTED]
interface Props {
  steps: InstallStep[];
}

/**
 * Vertical stepper shown inside an installing-card. Premium detail:
 * the connector line between dots is gradient-filled up to the active
 * step. No bounce; durations 200ms cubic-bezier(0.16, 1, 0.3, 1).
 */
// [RCF:PROTECTED]
export function InstallStepper({ steps }: Props) {
  return (
    <ol className="flex flex-col gap-2.5" role="list">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        return (
          <li key={step.key} className="flex gap-3 relative">
            {/* connector */}
            {!isLast && (
              <span
                aria-hidden
                className="absolute left-[9px] top-5 bottom-[-10px] w-px"
                style={{
                  background:
                    step.status === "done"
                      ? "var(--ok)"
                      : "var(--line-strong)",
                  opacity: step.status === "done" ? 0.55 : 0.45,
                  transition: "background 200ms cubic-bezier(0.16, 1, 0.3, 1)",
                }}
              />
            )}

            {/* dot */}
            <span
              aria-hidden
              className="relative z-10 inline-flex items-center justify-center shrink-0"
              style={{
                width: 18,
                height: 18,
                borderRadius: 999,
                background:
                  step.status === "done"
                    ? "var(--ok-soft)"
                    : step.status === "running"
                      ? "var(--violet-soft)"
                      : step.status === "error"
                        ? "var(--err-soft)"
                        : "var(--bg-3)",
                border: `1px solid ${
                  step.status === "done"
                    ? "color-mix(in oklab, var(--ok) 45%, transparent)"
                    : step.status === "running"
                      ? "var(--violet-line)"
                      : step.status === "error"
                        ? "color-mix(in oklab, var(--err) 45%, transparent)"
                        : "var(--line)"
                }`,
                color:
                  step.status === "done"
                    ? "var(--ok)"
                    : step.status === "running"
                      ? "var(--violet)"
                      : step.status === "error"
                        ? "var(--err)"
                        : "var(--fg-4)",
                transition: "all 200ms cubic-bezier(0.16, 1, 0.3, 1)",
              }}
            >
              {step.status === "done" && <Check size={10} strokeWidth={3} />}
              {step.status === "running" && (
                <Loader2 size={10} className="motion-safe:animate-spin" strokeWidth={2.5} />
              )}
              {step.status === "error" && <AlertTriangle size={10} strokeWidth={2.5} />}
            </span>

            {/* label */}
            <div className="flex flex-col gap-0.5 min-w-0 flex-1 pt-[1px]">
              <span
                className="text-[12.5px] leading-tight font-medium"
                style={{
                  color:
                    step.status === "running"
                      ? "var(--fg)"
                      : step.status === "done"
                        ? "var(--fg-2)"
                        : step.status === "error"
                          ? "var(--err)"
                          : "var(--fg-3)",
                }}
              >
                {step.label}
              </span>
              {step.detail && (
                <span
                  className="text-[11px] leading-tight truncate"
                  style={{ color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}
                  title={step.detail}
                >
                  {step.detail}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
