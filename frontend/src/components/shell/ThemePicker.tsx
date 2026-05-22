"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "./ThemeProvider";
import {
  THEME_FAMILIES,
  THEMES,
  THEME_BY_ID,
  type ThemeId,
} from "./theme-list";

export function ThemePicker() {
  const { theme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Theme is read from localStorage on the client, but SSR renders the default.
  // The swatch and label inevitably diverge between the two — they're marked
  // suppressHydrationWarning on the rendering nodes below so React tolerates
  // the deliberate post-hydration patch.

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = THEME_BY_ID[theme];

  return (
    <div ref={rootRef} className="theme-picker">
      <button
        type="button"
        className="theme-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Switch theme"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="dot-pair" aria-hidden="true" suppressHydrationWarning>
          <i style={{ background: current.primary }} suppressHydrationWarning />
          <i style={{ background: current.accent }} suppressHydrationWarning />
        </span>
        <span className="theme-trigger-name" suppressHydrationWarning>{current.name}</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="11" height="11" aria-hidden="true">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {open && (
        <div className="theme-menu" role="menu">
          {THEME_FAMILIES.map(({ label, family }) => {
            const themes = THEMES.filter((t) => t.family === family);
            if (themes.length === 0) return null;
            return (
              <div key={family}>
                <div className="theme-section">{label}</div>
                {themes.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    role="menuitemradio"
                    aria-checked={theme === t.id}
                    className={`theme-opt${theme === t.id ? " active" : ""}`}
                    onClick={() => {
                      setTheme(t.id as ThemeId);
                      setOpen(false);
                    }}
                  >
                    <span className="swatch-pair" aria-hidden="true">
                      <i style={{ background: t.primary }} />
                      <i style={{ background: t.accent }} />
                    </span>
                    <span className="theme-opt-text">
                      <span className="name">{t.name}</span>
                      <span className="sub">{t.sub}</span>
                    </span>
                    <span className="check" aria-hidden="true">✓</span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
