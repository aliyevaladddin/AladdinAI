"use client";

/**
 * Drawer that hosts the terminal provider iframe.
 *
 * Single pane, single iframe. The iframe's `src` is a Traefik-routable URL
 * pointing at the user's active provider container (e.g. ttyd). The token in
 * that URL is single-use and short-TTL; once the iframe loads, the session
 * is alive inside the iframe and survives drawer collapse — we only clear it
 * when the user closes (X) the session, which forces a fresh `refresh()` on
 * next open.
 *
 * Empty states:
 *   - `idle`        — drawer opening for the first time; spinner.
 *   - `loading`     — /session call in flight.
 *   - `no-provider` — user has nothing installed yet; CTA to the marketplace.
 *   - `error`       — anything else; show message + retry.
 *   - `ready`       — render the iframe.
 *
 * No xterm imports — fixes the bug where xterm canvases stacked on top of
 * each other when the drawer mounted before its host had non-zero size.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import {
  X,
  ChevronDown,
  ChevronUp,
  Terminal as TerminalIcon,
  GripHorizontal,
  RotateCcw,
  PackageOpen,
} from "lucide-react";
import { useTerminal } from "./TerminalProvider";

/** Drawer is overlaid into `.shell__body`, snapped to its bottom edge. */
export function TerminalDrawer() {
  const t = useTerminal();
  if (!t.open) return null;
  return <DrawerInner />;
}

function DrawerInner() {
  const t = useTerminal();
  const dragRef = useRef<{ startY: number; startH: number } | null>(null);

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

  const title = t.slot.providerType ?? "Terminal";

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
          <div
            className="term-tab is-active"
            role="tab"
            aria-selected="true"
          >
            <span className="term-tab__label">{title}</span>
          </div>
        </div>

        <div className="term-drawer__actions">
          {t.slot.status === "ready" && (
            <button
              type="button"
              className="term-iconbtn"
              title="Reload session"
              onClick={() => void t.refresh()}
            >
              <RotateCcw size={13} />
            </button>
          )}
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
        <SessionPane />
      </div>
    </div>
  );
}

/** Visual body — branches on the slot status. */
function SessionPane() {
  const t = useTerminal();
  const { slot } = t;

  if (slot.status === "no-provider") {
    return <EmptyProvider />;
  }
  if (slot.status === "error") {
    return <ErrorPane message={slot.error} onRetry={() => void t.refresh()} />;
  }
  if (slot.status === "loading" || slot.status === "idle" || !slot.url) {
    return <LoadingPane />;
  }
  // ready
  return <IframePane key={slot.id} url={slot.url} />;
}

function IframePane({ url }: { url: string }) {
  // `loaded` is local — we want the spinner overlay only on the first paint.
  // The iframe stays in the DOM across loads so we never lose its terminal
  // state to a React unmount.
  const [loaded, setLoaded] = useState(false);
  return (
    <div className="term-pane is-visible">
      <iframe
        className="term-iframe"
        src={url}
        // ttyd talks WebSockets; we need `allow-scripts` for its JS, and
        // `allow-same-origin` because Traefik proxies it on our public host
        // and ttyd uses same-origin WS upgrades. We deliberately do NOT
        // allow top-navigation or popups.
        sandbox="allow-scripts allow-same-origin allow-clipboard-read allow-clipboard-write allow-forms"
        onLoad={() => setLoaded(true)}
        title="Terminal"
      />
      {!loaded && (
        <div className="term-pane__overlay">
          <div className="term-spinner" />
        </div>
      )}
    </div>
  );
}

function LoadingPane() {
  return (
    <div className="term-pane is-visible term-pane--center">
      <div className="term-spinner" />
    </div>
  );
}

function ErrorPane({ message, onRetry }: { message: string | null; onRetry: () => void }) {
  return (
    <div className="term-pane is-visible term-pane--center">
      <div className="term-empty">
        <X size={20} />
        <div className="term-empty__title">Couldn&apos;t open terminal</div>
        {message && <div className="term-empty__sub">{message}</div>}
        <button type="button" className="term-empty__cta" onClick={onRetry}>
          <RotateCcw size={12} />
          Try again
        </button>
      </div>
    </div>
  );
}

function EmptyProvider() {
  return (
    <div className="term-pane is-visible term-pane--center">
      <div className="term-empty">
        <PackageOpen size={20} />
        <div className="term-empty__title">No terminal provider installed</div>
        <div className="term-empty__sub">
          Install one from the marketplace to use the embedded terminal.
        </div>
        <Link href="/dashboard/settings?tab=terminal" className="term-empty__cta">
          <PackageOpen size={12} />
          Open marketplace
        </Link>
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- */
/* Status-bar launcher — kept in this file so the layout import path */
/* (TerminalLauncherButton from ./TerminalDrawer) stays unchanged.   */
/* ----------------------------------------------------------------- */

export function TerminalLauncherButton() {
  const t = useTerminal();
  return (
    <button
      type="button"
      className="sb-launcher"
      onClick={t.toggle}
      title="Toggle terminal (Ctrl+`)"
    >
      <TerminalIcon size={11} />
      <span>Terminal</span>
      {t.open ? <ChevronDown size={10} /> : <ChevronUp size={10} />}
    </button>
  );
}

// Re-exports — VmsSettings still imports VM from this barrel.
// (It used to import from TerminalProvider; the type lives there now, but
// we keep this re-export for code that points at TerminalDrawer.)
export type { VM } from "./TerminalProvider";

// Defensive: a couple of consumers (like a future tab strip) used to import
// `useTerminal` from this module. Re-export to avoid breaking them.
export { useTerminal } from "./TerminalProvider";
