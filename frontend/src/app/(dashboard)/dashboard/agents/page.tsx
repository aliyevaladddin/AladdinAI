"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface Agent {
  id: number;
  name: string;
  role: string;
  model: string;
  status: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);

  const load = () => api.get<Agent[]>("/agents").then(setAgents);
  useEffect(() => { load(); }, []);

  const handleToggle = async (agent: Agent) => {
    const action = agent.status === "running" ? "stop" : "start";
    await api.post(`/agents/${agent.id}/${action}`);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this agent?")) return;
    await api.delete(`/agents/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">AI Agents</h2>
        <Link href="/dashboard/agents/new">
          <Button>Create Agent</Button>
        </Link>
      </div>

      <div className="space-y-3">
        {agents.map((a) => (
          <div key={a.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{a.name}</p>
              <p className="text-sm text-muted-foreground">{a.role} — {a.model}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded ${a.status === "running" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                {a.status}
              </span>
              <Button variant="outline" size="sm" onClick={() => handleToggle(a)}>
                {a.status === "running" ? "Stop" : "Start"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(a.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {agents.length === 0 && <p className="text-muted-foreground text-sm">No agents created yet.</p>}
      </div>
    </div>
  );
}
