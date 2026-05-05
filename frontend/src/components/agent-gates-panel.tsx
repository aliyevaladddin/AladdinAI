"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface GateState {
  enabled: boolean;
  model: string | null;
}

interface GatesConfig {
  default_gate_model: string | null;
  gates: Record<string, GateState>;
}

interface GateLogEntry {
  _id: string;
  gate: string;
  model: string | null;
  decision: string;
  reason: string;
  latency_ms: number;
  input_preview: string;
  created_at: string;
}

const GATE_LABELS: Record<string, { title: string; help: string }> = {
  handoff: {
    title: "Handoff filter",
    help: "Cleans context before delegate / ask_agent — strips irrelevant chatter.",
  },
  memory_write: {
    title: "Memory write classifier",
    help: "Decides if a fact is worth saving via remember.",
  },
  recall_rerank: {
    title: "Recall reranker",
    help: "Reorders vector-search results by semantic relevance.",
  },
};

export function AgentGatesPanel({
  agentId,
  providerId,
}: {
  agentId: number;
  providerId: number | null;
}) {
  const [cfg, setCfg] = useState<GatesConfig | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const [logEntries, setLogEntries] = useState<GateLogEntry[]>([]);
  const [logLoading, setLogLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const c = await api.get<GatesConfig>(`/agents/${agentId}/gates`);
        if (cancelled) return;
        setCfg(c);
      } catch (e) {
        console.error(e);
      }
      if (providerId) {
        try {
          const r = await api.get<{ models: string[] }>(
            `/providers/${providerId}/models`,
          );
          if (cancelled) return;
          setModels(r.models || []);
        } catch (e) {
          console.error(e);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [agentId, providerId]);

  const save = async (next: GatesConfig) => {
    setSaving(true);
    try {
      const updated = await api.patch<GatesConfig>(
        `/agents/${agentId}/gates`,
        {
          default_gate_model: next.default_gate_model,
          gates: next.gates,
        },
      );
      setCfg(updated);
    } catch (e) {
      console.error(e);
      alert("Failed to save gates config");
    } finally {
      setSaving(false);
    }
  };

  const toggleGate = (name: string, enabled: boolean) => {
    if (!cfg) return;
    const next = {
      ...cfg,
      gates: {
        ...cfg.gates,
        [name]: { ...cfg.gates[name], enabled },
      },
    };
    setCfg(next);
    save(next);
  };

  const setGateModel = (name: string, model: string | null) => {
    if (!cfg) return;
    const next = {
      ...cfg,
      gates: {
        ...cfg.gates,
        [name]: { ...cfg.gates[name], model },
      },
    };
    setCfg(next);
    save(next);
  };

  const setDefaultModel = (model: string | null) => {
    if (!cfg) return;
    const next = { ...cfg, default_gate_model: model };
    setCfg(next);
    save(next);
  };

  const loadLog = async () => {
    setShowLog(true);
    setLogLoading(true);
    try {
      const r = await api.get<GateLogEntry[]>(
        `/agents/${agentId}/gates/log?limit=50`,
      );
      setLogEntries(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLogLoading(false);
    }
  };

  if (!cfg) {
    return (
      <p className="text-xs text-muted-foreground mt-2">Loading gates…</p>
    );
  }

  return (
    <div className="mt-4 border-t border-border pt-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Gates</p>
        <span className="text-xs text-muted-foreground">
          {saving ? "Saving…" : "Auto-saves"}
        </span>
      </div>

      <div>
        <label className="block text-xs text-muted-foreground mb-1">
          Default gate model (used when a gate has no model selected)
        </label>
        <select
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
          value={cfg.default_gate_model ?? ""}
          onChange={(e) => setDefaultModel(e.target.value || null)}
        >
          <option value="">— none —</option>
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-3">
        {Object.entries(GATE_LABELS).map(([name, meta]) => {
          const state = cfg.gates[name] ?? { enabled: false, model: null };
          return (
            <div
              key={name}
              className="rounded border border-border p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{meta.title}</p>
                  <p className="text-xs text-muted-foreground">{meta.help}</p>
                </div>
                <label className="inline-flex items-center cursor-pointer shrink-0">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={state.enabled}
                    onChange={(e) => toggleGate(name, e.target.checked)}
                  />
                  <div className="w-9 h-5 bg-zinc-700 peer-checked:bg-green-500 rounded-full relative transition">
                    <div
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${
                        state.enabled ? "translate-x-4" : ""
                      }`}
                    />
                  </div>
                </label>
              </div>
              <select
                className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
                value={state.model ?? ""}
                onChange={(e) => setGateModel(name, e.target.value || null)}
                disabled={!state.enabled}
              >
                <option value="">
                  — use default ({cfg.default_gate_model ?? "none"}) —
                </option>
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>

      <div>
        {!showLog ? (
          <Button variant="outline" size="sm" onClick={loadLog}>
            View recent decisions
          </Button>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium">Recent decisions</p>
              <Button variant="outline" size="sm" onClick={loadLog}>
                Refresh
              </Button>
            </div>
            {logLoading ? (
              <p className="text-xs text-muted-foreground">Loading…</p>
            ) : logEntries.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No decisions logged yet.
              </p>
            ) : (
              <ul className="space-y-1 max-h-64 overflow-y-auto">
                {logEntries.map((e) => (
                  <li
                    key={e._id}
                    className="text-xs border border-border rounded px-2 py-1"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{e.gate}</span>
                      <span
                        className={`px-1.5 rounded ${
                          e.decision === "block"
                            ? "bg-red-500/20 text-red-400"
                            : e.decision === "rerank"
                              ? "bg-blue-500/20 text-blue-400"
                              : "bg-zinc-500/20 text-zinc-400"
                        }`}
                      >
                        {e.decision}
                      </span>
                      <span className="text-muted-foreground">
                        {e.latency_ms}ms
                      </span>
                    </div>
                    {e.reason && (
                      <p className="text-muted-foreground mt-0.5 line-clamp-2">
                        {e.reason}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
