"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface BentoML {
  id: number;
  name: string;
  endpoint_url: string;
  status: string;
}

export default function BentoMLPage() {
  const [conns, setConns] = useState<BentoML[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", endpoint_url: "", api_key: "" });

  const load = () => api.get<BentoML[]>("/bentoml").then(setConns);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/bentoml", form);
    setForm({ name: "", endpoint_url: "", api_key: "" });
    setShowForm(false);
    load();
  };

  const handleTest = async (id: number) => {
    const res = await api.post<{ status: string; message?: string }>(`/bentoml/${id}/test`);
    alert(res.message || res.status);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/bentoml/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">BentoML Connections</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Connection"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <input placeholder="Endpoint URL (http://...)" value={form.endpoint_url} onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <input placeholder="API Key (optional)" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {conns.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground">{c.endpoint_url}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded ${c.status === "connected" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                {c.status}
              </span>
              <Button variant="outline" size="sm" onClick={() => handleTest(c.id)}>Test</Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {conns.length === 0 && <p className="text-muted-foreground text-sm">No BentoML connections yet.</p>}
      </div>
    </div>
  );
}
