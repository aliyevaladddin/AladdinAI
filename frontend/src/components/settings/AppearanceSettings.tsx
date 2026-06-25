// NOTICE: This file is protected under RCF-PL
"use client";

import { useTheme } from "@/components/shell/ThemeProvider";
import {
  THEME_FAMILIES,
  THEMES,
  THEME_BY_ID,
  type ThemeId,
} from "@/components/shell/theme-list";

/**
 * Appearance settings panel — theme selection with premium visual presentation.
 * Migrated from the titlebar ThemePicker to give themes proper breathing room.
 */
// [RCF:PROTECTED]
export function AppearanceSettings() {
  const { theme, setTheme } = useTheme();
  const current = THEME_BY_ID[theme];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-[var(--fg)]">Appearance</h2>
        <p className="text-xs text-[var(--fg-3)] mt-1">
          Choose your visual theme — 12 curated palettes from mystic to daylight
        </p>
      </div>

      {/* Current theme display */}
      <div
        style={{
          padding: "16px 20px",
          background: "var(--bg-2)",
          border: "1px solid var(--line-strong)",
          borderRadius: "var(--r-lg)",
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "center",
          }}
        >
          <span
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: current.primary,
              border: "2px solid var(--bg-0)",
              boxShadow: `0 0 0 1px ${current.primary}40`,
            }}
          />
          <span
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: current.accent,
              border: "2px solid var(--bg-0)",
              boxShadow: `0 0 0 1px ${current.accent}40`,
              marginLeft: -12,
            }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--fg)" }}>
            {current.name}
          </div>
          <div style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
            {current.sub}
          </div>
        </div>
        <div
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "var(--violet)",
            padding: "4px 10px",
            background: "var(--violet-soft)",
            border: "1px solid var(--violet-line)",
            borderRadius: "var(--r-sm)",
          }}
        >
          Active
        </div>
      </div>

      {/* Theme families */}
      {THEME_FAMILIES.map(({ label, family }) => {
        const themes = THEMES.filter((t) => t.family === family);
        if (themes.length === 0) return null;

        return (
          <div key={family}>
            <h3
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--fg-3)",
                marginBottom: 12,
              }}
            >
              {label}
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                gap: 12,
              }}
            >
              {themes.map((t) => {
                const isActive = theme === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTheme(t.id as ThemeId)}
                    style={{
                      position: "relative",
                      padding: "14px 16px",
                      background: isActive ? "var(--bg-3)" : "var(--bg-2)",
                      border: `1px solid ${isActive ? "var(--violet-line)" : "var(--line)"}`,
                      borderRadius: "var(--r-md)",
                      cursor: "pointer",
                      transition: "all 150ms cubic-bezier(0.16, 1, 0.3, 1)",
                      textAlign: "left",
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      boxShadow: isActive ? "0 0 0 3px var(--violet-soft)" : "none",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "var(--bg-3)";
                        e.currentTarget.style.borderColor = "var(--line-strong)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "var(--bg-2)";
                        e.currentTarget.style.borderColor = "var(--line)";
                      }
                    }}
                  >
                    {/* Swatch pair */}
                    <div
                      style={{
                        display: "flex",
                        gap: 4,
                        alignItems: "center",
                        flexShrink: 0,
                      }}
                    >
                      <span
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: "50%",
                          background: t.primary,
                          border: "2px solid var(--bg-0)",
                          boxShadow: `0 0 0 1px ${t.primary}40`,
                        }}
                      />
                      <span
                        style={{
                          width: 24,
                          height: 24,
                          borderRadius: "50%",
                          background: t.accent,
                          border: "2px solid var(--bg-0)",
                          boxShadow: `0 0 0 1px ${t.accent}40`,
                          marginLeft: -8,
                        }}
                      />
                    </div>

                    {/* Text */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "var(--fg)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {t.name}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--fg-3)",
                          marginTop: 2,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {t.sub}
                      </div>
                    </div>

                    {/* Active indicator */}
                    {isActive && (
                      <div
                        style={{
                          width: 18,
                          height: 18,
                          borderRadius: "50%",
                          background: "var(--violet)",
                          color: "var(--bg-0)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: 11,
                          fontWeight: 700,
                          flexShrink: 0,
                        }}
                      >
                        ✓
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
