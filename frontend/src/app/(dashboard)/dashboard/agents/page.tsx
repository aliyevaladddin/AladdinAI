"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { AgentGatesPanel } from "@/components/agent-gates-panel";
import { AgentSafetyPanel } from "@/components/agent-safety-panel";
import { AgentExtractionPanel } from "@/components/agent-extraction-panel";
import { AgentMemoryPanel } from "@/components/agent-memory-panel";
import { ChevronRight, Trash2 } from "lucide-react";

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

interface Provider {
  id: number;
  name: string;
  type: string;
}

const STATUS_COLORS: Record<string, string> = {
  running: "bg-green-500/20 text-green-400",
  active: "bg-green-500/20 text-green-400",
  stopped: "bg-zinc-500/20 text-zinc-400",
  idle: "bg-zinc-500/20 text-zinc-400",
  error: "bg-red-500/20 text-red-400",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [openGates, setOpenGates] = useState<number | null>(null);
  const [openSafety, setOpenSafety] = useState<number | null>(null);
  const [openExtraction, setOpenExtraction] = useState<number | null>(null);
  const [openMemory, setOpenMemory] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [a, p] = await Promise.all([
        api.get<Agent[]>("/agents"),
        api.get<Provider[]>("/providers").catch(() => [] as Provider[]),
      ]);
      setAgents(a);
      setProviders(p);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const providerName = (id: number | null) =>
    id ? providers.find((p) => p.id === id)?.name ?? `#${id}` : "—";

  const handleStart = async (id: number) => {
    setBusyId(id);
    try {
      await api.post(`/agents/${id}/start`);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  const handleStop = async (id: number) => {
    setBusyId(id);
    try {
      await api.post(`/agents/${id}/stop`);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this agent?")) return;
    setBusyId(id);
    try {
      await api.delete(`/agents/${id}`);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Agents</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {agents.length} total
          </p>
        </div>
        <Link href="/dashboard/agents/new">
          <Button>New Agent</Button>
        </Link>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : agents.length === 0 ? (
        <div className="rounded-lg border border-border p-8 text-center">
          <p className="text-muted-foreground text-sm mb-4">
            No agents yet. Create one to start orchestrating tasks.
          </p>
          <Link href="/dashboard/agents/new">
            <Button>Create your first agent</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {agents.map((a) => {
            const isRunning = ["running", "active"].includes(a.status);
            const busy = busyId === a.id;
            return (
              <div
                key={a.id}
                className="rounded-2xl border border-border/50 p-5 bg-surface-1 transition-all hover:border-accent/30 hover:shadow-xl hover:shadow-accent/5 group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <Link 
                        href={`/dashboard/agents/${a.id}`}
                        className="text-lg font-bold hover:text-accent transition-colors flex items-center gap-2"
                      >
                        {a.name}
                        <ChevronRight size={16} className="opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                      </Link>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-widest border ${
                          STATUS_COLORS[a.status] ??
                          "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                        }`}
                      >
                        {a.status}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full border border-border bg-muted text-muted-foreground uppercase font-bold tracking-tighter">
                        {a.role}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1.5 flex items-center gap-2">
                      <span className="font-medium text-foreground/70">{a.model}</span>
                      <span className="w-1 h-1 rounded-full bg-border" />
                      <span>{providerName(a.llm_provider_id)}</span>
                      {a.port && (
                        <>
                           <span className="w-1 h-1 rounded-full bg-border" />
                           <span className="font-mono text-xs">:{a.port}</span>
                        </>
                      )}
                    </p>
                    {a.system_prompt && (
                      <p className="text-xs text-muted-foreground mt-3 line-clamp-1 italic opacity-60">
                        &ldquo;{a.system_prompt}&rdquo;
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isRunning ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => handleStop(a.id)}
                        className="h-9 px-4"
                      >
                        Stop
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => handleStart(a.id)}
                        className="h-9 px-4 shadow-lg shadow-accent/20"
                      >
                        Start
                      </Button>
                    )}
                    
                    <Link href={`/dashboard/agents/${a.id}`}>
                        <Button variant="outline" size="sm" className="h-9 px-4">
                            Configure
                        </Button>
                    </Link>

                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busy}
                      onClick={() => handleDelete(a.id)}
                      className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive transition-colors"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
