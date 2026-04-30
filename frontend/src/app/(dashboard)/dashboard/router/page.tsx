"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface RouterCfg {
  id: number;
  name: string;
  type: string;
  config: Record<string, unknown>;
  is_active: boolean;
}

export default function RouterPage() {
  const [configs, setConfigs] = useState<RouterCfg[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", type: "keyword", config: "{}", is_active: false });

  const load = () => api.get<RouterCfg[]>("/router").then(setConfigs);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/router", { ...form, config: JSON.parse(form.config) });
    setForm({ name: "", type: "keyword", config: "{}", is_active: false });
    setShowForm(false);
    load();
  };

  const handleActivate = async (cfg: RouterCfg) => {
    await api.put(`/router/${cfg.id}`, { is_active: !cfg.is_active });
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Router Config</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Config"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
            <option value="keyword">Keyword</option>
            <option value="llm_classifier">LLM Classifier</option>
            <option value="hybrid">Hybrid</option>
          </select>
          <textarea placeholder='Config JSON (e.g. {"rules": []})' value={form.config} onChange={(e) => setForm({ ...form, config: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm h-24 font-mono" />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {configs.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground">Type: {c.type}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded ${c.is_active ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                {c.is_active ? "Active" : "Inactive"}
              </span>
              <Button variant="outline" size="sm" onClick={() => handleActivate(c)}>
                {c.is_active ? "Deactivate" : "Activate"}
              </Button>
            </div>
          </div>
        ))}
        {configs.length === 0 && <p className="text-muted-foreground text-sm">No router configs yet.</p>}
      </div>
    </div>
  );
}
