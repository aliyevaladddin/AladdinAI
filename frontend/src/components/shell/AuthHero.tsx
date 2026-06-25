// NOTICE: This file is protected under RCF-PL
import { Lamp } from "./Lamp";


interface AuthHeroProps {
  /**
   * Tagline shown beneath the wordmark. A few candidates we tried:
   *  - "Wishes, granted by AI."           (poetic, on-brand)
   *  - "Your multi-agent workspace."      (functional)
   *  - "Where intent becomes action."     (operational)
   *  - "A council of agents, at your command."
   *
   * Default is the most evocative — the lamp metaphor justifies it.
   */
  tagline?: string;
  /** Short follow-up line under the tagline. */
  subtitle?: string;
}

const DEFAULT_TAGLINE = "Wishes, granted by AI.";
const DEFAULT_SUBTITLE =
  "A sovereign workspace where agents reason, remember, and act on your behalf.";

/**
 * Left-side branding panel for auth screens.
 *
 * - Large lamp (104px) with amplified golden halo
 * - Display-font wordmark, sized to compete with the form on the right
 * - Ambient amber+violet radial gradients, layered for depth
 * - Subtle grid noise on top so flat color doesn't read as cheap
 * - Adapts via CSS variables; light themes invert the contrast naturally
 *
 * Hidden below 768px (see `.auth-hero` in globals.css).
 */

export function AuthHero({
  tagline = DEFAULT_TAGLINE,
  subtitle = DEFAULT_SUBTITLE,
}: AuthHeroProps) {
  return (
    <aside className="auth-hero" aria-hidden="true">
      <div className="auth-hero__ambient" />
      <div className="auth-hero__grid" />

      <div className="auth-hero__content">
        <div className="auth-hero__brand">
          <div className="auth-hero__lamp">
            <Lamp size={104} label="" />
          </div>
          <h1 className="auth-hero__wordmark">
            Aladdin<i>AI</i>
          </h1>
        </div>

        <div className="auth-hero__copy">
          <p className="auth-hero__tagline">{tagline}</p>
          <p className="auth-hero__subtitle">{subtitle}</p>
        </div>

        <ul className="auth-hero__pillars">
          <li>
            <span className="auth-hero__pillar-dot" />
            Multi-agent reasoning with persistent memory
          </li>
          <li>
            <span className="auth-hero__pillar-dot" />
            Tool use, scheduled triggers, safety gates
          </li>
          <li>
            <span className="auth-hero__pillar-dot" />

            Sovereign by design — your data stays yours
          </li>
        </ul>
      </div>

      <div className="auth-hero__footer">
        <span>v1 · Operational</span>
        <span className="auth-hero__sep">·</span>
        <span>RCF-protected</span>
      </div>
    </aside>
  );
}
