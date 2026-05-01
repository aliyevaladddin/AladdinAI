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

interface ConnectResult {
  status: string;
  message?: string;
}

export default function VMsPage() {
  const [vms, setVms] = useState<VM[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", host: "", port: "22", username: "root", ssh_key: "", password: "" });
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, ConnectResult>>({});

  const load = () => api.get<VM[]>("/vms").then(setVms);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/vms", {
      name: form.name,
      host: form.host,
      port: parseInt(form.port),
      username: form.username,
      ssh_key: form.ssh_key || null,
      password: form.password || null,
    });
    setForm({ name: "", host: "", port: "22", username: "root", ssh_key: "", password: "" });
    setShowForm(false);
    load();
  };

  const handleConnect = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    setResult((prev) => ({ ...prev, [id]: { status: "connecting..." } }));
    try {
      const res = await api.post<ConnectResult>(`/vms/${id}/connect`);
      setResult((prev) => ({ ...prev, [id]: res }));
      load();
    } catch {
      setResult((prev) => ({ ...prev, [id]: { status: "error", message: "Request failed" } }));
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const handleDisconnect = async (id: number) => {
    setLoading((prev) => ({ ...prev, [id]: true }));
    try {
      await api.post(`/vms/${id}/disconnect`);
      load();
    } finally {
      setLoading((prev) => ({ ...prev, [id]: false }));
      setResult((prev) => { const next = { ...prev }; delete next[id]; return next; });
    }
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
          <input
            placeholder="Name (e.g. My GPU Server)"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            required
          />
          <div className="grid grid-cols-3 gap-3">
            <input
              placeholder="Host (IP or domain)"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
            <input
              placeholder="Port"
              value={form.port}
              onChange={(e) => setForm({ ...form, port: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <input
              placeholder="Username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <input
            placeholder="Password (optional, for password auth)"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            type="password"
          />
          <textarea
            placeholder="SSH Private Key (paste full key, optional)"
            value={form.ssh_key}
            onChange={(e) => setForm({ ...form, ssh_key: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono text-xs"
            rows={4}
          />
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {vms.map((vm) => (
          <div key={vm.id} className="rounded-lg border border-border p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{vm.name}</p>
                <p className="text-sm text-muted-foreground">
                  {vm.username}@{vm.host}:{vm.port}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded ${
                  vm.status === "connected"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-zinc-500/20 text-zinc-400"
                }`}>
                  {vm.status}
                </span>
                {vm.status === "connected" ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDisconnect(vm.id)}
                    disabled={loading[vm.id]}
                  >
                    {loading[vm.id] ? "..." : "Disconnect"}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleConnect(vm.id)}
                    disabled={loading[vm.id]}
                  >
                    {loading[vm.id] ? "Connecting..." : "Connect"}
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={() => handleDelete(vm.id)}>
                  Delete
                </Button>
              </div>
            </div>

            {result[vm.id] && (
              <div className={`text-xs rounded p-2 ${
                result[vm.id].status === "connected"
                  ? "bg-green-500/10 text-green-400"
                  : result[vm.id].status === "connecting..."
                  ? "bg-blue-500/10 text-blue-400"
                  : "bg-red-500/10 text-red-400"
              }`}>
                {result[vm.id].status === "connected" ? (
                  <>✓ {result[vm.id].message}</>
                ) : result[vm.id].status === "connecting..." ? (
                  <>⟳ Establishing SSH connection...</>
                ) : (
                  <>✗ {result[vm.id].message}</>
                )}
              </div>
            )}
          </div>
        ))}
        {vms.length === 0 && (
          <p className="text-muted-foreground text-sm">No VMs connected yet.</p>
        )}
      </div>
    </div>
  );
}
