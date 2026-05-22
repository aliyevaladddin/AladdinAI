"use client";

/**
 * TerminalDrawer — plugin-slot edition.
 *
 * We no longer own xterm. Each tab is an <iframe> pointed at whatever provider
 * the backend chose (ttyd / Wetty / Guacamole / custom). Our job is to:
 *   1. ask `POST /api/terminal/session` for a URL (provider handles auth & PTY),
 *   2. render the iframe with a strict sandbox + no-referrer policy,
 *   3. show our own spinner until the iframe says `onload`,
 *   4. show a Reconnect button on iframe error or 5xx / token expiry,
 *   5. keep all opened iframes mounted so a backgrounded tab keeps its state
 *      (display: none, NOT unmount).
 *
 * Drawer chrome (drag handle, tabs with close, [+] menu, collapse) is
 * unchanged in spirit but trimmed down — no more wheel routing, no fit/RO,
 * no ws lifecycle, no canvas/DOM renderer choice.
 */

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
  RefreshCw,
  Settings,
} from "lucide-react";
import {
  useTerminal,
  type TerminalSession,
  type SessionStatus,
  type VM,
} from "./TerminalProvider";

/* ------------------------------------------------------------------ */
/* Drawer shell                                                       */
/* ------------------------------------------------------------------ */

export function TerminalDrawer() {
  const t = useTerminal();
  if (!t.open) return null;
  if (t.sessions.length === 0) return <EmptyDrawer />;
  return <DrawerInner />;
}

/**
 * Drawer opened with no sessions yet — spawn one and let DrawerInner take over.
 * Module-level latch survives StrictMode's mount→cleanup→mount in dev so we
 * don't double-spawn or get stuck on the placeholder.
 */
let __emptyDrawerSpawned = false;
function EmptyDrawer() {
  const t = useTerminal();
  useEffect(() => {
    if (__emptyDrawerSpawned) return;
    __emptyDrawerSpawned = true;
    void t.newLocal();
    return () => { __emptyDrawerSpawned = false; };
  }, [t]);

  return (
    <div
      className="term-drawer"
      style={{ height: t.height }}
      role="region"
      aria-label="Terminal drawer"
    >
      <div className="term-drawer__head">
        <div className="term-drawer__title">
          <TerminalIcon size={13} />
          <span>Starting terminal…</span>
        </div>
        <div className="term-drawer__actions">
          <button type="button" className="term-iconbtn" title="Collapse" onClick={t.hide}>
            <ChevronDown size={14} />
          </button>
        </div>
      </div>
      <div className="term-drawer__body" />
    </div>
  );
}

function DrawerInner() {
  const t = useTerminal();
  const drawerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);
  const plusBtnRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const [vms, setVms] = useState<VM[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerPos, setPickerPos] = useState<{ left: number; bottom: number } | null>(null);

  // VM list for the [+] picker.
  useEffect(() => {
    let active = true;
    t.listVMs().then((list) => { if (active) setVms(list); });
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
    if (pickerOpen) { setPickerOpen(false); return; }
    const rect = plusBtnRef.current?.getBoundingClientRect();
    if (rect) {
      setPickerPos({
        left: Math.max(8, rect.left),
        bottom: Math.max(8, window.innerHeight - rect.top + 6),
      });
    } else {
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
      ref={drawerRef}
      className="term-drawer"
      style={{ height: t.height }}
      role="region"
      aria-label="Terminal drawer"
    >
      <div className="term-drawer__grip" onMouseDown={onMouseDown} title="Drag to resize">
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
              title={s.providerType !== "none" ? `via ${s.providerType}` : undefined}
            >
              <SessionDot status={s.status} vm={s.vm} />
              <span className="term-tab__label">{s.title}</span>
              {s.status === "error" && (
                <span
                  className="term-tab__action"
                  role="button"
                  aria-label={`Reconnect ${s.title}`}
                  title="Reconnect"
                  onClick={(ev) => { ev.stopPropagation(); void t.reconnect(s.id); }}
                >
                  <RefreshCw size={11} />
                </span>
              )}
              <span
                className="term-tab__close"
                role="button"
                aria-label={`Close ${s.title}`}
                onClick={(ev) => { ev.stopPropagation(); t.closeSession(s.id); }}
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
          <button type="button" className="term-iconbtn" title="Collapse" onClick={t.hide}>
            <ChevronDown size={14} />
          </button>
        </div>
      </div>

      <div className="term-drawer__body">
        {t.sessions.map((s) => (
          <IframePane key={s.id} session={s} visible={s.id === active?.id} />
        ))}
      </div>

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
            onClick={() => { void t.newLocal(); setPickerOpen(false); }}
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
              onClick={() => { void t.newSSH(vm); setPickerOpen(false); }}
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
  if (status === "ready") color = "var(--ok, #5ec27a)";
  else if (status === "loading") color = "var(--amber, #d8a25c)";
  else if (status === "error") color = "var(--err, #c25e63)";
  else if (vm === null) color = "var(--violet)";
  return <Circle size={7} fill={color} stroke="none" style={{ flexShrink: 0 }} />;
}

/* ------------------------------------------------------------------ */
/* IframePane — one iframe per session, kept mounted while backgrounded */
/* ------------------------------------------------------------------ */

/**
 * Sandbox flags rationale:
 *   - allow-scripts          — ttyd/Wetty need JS to render the terminal
 *   - allow-same-origin      — required for clipboard/cookies on a same-origin provider
 *   - allow-forms            — Guacamole login form posts back to itself
 *   - allow-clipboard-*      — paste into the terminal, copy selection out
 * We deliberately omit allow-top-navigation, allow-popups, allow-modals, etc.
 * `referrerpolicy="no-referrer"` keeps the dashboard URL out of provider logs.
 */
const IFRAME_SANDBOX = "allow-scripts allow-same-origin allow-forms allow-clipboard-read allow-clipboard-write";
const IFRAME_ALLOW = "clipboard-read; clipboard-write";

function IframePane({ session, visible }: { session: TerminalSession; visible: boolean }) {
  const t = useTerminal();
  // `display: none` instead of unmount — keeps the iframe's PTY warm when the
  // user switches to a different tab and comes back.
  const style: React.CSSProperties = visible
    ? { display: "block" }
    : { display: "none" };

  const onLoad = useCallback(() => {
    // A cross-origin iframe always fires `load` once the navigation completes,
    // even if the provider then renders an error page — we can only verify
    // network-level success. Token-expiry / auth errors must come back as
    // 5xx from `POST /api/terminal/session` (handled in the provider) so the
    // tab flips to "error" before we ever render the iframe.
    if (session.url === "about:blank") return;
    t.markReady(session.id);
  }, [session.id, session.url, t]);

  const onError = useCallback(() => {
    t.markError(session.id, "Provider iframe failed to load");
  }, [session.id, t]);

  // No provider installed yet → empty-state placeholder pointing at settings.
  if (session.providerType === "none" && session.status === "ready") {
    return (
      <div className={`term-pane ${visible ? "is-visible" : "is-hidden"}`} style={style}>
        <div className="term-empty">
          <Settings size={18} />
          <div className="term-empty__title">No terminal provider configured</div>
          <div className="term-empty__hint">
            Install one in <strong>Settings → Terminal Providers</strong> (ttyd, Wetty or Guacamole),
            then reopen this drawer.
          </div>
        </div>
      </div>
    );
  }

  if (session.status === "error") {
    return (
      <div className={`term-pane ${visible ? "is-visible" : "is-hidden"}`} style={style}>
        <div className="term-empty">
          <RefreshCw size={18} />
          <div className="term-empty__title">Session unavailable</div>
          <div className="term-empty__hint">{session.errorMessage ?? "The provider returned an error."}</div>
          <button type="button" className="term-iconbtn" onClick={() => void t.reconnect(session.id)}>
            <RefreshCw size={12} /> Reconnect
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`term-pane ${visible ? "is-visible" : "is-hidden"}`} style={style}>
      {session.status === "loading" && (
        <div className="term-pane__overlay" aria-hidden>
          <div className="term-spinner" />
          <span>Connecting…</span>
        </div>
      )}
      <iframe
        // Keying on (id, url) — when reconnect() refreshes the URL we want a
        // hard reload of the iframe even if the new URL string happens to
        // match the old one.
        key={`${session.id}:${session.url}`}
        src={session.url}
        title={session.title}
        className="term-iframe"
        sandbox={IFRAME_SANDBOX}
        referrerPolicy="no-referrer"
        allow={IFRAME_ALLOW}
        onLoad={onLoad}
        onError={onError}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Launcher button (status bar) — unchanged contract                  */
/* ------------------------------------------------------------------ */

export function TerminalLauncherButton() {
  const t = useTerminal();
  const count = t.sessions.length;
  return (
    <button
      type="button"
      className="sb-launcher"
      onClick={() => { t.open ? t.hide() : t.show(); }}
      title="Toggle terminal (Ctrl+`)"
    >
      <TerminalIcon size={11} />
      <span>Terminal</span>
      {count > 0 && <code>{count}</code>}
      {t.open ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
    </button>
  );
}
