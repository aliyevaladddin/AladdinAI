"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Mongo {
  id: number;
  name: string;
  db_name: string;
  status: string;
}

export default function MongoDBPage() {
  const [conns, setConns] = useState<Mongo[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", connection_string: "", db_name: "" });

  const load = () => api.get<Mongo[]>("/mongodb").then(setConns);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/mongodb", form);
    setForm({ name: "", connection_string: "", db_name: "" });
    setShowForm(false);
    load();
  };

  const handleTest = async (id: number) => {
    const res = await api.post<{ status: string; message?: string }>(`/mongodb/${id}/test`);
    const msg = res.message || res.status;
    res.status === "ok" || res.status === "success" || res.status === "connected"
      ? toast.success(msg)
      : toast.error(msg);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/mongodb/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">MongoDB Connections</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Connection"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <input placeholder="Connection String (mongodb+srv://...)" value={form.connection_string} onChange={(e) => setForm({ ...form, connection_string: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" required />
          <input placeholder="Database Name" value={form.db_name} onChange={(e) => setForm({ ...form, db_name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {conns.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground">DB: {c.db_name}</p>
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
        {conns.length === 0 && <p className="text-muted-foreground text-sm">No MongoDB connections yet.</p>}
      </div>
    </div>
  );
}
