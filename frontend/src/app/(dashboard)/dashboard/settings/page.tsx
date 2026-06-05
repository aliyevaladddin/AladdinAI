"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProvidersSettings } from "@/components/settings/ProvidersSettings";
import { VmsSettings } from "@/components/settings/VmsSettings";
import { MongoSettings } from "@/components/settings/MongoSettings";
import { BentoSettings } from "@/components/settings/BentoSettings";
import { RouterSettings } from "@/components/settings/RouterSettings";
import { AppearanceSettings } from "@/components/settings/AppearanceSettings";
import { StorageSettings } from "@/components/settings/StorageSettings";
import { Cpu, Cloud, Database, Server, Network, Palette, HardDrive } from "lucide-react";

type TabId = "appearance" | "storage" | "providers" | "vms" | "mongo" | "bento" | "router";

const tabs: { id: TabId; label: string; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "storage", label: "Storage", icon: HardDrive },
  { id: "providers", label: "LLM Providers", icon: Cpu },
  { id: "vms", label: "Cloud VMs", icon: Cloud },
  { id: "mongo", label: "MongoDB", icon: Database },
  { id: "bento", label: "BentoML", icon: Server },
  { id: "router", label: "Routing", icon: Network },
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
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left ${
                  isActive
                    ? "bg-[var(--color-surface-2)] text-[var(--color-fg)] border border-[var(--color-border-strong)]"
                    : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface-2)] hover:text-[var(--color-fg)] border border-transparent"
                }`}
              >
                <Icon size={15} className={isActive ? "text-[var(--color-accent)]" : "opacity-50"} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Content panel — fills remaining space */}
        <div className="flex-1 min-w-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 overflow-y-auto">
          {activeTab === "appearance" && <AppearanceSettings />}
          {activeTab === "storage" && <StorageSettings />}
          {activeTab === "providers" && <ProvidersSettings />}
          {activeTab === "vms" && <VmsSettings />}
          {activeTab === "mongo" && <MongoSettings />}
          {activeTab === "bento" && <BentoSettings />}
          {activeTab === "router" && <RouterSettings />}
        </div>
      </div>
    </div>
  );
}
