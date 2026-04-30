"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface VM {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
  status: string;
}

export default function VMsPage() {
  const [vms, setVms] = useState<VM[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", host: "", port: "22", username: "root" });

  const load = () => api.get<VM[]>("/vms").then(setVms);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/vms", { ...form, port: parseInt(form.port) });
    setForm({ name: "", host: "", port: "22", username: "root" });
    setShowForm(false);
    load();
  };

  const handleTest = async (id: number) => {
    const res = await api.post<{ status: string; message?: string }>(`/vms/${id}/test`);
    alert(res.message || res.status);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this VM connection?")) return;
    await api.delete(`/vms/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Cloud VMs</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add VM"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="Host (IP/Domain)" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
            <input placeholder="Port" value={form.port} onChange={(e) => setForm({ ...form, port: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
            <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {vms.map((vm) => (
          <div key={vm.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{vm.name}</p>
              <p className="text-sm text-muted-foreground">{vm.username}@{vm.host}:{vm.port}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-1 rounded ${vm.status === "connected" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                {vm.status}
              </span>
              <Button variant="outline" size="sm" onClick={() => handleTest(vm.id)}>Test</Button>
              <Button variant="outline" size="sm" onClick={() => handleDelete(vm.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {vms.length === 0 && <p className="text-muted-foreground text-sm">No VMs connected yet.</p>}
      </div>
    </div>
  );
}
