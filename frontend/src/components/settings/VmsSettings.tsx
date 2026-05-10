"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Cloud, Plus, X, CheckCircle2, XCircle, Loader2,
  Trash2, Unplug, PlugZap, Pencil, Check
} from "lucide-react";

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

export function VmsSettings() {
  const [vms, setVms] = useState<VM[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", host: "", port: "22", username: "root", ssh_key: "", password: "" });
  const [loading, setLoading] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, ConnectResult>>({});
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", host: "", port: "22", username: "" });

  const load = () => api.get<VM[]>("/vms").then(setVms);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/vms", {
      name: form.name, host: form.host, port: parseInt(form.port),
      username: form.username, ssh_key: form.ssh_key || null, password: form.password || null,
    });
    setForm({ name: "", host: "", port: "22", username: "root", ssh_key: "", password: "" });
    setShowForm(false);
    load();
  };

  const startEdit = (vm: VM) => {
    setEditId(vm.id);
    setEditForm({ name: vm.name, host: vm.host, port: String(vm.port), username: vm.username });
  };

  const handleSaveEdit = async (id: number) => {
    await api.put(`/vms/${id}`, {
      name: editForm.name,
      host: editForm.host,
      port: parseInt(editForm.port),
      username: editForm.username,
    });
    setEditId(null);
    load();
  };

  const handleConnect = async (id: number) => {
    setLoading((p) => ({ ...p, [id]: true }));
    setResult((p) => ({ ...p, [id]: { status: "connecting" } }));
    try {
      const res = await api.post<ConnectResult>(`/vms/${id}/connect`);
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
      await api.post(`/vms/${id}/disconnect`);
      load();
    } finally {
      setLoading((p) => ({ ...p, [id]: false }));
      setResult((p) => { const n = { ...p }; delete n[id]; return n; });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this VM connection?")) return;
    await api.delete(`/vms/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Cloud size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">Cloud VMs</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Manage your compute nodes via SSH</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add VM</>}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">VM Name</label>
            <input className="input" placeholder="e.g. GPU Worker 1" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Host</label>
              <input className="input" placeholder="192.168.1.1" value={form.host}
                onChange={(e) => setForm({ ...form, host: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Port</label>
              <input className="input" placeholder="22" value={form.port}
                onChange={(e) => setForm({ ...form, port: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Username</label>
              <input className="input" placeholder="root" value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Password <span className="opacity-40">(optional)</span></label>
              <input className="input" type="password" placeholder="••••••••" value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">SSH Private Key <span className="opacity-40">(optional)</span></label>
            <textarea className="input font-mono text-[11px]" rows={4}
              placeholder="-----BEGIN OPENSSH PRIVATE KEY-----" value={form.ssh_key}
              onChange={(e) => setForm({ ...form, ssh_key: e.target.value })}
              style={{ resize: "vertical" }} />
          </div>
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" size="sm">Save Connection</Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {vms.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">
            No virtual machines configured yet
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {vms.map((vm) => {
              const isConnected = vm.status === "connected";
              const isBusy = loading[vm.id];
              const res = result[vm.id];
              const isEditing = editId === vm.id;

              return (
                <div key={vm.id}>
                  {/* Row */}
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
                      <span className="text-sm font-medium text-[var(--color-fg)]">{vm.name}</span>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs text-[var(--color-fg-subtle)] font-mono">
                          {vm.username}@{vm.host}:{vm.port}
                        </span>
                      </div>
                      {res && (
                        <div className={`mt-1.5 text-xs px-2 py-1 rounded-md w-fit ${
                          res.status === "connected" ? "bg-[var(--color-success-soft)] text-[var(--color-success)]" :
                          res.status === "connecting" ? "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]" :
                          "bg-[var(--color-danger-soft)] text-[var(--color-danger)]"
                        }`}>
                          {res.status === "connected" ? `✓ ${res.message}` :
                           res.status === "connecting" ? "Establishing SSH connection..." :
                           `✗ ${res.message}`}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {isConnected ? (
                        <Button variant="outline" size="sm" onClick={() => handleDisconnect(vm.id)} disabled={isBusy}>
                          <Unplug size={13} /> Disconnect
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleConnect(vm.id)} disabled={isBusy}>
                          <PlugZap size={13} /> Connect
                        </Button>
                      )}
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => isEditing ? setEditId(null) : startEdit(vm)}
                        title="Edit"
                        className={isEditing ? "text-[var(--color-accent)]" : "text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"}
                      >
                        <Pencil size={13} />
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => handleDelete(vm.id)} disabled={isBusy} title="Delete"
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>

                  {/* Inline edit form */}
                  {isEditing && (
                    <div className="px-4 py-3 bg-[var(--color-surface-2)] border-t border-[var(--color-border)] space-y-3">
                      <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
                          <input className="input" value={editForm.name}
                            onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Host</label>
                          <input className="input" value={editForm.host}
                            onChange={(e) => setEditForm({ ...editForm, host: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Port</label>
                          <input className="input" value={editForm.port}
                            onChange={(e) => setEditForm({ ...editForm, port: e.target.value })} />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Username</label>
                        <input className="input" value={editForm.username}
                          onChange={(e) => setEditForm({ ...editForm, username: e.target.value })} />
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditId(null)}>Cancel</Button>
                        <Button size="sm" onClick={() => handleSaveEdit(vm.id)}>
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
