"use client";

import { useState } from "react";
import { Zap, Webhook, Network, Clock } from "lucide-react";
import { AgentTriggersPanel } from "@/components/agent-triggers-panel";
import { RouterSettings } from "@/components/settings/RouterSettings";
import { WebhooksPanel } from "@/components/settings/WebhooksPanel";

type TabId = "triggers" | "webhooks" | "router";

const tabs: { id: TabId; label: string; icon: any; desc: string }[] = [
  {
    id: "triggers",
    label: "Triggers",
    icon: Clock,
    desc: "Schedule recurring tasks and fan them out to agents",
  },
  {
    id: "webhooks",
    label: "Webhooks",
    icon: Webhook,
    desc: "Send real-time events to external systems on platform events",
  },
  {
    id: "router",
    label: "Router Rules",
    icon: Network,
    desc: "Route incoming messages to the right agent by keyword or AI classification",
  },
];

export default function AutomationsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("triggers");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div
          className="mt-1 w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
        >
          <Zap size={20} />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Automations</h2>
          <p className="text-sm mt-1" style={{ color: "var(--color-fg-muted)" }}>
            Everything that runs automatically — triggers, webhooks, and routing rules.
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div
        className="flex items-center gap-1 p-1 rounded-xl w-fit"
        style={{ background: "var(--color-surface-2)", border: "1px solid var(--color-border)" }}
      >
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all"
              style={{
                background: active ? "var(--color-surface)" : "transparent",
                color: active ? "var(--color-fg)" : "var(--color-fg-muted)",
                boxShadow: active ? "0 1px 4px rgba(0,0,0,0.15)" : "none",
              }}
            >
              <Icon size={14} className={active ? "text-[var(--color-accent)]" : ""} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab description */}
      <p className="text-xs" style={{ color: "var(--color-fg-subtle)" }}>
        {tabs.find((t) => t.id === activeTab)?.desc}
      </p>

      {/* Tab content — each section is self-contained */}
      {activeTab === "triggers" && <AgentTriggersPanel />}
      {activeTab === "webhooks" && <WebhooksPanel />}
      {activeTab === "router" && <RouterSettings />}
    </div>
  );
}
