"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { AgentGatesPanel } from "@/components/agent-gates-panel";
import { AgentSafetyPanel } from "@/components/agent-safety-panel";
import { AgentExtractionPanel } from "@/components/agent-extraction-panel";
import { AgentMemoryPanel } from "@/components/agent-memory-panel";
import { AgentActivityTab } from "@/components/agent-activity-tab";
import { ArrowLeft, Bot, Shield, Database, Activity, Lock, Zap } from "lucide-react";
import Link from "next/link";

interface Agent {
  id: number;
  name: string;
  role: string;
  model: string;
  system_prompt: string;
  llm_provider_id: number | null;
  port: number | null;
  status: string;
}

type TabId = "overview" | "memory" | "gates" | "safety" | "activity";

export default function AgentDetailsPage() {
  const { id } = useParams();
  const router = useRouter();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [busy, setBusy] = useState(false);

  const loadAgent = async () => {
    try {
      const data = await api.get<Agent>(`/agents/${id}`);
      setAgent(data);
    } catch (err) {
      console.error("Failed to load agent", err);
    }
  };

  useEffect(() => {
    loadAgent();
  }, [id]);

  const handleStart = async () => {
    if (!agent) return;
    setBusy(true);
    try {
      await api.post(`/agents/${agent.id}/start`);
      await loadAgent();
    } finally {
      setBusy(false);
    }
  };

  const handleStop = async () => {
    if (!agent) return;
    setBusy(true);
    try {
      await api.post(`/agents/${agent.id}/stop`);
      await loadAgent();
    } finally {
      setBusy(false);
    }
  };

  if (!agent) return <div className="p-8 text-muted-foreground">Loading agent...</div>;

  const isRunning = ["running", "active"].includes(agent.status);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/agents" className="p-2 hover:bg-surface-2 rounded-lg transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="p-3 rounded-2xl bg-accent/10 text-accent">
            <Bot size={32} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{agent.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-widest ${
                isRunning ? "bg-green-500/10 text-green-500 border border-green-500/20" : "bg-zinc-500/10 text-zinc-500 border border-zinc-500/20"
              }`}>
                {agent.status}
              </span>
              <span className="text-xs text-muted-foreground">{agent.role}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Button variant="outline" onClick={handleStop} disabled={busy}>Stop Agent</Button>
          ) : (
            <Button onClick={handleStart} disabled={busy}>Start Agent</Button>
          )}
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-1 border-b border-border/50 pb-px overflow-x-auto">
        {[
          { id: "overview", label: "Overview", icon: Zap },
          { id: "memory", label: "Memory", icon: Database },
          { id: "gates", label: "Gates", icon: Lock },
          { id: "safety", label: "Safety", icon: Shield },
          { id: "activity", label: "Activity", icon: Activity },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabId)}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-all relative whitespace-nowrap ${
                isActive ? "text-accent" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon size={16} />
              {tab.label}
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent shadow-[0_0_8px_rgba(var(--color-accent-rgb),0.5)]" />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-300">
            <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-surface-1 border border-border/50">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-4">Configuration</h3>
                    <div className="space-y-4">
                        <div>
                            <p className="text-[11px] text-muted-foreground uppercase">Base Model</p>
                            <p className="text-sm font-mono mt-1">{agent.model}</p>
                        </div>
                        {agent.port && (
                            <div>
                                <p className="text-[11px] text-muted-foreground uppercase">External Port</p>
                                <p className="text-sm font-mono mt-1">:{agent.port}</p>
                            </div>
                        )}
                    </div>
                </div>
                <div className="p-6 rounded-2xl bg-surface-1 border border-border/50">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-4">System Prompt</h3>
                    <div className="p-4 rounded-xl bg-surface-2 border border-border/30 text-sm font-mono leading-relaxed whitespace-pre-wrap">
                        {agent.system_prompt || "No system prompt configured."}
                    </div>
                </div>
            </div>
            <div className="space-y-6">
                <div className="p-6 rounded-2xl bg-surface-1 border border-border/50">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-4">Agentic Stats</h3>
                    <AgenticStatsPanel agentId={agent.id} />
                </div>
            </div>
          </div>
        )}

        {activeTab === "memory" && <AgentMemoryPanel agentId={agent.id} />}
        
        {activeTab === "gates" && (
          <AgentGatesPanel agentId={agent.id} providerId={agent.llm_provider_id} />
        )}

        {activeTab === "safety" && (
          <div className="space-y-8 animate-in fade-in duration-300">
            <AgentSafetyPanel agentId={agent.id} providerId={agent.llm_provider_id} />
            <div className="pt-8 border-t border-border/50">
                <AgentExtractionPanel agentId={agent.id} providerId={agent.llm_provider_id} />
            </div>
          </div>
        )}

        {activeTab === "activity" && <AgentActivityTab agentId={agent.id} />}
      </div>
    </div>
  );
}

/* ── Agentic Stats (real data) ─────────────────────────────────────── */
function AgenticStatsPanel({ agentId }: { agentId: number }) {
  const [stats, setStats] = useState<{
    uptime_display: string;
    tokens_display: string;
    total_tasks: number;
    gate_decisions: number;
  } | null>(null);

  useEffect(() => {
    api.get<any>(`/agents/${agentId}/stats`)
      .then(setStats)
      .catch(() => setStats(null));
  }, [agentId]);

  if (!stats) {
    return (
      <div className="grid grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="p-4 rounded-xl bg-surface-2 border border-border/30 animate-pulse">
            <div className="h-3 w-16 bg-border/30 rounded mb-2" />
            <div className="h-6 w-12 bg-border/30 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const items = [
    { label: "Uptime", value: stats.uptime_display },
    { label: "Token Usage", value: stats.tokens_display },
    { label: "Tasks Done", value: String(stats.total_tasks) },
    { label: "Gate Decisions", value: String(stats.gate_decisions) },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {items.map((item) => (
        <div key={item.label} className="p-4 rounded-xl bg-surface-2 border border-border/30">
          <p className="text-[10px] text-muted-foreground uppercase">{item.label}</p>
          <p className="text-xl font-bold mt-1">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
