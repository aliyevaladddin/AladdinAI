"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { RefreshCw, ChevronDown, ChevronRight, Loader2 } from "lucide-react";

interface Provider {
  id: number;
  name: string;
  type: string;
  base_url: string;
  status: string;
}

interface ConnectResult {
  status: string;
  message?: string;
  models?: string[];
  count?: number;
}

const TYPES = ["nvidia_nim", "openai", "anthropic", "ollama", "huggingface", "custom"];

const TYPE_LABELS: Record<string, string> = {
  nvidia_nim: "NVIDIA NIM",
  openai: "OpenAI",
  anthropic: "Anthropic",
  ollama: "Ollama",
  huggingface: "Hugging Face",
  custom: "Custom",
};

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", type: "huggingface", api_key: "", base_url: "" });
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [refreshing, setRefreshing] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, ConnectResult>>({});
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [models, setModels] = useState<Record<number, string[]>>({});

  const load = () => api.get<Provider[]>("/providers").then(setProviders);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/providers", form);
    setForm({ name: "", type: "nvidia_nim", api_key: "", base_url: "" });
    setShowForm(false);
    load();
  };

  const handleConnect = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    setResult((prev) => ({ ...prev, [id]: { status: "connecting..." } }));
    try {
      const res = await api.post<ConnectResult>(`/providers/${id}/connect`);
      setResult((prev) => ({ ...prev, [id]: res }));
      if (res.models) setModels((prev) => ({ ...prev, [id]: res.models! }));
      load();
    } catch {
      setResult((prev) => ({ ...prev, [id]: { status: "error", message: "Request failed" } }));
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  // Refresh hits the same /connect endpoint — that's what re-fetches /v1/models
  // and persists the catalog. Keep the connected status visible while it runs.
  const handleRefreshModels = async (id: number) => {
    setRefreshing((prev) => ({ ...prev, [id]: true }));
    try {
      const res = await api.post<ConnectResult>(`/providers/${id}/connect`);
      if (res.status === "connected") {
        setResult((prev) => ({ ...prev, [id]: res }));
        if (res.models) setModels((prev) => ({ ...prev, [id]: res.models! }));
        toast.success(`Refreshed — ${res.count ?? res.models?.length ?? 0} models available`);
      } else {
        toast.error(res.message || "Refresh failed");
        setResult((prev) => ({ ...prev, [id]: res }));
        load();
      }
    } catch (e: any) {
      toast.error(e?.message || "Refresh failed");
    } finally {
      setRefreshing((prev) => ({ ...prev, [id]: false }));
    }
  };

  const toggleExpand = async (id: number) => {
    const willOpen = !expanded[id];
    setExpanded((prev) => ({ ...prev, [id]: willOpen }));
    if (willOpen && !models[id]) {
      try {
        const res = await api.get<{ models: string[]; hint?: string }>(`/providers/${id}/models`);
        setModels((prev) => ({ ...prev, [id]: res.models || [] }));
      } catch {
        // ignore — empty state will render
      }
    }
  };

  const handleDisconnect = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      await api.post(`/providers/${id}/disconnect`);
      load();
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
      setResult((prev) => { const next = { ...prev }; delete next[id]; return next; });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this provider?")) return;
    await api.delete(`/providers/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">LLM Providers</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Provider"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input
            placeholder="Name (e.g. My NVIDIA NIM)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
          />
          <div className="grid grid-cols-2 gap-3">
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>
              ))}
            </select>
            <input
              placeholder="Base URL (e.g. https://integrate.api.nvidia.com)"
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
          </div>
          <input
            placeholder="API Key (optional)"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            type="password"
          />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {providers.map((p) => (
          <div key={p.id} className="rounded-lg border border-border p-4 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-medium truncate">{p.name}</p>
                <p className="text-sm text-muted-foreground truncate">
                  {TYPE_LABELS[p.type] ?? p.type} — {p.base_url}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-xs px-2 py-1 rounded ${
                  p.status === "connected"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-zinc-500/20 text-zinc-400"
                }`}>
                  {p.status}
                </span>
                {p.status === "connected" ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRefreshModels(p.id)}
                      disabled={refreshing[p.id] || loading[p.id]}
                      title="Re-fetch the model catalog from the provider"
                    >
                      {refreshing[p.id]
                        ? <Loader2 size={12} className="animate-spin" />
                        : <RefreshCw size={12} />}
                      Refresh models
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDisconnect(p.id)}
                      disabled={loading[p.id]}
                    >
                      {loading[p.id] ? "..." : "Disconnect"}
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleConnect(p.id)}
                    disabled={loading[p.id]}
                  >
                    {loading[p.id] ? "Connecting..." : "Connect"}
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={() => handleDelete(p.id)}>
                  Delete
                </Button>
              </div>
            </div>

            {p.status === "connected" && (
              <button
                type="button"
                onClick={() => toggleExpand(p.id)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {expanded[p.id] ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                {models[p.id]
                  ? `${models[p.id].length} models available`
                  : "Show models"}
              </button>
            )}

            {expanded[p.id] && (
              <div className="rounded-md border border-border bg-muted/30 p-3 max-h-64 overflow-y-auto">
                {models[p.id] && models[p.id].length > 0 ? (
                  <ul className="space-y-1 text-xs font-mono">
                    {models[p.id].map((m) => (
                      <li key={m} className="text-muted-foreground hover:text-foreground transition-colors">
                        {m}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    No models cached. Click <span className="font-medium">Refresh models</span> to fetch from the provider.
                  </p>
                )}
              </div>
            )}

            {result[p.id] && (
              <div className={`text-xs rounded p-2 ${
                result[p.id].status === "connected"
                  ? "bg-green-500/10 text-green-400"
                  : result[p.id].status === "connecting..."
                  ? "bg-blue-500/10 text-blue-400"
                  : "bg-red-500/10 text-red-400"
              }`}>
                {result[p.id].status === "connected" ? (
                  <>✓ Connected — {result[p.id].count} models available: {result[p.id].models?.slice(0, 3).join(", ")}{(result[p.id].count ?? 0) > 3 ? "..." : ""}</>
                ) : result[p.id].status === "connecting..." ? (
                  <>⟳ Connecting to API...</>
                ) : (
                  <>✗ {result[p.id].message}</>
                )}
              </div>
            )}
          </div>
        ))}
        {providers.length === 0 && (
          <p className="text-muted-foreground text-sm">No providers connected yet.</p>
        )}
      </div>
    </div>
  );
}
