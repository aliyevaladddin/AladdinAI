"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Provider {
  id: number;
  name: string;
  type: string;
  base_url: string;
  status: string;
}

const TYPES = ["nvidia_nim", "openai", "anthropic", "ollama", "custom"];

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", type: "nvidia_nim", api_key: "", base_url: "" });

  const load = () => api.get<Provider[]>("/providers").then(setProviders);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/providers", form);
    setForm({ name: "", type: "nvidia_nim", api_key: "", base_url: "" });
    setShowForm(false);
    load();
  };

  const handleTest = async (id: number) => {
    const res = await api.post<{ status: string; message?: string }>(`/providers/${id}/test`);
    alert(JSON.stringify(res, null, 2));
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
          <input placeholder="Name (e.g. My NVIDIA NIM)" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <div className="grid grid-cols-2 gap-3">
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm">
              {TYPES.map((t) => <option key={t} value={t}>{t.replace("_", " ").toUpperCase()}</option>)}
            </select>
            <input placeholder="Base URL" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          </div>
          <input placeholder="API Key (optional)" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {providers.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{p.name}</p>
              <p className="text-sm text-muted-foreground">{p.type.replace("_", " ").toUpperCase()} — {p.base_url}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded ${p.status === "connected" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                {p.status}
              </span>
              <Button variant="outline" size="sm" onClick={() => handleTest(p.id)}>Test</Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(p.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {providers.length === 0 && <p className="text-muted-foreground text-sm">No providers connected yet.</p>}
      </div>
    </div>
  );
}
