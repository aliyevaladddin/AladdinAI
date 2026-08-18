"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Download,
  FlaskConical,
  RefreshCw,
  Snowflake,
  Sparkles,
  XCircle,
} from "lucide-react";

interface GoldenExample {
  input: string;
  expected: string;
  reward: number;
  agent_id?: number;
  created_at?: string;
}

interface FreezeResult {
  frozen: number;
  frozen_at: string;
  min_reward: number;
  human_only: boolean;
  replaced: boolean;
}

interface HarnessResult {
  evaluated: number;
  base_model: string;
  forged_model: string;
  mean_base: number;
  mean_forged: number;
  delta: number;
  message?: string;
  examples: { input: string; base_score: number; forged_score: number; delta: number }[];
}

export default function ForgingPage() {
  const [goldenSet, setGoldenSet] = useState<GoldenExample[]>([]);
  const [loadingGolden, setLoadingGolden] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [freezing, setFreezing] = useState(false);
  const [freezeResult, setFreezeResult] = useState<FreezeResult | null>(null);
  const [minReward, setMinReward] = useState("0.5");
  const [humanOnly, setHumanOnly] = useState(true);

  const loadGolden = useCallback(async () => {
    setLoadingGolden(true);
    setError(null);
    try {
      const data = await api.get<GoldenExample[]>("/forging/golden-set", { bypassCache: true });
      setGoldenSet(data);
    } catch (err: any) {
      if (err?.status === 403) {
        setError("Self-Forging requires a non-community edition.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load golden set");
      }
    } finally {
      setLoadingGolden(false);
    }
  }, []);

  useEffect(() => { loadGolden(); }, [loadGolden]);

  const handleFreeze = async () => {
    setFreezing(true);
    try {
      const result = await api.post<FreezeResult>("/forging/golden-set", {
        min_reward: parseFloat(minReward),
        human_only: humanOnly,
      });
      setFreezeResult(result);
      toast.success(`Frozen ${result.frozen} examples`);
      loadGolden();
    } catch (err: any) {
      if (err?.status === 403) {
        toast.error("Self-Forging requires a non-community edition.");
      } else {
        toast.error("Failed to freeze golden set");
      }
    } finally {
      setFreezing(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await fetch(`${window.location.origin}/api/forging/golden-set/export?format=sft`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "golden-set-sft.jsonl";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Failed to export golden set");
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20">
            <FlaskConical size={24} className="text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Self-Forging</h1>
            <p className="text-xs text-muted-foreground">Golden set management and base-vs-forged evaluation</p>
          </div>
        </div>
      </div>

      {/* Error state (edition-gated) */}
      {error && (
        <EmptyState
          icon={<XCircle size={40} />}
          title="Self-Forging unavailable"
          description={error}
        />
      )}

      {/* Golden set section */}
      {!error && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">
                Golden Set
              </h2>
              {!loadingGolden && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-2 border border-border/40 font-mono text-muted-foreground">
                  {goldenSet.length} examples
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {goldenSet.length > 0 && (
                <Button size="sm" variant="outline" onClick={handleExport} className="gap-1.5">
                  <Download size={13} /> Export JSONL
                </Button>
              )}
              <button onClick={loadGolden} className="text-[10px] uppercase tracking-widest text-accent hover:underline flex items-center gap-1">
                <RefreshCw size={11} /> Refresh
              </button>
            </div>
          </div>

          {/* Freeze controls */}
          <div className="rounded-xl border border-border/50 bg-surface-1 p-4">
            <div className="flex items-end gap-4 flex-wrap">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Min reward (-1.0 to 1.0)</label>
                <input
                  type="number"
                  step="0.1"
                  min="-1"
                  max="1"
                  value={minReward}
                  onChange={(e) => setMinReward(e.target.value)}
                  className="w-24 rounded-md border border-input bg-background px-2 py-1 text-xs font-mono"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={humanOnly}
                    onChange={(e) => setHumanOnly(e.target.checked)}
                  />
                  <div className="w-9 h-5 bg-muted peer-checked:bg-success rounded-full relative transition">
                    <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${humanOnly ? "translate-x-4" : ""}`} />
                  </div>
                </label>
                <span className="text-xs text-muted-foreground">Human-labeled only</span>
              </div>
              <Button size="sm" onClick={handleFreeze} disabled={freezing} className="gap-1.5">
                <Snowflake size={13} /> {freezing ? "Freezing…" : "Freeze Golden Set"}
              </Button>
            </div>
            {freezeResult && (
              <p className="text-xs text-success mt-2">
                Frozen {freezeResult.frozen} examples at {new Date(freezeResult.frozen_at).toLocaleString()}
                {freezeResult.replaced ? " (replaced previous set)" : ""}
              </p>
            )}
          </div>

          {/* Golden set list */}
          {loadingGolden ? (
            <div className="p-8 text-center text-muted-foreground animate-pulse">Loading golden set…</div>
          ) : goldenSet.length === 0 ? (
            <EmptyState
              icon={<Snowflake size={40} />}
              title="Golden set is empty."
              description="Label some traces with 👍/👎 in the traces view, then freeze them here."
            />
          ) : (
            <div className="space-y-2">
              {goldenSet.slice(0, 50).map((g, i) => (
                <div key={i} className="rounded-lg border border-border/40 bg-surface-1 p-3 text-xs">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] font-mono text-success">reward {g.reward.toFixed(2)}</span>
                  </div>
                  <p className="text-foreground line-clamp-1 font-medium">{g.input}</p>
                  <p className="text-muted-foreground line-clamp-1 mt-0.5">{g.expected}</p>
                </div>
              ))}
              {goldenSet.length > 50 && (
                <p className="text-xs text-muted-foreground text-center pt-2">
                  Showing 50 of {goldenSet.length}. Export to see all.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
