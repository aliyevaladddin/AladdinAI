"use client";

import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface RouterCfg {
  id: number;
  name: string;
  type: string;
  config: Record<string, unknown>;
  is_active: boolean;
}

interface Agent {
  id: number;
  name: string;
  role: string;
}

const TYPE_INFO: Record<string, { label: string; description: string }> = {
  keyword: {
    label: "Keyword Router",
    description: "Routes messages to agents based on matching keywords.",
  },
  llm_classifier: {
    label: "LLM Classifier",
    description: "Uses an LLM to classify the intent and route to the right agent.",
  },
  hybrid: {
    label: "Hybrid",
    description: "Tries keyword matching first, falls back to LLM classification.",
  },
};

export default function RouterPage() {
  const [configs, setConfigs] = useState<RouterCfg[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState("keyword");
  const [formName, setFormName] = useState("");
  // keyword rules: [{keywords: [], agent_id: ""}]
  const [rules, setRules] = useState([{ keywords: "", agent_id: "" }]);
  // llm_classifier: fallback agent
  const [fallbackAgentId, setFallbackAgentId] = useState("");

  const load = () => api.get<RouterCfg[]>("/router").then(setConfigs);
  useEffect(() => {
    load();
    api.get<Agent[]>("/agents").then(setAgents);
  }, []);

  const buildConfig = () => {
    if (formType === "keyword" || formType === "hybrid") {
      return {
        rules: rules.map((r: { keywords: string; agent_id: string }) => ({
          keywords: r.keywords.split(",").map((k: string) => k.trim()).filter(Boolean),
          agent_id: r.agent_id ? parseInt(r.agent_id) : null,
        })),
        fallback_agent_id: fallbackAgentId ? parseInt(fallbackAgentId) : null,
      };
    }
    if (formType === "llm_classifier") {
      return {
        fallback_agent_id: fallbackAgentId ? parseInt(fallbackAgentId) : null,
        agents: agents.map((a: Agent) => ({ id: a.id, name: a.name, role: a.role })),
      };
    }
    return {};
  };

  const handleCreate = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    await api.post("/router", {
      name: formName,
      type: formType,
      config: buildConfig(),
      is_active: false,
    });
    setFormName("");
    setRules([{ keywords: "", agent_id: "" }]);
    setFallbackAgentId("");
    setShowForm(false);
    load();
  };

  const handleActivate = async (cfg: RouterCfg) => {
    await api.put(`/router/${cfg.id}`, { is_active: !cfg.is_active });
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this router config?")) return;
    await api.delete(`/router/${id}`);
    load();
  };

  const agentName = (id: number): string => agents.find((a: Agent) => a.id === id)?.name ?? `#${id}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Router Config</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Configure how incoming messages are routed to your AI agents
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Config"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-5 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-1">Config Name</label>
            <input
              placeholder="e.g. Main Router"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-sm font-medium mb-1">Router Type</label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(TYPE_INFO).map(([key, info]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFormType(key)}
                  className={`rounded-lg border p-3 text-left transition-colors ${
                    formType === key
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-accent"
                  }`}
                >
                  <p className="text-sm font-medium">{info.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{info.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Keyword rules */}
          {(formType === "keyword" || formType === "hybrid") && (
            <div>
              <label className="block text-sm font-medium mb-2">Routing Rules</label>
              <div className="space-y-2">
                {rules.map((rule: { keywords: string; agent_id: string }, i: number) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_auto] gap-2 items-center">
                    <input
                      placeholder="Keywords (comma-separated)"
                      value={rule.keywords}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                        const next = [...rules];
                        next[i].keywords = e.target.value;
                        setRules(next);
                      }}
                      className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    />
                    <select
                      value={rule.agent_id}
                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                        const next = [...rules];
                        next[i].agent_id = e.target.value;
                        setRules(next);
                      }}
                      className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="">Select agent...</option>
                      {agents.map((a: Agent) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    {rules.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setRules(rules.filter((_: { keywords: string; agent_id: string }, j: number) => j !== i))}
                        className="text-muted-foreground hover:text-destructive text-sm px-2"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setRules([...rules, { keywords: "", agent_id: "" }])}
                >
                  + Add Rule
                </Button>
              </div>
            </div>
          )}

          {/* LLM Classifier info */}
          {formType === "llm_classifier" && (
            <div className="rounded-md bg-blue-500/10 border border-blue-500/20 p-3 text-sm text-blue-400">
              The LLM classifier will automatically route messages using your agents&apos; roles and names.
              All {agents.length} agents will be included in the classification context.
            </div>
          )}

          {/* Fallback agent */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Fallback Agent <span className="text-muted-foreground font-normal">(when no rule matches)</span>
            </label>
            <select
              value={fallbackAgentId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setFallbackAgentId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">None</option>
              {agents.map((a: Agent) => (
                <option key={a.id} value={a.id}>{a.name} ({a.role})</option>
              ))}
            </select>
          </div>

          <Button type="submit">Create Config</Button>
        </form>
      )}

      <div className="space-y-3">
        {configs.map((c: RouterCfg) => (
          <div key={c.id} className="rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{c.name}</p>
                <p className="text-sm text-muted-foreground">
                  {TYPE_INFO[c.type]?.label ?? c.type}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded ${c.is_active ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                  {c.is_active ? "Active" : "Inactive"}
                </span>
                <Button variant="outline" size="sm" onClick={() => handleActivate(c)}>
                  {c.is_active ? "Deactivate" : "Activate"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)}>
                  Delete
                </Button>
              </div>
            </div>

            {/* Config preview */}
            {Boolean(c.config.rules) && Array.isArray(c.config.rules) && (c.config.rules as { keywords: string[]; agent_id: number }[]).length > 0 && (
              <div className="text-xs space-y-1">
                {(c.config.rules as { keywords: string[]; agent_id: number }[]).map((r, i) => (
                  <div key={i} className="flex items-center gap-2 text-muted-foreground">
                    <span className="font-mono bg-muted px-1.5 py-0.5 rounded">
                      {Array.isArray(r.keywords) ? r.keywords.join(", ") : String(r.keywords)}
                    </span>
                    <span>→</span>
                    <span>{agentName(r.agent_id)}</span>
                  </div>
                ))}
              </div>
            )}
            {Boolean(c.config.fallback_agent_id) && (
              <p className="text-xs text-muted-foreground">
                Fallback: {agentName(c.config.fallback_agent_id as number)}
              </p>
            )}
          </div>
        ))}
        {configs.length === 0 && (
          <p className="text-muted-foreground text-sm">No router configs yet.</p>
        )}
      </div>
    </div>
  );
}
