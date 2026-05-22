import { type ReactNode } from "react";
import { Lamp } from "./Lamp";
import { ThemePicker } from "./ThemePicker";
import { Wordmark } from "./Wordmark";

interface TitlebarProps {
  /** Items shown to the left of the lamp wordmark, e.g. breadcrumb chain. */
  crumbs?: ReactNode;
  /** Right-aligned slot — search, notifications, avatar. */
  right?: ReactNode;
}

/**
 * Top frame of the AladdinAI shell — 44px tall.
 * The lamp sits in a 56px column so it aligns vertically with the
 * activity bar below it (one continuous edge).
 */
export function Titlebar({ crumbs, right }: TitlebarProps) {
  return (
    <header className="titlebar">
      <div className="titlebar__brand">
        <Lamp />
      </div>
      <div className="titlebar__crumbs">
        <Wordmark />
        {crumbs ? (
          <>
            <span className="crumb-sep">/</span>
            {crumbs}
          </>
        ) : null}
      </div>
      <div className="titlebar__right">
        {right}
        <ThemePicker />
      </div>
    </header>
  );
}
