// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";


interface Mongo {
  id: number;
  name: string;
  db_name: string;
  status: string;
}

export default function MongoDBPage() {
  const [conns, setConns] = useState<Mongo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", connection_string: "", db_name: "" });


  const load = async () => {
    setLoading(true);
    try {
      const data = await api.get<Mongo[]>("/mongodb");
      setConns(data);
    } finally {
      setLoading(false);
    }
  };
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
          <input placeholder="Connection string" value={form.connection_string} onChange={(e) => setForm({ ...form, connection_string: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <input placeholder="Database name" value={form.db_name} onChange={(e) => setForm({ ...form, db_name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <Button type="submit">Create</Button>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="animate-spin mr-2 h-4 w-4" /> Loading connections…
        </div>
      ) : (
      <div className="space-y-3">
        {conns.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground">DB: {c.db_name} · {c.status}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => handleTest(c.id)}>Test</Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {conns.length === 0 && <p className="text-muted-foreground text-sm">No MongoDB connections configured.</p>}
      </div>
      )}
    </div>
  );
}
