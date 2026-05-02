"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

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
                className="rounded-lg border border-border p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium truncate">{a.name}</p>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          STATUS_COLORS[a.status] ??
                          "bg-zinc-500/20 text-zinc-400"
                        }`}
                      >
                        {a.status}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                        {a.role}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {a.model} · {providerName(a.llm_provider_id)}
                      {a.port ? ` · :${a.port}` : ""}
                    </p>
                    {a.system_prompt && (
                      <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                        {a.system_prompt}
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
                      >
                        Stop
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => handleStart(a.id)}
                      >
                        Start
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={busy}
                      onClick={() => handleDelete(a.id)}
                    >
                      Delete
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
