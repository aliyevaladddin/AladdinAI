// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Check, X, Pencil, Loader2, RefreshCw } from "lucide-react";

interface Model {
  id: string;
  type: string;
  is_supported: boolean;
}

export function ModelSelectionDrawer({
  agentId,
  providerId,
  currentModel,
  onSelect,
  onClose,
}: {
  agentId: number;
  providerId: number | null;
  currentModel: string;
  onSelect: (model: string) => void;
  onClose: () => void;
}) {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [pings, setPings] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!providerId) return;
    api
      .get<{ models: Model[] }>(`/providers/${providerId}/models`)
      .then((r) => setModels(r.models || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [providerId]);

  const pingModel = async (modelId: string) => {
    setPings((prev) => ({ ...prev, [modelId]: "pinging" }));
    try {
      const res = await api.post(`/providers/${providerId}/models/${encodeURIComponent(modelId)}/ping`);
      setPings((prev) => ({ ...prev, [modelId]: res.status === "ok" ? "online" : "offline" }));
    } catch {
      setPings((prev) => ({ ...prev, [modelId]: "error" }));
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-80 bg-background border-l border-border p-6 shadow-xl z-50 animate-in slide-in-from-right duration-300">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold">Select Model</h2>
        <Button variant="ghost" size="icon-sm" onClick={onClose}>
          <X size={16} />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-8">
          <Loader2 className="animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {models.map((model) => (
            <div key={model.id} className="p-3 bg-surface-1 rounded-lg border border-border">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-mono truncate">{model.id}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${model.is_supported ? "bg-success-soft text-success" : "bg-muted text-muted-foreground"}`}>
                  {model.type}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Button size="xs" onClick={() => onSelect(model.id)} disabled={model.id === currentModel}>
                  Select
                </Button>
                <Button size="xs" variant="outline" onClick={() => pingModel(model.id)}>
                  {pings[model.id] === "pinging" ? <Loader2 className="animate-spin" size={12} /> : <RefreshCw size={12} />}
                </Button>
                {pings[model.id] && (
                  <span className={`text-xs ml-auto ${pings[model.id] === "online" ? "text-success" : pings[model.id] === "offline" ? "text-danger" : "text-muted-foreground"}`}>
                    {pings[model.id]}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
