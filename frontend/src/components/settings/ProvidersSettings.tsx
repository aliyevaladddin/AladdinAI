// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Cpu, Plus, X, CheckCircle2, XCircle, Loader2, Trash2,
  Unplug, PlugZap, Pencil, Check
} from "lucide-react";


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


export function ProvidersSettings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", type: "nvidia_nim", api_key: "", base_url: "" });
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, ConnectResult>>({});
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", type: "", base_url: "", api_key: "" });


  const load = () => api.get<Provider[]>("/providers").then(setProviders);
  useEffect(() => { load(); }, []);


  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/providers", form);
    setForm({ name: "", type: "nvidia_nim", api_key: "", base_url: "" });
    setShowForm(false);
    load();
  };


  const handleSaveEdit = async (id: number) => {
    await api.put(`/providers/${id}`, {
      name: editForm.name,
      type: editForm.type,
      base_url: editForm.base_url,
      ...(editForm.api_key ? { api_key: editForm.api_key } : {}),
    });
    setEditId(null);
    load();
  };


  const startEdit = (p: Provider) => {
    setEditId(p.id);
    setEditForm({ name: p.name, type: p.type, base_url: p.base_url, api_key: "" });
  };


  const handleConnect = async (id: number) => {
    setLoading((p) => ({ ...p, [id]: true }));
    setResult((p) => ({ ...p, [id]: { status: "connecting" } }));
    try {
      const res = await api.post<ConnectResult>(`/providers/${id}/connect`);
      setResult((p) => ({ ...p, [id]: res }));
      load();
    } catch {
      setResult((p) => ({ ...p, [id]: { status: "error", message: "Connection failed" } }));
    } finally {
      setLoading((p) => ({ ...p, [id]: false }));
    }
  };


  const handleDisconnect = async (id: number) => {
    setLoading((p) => ({ ...p, [id]: true }));
    try {
      await api.post(`/providers/${id}/disconnect`);
      load();
    } finally {
      setLoading((p) => ({ ...p, [id]: false }));
      setResult((p) => { const n = { ...p }; delete n[id]; return n; });
    }
  };


  const handleDelete = async (id: number) => {
    if (!confirm("Delete this provider?")) return;
    await api.delete(`/providers/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Cpu size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">LLM Providers</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Connect your AI model providers and API keys</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Provider</>}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Provider Name</label>
              <input className="input" placeholder="e.g. My NVIDIA NIM" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Type</label>
              <select className="input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                {TYPES.map((t) => <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>)}
              </select>
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Base URL</label>
            <input className="input" placeholder="https://integrate.api.nvidia.com/v1"
              value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">
              API Key <span className="opacity-50">(optional)</span>
            </label>
            <input className="input" type="password" placeholder="sk-..."
              value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
          </div>
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" size="sm">Create Provider</Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {providers.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">
            No providers connected yet
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {providers.map((p) => {
              const isConnected = p.status === "connected";
              const isBusy = loading[p.id];
              const res = result[p.id];
              const isEditing = editId === p.id;

              return (
                <div key={p.id}>
                  {/* View row */}
                  <div className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors">
                    {/* Status icon */}
                    <div className="shrink-0">
                      {isBusy ? (
                        <Loader2 size={15} className="animate-spin text-[var(--color-fg-subtle)]" />
                      ) : isConnected ? (
                        <CheckCircle2 size={15} className="text-[var(--color-success)]" />
                      ) : (
                        <XCircle size={15} className="text-[var(--color-fg-subtle)]" />
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-fg)] truncate">{p.name}</span>
                        <span className="text-[10px] px-1.5 py-px rounded bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[var(--color-fg-subtle)] font-mono uppercase shrink-0">
                          {TYPE_LABELS[p.type] ?? p.type}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--color-fg-subtle)] font-mono truncate mt-0.5">{p.base_url}</div>
                      {res && (
                        <div className={`mt-1.5 text-xs px-2 py-1 rounded-md w-fit ${res.status === "connected" ? "bg-[var(--color-success-soft)] text-[var(--color-success)]" :
                            res.status === "connecting" ? "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]" :
                              "bg-[var(--color-danger-soft)] text-[var(--color-danger)]"
                          }`}>
                          {res.status === "connected" ? `✓ Connected · ${res.count ?? 0} models`
                            : res.status === "connecting" ? "Connecting..."
                              : `✗ ${res.message}`}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {isConnected ? (
                        <Button variant="outline" size="sm" onClick={() => handleDisconnect(p.id)} disabled={isBusy}>
                          <Unplug size={13} /> Disconnect
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleConnect(p.id)} disabled={isBusy}>
                          <PlugZap size={13} /> Connect
                        </Button>
                      )}
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => isEditing ? setEditId(null) : startEdit(p)}
                        title="Edit"
                        className={isEditing ? "text-[var(--color-accent)]" : "text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"}
                      >
                        <Pencil size={13} />
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => handleDelete(p.id)} disabled={isBusy} title="Delete"
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>

                  {/* Inline edit form */}
                  {isEditing && (
                    <div className="px-4 py-3 bg-[var(--color-surface-2)] border-t border-[var(--color-border)] space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
                          <input className="input" value={editForm.name}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Type</label>
                          <select className="input" value={editForm.type}
                            onChange={(e) => setEditForm({ ...editForm, type: e.target.value })}>
                            {TYPES.map((t) => <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>)}
                          </select>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Base URL</label>
                        <input className="input" value={editForm.base_url}
                          onChange={(e) => setEditForm({ ...editForm, base_url: e.target.value })} />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">
                          New API Key <span className="opacity-50">(leave blank to keep current)</span>
                        </label>
                        <input className="input" type="password" placeholder="sk-..."
                          value={editForm.api_key}
                          onChange={(e) => setEditForm({ ...editForm, api_key: e.target.value })} />
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditId(null)}>Cancel</Button>
                        <Button size="sm" onClick={() => handleSaveEdit(p.id)}>
                          <Check size={13} /> Save
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
