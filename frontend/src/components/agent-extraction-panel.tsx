// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";


interface ExtractionConfig {
  enabled: boolean;
  model: string | null;
  max_facts: number | null;
}


export function AgentExtractionPanel({
  agentId,
  providerId,
}: {
  agentId: number;
  providerId: number | null;
}) {
  const [cfg, setCfg] = useState<ExtractionConfig | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [maxFactsDraft, setMaxFactsDraft] = useState<string>("5");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const c = await api.get<ExtractionConfig>(`/agents/${agentId}/extraction`);
        if (cancelled) return;
        setCfg(c);
        setMaxFactsDraft(String(c.max_facts ?? 5));
      } catch (e) {
        console.error(e);
      }
      if (providerId) {
        try {
          const r = await api.get<{ models: string[] }>(
            `/providers/${providerId}/models`,
          );
          if (cancelled) return;
          setModels(Array.from(new Set(r.models || [])));
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


  const save = async (patch: Partial<ExtractionConfig>) => {
    setSaving(true);
    try {
      const updated = await api.patch<ExtractionConfig>(
        `/agents/${agentId}/extraction`,
        patch,
      );
      setCfg(updated);
      setMaxFactsDraft(String(updated.max_facts ?? 5));
    } catch (e) {
      console.error(e);
      toast.error("Failed to save extraction config");
    } finally {
      setSaving(false);
    }
  };


  const toggleEnabled = (enabled: boolean) => {
    save({ enabled });
  };


  const setModel = (model: string | null) => {
    save({ model });
  };


  const commitMaxFacts = () => {
    const n = parseInt(maxFactsDraft, 10);
    if (!Number.isFinite(n) || n < 1 || n > 20) {
      toast.error("max_facts must be between 1 and 20");
      setMaxFactsDraft(String(cfg?.max_facts ?? 5));
      return;
    }
    if (n === cfg?.max_facts) return;
    save({ max_facts: n });
  };


  const applyRecommended = async () => {
    if (!cfg) return;
    setSaving(true);
    try {
      const r = await api.get<{
        recommendation: string | null;
        catalog_size: number;
      }>(`/agents/${agentId}/extraction/recommendations`);
      if (!r.recommendation) {
        toast.error("No extraction model recommendation matches this provider's catalog.", {
          description: r.catalog_size
            ? `Provider exposes ${r.catalog_size} models, none matched.`
            : "Connect the provider to populate the model catalog.",
        });
        return;
      }
      await save({ enabled: true, model: r.recommendation });
      toast.success(`Applied: ${r.recommendation}`);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load recommendation");
    } finally {
      setSaving(false);
    }
  };

  if (!cfg) {
    return <p className="text-xs text-muted-foreground mt-2">Loading extraction…</p>;
  }

  return (
    <div className="mt-4 border-t border-border pt-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Extraction</p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={applyRecommended}
            disabled={saving || !providerId}
            title={
              providerId
                ? "Apply recommended NIM model for this provider"
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

      <div className="rounded border border-border p-3 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium">Background fact extraction</p>
            <p className="text-xs text-muted-foreground">
              After each turn, extract durable facts from the conversation and store them in
              private memory. Used for recall in future turns.
            </p>
          </div>
          <label className="inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={cfg.enabled}
              onChange={(e) => toggleEnabled(e.target.checked)}
            />
            <div className="w-9 h-5 bg-zinc-700 peer-checked:bg-green-500 rounded-full relative transition">
              <div
                className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${cfg.enabled ? "translate-x-4" : ""
                  }`}
              />
            </div>
          </label>
        </div>

        <div>
          <label className="block text-xs text-muted-foreground mb-1">
            Extraction model (leave empty to use the agent's main model)
          </label>
          <select
            className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
            value={cfg.model ?? ""}
            onChange={(e) => setModel(e.target.value || null)}
            disabled={!cfg.enabled}
          >
            <option value="">— use agent's main model —</option>
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-muted-foreground mb-1">
            Max facts per turn (1–20)
          </label>
          <input
            type="number"
            min={1}
            max={20}
            className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
            value={maxFactsDraft}
            disabled={!cfg.enabled}
            onChange={(e) => setMaxFactsDraft(e.target.value)}
            onBlur={commitMaxFacts}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.blur();
            }}
          />
        </div>
      </div>
    </div>
  );
}
