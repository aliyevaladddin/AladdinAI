// NOTICE: This file is protected under RCF-PL




"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";


interface CheckState {
  enabled: boolean;
  model: string | null;
}


interface SafetyConfig {
  default_safety_model: string | null;
  safety_block_response: string | null;
  safety: Record<string, CheckState>;
}


interface SafetyLogEntry {
  _id: string;
  gate: string;
  model: string | null;
  decision: string;
  reason: string;
  latency_ms: number;
  input_preview: string;
  created_at: string;
}

const CHECK_LABELS: Record<string, { title: string; help: string }> = {
  ingress: {
    title: "Input moderation",
    help: "Classify user input before the agent runs. Blocks jailbreaks and disallowed content.",
  },
  egress: {
    title: "Output moderation",
    help: "Classify the agent's reply before it is returned. Blocks unsafe outputs.",
  },
  pii: {
    title: "PII redaction",
    help: "Detect and redact personal data (emails, phones, names…) before facts hit memory.",
  },
};


export function AgentSafetyPanel({
  agentId,
  providerId,
}: {
  agentId: number;
  providerId: number | null;
}) {
  const [cfg, setCfg] = useState<SafetyConfig | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [blockDraft, setBlockDraft] = useState("");
  const [showLog, setShowLog] = useState(false);
  const [logEntries, setLogEntries] = useState<SafetyLogEntry[]>([]);
  const [logLoading, setLogLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const c = await api.get<SafetyConfig>(`/agents/${agentId}/safety`);
        if (cancelled) return;
        setCfg(c);
        setBlockDraft(c.safety_block_response ?? "");
      } catch (e) {
        console.error(e);
      }
      if (providerId) {
        try {
          const r = await api.get<{ models: string[] }>(
            `/providers/${providerId}/models`,
          );
          if (cancelled) return;
          // De-duplicate models to avoid React 'same key' warning
          const uniqueModels = Array.from(new Set(r.models || []));
          setModels(uniqueModels);
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


  const save = async (next: SafetyConfig) => {
    setSaving(true);
    try {
      const updated = await api.patch<SafetyConfig>(
        `/agents/${agentId}/safety`,
        {
          default_safety_model: next.default_safety_model,
          safety_block_response: next.safety_block_response,
          safety: next.safety,
        },
      );
      setCfg(updated);
    } catch (e) {
      console.error(e);
      alert("Failed to save safety config");
    } finally {
      setSaving(false);
    }
  };


  const toggleCheck = (name: string, enabled: boolean) => {
    if (!cfg) return;
    const next = {
      ...cfg,
      safety: {
        ...cfg.safety,
        [name]: { ...cfg.safety[name], enabled },
      },
    };
    setCfg(next);
    save(next);
  };


  const setCheckModel = (name: string, model: string | null) => {
    if (!cfg) return;
    const next = {
      ...cfg,
      safety: {
        ...cfg.safety,
        [name]: { ...cfg.safety[name], model },
      },
    };
    setCfg(next);
    save(next);
  };


  const setDefaultModel = (model: string | null) => {
    if (!cfg) return;
    const next = { ...cfg, default_safety_model: model };
    setCfg(next);
    save(next);
  };


  const commitBlockResponse = () => {
    if (!cfg) return;
    if ((cfg.safety_block_response ?? "") === blockDraft) return;
    save({ ...cfg, safety_block_response: blockDraft });
  };


  const applyRecommended = async () => {
    if (!cfg) return;
    setSaving(true);
    try {
      const r = await api.get<{
        recommendations: Record<string, string | null>;
        catalog_size: number;
      }>(`/agents/${agentId}/safety/recommendations`);

      const recs = r.recommendations ?? {};
      const applied: string[] = [];
      const skipped: string[] = [];
      const nextSafety: Record<string, CheckState> = { ...cfg.safety };

      for (const name of Object.keys(CHECK_LABELS)) {
        const recModel = recs[name];
        if (recModel) {
          nextSafety[name] = { enabled: true, model: recModel };
          applied.push(`${name} → ${recModel}`);
        } else {
          skipped.push(name);
        }
      }

      const next: SafetyConfig = { ...cfg, safety: nextSafety };
      await save(next);

      if (applied.length === 0) {
        toast.error("No recommendations match this provider's catalog.", {
          description: r.catalog_size
            ? `Provider exposes ${r.catalog_size} models, none matched.`
            : "Connect the provider to populate the model catalog.",
        });
      } else {
        toast.success(`Applied ${applied.length} recommendation(s)`, {
          description: applied.join("\n"),
        });
        if (skipped.length) {
          toast.warning(`No match for: ${skipped.join(", ")}`);
        }
      }
    } catch (e) {
      console.error(e);
      toast.error("Failed to load recommendations");
    } finally {
      setSaving(false);
    }
  };


  const loadLog = async () => {
    setShowLog(true);
    setLogLoading(true);
    try {
      const r = await api.get<SafetyLogEntry[]>(
        `/agents/${agentId}/safety/log?limit=50`,
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
      <p className="text-xs text-muted-foreground mt-2">Loading safety…</p>
    );
  }

  return (
    <div className="mt-4 border-t border-border pt-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Safety</p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={applyRecommended}
            disabled={saving || !providerId}
            title={
              providerId
                ? "Apply recommended NIM models for this provider"
                : "Attach an LLM provider to enable recommendations"
            }
          >
            Apply recommended
          </Button>
          <span className="text-xs text-muted-foreground">
            {saving ? "Saving…" : "Auto-saves"}
          </span>
        </div>
      </div>

      <div>
        <label className="block text-xs text-muted-foreground mb-1">
          Default safety model (used when a check has no model selected)
        </label>
        <select
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
          value={cfg.default_safety_model ?? ""}
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

      <div>
        <label className="block text-xs text-muted-foreground mb-1">
          Block response (returned when ingress/egress blocks a turn)
        </label>
        <input
          type="text"
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
          placeholder="I can't help with that."
          value={blockDraft}
          onChange={(e) => setBlockDraft(e.target.value)}
          onBlur={commitBlockResponse}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.currentTarget.blur();
            }
          }}
        />
      </div>

      <div className="space-y-3">
        {Object.entries(CHECK_LABELS).map(([name, meta]) => {
          const state = cfg.safety[name] ?? { enabled: false, model: null };
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
                    onChange={(e) => toggleCheck(name, e.target.checked)}
                  />
                  <div className="w-9 h-5 bg-zinc-700 peer-checked:bg-green-500 rounded-full relative transition">
                    <div
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${state.enabled ? "translate-x-4" : ""
                        }`}
                    />
                  </div>
                </label>
              </div>
              <select
                className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
                value={state.model ?? ""}
                onChange={(e) => setCheckModel(name, e.target.value || null)}
                disabled={!state.enabled}
              >
                <option value="">
                  — use default ({cfg.default_safety_model ?? "none"}) —
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
                        className={`px-1.5 rounded ${e.decision === "block"
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
