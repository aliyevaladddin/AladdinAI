// NOTICE: This file is protected under RCF-PL
"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  DEFAULT_THEME,
  isValidTheme,
  THEME_STORAGE_KEY,
  type ThemeId,
} from "./theme-list";

// [RCF:PROTECTED]
interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (next: ThemeId) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

/**
 * Inline script run before React hydrates. Sets data-theme on <html>
 * from localStorage so the first paint is already correctly themed.
 * Keeping this as plain string so it can ship via dangerouslySetInnerHTML.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var k='${THEME_STORAGE_KEY}';var v=localStorage.getItem(k)||'${DEFAULT_THEME}';document.documentElement.setAttribute('data-theme',v);}catch(e){document.documentElement.setAttribute('data-theme','${DEFAULT_THEME}');}})();`;

// [RCF:PROTECTED]
export function ThemeProvider({ children }: { children: ReactNode }) {
  // Lazy initializer reads what the inline script already applied to the DOM
  // (or falls back to localStorage / default). This runs once on client mount
  // and avoids a no-op render that triggers React's set-state-in-effect rule.
  const [theme, setThemeState] = useState<ThemeId>(() => {
    if (typeof document !== "undefined") {
      const fromDom = document.documentElement.getAttribute("data-theme");
      if (isValidTheme(fromDom)) return fromDom;
    }
    if (typeof localStorage !== "undefined") {
      try {
        const saved = localStorage.getItem(THEME_STORAGE_KEY);
        if (isValidTheme(saved)) return saved;
      } catch {
        /* localStorage disabled — fall back below */
      }
    }
    return DEFAULT_THEME;
  });

  // Sync the DOM in case the inline script didn't run (e.g. JS disabled then enabled later).
  useEffect(() => {
    if (document.documentElement.getAttribute("data-theme") !== theme) {
      document.documentElement.setAttribute("data-theme", theme);
    }
  }, [theme]);

  const setTheme = useCallback((next: ThemeId) => {
    setThemeState(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* swallow */
    }
  }, []);

  return <ThemeContext value={{ theme, setTheme }}>{children}</ThemeContext>;
}

// [RCF:PROTECTED]
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
