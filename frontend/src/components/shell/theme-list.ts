/**
 * Canonical theme catalog — single source of truth for the 12 themes.
 * Each entry includes the swatch pair so the ThemePicker and Lamp glow
 * stay in sync without duplication.
 */

export type ThemeId =
  | "violet-amber"
  | "indigo-saffron"
  | "plum-champagne"
  | "sapphire-copper"
  | "titanium-copper"
  | "gunmetal-amber"
  | "onyx-gold"
  | "twilight-cyan"
  | "sepia-coral"
  | "mist-sapphire"
  | "ivory-indigo"
  | "linen-sand";

export type ThemeFamily = "dark-mystic" | "dark-metal" | "dim" | "light";

export interface ThemeDef {
  id: ThemeId;
  name: string;
  sub: string;
  family: ThemeFamily;
  primary: string;
  accent: string;
}

export const THEMES: ThemeDef[] = [
  // Dark · mystic
  { id: "violet-amber",   name: "Violet × Amber",         sub: "Mystic genie · default", family: "dark-mystic", primary: "#8b5cf6", accent: "#f5b544" },
  { id: "indigo-saffron", name: "Indigo × Saffron",       sub: "Persian regal",          family: "dark-mystic", primary: "#6366f1", accent: "#f59e0b" },
  { id: "plum-champagne", name: "Plum × Champagne",       sub: "Sotheby's luxury",       family: "dark-mystic", primary: "#a855f7", accent: "#e7c989" },
  { id: "sapphire-copper",name: "Sapphire × Copper",      sub: "Premium industrial",     family: "dark-mystic", primary: "#3b82f6", accent: "#e2723a" },

  // Dark · metal
  { id: "titanium-copper",name: "Titanium × Copper",      sub: "Desert titanium",        family: "dark-metal",  primary: "#a1a1aa", accent: "#ea580c" },
  { id: "gunmetal-amber", name: "Gunmetal × Amber",       sub: "Machine amber",          family: "dark-metal",  primary: "#94a3b8", accent: "#f59e0b" },
  { id: "onyx-gold",      name: "Onyx × Molten Gold",     sub: "Forge of a genie",       family: "dark-metal",  primary: "#78716c", accent: "#d4a017" },

  // Dim · between
  { id: "twilight-cyan",  name: "Twilight × Cyan",        sub: "Classic dim",            family: "dim",         primary: "#38bdf8", accent: "#a78bfa" },
  { id: "sepia-coral",    name: "Sepia Dusk × Coral",     sub: "Warm evening",           family: "dim",         primary: "#fca5a5", accent: "#fcd34d" },
  { id: "mist-sapphire",  name: "Morning Mist × Sapphire",sub: "Overcast · soft light",  family: "dim",         primary: "#2563eb", accent: "#ea580c" },

  // Light · daylight
  { id: "ivory-indigo",   name: "Ivory × Indigo",         sub: "Daylight studio",        family: "light",       primary: "#4f46e5", accent: "#c2410c" },
  { id: "linen-sand",     name: "Linen × Sand",           sub: "Calm document",          family: "light",       primary: "#7c2d12", accent: "#a16207" },
];

export const THEME_BY_ID: Record<ThemeId, ThemeDef> = Object.fromEntries(
  THEMES.map((t) => [t.id, t])
) as Record<ThemeId, ThemeDef>;

export const DEFAULT_THEME: ThemeId = "violet-amber";
export const THEME_STORAGE_KEY = "aladdin-theme";

export const THEME_FAMILIES: { label: string; family: ThemeFamily }[] = [
  { label: "Dark · mystic",   family: "dark-mystic" },
  { label: "Dark · metal",    family: "dark-metal" },
  { label: "Dim · between",   family: "dim" },
  { label: "Light · daylight",family: "light" },
];

export function isValidTheme(value: string | null | undefined): value is ThemeId {
  return !!value && value in THEME_BY_ID;
}
