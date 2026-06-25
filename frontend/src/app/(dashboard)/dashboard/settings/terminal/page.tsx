// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Plus,
  Power,
  Settings,
  Trash2,
  ExternalLink,
  Download,
  Check,
  AlertTriangle,
  Terminal,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
  listProviders,
  installPreset,
  installCustom as installCustomApi,
  startProvider,
  stopProvider,
  activateProvider,
  uninstallProvider,
} from "./api";
import { MARKETPLACE, getMarketplaceProvider, type MarketplaceProvider } from "./marketplace";
import { ProviderIcon } from "./ProviderIcon";
import { InstallStepper } from "./InstallStepper";
import { CustomProviderModal } from "./CustomProviderModal";
import type {
  InstalledProvider,
  InstallStep,
  CustomProviderDraft,
  TerminalProviderStatus,
} from "./types";

type Tab = "installed" | "marketplace";

const STATUS_TINT: Record<
  TerminalProviderStatus,
  { fg: string; soft: string; label: string }
> = {
  running:    { fg: "var(--ok)",     soft: "var(--ok-soft)",     label: "running" },
  stopped:    { fg: "var(--fg-3)",   soft: "var(--bg-3)",        label: "stopped" },
  error:      { fg: "var(--err)",    soft: "var(--err-soft)",    label: "error" },
  installing: { fg: "var(--violet)", soft: "var(--violet-soft)", label: "installing" },
};

const DEFAULT_STEPS: InstallStep[] = [
  { key: "pull",        label: "Pulling image",   status: "pending" },
  { key: "create",      label: "Creating container", status: "pending" },
  { key: "start",       label: "Starting container", status: "pending" },
  { key: "healthcheck", label: "Healthcheck",     status: "pending" },
];

export default function TerminalProvidersPage() {
  const [tab, setTab] = useState<Tab>("installed");
  const [installed, setInstalled] = useState<InstalledProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customOpen, setCustomOpen] = useState(false);
  const [detail, setDetail] = useState<MarketplaceProvider | null>(null);
  const [vmSelectOpen, setVmSelectOpen] = useState(false);
  const [pendingProvider, setPendingProvider] = useState<MarketplaceProvider | null>(null);
  /** Per-slug install progress, keyed while a provider is in `installing` state. */
  const [installSteps, setInstallSteps] = useState<Record<string, InstallStep[]>>({});

// [RCF:PROTECTED]
  const load = async () => {
    try {
      const res = await listProviders();
      setInstalled(res);
      setError(null);
    } catch (e: any) {
      // 404 on first run is acceptable — backend may not have wired the route yet.
      setError(e?.message ?? "Failed to load installed providers");
      setInstalled([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Poll while anything is installing, so the stepper actually moves.
  const polling = installed.some((p) => p.status === "installing");
  useEffect(() => {
    if (!polling) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [polling]);

  const installedSlugs = useMemo(() => new Set(installed.map((p) => p.slug)), [installed]);

// [RCF:PROTECTED]
  const installFromMarketplace = async (mp: MarketplaceProvider, vmId?: number) => {
    setInstallSteps((s) => ({ ...s, [mp.id]: DEFAULT_STEPS.map((x) => ({ ...x, status: x.key === "pull" ? "running" : "pending" })) }));
    // Optimistic insert
    setInstalled((p) => [
      ...p,
      {
        id: -Date.now(),
        slug: mp.id,
        name: mp.name,
        type: mp.id,
        status: "installing",
        endpoint: "",
        url_template: mp.docker.urlTemplate,
        active: false,
        updated_at: new Date().toISOString(),
      },
    ]);
    setTab("installed");
    try {
      await installPreset(mp.id, mp.name, vmId);
      toast.success(`${mp.name} install queued`);
      load();
    } catch (e: any) {
      toast.error(e?.message || `Failed to install ${mp.name}`);
      setInstalled((p) => p.filter((x) => x.slug !== mp.id || x.id > 0));
    }
  };

// [RCF:PROTECTED]
  const handleInstallClick = (mp: MarketplaceProvider) => {
    // If wetty, show VM selector first
    if (mp.id === "wetty") {
      setPendingProvider(mp);
      setVmSelectOpen(true);
    } else {
      installFromMarketplace(mp);
    }
  };

// [RCF:PROTECTED]
  const handleVmSelected = (vmId: number) => {
    if (pendingProvider) {
      installFromMarketplace(pendingProvider, vmId);
    }
    setVmSelectOpen(false);
    setPendingProvider(null);
  };

// [RCF:PROTECTED]
  const installCustom = async (draft: CustomProviderDraft) => {
    try {
      await installCustomApi(draft);
      toast.success(`${draft.name} install queued`);
      setTab("installed");
      load();
    } catch (e: any) {
      toast.error(e?.message || "Failed to install custom provider");
    }
  };

// [RCF:PROTECTED]
  const toggleRunning = async (p: InstalledProvider) => {
    try {
      if (p.status === "running") {
        await stopProvider(p.id);
      } else {
        await startProvider(p.id);
      }
      load();
    } catch (e: any) {
      toast.error(e?.message || "Action failed");
    }
  };

// [RCF:PROTECTED]
  const setActive = async (p: InstalledProvider) => {
    try {
      await activateProvider(p.id);
      // Optimistic — flip locally then reload.
      setInstalled((list) => list.map((x) => ({ ...x, active: x.id === p.id })));
      load();
    } catch (e: any) {
      toast.error(e?.message || "Could not set active");
    }
  };

// [RCF:PROTECTED]
  const uninstall = async (p: InstalledProvider) => {
    if (!confirm(`Uninstall ${p.name}? Running sessions will be terminated.`)) return;
    try {
      await uninstallProvider(p.id);
      toast.success(`${p.name} uninstalled`);
      load();
    } catch (e: any) {
      toast.error(e?.message || "Uninstall failed");
    }
  };

  return (
    <div className="space-y-5">
      {/* Heading */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="space-y-1">
          <h1 className="text-[20px] leading-tight font-semibold tracking-tight" style={{ color: "var(--fg)" }}>
            Terminal Providers
          </h1>
          <p className="text-[12.5px] leading-tight" style={{ color: "var(--fg-3)" }}>
            Pluggable web-terminals. Install one, then activate it to back the in-app terminal drawer.
          </p>
        </div>
        <Button onClick={() => setCustomOpen(true)} size="sm">
          <Plus size={14} strokeWidth={2.4} /> Add custom provider
        </Button>
      </div>

      {/* Tabs */}
      <TabBar tab={tab} setTab={setTab} installedCount={installed.length} marketCount={MARKETPLACE.length} />

      {tab === "installed" ? (
        <InstalledPanel
          loading={loading}
          error={error}
          installed={installed}
          installSteps={installSteps}
          onOpenMarketplace={() => setTab("marketplace")}
          onToggleRunning={toggleRunning}
          onSetActive={setActive}
          onUninstall={uninstall}
        />
      ) : (
        <MarketplacePanel
          installedSlugs={installedSlugs}
          onInstall={handleInstallClick}
          onOpenDetail={setDetail}
        />
      )}

      {/* Modals */}
      <CustomProviderModal
        open={customOpen}
        onClose={() => setCustomOpen(false)}
        onSubmit={installCustom}
      />
      <VmSelectModal
        open={vmSelectOpen}
        onClose={() => { setVmSelectOpen(false); setPendingProvider(null); }}
        onSelect={handleVmSelected}
      />
      <MarketplaceDetail
        provider={detail}
        installed={detail ? installedSlugs.has(detail.id) : false}
        onClose={() => setDetail(null)}
        onInstall={(mp) => { setDetail(null); handleInstallClick(mp); }}
      />
    </div>
  );
}

/* ============================================================
   Tab bar — segmented, premium underline animation
   ============================================================ */
// [RCF:PROTECTED]
function TabBar({
  tab, setTab, installedCount, marketCount,
}: {
  tab: Tab;
  setTab: (t: Tab) => void;
  installedCount: number;
  marketCount: number;
}) {
  const items: Array<{ id: Tab; label: string; count: number }> = [
    { id: "installed",   label: "Installed",   count: installedCount },
    { id: "marketplace", label: "Marketplace", count: marketCount },
  ];
  return (
    <div
      className="inline-flex items-center gap-1 p-1 rounded-lg"
      style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
      role="tablist"
    >
      {items.map((it) => {
        const active = tab === it.id;
        return (
          <button
            key={it.id}
            role="tab"
            aria-selected={active}
            onClick={() => setTab(it.id)}
            className="relative inline-flex items-center gap-2 px-3 h-7 rounded-md text-[12.5px] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{
              background: active ? "var(--bg-3)" : "transparent",
              color: active ? "var(--fg)" : "var(--fg-3)",
              outlineColor: "var(--violet)",
              boxShadow: active ? "0 1px 0 var(--line-strong) inset, 0 -1px 0 var(--line) inset" : undefined,
            }}
          >
            {it.label}
            <span
              className="inline-flex items-center justify-center min-w-[18px] h-[16px] px-1 rounded-full text-[10.5px] font-semibold tabular-nums"
              style={{
                background: active ? "var(--violet-soft)" : "var(--bg-3)",
                color: active ? "var(--violet)" : "var(--fg-3)",
                border: active ? "1px solid var(--violet-line)" : "1px solid var(--line)",
              }}
            >
              {it.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

/* ============================================================
   Installed panel
   ============================================================ */
// [RCF:PROTECTED]
function InstalledPanel({
  loading, error, installed, installSteps,
  onOpenMarketplace, onToggleRunning, onSetActive, onUninstall,
}: {
  loading: boolean;
  error: string | null;
  installed: InstalledProvider[];
  installSteps: Record<string, InstallStep[]>;
  onOpenMarketplace: () => void;
  onToggleRunning: (p: InstalledProvider) => void;
  onSetActive: (p: InstalledProvider) => void;
  onUninstall: (p: InstalledProvider) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-2.5">
        {[0, 1].map((i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (error && installed.length === 0) {
    return (
      <EmptyOrError
        icon={<AlertTriangle size={20} style={{ color: "var(--err)" }} />}
        title="Couldn't load providers"
        body={error}
      />
    );
  }

  if (installed.length === 0) {
    return (
      <EmptyOrError
        icon={<Terminal size={20} style={{ color: "var(--violet)" }} />}
        title="No terminal providers installed yet"
        body="Pick one from the marketplace to back the in-app terminal drawer."
        action={
          <Button size="sm" onClick={onOpenMarketplace}>
            Browse marketplace
          </Button>
        }
      />
    );
  }

  return (
    <ul className="space-y-2.5" role="list">
      {installed.map((p) => (
        <InstalledCard
          key={p.id + ":" + p.slug}
          provider={p}
          steps={installSteps[p.slug]}
          onToggleRunning={onToggleRunning}
          onSetActive={onSetActive}
          onUninstall={onUninstall}
        />
      ))}
    </ul>
  );
}

// [RCF:PROTECTED]
function InstalledCard({
  provider, steps, onToggleRunning, onSetActive, onUninstall,
}: {
  provider: InstalledProvider;
  steps?: InstallStep[];
  onToggleRunning: (p: InstalledProvider) => void;
  onSetActive: (p: InstalledProvider) => void;
  onUninstall: (p: InstalledProvider) => void;
}) {
  const mp = getMarketplaceProvider(provider.slug);
  const tint = STATUS_TINT[provider.status];
  const isInstalling = provider.status === "installing";
  const isActive = provider.active;

  return (
    <li
      className="rounded-lg p-4 transition-[border-color,background] motion-safe:duration-200"
      style={{
        background: "var(--bg-2)",
        border: `1px solid ${isActive ? "var(--violet-line)" : "var(--line)"}`,
        boxShadow: isActive
          ? "0 0 0 1px var(--violet-line) inset, 0 1px 0 rgba(255,255,255,0.02) inset"
          : "0 1px 0 rgba(255,255,255,0.02) inset",
      }}
    >
      <div className="flex items-start gap-3">
        <ProviderIcon
          accent={mp?.accent ?? "violet"}
          monogram={mp?.monogram ?? provider.name.slice(0, 2).toLowerCase()}
          size={32}
        />

        {/* Main meta */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-medium text-[13.5px] tracking-tight truncate" style={{ color: "var(--fg)" }}>
              {provider.name}
            </p>
            <span
              className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded-full text-[10.5px] font-medium uppercase tracking-wider"
              style={{ background: tint.soft, color: tint.fg }}
            >
              {provider.status === "installing" && (
                <Loader2 size={9} className="motion-safe:animate-spin" strokeWidth={3} />
              )}
              {provider.status === "running" && (
                <span aria-hidden style={{
                  width: 5, height: 5, borderRadius: 999,
                  background: tint.fg, boxShadow: `0 0 6px ${tint.fg}`,
                }} />
              )}
              {tint.label}
            </span>
            {isActive && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10.5px] font-semibold uppercase tracking-wider"
                style={{ background: "var(--violet-soft)", color: "var(--violet)", border: "1px solid var(--violet-line)" }}
              >
                <Check size={9} strokeWidth={3} /> active
              </span>
            )}
          </div>
          <p className="text-[12px] mt-0.5 truncate" style={{ color: "var(--fg-3)" }}>
            <span style={{ color: "var(--fg-4)" }}>{provider.type}</span>
            {provider.endpoint && (
              <>
                <span className="mx-1.5" style={{ color: "var(--fg-4)" }}>·</span>
                <span style={{ fontFamily: "var(--font-mono)" }}>{provider.endpoint}</span>
              </>
            )}
          </p>
        </div>

        {/* Actions */}
        {!isInstalling && (
          <div className="flex items-center gap-1.5 shrink-0">
            {!isActive && provider.status === "running" && (
              <Button variant="ghost" size="xs" onClick={() => onSetActive(provider)}>
                Set active
              </Button>
            )}
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => onToggleRunning(provider)}
              title={provider.status === "running" ? "Stop" : "Start"}
              aria-label={provider.status === "running" ? "Stop" : "Start"}
            >
              <Power size={13} style={{ color: provider.status === "running" ? "var(--ok)" : "var(--fg-3)" }} />
            </Button>
            <Button variant="outline" size="icon-sm" title="Configure" aria-label="Configure">
              <Settings size={13} />
            </Button>
            {provider.endpoint && (
              <a
                href={provider.endpoint}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center size-7 rounded-md transition-colors"
                style={{ color: "var(--fg-3)", border: "1px solid var(--line)", background: "var(--bg-1)" }}
                title="Open in new tab"
              >
                <ExternalLink size={13} />
              </a>
            )}
            <Button variant="ghost" size="icon-sm" onClick={() => onUninstall(provider)} title="Uninstall" aria-label="Uninstall">
              <Trash2 size={13} style={{ color: "var(--err)" }} />
            </Button>
          </div>
        )}
      </div>

      {/* Installing stepper */}
      {isInstalling && (
        <div
          className="mt-3.5 pt-3.5"
          style={{ borderTop: "1px dashed var(--line)" }}
        >
          <InstallStepper steps={steps ?? DEFAULT_STEPS} />
        </div>
      )}

      {/* Error footer */}
      {provider.status === "error" && (
        <div
          className="mt-3 rounded-md px-3 py-2 flex items-center justify-between gap-3"
          style={{ background: "var(--err-soft)", color: "var(--err)" }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <AlertTriangle size={13} className="shrink-0" />
            <span className="text-[12px] truncate">
              {provider.error ?? "Container is unhealthy."}
            </span>
          </div>
          <button
            type="button"
            className="text-[11.5px] font-medium underline-offset-2 hover:underline shrink-0"
            style={{ color: "var(--err)" }}
            onClick={() => toast.message("Logs viewer is on the roadmap")}
          >
            View logs
          </button>
        </div>
      )}
    </li>
  );
}

/* ============================================================
   Marketplace panel
   ============================================================ */
// [RCF:PROTECTED]
function MarketplacePanel({
  installedSlugs, onInstall, onOpenDetail,
}: {
  installedSlugs: Set<string>;
  onInstall: (mp: MarketplaceProvider) => void;
  onOpenDetail: (mp: MarketplaceProvider) => void;
}) {
  return (
    <ul
      className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5"
      role="list"
    >
      {MARKETPLACE.map((mp, i) => (
        <MarketplaceCard
          key={mp.id}
          mp={mp}
          installed={installedSlugs.has(mp.id)}
          onInstall={onInstall}
          onOpenDetail={onOpenDetail}
          // stagger mount, capped at 200ms
          delay={Math.min(i * 35, 200)}
        />
      ))}
    </ul>
  );
}

// [RCF:PROTECTED]
function MarketplaceCard({
  mp, installed, onInstall, onOpenDetail, delay,
}: {
  mp: MarketplaceProvider;
  installed: boolean;
  onInstall: (mp: MarketplaceProvider) => void;
  onOpenDetail: (mp: MarketplaceProvider) => void;
  delay: number;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <li
      className="group rounded-lg p-4 flex flex-col gap-3 cursor-pointer motion-safe:animate-[mpIn_280ms_cubic-bezier(0.16,1,0.3,1)_both] transition-[border-color,background,transform] motion-safe:duration-200"
      style={{
        background: hovered ? "var(--bg-3)" : "var(--bg-2)",
        border: `1px solid ${hovered ? "var(--line-strong)" : "var(--line)"}`,
        animationDelay: `${delay}ms`,
        transform: hovered ? "translateY(-1px)" : "translateY(0)",
        boxShadow: hovered
          ? "0 8px 24px -12px rgba(0,0,0,0.4), 0 1px 0 rgba(255,255,255,0.03) inset"
          : "0 1px 0 rgba(255,255,255,0.02) inset",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={(e) => {
        // Don't open detail when clicking install button
        if ((e.target as HTMLElement).closest("[data-stop]")) return;
        onOpenDetail(mp);
      }}
    >
      <div className="flex items-start gap-3">
        <ProviderIcon accent={mp.accent} monogram={mp.monogram} size={32} />
        <div className="min-w-0 flex-1">
          <h3 className="font-medium text-[13.5px] tracking-tight" style={{ color: "var(--fg)" }}>
            {mp.name}
          </h3>
          <p className="text-[11.5px] leading-snug mt-0.5 line-clamp-2" style={{ color: "var(--fg-3)" }}>
            {mp.tagline}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        {mp.tags.map((t) => (
          <span
            key={t}
            className="px-1.5 py-0.5 rounded text-[10.5px] font-medium"
            style={{
              background: "var(--bg-1)",
              color: "var(--fg-3)",
              border: "1px solid var(--line)",
            }}
          >
            {t}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between gap-2 mt-auto pt-1">
        <span className="text-[11px]" style={{ color: "var(--fg-4)", fontFamily: "var(--font-mono)" }}>
          {mp.docker.image.split("/").pop()}
        </span>
        <div data-stop>
          {installed ? (
            <Button variant="outline" size="xs" onClick={() => onOpenDetail(mp)}>
              <Check size={11} strokeWidth={3} style={{ color: "var(--ok)" }} />
              Installed
            </Button>
          ) : (
            <Button size="xs" onClick={() => onInstall(mp)}>
              <Download size={11} strokeWidth={2.6} /> Install
            </Button>
          )}
        </div>
      </div>
    </li>
  );
}

/* ============================================================
   Marketplace detail modal — hover/click for deep info
   ============================================================ */
// [RCF:PROTECTED]
function MarketplaceDetail({
  provider, installed, onClose, onInstall,
}: {
  provider: MarketplaceProvider | null;
  installed: boolean;
  onClose: () => void;
  onInstall: (mp: MarketplaceProvider) => void;
}) {
  useEffect(() => {
    if (!provider) return;
// [RCF:PROTECTED]
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [provider, onClose]);

  if (!provider) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`${provider.name} details`}
      className="fixed inset-0 z-[200] flex items-center justify-center motion-safe:animate-[modalFadeIn_180ms_cubic-bezier(0.16,1,0.3,1)]"
      style={{ background: "color-mix(in oklab, var(--bg-0) 70%, transparent)", backdropFilter: "blur(6px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-[620px] mx-4 motion-safe:animate-[modalSlideIn_220ms_cubic-bezier(0.16,1,0.3,1)]"
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--line-strong)",
          borderRadius: "var(--r-lg)",
          boxShadow: "0 32px 80px -16px rgba(0,0,0,0.55)",
          overflow: "hidden",
        }}
      >
        {/* mock screenshot — accent-tinted gradient placeholder */}
        <div
          className="h-[160px] relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg,
              color-mix(in oklab, var(${provider.accent === "violet" ? "--violet" : provider.accent === "amber" ? "--amber" : provider.accent === "ok" ? "--ok" : "--info"}) 24%, var(--bg-2)) 0%,
              var(--bg-2) 60%,
              var(--bg-1) 100%)`,
            borderBottom: "1px solid var(--line)",
          }}
        >
          {/* faux terminal lines */}
          <div className="absolute inset-0 flex flex-col gap-1.5 justify-center px-6 opacity-60" style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>
            <div style={{ color: "var(--fg-3)" }}>$ docker run -d -p {provider.docker.suggestedExternalPort}:{provider.docker.internalPort} {provider.docker.image}</div>
            <div style={{ color: "var(--ok)" }}>✓ container up · listening on :{provider.docker.internalPort}</div>
            <div style={{ color: "var(--fg-4)" }}>healthcheck {provider.docker.healthcheck ?? "/"} → 200 OK</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute top-3 right-3 size-7 inline-flex items-center justify-center rounded-md"
            style={{ background: "color-mix(in oklab, var(--bg-0) 70%, transparent)", color: "var(--fg-2)", border: "1px solid var(--line)" }}
          >
            <X size={14} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex items-start gap-3">
            <ProviderIcon accent={provider.accent} monogram={provider.monogram} size={40} />
            <div className="flex-1 min-w-0">
              <h3 className="text-[16px] font-semibold tracking-tight" style={{ color: "var(--fg)" }}>{provider.name}</h3>
              <p className="text-[12px] mt-0.5" style={{ color: "var(--fg-3)" }}>{provider.tagline}</p>
            </div>
          </div>

          <p className="text-[12.5px] leading-relaxed" style={{ color: "var(--fg-2)" }}>
            {provider.description}
          </p>

          <div className="flex items-center gap-1.5 flex-wrap">
            {provider.tags.map((t) => (
              <span key={t} className="px-1.5 py-0.5 rounded text-[10.5px] font-medium" style={{ background: "var(--bg-2)", color: "var(--fg-3)", border: "1px solid var(--line)" }}>
                {t}
              </span>
            ))}
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11.5px]" style={{ fontFamily: "var(--font-mono)" }}>
            <Spec k="image" v={provider.docker.image} />
            <Spec k="internal port" v={String(provider.docker.internalPort)} />
            <Spec k="suggested port" v={String(provider.docker.suggestedExternalPort)} />
            <Spec k="healthcheck" v={provider.docker.healthcheck ?? "—"} />
          </dl>

          <div className="flex items-center justify-between pt-2" style={{ borderTop: "1px solid var(--line)" }}>
            <a
              href={provider.homepage}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[12px] font-medium"
              style={{ color: "var(--violet)" }}
            >
              Homepage <ExternalLink size={11} />
            </a>
            {installed ? (
              <Button variant="outline" size="sm" disabled>
                <Check size={12} strokeWidth={3} style={{ color: "var(--ok)" }} /> Installed
              </Button>
            ) : (
              <Button size="sm" onClick={() => onInstall(provider)}>
                <Download size={12} strokeWidth={2.6} /> Install {provider.name}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// [RCF:PROTECTED]
function Spec({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <dt className="text-[10px] uppercase tracking-wider" style={{ color: "var(--fg-4)", fontFamily: "var(--font-inter)" }}>{k}</dt>
      <dd className="truncate" style={{ color: "var(--fg-2)" }} title={v}>{v}</dd>
    </div>
  );
}

/* ============================================================
   Skeleton + Empty/Error helpers
   ============================================================ */
// [RCF:PROTECTED]
function SkeletonCard() {
  return (
    <div
      className="rounded-lg p-4 flex items-start gap-3"
      style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
    >
      <Shimmer w={32} h={32} radius={8} />
      <div className="flex-1 space-y-2">
        <Shimmer w={140} h={12} radius={4} />
        <Shimmer w={220} h={10} radius={4} />
      </div>
      <Shimmer w={80} h={26} radius={6} />
    </div>
  );
}

// [RCF:PROTECTED]
function Shimmer({ w, h, radius }: { w: number; h: number; radius: number }) {
  return (
    <span
      aria-hidden
      className="block motion-safe:animate-[shimmer_1400ms_linear_infinite]"
      style={{
        width: w,
        height: h,
        borderRadius: radius,
        background: "linear-gradient(90deg, var(--bg-3) 0%, var(--bg-4) 50%, var(--bg-3) 100%)",
        backgroundSize: "200% 100%",
      }}
    />
  );
}

// [RCF:PROTECTED]
function EmptyOrError({
  icon, title, body, action,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="rounded-lg px-6 py-10 flex flex-col items-center text-center gap-3"
      style={{
        background: "var(--bg-2)",
        border: "1px dashed var(--line-strong)",
      }}
    >
      <div
        className="size-10 rounded-xl flex items-center justify-center"
        style={{ background: "var(--bg-3)", border: "1px solid var(--line)" }}
      >
        {icon}
      </div>
      <div className="space-y-1 max-w-[400px]">
        <h3 className="text-[13.5px] font-medium" style={{ color: "var(--fg)" }}>{title}</h3>
        <p className="text-[12px]" style={{ color: "var(--fg-3)" }}>{body}</p>
      </div>
      {action}
    </div>
  );
}

/* ============================================================
   VM Select Modal — for wetty installation
   ============================================================ */
// [RCF:PROTECTED]
function VmSelectModal({
  open, onClose, onSelect,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (vmId: number) => void;
}) {
  const [vms, setVms] = useState<Array<{ id: number; name: string; host: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.get<Array<{ id: number; name: string; host: string }>>("/vms")
      .then((data) => {
        setVms(Array.isArray(data) ? data : []);
        if (data.length > 0) setSelected(data[0].id);
      })
      .catch((err) => {
        console.error("Failed to load VMs:", err);
        setVms([]);
      })
      .finally(() => setLoading(false));
  }, [open]);

  useEffect(() => {
    if (!open) return;
// [RCF:PROTECTED]
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Select VM for Wetty"
      className="fixed inset-0 z-[200] flex items-center justify-center motion-safe:animate-[modalFadeIn_180ms_cubic-bezier(0.16,1,0.3,1)]"
      style={{ background: "color-mix(in oklab, var(--bg-0) 70%, transparent)", backdropFilter: "blur(6px)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative w-full max-w-[480px] mx-4 motion-safe:animate-[modalSlideIn_220ms_cubic-bezier(0.16,1,0.3,1)]"
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--line-strong)",
          borderRadius: "var(--r-lg)",
          boxShadow: "0 32px 80px -16px rgba(0,0,0,0.55)",
          overflow: "hidden",
        }}
      >
        <div className="p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-[16px] font-semibold tracking-tight" style={{ color: "var(--fg)" }}>
                Select VM for Wetty
              </h3>
              <p className="text-[12px] mt-1" style={{ color: "var(--fg-3)" }}>
                Wetty will SSH into this VM when you open the terminal.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="size-7 inline-flex items-center justify-center rounded-md"
              style={{ background: "var(--bg-2)", color: "var(--fg-2)", border: "1px solid var(--line)" }}
            >
              <X size={14} />
            </button>
          </div>

          {loading ? (
            <div className="py-8 flex items-center justify-center gap-2" style={{ color: "var(--fg-3)" }}>
              <Loader2 size={16} className="motion-safe:animate-spin" />
              <span className="text-[12px]">Loading VMs...</span>
            </div>
          ) : vms.length === 0 ? (
            <div className="py-8 text-center space-y-2">
              <p className="text-[13px]" style={{ color: "var(--fg-2)" }}>No VMs configured yet.</p>
              <p className="text-[12px]" style={{ color: "var(--fg-3)" }}>
                Add a VM in Settings → Cloud VMs first.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {vms.map((vm) => (
                <label
                  key={vm.id}
                  className="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors"
                  style={{
                    background: selected === vm.id ? "var(--violet-soft)" : "var(--bg-2)",
                    border: `1px solid ${selected === vm.id ? "var(--violet-line)" : "var(--line)"}`,
                  }}
                >
                  <input
                    type="radio"
                    name="vm"
                    value={vm.id}
                    checked={selected === vm.id}
                    onChange={() => setSelected(vm.id)}
                    className="size-4"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium truncate" style={{ color: "var(--fg)" }}>
                      {vm.name}
                    </p>
                    <p className="text-[11.5px] truncate" style={{ color: "var(--fg-3)", fontFamily: "var(--font-mono)" }}>
                      {vm.host}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2" style={{ borderTop: "1px solid var(--line)" }}>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => selected && onSelect(selected)}
              disabled={!selected || vms.length === 0}
            >
              Install Wetty
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

