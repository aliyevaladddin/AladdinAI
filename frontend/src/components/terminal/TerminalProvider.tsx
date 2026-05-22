"use client";

/**
 * Terminal sessions live for the lifetime of the dashboard. The drawer can be
 * collapsed without killing them — buffers, websocket, and xterm instance all
 * survive until the user explicitly closes a tab.
 *
 * `TerminalSession` (state) holds *only* serialisable, render-relevant data.
 * Imperative resources (xterm instance, websocket) live in `instancesRef` —
 * a mutable map keyed by session id, accessed via `useTerminalInstances`.
 * That keeps React 19's immutability rules happy and avoids re-renders on
 * every keystroke.
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
  type MutableRefObject,
} from "react";
import { api } from "@/lib/api";

export interface VM {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
}

export type SessionStatus = "idle" | "connecting" | "connected" | "closed";

/** Render-state view of a session. */
export interface TerminalSession {
  id: string;
  title: string;
  vm: VM | null;
  status: SessionStatus;
}

/** Imperative side-band — xterm instance, fit addon, websocket. */
export interface TerminalInstance {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  term: any | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fitAddon: any | null;
  ws: WebSocket | null;
  /** Local-shell input buffer (between Enters). */
  localBuf: string;
}

interface TerminalCtx {
  open: boolean;
  height: number;
  sessions: TerminalSession[];
  activeId: string | null;
  setHeight: (h: number) => void;
  toggle: () => void;
  show: () => void;
  hide: () => void;
  setActive: (id: string) => void;
  newLocal: () => string;
  newSSH: (vm: VM) => string;
  closeSession: (id: string) => void;
  setStatus: (id: string, status: SessionStatus) => void;
  listVMs: () => Promise<VM[]>;
  instancesRef: MutableRefObject<Map<string, TerminalInstance>>;
}

const TerminalContext = createContext<TerminalCtx | null>(null);

const MIN_HEIGHT = 160;
const MAX_HEIGHT_RATIO = 0.8;
const DEFAULT_HEIGHT = 320;
const HEIGHT_KEY = "aladdin-terminal-height";

let sidCounter = 0;
const nextId = () => `term-${++sidCounter}-${Date.now()}`;

function readInitialHeight(): number {
  if (typeof window === "undefined") return DEFAULT_HEIGHT;
  try {
    const raw = window.localStorage.getItem(HEIGHT_KEY);
    const n = raw ? parseInt(raw, 10) : NaN;
    if (Number.isFinite(n) && n >= MIN_HEIGHT) return n;
  } catch { /* ignore */ }
  return DEFAULT_HEIGHT;
}

export function TerminalProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [height, setHeightState] = useState<number>(readInitialHeight);
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const instancesRef = useRef<Map<string, TerminalInstance>>(new Map());

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

  const setActive = useCallback((id: string) => setActiveId(id), []);

  const ensureInstance = useCallback((id: string) => {
    if (!instancesRef.current.has(id)) {
      instancesRef.current.set(id, { term: null, fitAddon: null, ws: null, localBuf: "" });
    }
    return instancesRef.current.get(id)!;
  }, []);

  const newLocal = useCallback(() => {
    const id = nextId();
    ensureInstance(id);
    setSessions((cur) => [...cur, { id, title: "local", vm: null, status: "idle" }]);
    setActiveId(id);
    setOpen(true);
    return id;
  }, [ensureInstance]);

  const newSSH = useCallback((vm: VM) => {
    const id = nextId();
    ensureInstance(id);
    setSessions((cur) => [...cur, { id, title: vm.name, vm, status: "idle" }]);
    setActiveId(id);
    setOpen(true);
    return id;
  }, [ensureInstance]);

  const setStatus = useCallback((id: string, status: SessionStatus) => {
    setSessions((cur) => cur.map((s) => (s.id === id ? { ...s, status } : s)));
  }, []);

  const closeSession = useCallback((id: string) => {
    const inst = instancesRef.current.get(id);
    if (inst) {
      try { inst.ws?.close(); } catch { /* ignore */ }
      try { inst.term?.dispose(); } catch { /* ignore */ }
      instancesRef.current.delete(id);
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

  const listVMs = useCallback(async () => {
    try {
      return await api.get<VM[]>("/vms");
    } catch {
      return [];
    }
  }, []);

  // Global hotkey: Ctrl+`  (Cmd+` on macOS) — toggle, auto-spawn a local
  // session if none exists yet so the drawer has something to show.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        setSessions((curSessions) => {
          if (curSessions.length === 0) {
            const id = nextId();
            ensureInstance(id);
            setActiveId(id);
            setOpen(true);
            return [...curSessions, { id, title: "local", vm: null, status: "idle" }];
          }
          setOpen((v) => !v);
          return curSessions;
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ensureInstance]);

  // Tear down everything on provider unmount (logout / nav away).
  useEffect(() => {
    const map = instancesRef.current;
    return () => {
      for (const inst of map.values()) {
        try { inst.ws?.close(); } catch { /* ignore */ }
        try { inst.term?.dispose(); } catch { /* ignore */ }
      }
      map.clear();
    };
  }, []);

  const value = useMemo<TerminalCtx>(
    () => ({
      open,
      height,
      sessions,
      activeId,
      setHeight,
      toggle,
      show,
      hide,
      setActive,
      newLocal,
      newSSH,
      closeSession,
      setStatus,
      listVMs,
      instancesRef,
    }),
    [open, height, sessions, activeId, setHeight, toggle, show, hide, setActive, newLocal, newSSH, closeSession, setStatus, listVMs],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminal(): TerminalCtx {
  const ctx = useContext(TerminalContext);
  if (!ctx) throw new Error("useTerminal must be used inside <TerminalProvider>");
  return ctx;
}
