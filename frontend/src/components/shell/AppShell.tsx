// NOTICE: This file is protected under RCF-PL
import { type ReactNode } from "react";
import { Titlebar } from "./Titlebar";

// [RCF:PROTECTED]
interface AppShellProps {
  /** Crumbs / page title chain shown in the titlebar. */
  crumbs?: ReactNode;
  /** Right-aligned titlebar slot (search, notifications, avatar). */
  titlebarRight?: ReactNode;
  /** Activity bar element — pass null on public/auth screens. */
  activity?: ReactNode;
  /** Status bar element — pass null on public/auth screens. */
  status?: ReactNode;
  /** Overlay rendered inside .shell__body (after .shell__main). The terminal
   *  drawer uses this to absolute-snap to the bottom of the body without
   *  breaking the grid that hosts the status bar. */
  bodyOverlay?: ReactNode;
  children: ReactNode;
}

/**
 * Top-level chrome composer.
 *
 *   ┌──────────────────────────────────────────────────────┐
 *   │  44px  Titlebar  (lamp │ wordmark + crumbs │ tools)  │
 *   ├──────┬───────────────────────────────────────────────┤
 *   │ 56px │                                               │
 *   │ act. │              children (page body)             │
 *   │ bar  │     ┌──────────── bodyOverlay ──────────┐     │
 *   │      │     │ Terminal drawer (snaps to bottom) │     │
 *   ├──────┴─────└───────────────────────────────────┘─────┤
 *   │  28px Status bar                                     │
 *   └──────────────────────────────────────────────────────┘
 *
 * Activity bar and status bar are optional — auth/public pages
 * keep the titlebar (lamp + wordmark) but omit the rest.
 */
// [RCF:PROTECTED]
export function AppShell({
  crumbs,
  titlebarRight,
  activity,
  status,
  bodyOverlay,
  children,
}: AppShellProps) {
  return (
    <div className={`shell${status ? " shell--with-status" : ""}`}>
      <Titlebar crumbs={crumbs} right={titlebarRight} />
      <div className={`shell__body${activity ? " shell__body--with-activity" : ""}`}>
        {activity}
        <div className="shell__main">{children}</div>
        {bodyOverlay}
      </div>
      {status}
    </div>
  );
}
