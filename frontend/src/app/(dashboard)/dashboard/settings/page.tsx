// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProvidersSettings } from "@/components/settings/ProvidersSettings";
import { VmsSettings } from "@/components/settings/VmsSettings";
import { MongoSettings } from "@/components/settings/MongoSettings";
import { BentoSettings } from "@/components/settings/BentoSettings";
import { RouterSettings } from "@/components/settings/RouterSettings";
import { Button } from "@/components/ui/button";
import { AppearanceSettings } from "@/components/settings/AppearanceSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { SecuritySettings } from "@/components/settings/SecuritySettings";
import { ShortcutsSettings } from "@/components/settings/ShortcutsSettings";
import { ObservabilitySettings } from "@/components/settings/ObservabilitySettings";
import { TrainingSettings } from "@/components/settings/TrainingSettings";
import { Cpu, Cloud, Database, Server, Network, Palette, HardDrive, Shield, Keyboard, Activity, FlaskConical, Terminal } from "lucide-react";


type TabId = "appearance" | "storage" | "shortcuts" | "providers" | "vms" | "mongo" | "bento" | "router" | "security" | "observability" | "training" | "terminal";

const tabs: { id: TabId; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "shortcuts", label: "Shortcuts & Commands", icon: Keyboard },
  { id: "storage", label: "Storage", icon: HardDrive },
  { id: "providers", label: "LLM Providers", icon: Cpu },
  { id: "vms", label: "Cloud VMs", icon: Cloud },
  { id: "mongo", label: "MongoDB", icon: Database },
  { id: "bento", label: "BentoML", icon: Server },
  { id: "router", label: "Routing", icon: Network },
  { id: "security", label: "Security & Safety", icon: Shield },
  { id: "observability", label: "Observability", icon: Activity },
  { id: "training", label: "Training", icon: FlaskConical },
  { id: "terminal", label: "Terminal", icon: Terminal },
];


const VALID_TABS = new Set<TabId>(tabs.map((t) => t.id));

export default function SettingsPage() {
  const params = useSearchParams();
  const router = useRouter();

  // Legacy deep-link: /settings?tab=terminal now lives at /settings/terminal.
  useEffect(() => {
    if (params.get("tab") === "terminal") {
      router.replace("/dashboard/settings/terminal");
    }
  }, [params, router]);


  const initial = ((): TabId => {
    const raw = params.get("tab");
    return raw && VALID_TABS.has(raw as TabId) ? (raw as TabId) : "appearance";
  })();
  const [activeTab, setActiveTab] = useState<TabId>(initial);

  // Keep the URL in sync when the user clicks a sidebar entry — but only
  // shallow-update so we don't refetch on every tab change.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (url.searchParams.get("tab") !== activeTab) {
      url.searchParams.set("tab", activeTab);
      window.history.replaceState({}, "", url.toString());
    }
  }, [activeTab]);

  return (
    <div className="h-full flex flex-col">
      {/* Page title */}
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-[var(--color-fg)]">Settings</h1>
        <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">
          Infrastructure and orchestration configuration
        </p>
      </div>

      <div className="flex gap-5 flex-1 min-h-0">
        {/* Sidebar nav */}
        <nav className="w-52 shrink-0 space-y-0.5">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left ${isActive
                    ? "bg-[var(--color-surface-2)] text-[var(--color-fg)] border border-[var(--color-border-strong)]"
                    : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-fg)] border border-transparent"
                  }`}
              >
                <Icon size={15} className={isActive ? "text-[var(--color-accent)]" : "opacity-50"} />
                {tab.label}
                {tab.id === "terminal" && (
                  <span
                    className="ml-auto text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
                    style={{ background: "var(--violet-soft, rgba(139,92,246,.15))", color: "var(--violet, #8b5cf6)" }}
                  >
                    Beta
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Content panel — fills remaining space */}
        <div className="flex-1 min-w-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 overflow-y-auto">
          {activeTab === "appearance" && <AppearanceSettings />}
          {activeTab === "shortcuts" && <ShortcutsSettings />}
          {activeTab === "storage" && <StorageSettings />}
          {activeTab === "providers" && <ProvidersSettings />}
          {activeTab === "vms" && <VmsSettings />}
          {activeTab === "mongo" && <MongoSettings />}
          {activeTab === "bento" && <BentoSettings />}
          {activeTab === "router" && <RouterSettings />}
          {activeTab === "security" && <SecuritySettings />}
          {activeTab === "observability" && <ObservabilitySettings />}
          {activeTab === "training" && <TrainingSettings />}
          {activeTab === "terminal" && <TerminalSettingsTeaser />}

        </div>
      </div>
    </div>
  );
}

/**
 * Beta teaser for the Terminal settings — the full UI lives at
 * /dashboard/settings/terminal (marketplace, install stepper, sessions).
 * Shown inside the main Settings page until the terminal feature graduates
 * from beta and is embedded here directly.
 */
function TerminalSettingsTeaser() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-start gap-4 max-w-md">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-[var(--color-fg)]">Terminal Providers</h2>
        <span
          className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded"
          style={{ background: "var(--violet-soft, rgba(139,92,246,.15))", color: "var(--violet, #8b5cf6)" }}
        >
          Beta
        </span>
      </div>
      <p className="text-xs leading-relaxed text-[var(--color-fg-muted)]">
        Install pluggable web terminals (ttyd, gotty and more) as isolated
        containers, manage sessions and SSH proxies. Powered by the native C
        terminal daemon with an automatic Python PTY fallback.
      </p>
      <Button onClick={() => router.push("/dashboard/settings/terminal")}>
        <Terminal size={13} strokeWidth={2.4} />
        Open Terminal Settings
      </Button>
    </div>
  );
}
