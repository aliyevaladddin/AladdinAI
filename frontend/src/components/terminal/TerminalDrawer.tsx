"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import {
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  Terminal as TerminalIcon,
  Shield,
  Circle,
  GripHorizontal,
} from "lucide-react";
import {
  useTerminal,
  type TerminalSession,
  type SessionStatus,
  type TerminalInstance,
  type VM,
} from "./TerminalProvider";
import "xterm/css/xterm.css";

/** Drawer sits over `.shell__body`, snapped to its bottom edge. */
export function TerminalDrawer() {
  const t = useTerminal();
  if (!t.open || t.sessions.length === 0) {
    return null; // hidden by default until user opens it
  }
  return <DrawerInner />;
}

function DrawerInner() {
  const t = useTerminal();
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);
  const plusBtnRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const [vms, setVms] = useState<VM[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerPos, setPickerPos] = useState<{ left: number; bottom: number } | null>(null);

  // VM list for the [+] picker.
  useEffect(() => {
    let active = true;
    t.listVMs().then((list) => {
      if (active) setVms(list);
    });
    return () => { active = false; };
  }, [t]);

  // Click-outside / Escape to close the [+] picker.
  useEffect(() => {
    if (!pickerOpen) return;
    const onDown = (e: MouseEvent) => {
      const tgt = e.target as Node;
      if (popupRef.current?.contains(tgt)) return;
      if (plusBtnRef.current?.contains(tgt)) return;
      setPickerOpen(false);
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setPickerOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [pickerOpen]);

  const togglePicker = () => {
    if (pickerOpen) {
      setPickerOpen(false);
      return;
    }
    const rect = plusBtnRef.current?.getBoundingClientRect();
    console.log("[Terminal] +menu click; btn rect =", rect);
    if (rect) {
      // Popup pinned above the button — drawer is at the bottom of the viewport,
      // so dropping up keeps it on-screen and out of the terminal body.
      setPickerPos({
        left: Math.max(8, rect.left),
        bottom: Math.max(8, window.innerHeight - rect.top + 6),
      });
    } else {
      // Fallback: pin to bottom-left if we can't measure.
      setPickerPos({ left: 16, bottom: 60 });
    }
    setPickerOpen(true);
  };

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragRef.current = { startY: e.clientY, startH: t.height };
    document.body.style.userSelect = "none";
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dy = dragRef.current.startY - ev.clientY;
      t.setHeight(dragRef.current.startH + dy);
    };
    const onUp = () => {
      dragRef.current = null;
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [t]);

  const active = t.sessions.find((s) => s.id === t.activeId) ?? t.sessions[0];

  return (
    <div
      className="term-drawer"
      style={{ height: t.height }}
      role="region"
      aria-label="Terminal drawer"
    >
      <div
        className="term-drawer__grip"
        onMouseDown={onMouseDown}
        title="Drag to resize"
      >
        <GripHorizontal size={12} />
      </div>

      <div className="term-drawer__head">
        <div className="term-drawer__title">
          <TerminalIcon size={13} />
          <span>Terminal</span>
        </div>

        <div className="term-drawer__tabs" role="tablist">
          {t.sessions.map((s) => (
            <button
              key={s.id}
              type="button"
              role="tab"
              aria-selected={s.id === active?.id}
              className={`term-tab ${s.id === active?.id ? "is-active" : ""}`}
              onClick={() => t.setActive(s.id)}
            >
              <SessionDot status={s.status} vm={s.vm} />
              <span className="term-tab__label">{s.title}</span>
              <span
                className="term-tab__close"
                role="button"
                aria-label={`Close ${s.title}`}
                onClick={(ev) => {
                  ev.stopPropagation();
                  t.closeSession(s.id);
                }}
              >
                <X size={11} />
              </span>
            </button>
          ))}

          <div className="term-newmenu">
            <button
              ref={plusBtnRef}
              type="button"
              className="term-iconbtn"
              title="New session"
              aria-haspopup="menu"
              aria-expanded={pickerOpen}
              onClick={togglePicker}
            >
              <Plus size={13} />
            </button>
          </div>
        </div>

        <div className="term-drawer__actions">
          <button
            type="button"
            className="term-iconbtn"
            title="Collapse"
            onClick={t.hide}
          >
            <ChevronDown size={14} />
          </button>
        </div>
      </div>

      <div className="term-drawer__body">
        {t.sessions.map((s) => (
          <XTermPane key={s.id} session={s} visible={s.id === active?.id} />
        ))}
      </div>

      {/* Picker popup is portalled to <body> so no parent stacking context
          (the drawer itself sets z-index + absolute) can clip it. */}
      {pickerOpen && pickerPos && typeof document !== "undefined" && createPortal(
        <div
          ref={popupRef}
          className="term-newmenu__pop"
          role="menu"
          style={{ left: pickerPos.left, bottom: pickerPos.bottom }}
        >
          <button
            type="button"
            className="term-newmenu__row"
            onClick={() => { t.newLocal(); setPickerOpen(false); }}
          >
            <TerminalIcon size={12} />
            Local shell
          </button>
          {vms.length > 0 && <div className="term-newmenu__sep">SSH sessions</div>}
          {vms.length === 0 && (
            <div className="term-newmenu__empty">
              No VMs configured. Add one in Settings → Cloud VMs.
            </div>
          )}
          {vms.map((vm) => (
            <button
              key={vm.id}
              type="button"
              className="term-newmenu__row"
              onClick={() => { t.newSSH(vm); setPickerOpen(false); }}
            >
              <Shield size={12} />
              {vm.name}
              <span className="term-newmenu__hint">{vm.username}@{vm.host}</span>
            </button>
          ))}
        </div>,
        document.body,
      )}
    </div>
  );
}

function SessionDot({ status, vm }: { status: SessionStatus; vm: VM | null }) {
  let color = "var(--fg-4)";
  if (status === "connected") color = "var(--ok, #5ec27a)";
  else if (status === "connecting") color = "var(--amber, #d8a25c)";
  else if (status === "closed") color = "var(--err, #c25e63)";
  else if (vm === null) color = "var(--violet)";
  return <Circle size={7} fill={color} stroke="none" style={{ flexShrink: 0 }} />;
}

/* ----------------------------------------------------------------- */
/* XTermPane — owns one xterm instance and the optional websocket.   */
/* The instance lives in the provider's instancesRef so collapsing   */
/* the drawer does not destroy it.                                   */
/* ----------------------------------------------------------------- */

function XTermPane({ session, visible }: { session: TerminalSession; visible: boolean }) {
  const t = useTerminal();
  const hostRef = useRef<HTMLDivElement>(null);
  const bootedRef = useRef(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  // Initialize xterm on first mount; reuse later mounts via the instance map.
  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;
    let cancelled = false;

    const boot = async () => {
      if (typeof window === "undefined" || !hostRef.current) return;
      const { Terminal } = await import("xterm");
      const { FitAddon } = await import("xterm-addon-fit");
      if (cancelled || !hostRef.current) return;

      const instances = t.instancesRef.current;
      let inst: TerminalInstance | undefined = instances.get(session.id);
      if (!inst) {
        inst = { term: null, fitAddon: null, ws: null, localBuf: "" };
        instances.set(session.id, inst);
      }

      // If we already have a term (re-mount after collapse), just re-attach.
      if (inst.term) {
        try { inst.term.open(hostRef.current); inst.fitAddon?.fit(); inst.term.focus(); } catch { /* ignore */ }
        cleanupRef.current = registerListeners(inst, session, t);
        return;
      }

      const term = new Terminal({
        cursorBlink: true,
        fontSize: 12.5,
        lineHeight: 1.2,
        fontFamily: "var(--font-jetbrains), 'JetBrains Mono', ui-monospace, monospace",
        theme: readXTermTheme(),
        scrollback: 5000,
        allowProposedApi: true,
      });
      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(hostRef.current);
      try { fit.fit(); } catch { /* ignore */ }
      term.focus();

      inst.term = term;
      inst.fitAddon = fit;

      if (!session.vm) {
        writeLocalBanner(term);
      } else {
        connectSSH(session, inst, term, t.setStatus);
      }

      term.onData((data: string) => {
        if (inst!.ws && inst!.ws.readyState === WebSocket.OPEN) {
          inst!.ws.send(JSON.stringify({ type: "data", data }));
        } else if (!session.vm) {
          handleLocalInput(inst!, term, data);
        }
      });

      cleanupRef.current = registerListeners(inst, session, t);
    };

    boot();
    return () => {
      cancelled = true;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
    // session.id is stable for the lifetime of this pane
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refit when drawer height changes or this tab becomes visible.
  useEffect(() => {
    if (!visible) return;
    const inst = t.instancesRef.current.get(session.id);
    if (!inst?.fitAddon || !inst.term) return;
    const raf = requestAnimationFrame(() => {
      try { inst.fitAddon.fit(); } catch { /* ignore */ }
      if (inst.ws && inst.ws.readyState === WebSocket.OPEN) {
        inst.ws.send(JSON.stringify({ type: "resize", cols: inst.term.cols, rows: inst.term.rows }));
      }
      inst.term.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [visible, t.height, session.id, t.instancesRef]);

  return (
    <div
      ref={hostRef}
      className={`term-pane ${visible ? "is-visible" : "is-hidden"}`}
      onClick={() => t.instancesRef.current.get(session.id)?.term?.focus()}
    />
  );
}

/* ---------------- helpers ---------------- */

function registerListeners(
  inst: TerminalInstance,
  session: TerminalSession,
  t: ReturnType<typeof useTerminal>,
): () => void {
  const onResize = () => {
    try { inst.fitAddon?.fit(); } catch { /* ignore */ }
    if (inst.ws && inst.ws.readyState === WebSocket.OPEN && inst.term) {
      inst.ws.send(JSON.stringify({ type: "resize", cols: inst.term.cols, rows: inst.term.rows }));
    }
  };
  window.addEventListener("resize", onResize);

  const themeObs = new MutationObserver(() => {
    const newTheme = readXTermTheme();
    try {
      if (inst.term) inst.term.options.theme = newTheme;
    } catch { /* ignore */ }
  });
  themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  // session/t intentionally not used yet — kept for future hooks (e.g. status updates)
  void session; void t;
  return () => {
    window.removeEventListener("resize", onResize);
    themeObs.disconnect();
  };
}

function readXTermTheme() {
  if (typeof window === "undefined") {
    return { background: "#0c0c12", foreground: "#f2f3f7", cursor: "#f2f3f7" };
  }
  const styles = getComputedStyle(document.documentElement);
  const bg0 = styles.getPropertyValue("--bg-0").trim() || "#0c0c12";
  const fg = styles.getPropertyValue("--fg").trim() || "#f2f3f7";
  return {
    background: bg0,
    foreground: fg,
    cursor: fg,
    cursorAccent: bg0,
    selectionBackground: "rgba(190, 165, 255, 0.28)",
    black: "#0c0c12",
    red: "#e26b6b",
    green: "#5ec27a",
    yellow: "#d8a25c",
    blue: "#7aa6e4",
    magenta: "#b88cff",
    cyan: "#7ec7d6",
    white: fg,
  };
}

function writeLocalBanner(term: import("xterm").Terminal) {
  const lines = [
    "\x1b[38;5;183m  Aladdin Operational Console  \x1b[0m",
    "\x1b[38;5;245m  Local shell — type `help` for available commands.\x1b[0m",
    "",
  ];
  term.writeln(lines.join("\r\n"));
  term.write("\x1b[38;5;141m$\x1b[0m ");
}

/** Tiny local command set. */
function handleLocalInput(
  inst: TerminalInstance,
  term: import("xterm").Terminal,
  data: string,
) {
  for (const ch of data) {
    if (ch === "\r") {
      term.write("\r\n");
      runLocal(term, inst.localBuf);
      inst.localBuf = "";
      term.write("\x1b[38;5;141m$\x1b[0m ");
    } else if (ch === "") {
      if (inst.localBuf.length > 0) {
        inst.localBuf = inst.localBuf.slice(0, -1);
        term.write("\b \b");
      }
    } else if (ch >= " " || ch === "\t") {
      inst.localBuf += ch;
      term.write(ch);
    }
  }
}

function runLocal(term: import("xterm").Terminal, raw: string) {
  const cmd = raw.trim();
  if (!cmd) return;
  const [head, ...rest] = cmd.split(/\s+/);
  switch (head.toLowerCase()) {
    case "help":
      term.writeln("  help            Show this list");
      term.writeln("  clear           Clear screen");
      term.writeln("  echo …          Echo back");
      term.writeln("  Tip: use the [+] menu to open an SSH session.");
      break;
    case "clear":
      term.clear();
      break;
    case "echo":
      term.writeln(rest.join(" "));
      break;
    default:
      term.writeln(`\x1b[38;5;167mUnknown:\x1b[0m ${head} — try \x1b[38;5;183mhelp\x1b[0m`);
  }
}

function connectSSH(
  session: TerminalSession,
  inst: TerminalInstance,
  term: import("xterm").Terminal,
  setStatus: (id: string, status: SessionStatus) => void,
) {
  if (!session.vm) return;
  setStatus(session.id, "connecting");
  term.writeln(`\x1b[38;5;245mConnecting to ${session.vm.name}…\x1b[0m`);

  const token = (typeof window !== "undefined")
    ? window.localStorage.getItem("access_token")
    : null;
  const url = buildTerminalWsUrl(session.vm.id, token);

  const ws = new WebSocket(url);
  inst.ws = ws;

  ws.onopen = () => {
    setStatus(session.id, "connected");
    term.write("\x1b[2J\x1b[H");
    ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
  };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === "data") {
        term.write(msg.data);
      } else if (msg.type === "error") {
        term.writeln(`\r\n\x1b[38;5;167mSSH error:\x1b[0m ${msg.message}`);
      }
    } catch {
      /* ignore malformed frame */
    }
  };
  ws.onclose = () => {
    setStatus(session.id, "closed");
    term.writeln("\r\n\x1b[38;5;245mConnection closed.\x1b[0m");
  };
  ws.onerror = () => {
    setStatus(session.id, "closed");
    term.writeln("\r\n\x1b[38;5;167mConnection error.\x1b[0m");
  };
}

/**
 * Resolve the backend WebSocket origin. The backend lives at `NEXT_PUBLIC_API_URL`
 * (defaults to http://localhost:8000/api); we strip the trailing /api and swap
 * http(s) for ws(s). Falls back to the current page origin so a same-origin
 * deployment keeps working without an env var.
 */
function buildTerminalWsUrl(vmId: number, token: string | null): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";
  let origin = "";
  try {
    if (apiUrl) {
      const u = new URL(apiUrl);
      const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
      origin = `${wsProto}//${u.host}`;
    }
  } catch {
    /* malformed env var — fall through to window.location */
  }
  if (!origin && typeof window !== "undefined") {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    origin = `${wsProto}//${window.location.host}`;
  }
  return `${origin}/ws/terminal/${vmId}?token=${encodeURIComponent(token ?? "")}`;
}

/* Status-bar launcher button — kept in this file so we don't double-import xterm. */
export function TerminalLauncherButton() {
  const t = useTerminal();
  const count = t.sessions.length;
  return (
    <button
      type="button"
      className="sb-launcher"
      onClick={() => {
        console.log("[Terminal] launcher clicked", {
          sessions: t.sessions.length,
          open: t.open,
        });
        if (t.sessions.length === 0) {
          t.newLocal();
        } else {
          t.toggle();
        }
      }}
      title="Toggle terminal (Ctrl+`)"
    >
      <TerminalIcon size={11} />
      <span>Terminal</span>
      {count > 0 && <code>{count}</code>}
      {t.open ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
    </button>
  );
}
