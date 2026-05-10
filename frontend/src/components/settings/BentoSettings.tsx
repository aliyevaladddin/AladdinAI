"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Server, Plus, X, CheckCircle2, XCircle, Loader2,
  Trash2, FlaskConical, Rocket, Pencil, Check
} from "lucide-react";

interface BentoML {
  id: number;
  name: string;
  endpoint_url: string;
  status: string;
}

interface VM {
  id: number;
  name: string;
  host: string;
  username: string;
}

export function BentoSettings() {
  const [conns, setConns] = useState<BentoML[]>([]);
  const [vms, setVms] = useState<VM[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", endpoint_url: "", api_key: "" });
  const [testing, setTesting] = useState<Record<number, boolean>>({});

  const [deployingId, setDeployingId] = useState<number | null>(null);
  const [showDeployModal, setShowDeployModal] = useState<number | null>(null);
  const [deployForm, setDeployForm] = useState({ vm_id: "", service_name: "my_service:svc", port: "3000" });

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", endpoint_url: "", api_key: "" });

  const load = () => {
    api.get<BentoML[]>("/bentoml").then(setConns);
    api.get<VM[]>("/ssh/vms-list").then(setVms);
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/bentoml", form);
    setForm({ name: "", endpoint_url: "", api_key: "" });
    setShowForm(false);
    load();
  };

  const startEdit = (c: BentoML) => {
    setEditId(c.id);
    setEditForm({ name: c.name, endpoint_url: c.endpoint_url, api_key: "" });
  };

  const handleSaveEdit = async (id: number) => {
    await api.put(`/bentoml/${id}`, {
      name: editForm.name,
      endpoint_url: editForm.endpoint_url,
      ...(editForm.api_key ? { api_key: editForm.api_key } : {}),
    });
    setEditId(null);
    load();
  };

  const handleTest = async (id: number) => {
    setTesting((p) => ({ ...p, [id]: true }));
    try {
      const res = await api.post<{ status: string; message?: string }>(`/bentoml/${id}/test`);
      const msg = res.message || `Status: ${res.status}`;
      ["ok", "success", "connected"].includes(res.status) ? toast.success(msg) : toast.error(msg);
      load();
    } catch {
      toast.error("Test failed");
    } finally {
      setTesting((p) => ({ ...p, [id]: false }));
    }
  };

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showDeployModal) return;
    setDeployingId(showDeployModal);
    try {
      const res = await api.post<{ status: string; message?: string; endpoint_url?: string }>(
        `/bentoml/${showDeployModal}/deploy`,
        { vm_id: parseInt(deployForm.vm_id), service_name: deployForm.service_name, port: parseInt(deployForm.port) }
      );
      if (res.status === "deployed") {
        toast.success(`Deployed to ${res.endpoint_url}`);
        setShowDeployModal(null);
      } else {
        toast.error(`Deploy failed: ${res.message}`);
      }
      load();
    } catch {
      toast.error("Deploy request failed");
    } finally {
      setDeployingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/bentoml/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Server size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">BentoML Orchestration</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Manage and deploy model serving instances</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Connection</>}
        </Button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
            <input className="input" placeholder="e.g. Production LLM" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Endpoint URL</label>
            <input className="input" placeholder="http://your-server:3000" value={form.endpoint_url}
              onChange={(e) => setForm({ ...form, endpoint_url: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">API Key <span className="opacity-40">(optional)</span></label>
            <input className="input" type="password" placeholder="••••••••" value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
          </div>
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" size="sm">Save Connection</Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {conns.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">
            No BentoML instances configured
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {conns.map((c) => {
              const isLive = ["connected", "deployed"].includes(c.status);
              const isEditing = editId === c.id;
              return (
                <div key={c.id}>
                  <div className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors">
                    <div className="shrink-0">
                      {isLive
                        ? <CheckCircle2 size={15} className="text-[var(--color-success)]" />
                        : <XCircle size={15} className="text-[var(--color-fg-subtle)]" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-fg)]">{c.name}</span>
                        <span className={`text-[10px] px-1.5 py-px rounded border font-mono shrink-0 ${
                          isLive
                            ? "bg-[var(--color-success-soft)] border-transparent text-[var(--color-success)]"
                            : "bg-[var(--color-surface-2)] border-[var(--color-border)] text-[var(--color-fg-subtle)]"
                        }`}>
                          {c.status}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--color-fg-subtle)] font-mono mt-0.5 truncate">{c.endpoint_url}</div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button variant="outline" size="sm" onClick={() => handleTest(c.id)} disabled={testing[c.id]}>
                        <FlaskConical size={13} />
                        {testing[c.id] ? "Testing…" : "Test"}
                      </Button>
                      <Button
                        variant="outline" size="sm"
                        onClick={() => {
                          setShowDeployModal(c.id);
                          if (vms.length > 0 && !deployForm.vm_id)
                            setDeployForm({ ...deployForm, vm_id: vms[0].id.toString() });
                        }}
                      >
                        <Rocket size={13} /> Deploy
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => isEditing ? setEditId(null) : startEdit(c)}
                        title="Edit"
                        className={isEditing ? "text-[var(--color-accent)]" : "text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"}
                      >
                        <Pencil size={13} />
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => handleDelete(c.id)}
                        title="Delete"
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>

                  {/* Inline edit */}
                  {isEditing && (
                    <div className="px-4 py-3 bg-[var(--color-surface-2)] border-t border-[var(--color-border)] space-y-3">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
                        <input className="input" value={editForm.name}
                          onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Endpoint URL</label>
                        <input className="input" value={editForm.endpoint_url}
                          onChange={(e) => setEditForm({ ...editForm, endpoint_url: e.target.value })} />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">New API Key <span className="opacity-40">(leave blank to keep current)</span></label>
                        <input className="input" type="password" placeholder="••••••••"
                          value={editForm.api_key}
                          onChange={(e) => setEditForm({ ...editForm, api_key: e.target.value })} />
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditId(null)}>Cancel</Button>
                        <Button size="sm" onClick={() => handleSaveEdit(c.id)}>
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

      {/* Deploy Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
          <div className="w-full max-w-md rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Rocket size={16} className="text-[var(--color-accent)]" />
                <h3 className="text-sm font-semibold">Remote Deployment</h3>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={() => setShowDeployModal(null)}>
                <X size={15} />
              </Button>
            </div>

            <form onSubmit={handleDeploy} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--color-fg-muted)]">Target VM</label>
                <select className="input" value={deployForm.vm_id}
                  onChange={(e) => setDeployForm({ ...deployForm, vm_id: e.target.value })} required>
                  <option value="" disabled>Select a VM…</option>
                  {vms.map((vm) => (
                    <option key={vm.id} value={vm.id}>{vm.name} ({vm.username}@{vm.host})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--color-fg-muted)]">Service Identifier</label>
                  <input className="input font-mono text-xs" placeholder="service:svc"
                    value={deployForm.service_name}
                    onChange={(e) => setDeployForm({ ...deployForm, service_name: e.target.value })} required />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--color-fg-muted)]">Port</label>
                  <input className="input" type="number" value={deployForm.port}
                    onChange={(e) => setDeployForm({ ...deployForm, port: e.target.value })} required />
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--color-border)]">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowDeployModal(null)} disabled={!!deployingId}>Cancel</Button>
                <Button type="submit" size="sm" disabled={!!deployingId || !deployForm.vm_id}>
                  {deployingId ? <><Loader2 size={13} className="animate-spin" /> Deploying…</> : <><Rocket size={13} /> Start Deployment</>}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
