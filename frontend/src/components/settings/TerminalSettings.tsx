"use client";

/**
 * Terminal Marketplace — Settings tab.
 *
 * AppStore-feel picker for the Terminal Provider that powers the drawer.
 *
 * Layout:
 *   - Hero strip with ambient amber→violet glow + live counters and the
 *     currently active provider.
 *   - Installed section: one row per provider with a status pill,
 *     contextual primary action (Start / Set active) and quiet secondary
 *     actions. The active provider is visually dominant (violet rail).
 *   - Catalogue section: cards with per-type icon + accent colour, image
 *     size chip, capability chips, hover lift, and a "Recommended" ribbon
 *     on the lightest entry (ttyd).
 *
 * Empty + error + skeleton-loading states are all first-class.
 */

import {
  type ComponentType,
  type ReactNode,
  type SVGProps,
  useCallback,
  useEffect,
  useState,
} from "react";
import { toast } from "sonner";
import {
  TerminalSquare,
  Network,
  Code2,
  PlugZap,
  Play,
  Square,
  Star,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  HardDrive,
  Cable,
  PackageOpen,
  ShieldCheck,
  Plug,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/* ───────── types ───────── */

interface MarketplaceEntry {
  type: string;
  name: string;
  description: string | null;
  image: string;
  internal_port: number;
  requires_ssh_proxy: boolean;
}

interface InstalledProvider {
  id: number;
  name: string;
  type: string;
  source: string;
  image: string;
  internal_port: number;
  requires_ssh_proxy: boolean;
  is_active: boolean;
  status: string; // stopped | starting | running | unhealthy | error
  container_id: string | null;
  last_error: string | null;
  created_at: string;
}

type LucideIcon = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string }>;

/* ───────── per-type catalogue metadata ─────────
 *
 * Backend manifests are intentionally generic — the front-end owns the
 * presentation layer (icon, accent, capability chips, approximate image
 * weight). If a new provider type appears we fall back to neutral defaults.
 */

interface TypeMeta {
  icon: LucideIcon;
  accent: string;        // css token name (without var())
  capabilities: { label: string; icon: LucideIcon }[];
  /** Approximate pulled-image size — surfaced as a chip on the card. */
  size: string;
  /** Override of the (long) backend description for a tighter card body. */
  blurb?: string;
  featured?: boolean;
}

const TYPE_META: Record<string, TypeMeta> = {
  ttyd: {
    icon: TerminalSquare,
    accent: "--amber",
    capabilities: [
      { label: "shell", icon: TerminalSquare },
      { label: "container-local", icon: ShieldCheck },
    ],
    size: "~15 MB",
    blurb:
      "Lightweight web terminal. Opens a shell inside a per-user container — no SSH setup, no host port.",
    featured: true,
  },
  wetty: {
    icon: Network,
    accent: "--violet",
    capabilities: [
      { label: "ssh", icon: Cable },
      { label: "vm-routed", icon: Network },
    ],
    size: "~110 MB",
    blurb:
      "Web terminal that SSHs into one of your saved VMs. Credentials are brokered per session — never inside the container.",
  },
  "code-server": {
    icon: Code2,
    accent: "--info",
    capabilities: [
      { label: "editor", icon: Code2 },
      { label: "terminal", icon: TerminalSquare },
      { label: "extensions", icon: Sparkles },
    ],
    size: "~250 MB",
    blurb:
      "Full VS Code in the browser — integrated terminal, file editor, extensions. Alpine build, stays under 1 GB.",
  },
};

const DEFAULT_META: TypeMeta = {
  icon: PlugZap,
  accent: "--violet",
  capabilities: [{ label: "terminal", icon: TerminalSquare }],
  size: "container",
};

function metaFor(type: string): TypeMeta {
  return TYPE_META[type] ?? DEFAULT_META;
}

/* ───────── status mapping ───────── */

type Status = "running" | "starting" | "stopped" | "unhealthy" | "error" | "unknown";

function normalizeStatus(s: string): Status {
  switch (s) {
    case "running":
    case "starting":
    case "stopped":
    case "unhealthy":
    case "error":
      return s;
    default:
      return "unknown";
  }
}

function statusLabel(s: Status): string {
  if (s === "unknown") return "unknown";
  return s;
}

/* ───────── component ───────── */

export function TerminalSettings() {
  const [catalogue, setCatalogue] = useState<MarketplaceEntry[]>([]);
  const [installed, setInstalled] = useState<InstalledProvider[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoadingList(true);
    setLoadError(null);
    try {
      const [m, p] = await Promise.all([
        api.get<MarketplaceEntry[]>("/terminal/marketplace"),
        api.get<InstalledProvider[]>("/terminal/providers"),
      ]);
      setCatalogue(m);
      setInstalled(p);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setLoadError(msg);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setBusyKey = (k: string, v: boolean) =>
    setBusy((prev) => ({ ...prev, [k]: v }));

  const handleInstall = async (entry: MarketplaceEntry) => {
    setBusyKey(`install:${entry.type}`, true);
    try {
      await api.post("/terminal/providers", { type: entry.type });
      toast.success(`Installed ${entry.name}`);
      await load();
    } catch (e) {
      toast.error("Install failed", {
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setBusyKey(`install:${entry.type}`, false);
    }
  };

  const handleAction = async (
    id: number,
    action: "start" | "stop" | "set_active",
    label: string,
  ) => {
    setBusyKey(`${action}:${id}`, true);
    try {
      await api.post(`/terminal/providers/${id}/${action}`);
      toast.success(label);
      await load();
    } catch (e) {
      toast.error(`${label} failed`, {
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setBusyKey(`${action}:${id}`, false);
    }
  };

  const handleDelete = async (p: InstalledProvider) => {
    if (!confirm(`Uninstall "${p.name}"? The container will be removed.`)) return;
    setBusyKey(`delete:${p.id}`, true);
    try {
      await api.delete(`/terminal/providers/${p.id}`);
      toast.success("Uninstalled");
      await load();
    } catch (e) {
      toast.error("Delete failed", {
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setBusyKey(`delete:${p.id}`, false);
    }
  };

  const installedTypes = new Set(installed.map((p) => p.type));
  const activeProvider = installed.find((p) => p.is_active) ?? null;
  const runningCount = installed.filter((p) => p.status === "running").length;

  /* ── error state ─────────────────────────────── */
  if (loadError && !loadingList && installed.length === 0 && catalogue.length === 0) {
    return (
      <div className="space-y-6">
        <Hero
          activeProvider={null}
          installedCount={0}
          runningCount={0}
        />
        <div className="mkt-error" role="alert">
          <AlertTriangle size={18} className="mkt-error__icon" />
          <div className="min-w-0 flex-1">
            <div className="mkt-error__title">Couldn’t reach the terminal service</div>
            <div className="mkt-error__msg">{loadError}</div>
          </div>
          <Button variant="outline" size="sm" onClick={() => void load()}>
            <RotateCcw size={13} />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Hero
        activeProvider={activeProvider}
        installedCount={installed.length}
        runningCount={runningCount}
      />

      {/* Installed */}
      <section>
        <div className="mkt-section-head">
          <span className="mkt-eyebrow">Installed</span>
          <span className="mkt-count">{loadingList ? "…" : installed.length}</span>
          {activeProvider && (
            <span className="text-[11px] text-[var(--fg-3)] ml-auto">
              Active drives the dashboard drawer
            </span>
          )}
        </div>

        {loadingList ? (
          <div className="space-y-2">
            <RowSkeleton />
            <RowSkeleton />
          </div>
        ) : installed.length === 0 ? (
          <div className="mkt-empty">
            <div className="mkt-empty__icon">
              <PackageOpen size={22} />
            </div>
            <div>
              <div className="mkt-empty__title">No terminal provider installed</div>
              <div className="mkt-empty__sub">
                Pick one from the catalogue below — installation pulls the image, wires
                Traefik, and makes it available to the dashboard drawer.
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {installed.map((p, idx) => (
              <InstalledRow
                key={p.id}
                p={p}
                index={idx}
                busy={busy}
                onStart={() => handleAction(p.id, "start", `Started ${p.name}`)}
                onStop={() => handleAction(p.id, "stop", `Stopped ${p.name}`)}
                onSetActive={() =>
                  handleAction(p.id, "set_active", `${p.name} is now the active provider`)
                }
                onDelete={() => handleDelete(p)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Catalogue */}
      <section>
        <div className="mkt-section-head">
          <span className="mkt-eyebrow">Catalogue</span>
          <span className="mkt-count">{loadingList ? "…" : catalogue.length}</span>
          <span className="text-[11px] text-[var(--fg-3)] ml-auto">
            Container-isolated · Traefik-routed
          </span>
        </div>

        {loadingList ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : catalogue.length === 0 ? (
          <div className="mkt-empty">
            <div className="mkt-empty__icon">
              <PlugZap size={22} />
            </div>
            <div>
              <div className="mkt-empty__title">No providers shipped with this build</div>
              <div className="mkt-empty__sub">
                The backend reports an empty marketplace. Make sure
                <code className="mx-1 font-mono">backend/app/terminal_plugins/</code>
                contains at least one manifest.
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {catalogue.map((entry, idx) => (
              <CatalogueCard
                key={entry.type}
                entry={entry}
                index={idx}
                installed={installedTypes.has(entry.type)}
                busy={!!busy[`install:${entry.type}`]}
                onInstall={() => handleInstall(entry)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

/* ───────── Hero ───────── */

function Hero({
  activeProvider,
  installedCount,
  runningCount,
}: {
  activeProvider: InstalledProvider | null;
  installedCount: number;
  runningCount: number;
}) {
  const activeMeta = activeProvider ? metaFor(activeProvider.type) : null;
  const ActiveIcon = activeMeta?.icon ?? TerminalSquare;

  return (
    <header className="mkt-hero">
      <div className="flex items-start gap-4">
        <div
          className="mkt-card__icon"
          style={
            {
              width: 44,
              height: 44,
              borderRadius: 14,
              ["--mkt-accent" as string]: "var(--violet)",
            } as React.CSSProperties
          }
          aria-hidden
        >
          <TerminalSquare size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h2
            className="display"
            style={{
              fontSize: 22,
              lineHeight: 1.15,
              letterSpacing: "-0.02em",
              color: "var(--fg)",
              margin: 0,
            }}
          >
            Terminal Marketplace
          </h2>
          <p
            style={{
              margin: "4px 0 0",
              fontSize: 12.5,
              color: "var(--fg-2)",
              lineHeight: 1.5,
              maxWidth: 540,
            }}
          >
            Install a web-based terminal that runs in an isolated container.
            One <em style={{ color: "var(--violet)", fontStyle: "normal", fontWeight: 600 }}>active</em>{" "}
            provider powers the dashboard drawer.
          </p>
        </div>

        {/* Right rail — counters + active provider chip */}
        <div className="hidden md:flex flex-col items-end gap-2 shrink-0">
          <div
            className="flex items-center gap-3"
            style={{ fontSize: 11, color: "var(--fg-3)" }}
          >
            <Stat label="installed" value={installedCount} />
            <Sep />
            <Stat
              label="running"
              value={runningCount}
              accent={runningCount > 0 ? "var(--ok)" : undefined}
            />
          </div>
          {activeProvider && activeMeta && (
            <div
              className="flex items-center gap-2 pl-2 pr-2.5 py-1 rounded-lg"
              style={{
                background: "color-mix(in oklab, var(--violet) 10%, transparent)",
                border: "1px solid var(--violet-line)",
              }}
            >
              <span
                className="inline-flex items-center justify-center"
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 6,
                  background: "color-mix(in oklab, var(--violet) 18%, transparent)",
                  color: "var(--violet)",
                }}
              >
                <ActiveIcon size={11} />
              </span>
              <span style={{ fontSize: 11.5, color: "var(--fg)", fontWeight: 500 }}>
                {activeProvider.name}
              </span>
              <span
                style={{
                  fontSize: 9.5,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--violet)",
                }}
              >
                Active
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: string;
}) {
  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span
        style={{
          fontSize: 16,
          fontWeight: 600,
          fontVariantNumeric: "tabular-nums",
          color: accent ?? "var(--fg)",
          letterSpacing: "-0.02em",
        }}
      >
        {value}
      </span>
      <span style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 9.5 }}>
        {label}
      </span>
    </span>
  );
}

function Sep() {
  return (
    <span style={{ width: 1, height: 14, background: "var(--line)" }} aria-hidden />
  );
}

/* ───────── Installed row ───────── */

function InstalledRow({
  p,
  index,
  busy,
  onStart,
  onStop,
  onSetActive,
  onDelete,
}: {
  p: InstalledProvider;
  index: number;
  busy: Record<string, boolean>;
  onStart: () => void;
  onStop: () => void;
  onSetActive: () => void;
  onDelete: () => void;
}) {
  const meta = metaFor(p.type);
  const Icon = meta.icon;
  const status = normalizeStatus(p.status);
  const isRunning = status === "running";
  const isTransitional = status === "starting";

  const startBusy = !!busy[`start:${p.id}`];
  const stopBusy = !!busy[`stop:${p.id}`];
  const activeBusy = !!busy[`set_active:${p.id}`];
  const deleteBusy = !!busy[`delete:${p.id}`];

  // Decide the *primary* action so the user has one obvious next step.
  // - stopped/error → Start
  // - running but not active → Set active
  // - running + active → no primary (already wired)
  let primary: ReactNode = null;
  if (status === "stopped" || status === "error" || status === "unhealthy" || status === "unknown") {
    primary = (
      <Button variant="default" size="sm" onClick={onStart} disabled={startBusy || isTransitional}>
        {startBusy ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
        Start
      </Button>
    );
  } else if (isRunning && !p.is_active) {
    primary = (
      <Button variant="default" size="sm" onClick={onSetActive} disabled={activeBusy}>
        {activeBusy ? <Loader2 size={13} className="animate-spin" /> : <Plug size={13} />}
        Set active
      </Button>
    );
  }

  return (
    <div
      className={`mkt-row ${p.is_active ? "is-active" : ""}`}
      style={
        {
          ["--mkt-accent" as string]: `var(${meta.accent})`,
          ["--mkt-delay" as string]: `${Math.min(index * 40, 200)}ms`,
        } as React.CSSProperties
      }
    >
      <div className="mkt-row__icon" aria-hidden>
        <Icon size={16} />
      </div>

      <div className="mkt-row__meta">
        <div className="mkt-row__name">
          <span className="mkt-row__name-text">{p.name}</span>
          {p.is_active && <span className="mkt-active-badge">Active</span>}
          <StatusPill status={status} />
        </div>
        <div className="mkt-row__sub" title={p.image}>
          {p.type} · {p.image}
        </div>
        {p.last_error && (
          <div className="mkt-row__error" title={p.last_error}>
            <AlertTriangle size={11} />
            {p.last_error}
          </div>
        )}
      </div>

      <div className="mkt-row__actions">
        {primary}

        {/* Secondary: Stop is only shown when running. */}
        {isRunning && (
          <Button variant="outline" size="sm" onClick={onStop} disabled={stopBusy}>
            {stopBusy ? <Loader2 size={13} className="animate-spin" /> : <Square size={13} />}
            Stop
          </Button>
        )}

        {/* Tertiary: Set-active only when running + already-active row keeps it
            visible but neutral. For non-running rows we hide it — Set active
            without a healthy container would just race. */}
        {isRunning && !p.is_active && primary === null /* never */ && (
          <Button variant="ghost" size="sm" onClick={onSetActive} disabled={activeBusy}>
            <Star size={13} />
            Set active
          </Button>
        )}

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onDelete}
          disabled={deleteBusy}
          title="Uninstall"
          aria-label={`Uninstall ${p.name}`}
          className="text-[var(--fg-3)] hover:text-[var(--err)]"
        >
          {deleteBusy ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
        </Button>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: Status }) {
  const cls = `mkt-status mkt-status--${status === "unknown" ? "stopped" : status}`;
  return (
    <span className={cls} aria-label={`Status: ${statusLabel(status)}`}>
      <span className="mkt-status__dot" aria-hidden />
      {statusLabel(status)}
    </span>
  );
}

/* ───────── Catalogue card ───────── */

function CatalogueCard({
  entry,
  index,
  installed,
  busy,
  onInstall,
}: {
  entry: MarketplaceEntry;
  index: number;
  installed: boolean;
  busy: boolean;
  onInstall: () => void;
}) {
  const meta = metaFor(entry.type);
  const Icon = meta.icon;
  const description = (meta.blurb ?? entry.description ?? "").trim();

  return (
    <article
      className={`mkt-card ${installed ? "is-installed" : ""}`}
      style={
        {
          ["--mkt-accent" as string]: `var(${meta.accent})`,
          ["--mkt-delay" as string]: `${Math.min(index * 60, 240)}ms`,
        } as React.CSSProperties
      }
    >
      {meta.featured && !installed && (
        <span className="mkt-card__ribbon">
          <Sparkles size={9} />
          Recommended
        </span>
      )}

      <div className="flex items-start gap-3">
        <div className="mkt-card__icon" aria-hidden>
          <Icon size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mkt-card__title">{entry.name}</div>
          <code className="mkt-card__image" title={entry.image}>
            {entry.image}
          </code>
        </div>
      </div>

      <p className="mkt-card__desc">{description || "—"}</p>

      <div className="mkt-card__chips">
        <span className="mkt-chip" title="Approximate pulled image size">
          <HardDrive size={11} />
          {meta.size}
        </span>
        <span className="mkt-chip" title={`Internal container port ${entry.internal_port}`}>
          <Cable size={11} />
          :{entry.internal_port}
        </span>
        {meta.capabilities.map((c) => {
          const CapIcon = c.icon;
          return (
            <span key={c.label} className="mkt-chip mkt-chip--accent">
              <CapIcon size={11} />
              {c.label}
            </span>
          );
        })}
      </div>

      <div className="mkt-card__footer">
        {installed ? (
          <span className="mkt-card__installed-mark">
            <CheckCircle2 size={13} />
            Installed
          </span>
        ) : (
          <span style={{ fontSize: 10.5, color: "var(--fg-4)" }}>
            {entry.requires_ssh_proxy ? "Requires a saved VM" : "Self-contained"}
          </span>
        )}
        <Button
          variant={installed ? "ghost" : "outline"}
          size="sm"
          onClick={onInstall}
          disabled={busy || installed}
          aria-label={installed ? `${entry.name} already installed` : `Install ${entry.name}`}
        >
          {busy ? (
            <>
              <Loader2 size={13} className="animate-spin" />
              Installing…
            </>
          ) : installed ? (
            <>
              <CheckCircle2 size={13} />
              Installed
            </>
          ) : (
            <>
              <PackageOpen size={13} />
              Install
            </>
          )}
        </Button>
      </div>
    </article>
  );
}

/* ───────── Skeletons ───────── */

function CardSkeleton() {
  return (
    <div className="mkt-skeleton mkt-skeleton--card flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="mkt-skel-block" />
        <div className="flex-1 space-y-2 pt-1">
          <div className="mkt-skel-line" style={{ width: "55%" }} />
          <div className="mkt-skel-line" style={{ width: "75%", height: 8 }} />
        </div>
      </div>
      <div className="space-y-2">
        <div className="mkt-skel-line" />
        <div className="mkt-skel-line" style={{ width: "85%" }} />
        <div className="mkt-skel-line" style={{ width: "65%" }} />
      </div>
      <div className="flex gap-2 mt-auto">
        <div className="mkt-skel-line" style={{ width: 56, height: 18, borderRadius: 6 }} />
        <div className="mkt-skel-line" style={{ width: 48, height: 18, borderRadius: 6 }} />
        <div className="mkt-skel-line" style={{ width: 64, height: 18, borderRadius: 6 }} />
      </div>
    </div>
  );
}

function RowSkeleton() {
  return (
    <div className="mkt-skeleton mkt-skeleton--row flex items-center gap-3 px-4">
      <div className="mkt-skel-block" style={{ width: 36, height: 36, borderRadius: 10 }} />
      <div className="flex-1 space-y-2">
        <div className="mkt-skel-line" style={{ width: "30%" }} />
        <div className="mkt-skel-line" style={{ width: "55%", height: 8 }} />
      </div>
      <div className="mkt-skel-line" style={{ width: 60, height: 22, borderRadius: 999 }} />
      <div className="mkt-skel-line" style={{ width: 72, height: 28, borderRadius: 8 }} />
    </div>
  );
}
