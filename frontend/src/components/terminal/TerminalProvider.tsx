"use client";

/**
 * Plugin-slot terminal session model.
 *
 * The drawer is no longer an xterm host; it embeds an iframe whose `src` is
 * issued by the backend (`POST /api/terminal/session`). The backend picks the
 * user's active terminal provider, mints a single-use HMAC token, and returns
 * a Traefik-routable URL.
 *
 * State surface intentionally kept small — one session at a time in the MVP,
 * because the backend exposes one active provider per user. Multi-pane comes
 * later (it would need a provider × instance graph).
 *
 * `newSSH(vm)` is kept as a *compat shim* for VmsSettings — it just opens the
 * drawer (provider chooses the shell; VM-pick happens server-side, or in a
 * future SSH adapter). We don't break the existing button.
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
import { API_URL } from "@/lib/api";

/** Kept for VmsSettings compatibility — fields no longer used at the iframe layer. */
export interface VM {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
}

export type SessionStatus =
  | "idle"          // no session yet
  | "loading"      // /session call in flight
  | "ready"        // iframe URL issued
  | "no-provider"  // 503: user has no active provider — render empty state
  | "error";       // any other failure — show retry

export interface TerminalSlot {
  /** Stable id for React key purposes. Cycles on each (re)load. */
  id: string;
  url: string | null;
  providerType: string | null;
  expiresAt: number | null;       // unix seconds
  status: SessionStatus;
  error: string | null;
}

interface TerminalCtx {
  open: boolean;
  height: number;
  slot: TerminalSlot;
  setHeight: (h: number) => void;
  toggle: () => void;
  show: () => void;
  hide: () => void;
  /** Mint a fresh session URL from the backend. */
  refresh: () => Promise<void>;
  /** Compat shim — opens the drawer; VM is informational. */
  newSSH: (vm: VM) => void;
  /** Compat shim — opens the drawer (alias of show()). */
  newLocal: () => void;
}

const TerminalContext = createContext<TerminalCtx | null>(null);

const MIN_HEIGHT = 160;
const MAX_HEIGHT_RATIO = 0.8;
const DEFAULT_HEIGHT = 320;
const HEIGHT_KEY = "aladdin-terminal-height";

let slotCounter = 0;
const nextSlotId = () => `slot-${++slotCounter}-${Date.now()}`;

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

/** Reads the current access token without depending on `api.get` (we hit the
 *  session endpoint manually because we want fine-grained status codes). */
function authHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const tok = window.localStorage.getItem("access_token");
  return tok ? { Authorization: `Bearer ${tok}` } : {};
}

export function TerminalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [height, setHeightState] = useState<number>(readInitialHeight);
  const [slot, setSlot] = useState<TerminalSlot>(EMPTY_SLOT);

  // Guard against StrictMode double-invocation: any one render must not fire
  // two parallel /session requests.
  const fetchingRef = useRef(false);

  const setHeight = useCallback((h: number) => {
    const max = typeof window !== "undefined"
      ? Math.floor(window.innerHeight * MAX_HEIGHT_RATIO)
      : 800;
    const clamped = Math.max(MIN_HEIGHT, Math.min(max, h));
    setHeightState(clamped);
    try { window.localStorage.setItem(HEIGHT_KEY, String(clamped)); } catch { /* ignore */ }
  }, []);

  const toggle = useCallback(() => setOpen((v) => !v), []);
  const show = useCallback(() => setOpen(true), []);
  const hide = useCallback(() => setOpen(false), []);

  const refresh = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    setSlot((cur) => ({ ...cur, status: "loading", error: null }));
    try {
      const res = await fetch(`${API_URL}/terminal/session`, {
        method: "POST",
        headers: {
          ...authHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });
      if (res.status === 503) {
        // No provider installed — drawer renders the empty state with a link
        // to the marketplace. This is *not* an error from the user's POV.
        setSlot({
          id: nextSlotId(),
          url: null,
          providerType: null,
          expiresAt: null,
          status: "no-provider",
          error: null,
        });
        return;
      }
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        setSlot((cur) => ({
          ...cur,
          url: null,
          providerType: null,
          expiresAt: null,
          status: "error",
          error: text || `HTTP ${res.status}`,
        }));
        return;
      }
      const data = await res.json() as {
        url: string;
        expires_at: string;
        provider_type: string;
      };
      setSlot({
        id: nextSlotId(),
        url: data.url,
        providerType: data.provider_type,
        expiresAt: data.expires_at ? Math.floor(new Date(data.expires_at).getTime() / 1000) : null,
        status: "ready",
        error: null,
      });
    } catch (e) {
      // Network-level failure (CORS, backend down, DNS) — surface a hint that
      // points at the backend, not a vague "TypeError: Failed to fetch".
      const msg = e instanceof Error ? e.message : String(e);
      setSlot((cur) => ({
        ...cur,
        url: null,
        providerType: null,
        expiresAt: null,
        status: "error",
        error: `${msg} — is the backend running on ${API_URL}?`,
      }));
    } finally {
      fetchingRef.current = false;
    }
  }, []);

  // Mint a session the first time the drawer opens, and re-mint on each open
  // if the previous token has expired. Tokens are 5min single-use, but the
  // iframe consumes the token on its first load — re-opens after that just
  // navigate inside the iframe.
  // Auto-mint on first open of an idle slot. We deliberately don't auto-retry
  // on `error` or `no-provider` — those are terminal states the user resolves
  // via the explicit "Try again" / "Open marketplace" CTAs in the drawer.
  // Auto-retrying on error would loop forever when the backend is down.
  useEffect(() => {
    if (!open) return;
    if (slot.status === "idle") void refresh();
  }, [open, slot.status, refresh]);

  // Compat shims — VmsSettings & friends still call these.
  const newLocal = useCallback(() => { setOpen(true); }, []);
  const newSSH = useCallback((_vm: VM) => { setOpen(true); }, []);

  // Global hotkey: Ctrl+`  (Cmd+` on macOS) — toggle the drawer.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const value = useMemo<TerminalCtx>(
    () => ({
      open,
      height,
      slot,
      setHeight,
      toggle,
      show,
      hide,
      refresh,
      newLocal,
      newSSH,
    }),
    [open, height, slot, setHeight, toggle, show, hide, refresh, newLocal, newSSH],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminal(): TerminalCtx {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminal must be used inside <TerminalProvider>");
  return ctx;
}
