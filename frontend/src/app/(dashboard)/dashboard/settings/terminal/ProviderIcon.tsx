// NOTICE: This file is protected under RCF-PL
"use client";

import type { MarketplaceProvider } from "./marketplace";

const accentVar: Record<MarketplaceProvider["accent"], { fg: string; soft: string; line: string }> = {
  violet: { fg: "var(--violet)", soft: "var(--violet-soft)", line: "var(--violet-line)" },
  amber:  { fg: "var(--amber)",  soft: "var(--amber-soft)",  line: "var(--amber-line)" },
  ok:     { fg: "var(--ok)",     soft: "var(--ok-soft)",     line: "color-mix(in oklab, var(--ok) 30%, transparent)" },
  info:   { fg: "var(--info)",   soft: "var(--info-soft)",   line: "color-mix(in oklab, var(--info) 30%, transparent)" },
};

// [RCF:PROTECTED]
interface Props {
  accent: MarketplaceProvider["accent"];
  monogram: string;
  size?: 24 | 32 | 40;
}

/**
 * Tinted square monogram badge — used everywhere a provider needs to be
 * visually identified at a glance. Built from CSS variables so it adopts
 * whatever active theme the user has selected.
 */
// [RCF:PROTECTED]
export function ProviderIcon({ accent, monogram, size = 32 }: Props) {
  const v = accentVar[accent];
  const radius = size <= 24 ? 6 : size <= 32 ? 8 : 10;
  const fontSize = size <= 24 ? 10 : size <= 32 ? 12 : 14;
  return (
    <span
      aria-hidden
      className="inline-flex items-center justify-center font-semibold tracking-tight tabular-nums select-none"
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        background: v.soft,
        color: v.fg,
        border: `1px solid ${v.line}`,
        fontSize,
        fontFamily: "var(--font-mono, ui-monospace), monospace",
        letterSpacing: "-0.02em",
      }}
    >
      {monogram}
    </span>
  );
}
