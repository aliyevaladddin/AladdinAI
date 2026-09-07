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
  const [search, setSearch] = useState("");
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

  const filteredModels = models.filter((m) =>
    m.id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 animate-in fade-in duration-200"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 w-80 sm:w-96 bg-background border-l border-border p-5 shadow-2xl z-50 flex flex-col h-full max-h-screen animate-in slide-in-from-right duration-300">
        <div className="flex items-center justify-between pb-4 border-b border-border mb-4">
          <div>
            <h2 className="text-lg font-bold">Select Model</h2>
            <p className="text-xs text-muted-foreground">
              {models.length} models available
            </p>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={onClose}>
            <X size={16} />
          </Button>
        </div>

        <div className="mb-4">
          <input
            type="text"
            placeholder="Search models..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center p-8">
            <Loader2 className="animate-spin text-muted-foreground" />
          </div>
        ) : filteredModels.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground p-4 text-center">
            {models.length === 0 ? "No models found" : `No models matching "${search}"`}
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto pr-1 space-y-3 scrollbar-thin">
            {filteredModels.map((model) => (
              <div key={model.id} className="p-3 bg-surface-1 rounded-lg border border-border">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-mono truncate" title={model.id}>{model.id}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded flex-shrink-0 ${model.is_supported ? "bg-success-soft text-success" : "bg-muted text-muted-foreground"}`}>
                    {model.type}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Button size="xs" onClick={() => onSelect(model.id)} disabled={model.id === currentModel}>
                    {model.id === currentModel ? "Selected" : "Select"}
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
    </>
  );
}
