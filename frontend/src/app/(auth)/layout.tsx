import { AppShell } from "@/components/shell/AppShell";
import { AuthHero } from "@/components/shell/AuthHero";

/**
 * Minimal chrome for public/auth surfaces.
 *
 * Layout: Titlebar (lamp + wordmark, small) → split-screen body.
 *   - Left: large branding hero (≥768px only)
 *   - Right: form column, vertically centred, ~440px wide
 *
 * The mobile breakpoint (<768px) hides the hero and centres the form
 * full-width — see `.auth-split` / `.auth-hero` in globals.css.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <div className="auth-split">
        <AuthHero />
        <main className="auth-form-wrap" role="main">
          <div className="auth-form-card">{children}</div>
        </main>
      </div>
    </AppShell>
  );
}
