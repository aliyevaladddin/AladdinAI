// NOTICE: This file is protected under RCF-PL
"use client";

/**
 * Plugin-slot terminal provider.
 *
 * Each session is just a URL slot — we don't own the terminal anymore. The
 * pluggable backend provider (ttyd / Wetty / Guacamole / custom) sits on the
 * other side of an iframe and is responsible for its own PTY, rendering, and
 * input routing. This file only tracks render-state.
 *
 * Compared to the old xterm-owning provider:
 *   removed: `TerminalInstance`, `instancesRef`, xterm/ws lifecycle, fit logic.
 *   added:   `status: loading|ready|error`, `url`, `expiresAt`, `providerType`,
 *            `openSession({vm})`, `reconnect(id)`.
 *
 * The transport contract with the backend (see TODOs at the bottom):
 *   POST /api/terminal/session  { vm_id? }  -> 200 { url, expires_at, provider_type, provider_session_id? }
 *                                              503 if no terminal provider installed
 *   DELETE /api/terminal/session/{provider_session_id}                 (best-effort)
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, API_URL } from "@/lib/api";
import { quickSetupDefault } from "@/app/(dashboard)/dashboard/settings/terminal/api";

/** Kept for VmsSettings compatibility — fields no longer used at the iframe layer. */

export interface VM {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
}

/** Set of provider implementations we know how to label in the UI. */

export type ProviderType = "ttyd" | "wetty" | "guacamole" | "custom" | "none";


export type SessionStatus = "loading" | "ready" | "error";

/** Render-state view of a session. No imperative resources. */

export interface TerminalSession {
  id: string;
  title: string;
  vm: VM | null;
  status: SessionStatus;
  /** URL pointed at the terminal provider, or "about:blank" while loading / when no provider installed. */
  url: string;
  /** Optional ISO date — used by the drawer to surface a "Reconnect" button when the token expires. */
  expiresAt: string | null;
  /** Provider-side session id for cleanup on close. */
  providerSessionId: string | null;
  providerType: ProviderType;
  /** Human-readable error surfaced from the bootstrap call or the iframe `onerror`. */
  errorMessage: string | null;
}

/** Shape returned by `POST /api/terminal/session`. Mirrored on the backend when the endpoint lands. */

export interface TerminalSessionResponse {
  url: string;
  expires_at: string | null;
  provider_type: ProviderType;
  provider_session_id?: string | null;
}


export interface TerminalSlot {
  id: string;
  url: string | null;
  providerType: ProviderType | null;
  expiresAt: string | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
}

import type { TerminalThemePreset } from "./NativeTerminal";

interface TerminalCtx {
  open: boolean;
  height: number;
  sessions: TerminalSession[];
  activeId: string | null;
  slot: TerminalSlot;
  themePreset: TerminalThemePreset;
  setThemePreset: (preset: TerminalThemePreset) => void;
  setHeight: (h: number) => void;
  toggle: () => void;
  show: () => void;
  hide: () => void;
  setActive: (id: string) => void;
  /**
   * Open a new session. `vm = null` is a host-local shell (uses whichever
   * provider is configured as default on the backend); a VM yields an SSH
   * session via the same provider.
   */
  openSession: (vm: VM | null) => Promise<string>;
  /** Legacy alias kept so `VmsSettings.newSSH(vm)` keeps compiling. */
  newSSH: (vm: VM) => Promise<string>;
  /** Legacy alias kept for the [+] menu and Ctrl+` hotkey. */
  newLocal: () => Promise<string>;
  closeSession: (id: string) => void;
  /** Re-bootstrap the session URL after token expiry or iframe error. */
  reconnect: (id: string) => Promise<void>;
  /** Internal — used by the drawer when the iframe finally fires `onload`. */
  markReady: (id: string) => void;
  /** Internal — surfaced as the "error" status, drives the Reconnect button. */
  markError: (id: string, message: string) => void;
  listVMs: () => Promise<VM[]>;
}

const TerminalContext = createContext<TerminalCtx | null>(null);

const MIN_HEIGHT = 160;
const MAX_HEIGHT_RATIO = 0.8;
const DEFAULT_HEIGHT = 320;
const HEIGHT_KEY = "aladdin-terminal-height";
const THEME_KEY = "aladdin-terminal-theme";

let slotCounter = 0;

const nextSlotId = () => `slot-${++slotCounter}-${Date.now()}`;
const nextId = nextSlotId;

const EMPTY_SLOT: TerminalSlot = {
  id: "empty",
  url: null,
  providerType: null,
  expiresAt: null,
  status: "idle",
  error: null,
};


function readInitialHeight(): number {
  if (typeof window === "undefined") return DEFAULT_HEIGHT;
  try {
    const raw = window.localStorage.getItem(HEIGHT_KEY);
    const n = raw ? parseInt(raw, 10) : NaN;
    if (Number.isFinite(n) && n >= MIN_HEIGHT) return n;
  } catch { /* ignore */ }
  return DEFAULT_HEIGHT;
}

function readInitialTheme(): TerminalThemePreset {
  if (typeof window === "undefined") return "aladdin";
  try {
    const raw = window.localStorage.getItem(THEME_KEY) as TerminalThemePreset;
    if (raw && ["aladdin", "dracula", "monokai", "cyberpunk", "jetbrains", "matrix"].includes(raw)) return raw;
  } catch { /* ignore */ }
  return "aladdin";
}

async function bootstrapSession(vm: VM | null): Promise<TerminalSessionResponse> {
  const body = vm ? { vm_id: vm.id } : {};
  try {
    const res = await fetch(`${API_URL}/terminal/session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(typeof window !== "undefined" && localStorage.getItem("access_token")
          ? { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
          : {}),
      },
      body: JSON.stringify(body),
    });
    if (res.status === 404 || res.status === 503) {
      return { url: "about:blank", expires_at: null, provider_type: "none", provider_session_id: null };
    }
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Bootstrap failed (${res.status}): ${text || "unknown error"}`);
    }
    return (await res.json()) as TerminalSessionResponse;
  } catch (e) {
    if (e instanceof Error && e.message.startsWith("Bootstrap failed")) throw e;
    return { url: "about:blank", expires_at: null, provider_type: "none", provider_session_id: null };
  }
}


export function TerminalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [height, setHeightState] = useState<number>(readInitialHeight);
  const [themePreset, setThemePresetState] = useState<TerminalThemePreset>(readInitialTheme);
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const sessionsRef = useRef<TerminalSession[]>([]);
  useEffect(() => { sessionsRef.current = sessions; }, [sessions]);

  const setThemePreset = useCallback((preset: TerminalThemePreset) => {
    setThemePresetState(preset);
    try { window.localStorage.setItem(THEME_KEY, preset); } catch { /* ignore */ }
  }, []);

  const setHeight = useCallback((h: number) => {
    const max = typeof window !== "undefined"
      ? Math.floor(window.innerHeight * MAX_HEIGHT_RATIO)
      : 800;
    const clamped = Math.max(MIN_HEIGHT, Math.min(max, h));
    setHeightState(clamped);
    try { window.localStorage.setItem(HEIGHT_KEY, String(clamped)); } catch { /* ignore */ }
  }, []);

  const patchSession = useCallback((id: string, patch: Partial<TerminalSession>) => {
    setSessions((cur) => cur.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }, []);

  const markReady = useCallback((id: string) => {
    const cur = sessionsRef.current.find((s) => s.id === id);
    if (cur && cur.status === "loading") patchSession(id, { status: "ready", errorMessage: null });
  }, [patchSession]);

  const markError = useCallback((id: string, message: string) => {
    patchSession(id, { status: "error", errorMessage: message });
  }, [patchSession]);

  const openSession = useCallback(async (vm: VM | null): Promise<string> => {
    const id = nextId();
    const initial: TerminalSession = {
      id,
      title: vm ? vm.name : "local shell",
      vm,
      status: "ready",
      url: "native",
      expiresAt: null,
      providerSessionId: null,
      providerType: "custom",
      errorMessage: null,
    };
    setSessions((cur) => [...cur, initial]);
    setActiveId(id);
    setOpen(true);
    return id;
  }, []);

  const toggle = useCallback(() => {
    setOpen((v) => {
      const next = !v;
      if (next && sessionsRef.current.length === 0) {
        void openSession(null);
      }
      return next;
    });
  }, [openSession]);

  const show = useCallback(() => {
    setOpen(true);
    if (sessionsRef.current.length === 0) {
      void openSession(null);
    }
  }, [openSession]);

  const hide = useCallback(() => setOpen(false), []);
  const setActive = useCallback((id: string) => setActiveId(id), []);

  const newSSH = useCallback((vm: VM) => openSession(vm), [openSession]);
  const newLocal = useCallback(() => openSession(null), [openSession]);

  const closeSession = useCallback((id: string) => {
    const target = sessionsRef.current.find((s) => s.id === id);
    if (target?.providerSessionId) {
      api.delete(`/terminal/session/${target.providerSessionId}`).catch(() => { /* ignore */ });
    }
    setSessions((cur) => {
      const remaining = cur.filter((x) => x.id !== id);
      setActiveId((prev) => {
        if (prev !== id) return prev;
        const next = remaining[remaining.length - 1];
        return next ? next.id : null;
      });
      return remaining;
    });
  }, []);

  const reconnect = useCallback(async (id: string) => {
    const target = sessionsRef.current.find((s) => s.id === id);
    if (!target) return;
    patchSession(id, { status: "loading", url: "about:blank", errorMessage: null });
    try {
      let resp: TerminalSessionResponse;
      try {
        resp = await bootstrapSession(target.vm);
      } catch (e) {
        if (e instanceof Error && /\b409\b/.test(e.message)) {
          await quickSetupDefault("ttyd");
          resp = await bootstrapSession(target.vm);
        } else {
          throw e;
        }
      }
      patchSession(id, {
        url: resp.url,
        expiresAt: resp.expires_at,
        providerType: resp.provider_type,
        providerSessionId: resp.provider_session_id ?? null,
        status: resp.provider_type === "none" ? "ready" : "loading",
      });
    } catch (e) {
      markError(id, e instanceof Error ? e.message : "Failed to reconnect");
    }
  }, [patchSession, markError]);

  const listVMs = useCallback(async () => {
    try {
      return await api.get<VM[]>("/vms");
    } catch {
      return [];
    }
  }, []);

  // Ctrl+` / Cmd+` — toggle drawer; spawn a session if none exist.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        if (sessionsRef.current.length === 0) {
          void openSession(null);
        } else {
          setOpen((v) => !v);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openSession]);

  useEffect(() => {
    return () => {
      for (const s of sessionsRef.current) {
        if (s.providerSessionId) {
          api.delete(`/terminal/session/${s.providerSessionId}`).catch(() => { /* ignore */ });
        }
      }
    };
  }, []);

  const activeSession = sessions.find((s) => s.id === activeId);
  const slot: TerminalSlot = activeSession
    ? {
      id: activeSession.id,
      url: activeSession.url,
      providerType: activeSession.providerType,
      expiresAt: activeSession.expiresAt,
      status: activeSession.status,
      error: activeSession.errorMessage,
    }
    : EMPTY_SLOT;

  const value = useMemo<TerminalCtx>(
    () => ({
      open,
      height,
      sessions,
      activeId,
      slot,
      themePreset,
      setThemePreset,
      setHeight,
      toggle,
      show,
      hide,
      setActive,
      openSession,
      newSSH,
      newLocal,
      closeSession,
      reconnect,
      markReady,
      markError,
      listVMs,
    }),
    [
      open, height, sessions, activeId, slot, themePreset,
      setThemePreset, setHeight, toggle, show, hide, setActive,
      openSession, newSSH, newLocal, closeSession, reconnect,
      markReady, markError, listVMs,
    ],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}


export function useTerminal(): TerminalCtx {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminal must be used inside <TerminalProvider>");
  return ctx;
}
