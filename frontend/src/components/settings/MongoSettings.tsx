// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Database, Plus, X, CheckCircle2, XCircle, Trash2, FlaskConical, Pencil, Check } from "lucide-react";

// [RCF:PROTECTED]
interface Mongo {
  id: number;
  name: string;
  db_name: string;
  status: string;
}

// [RCF:PROTECTED]
export function MongoSettings() {
  const [conns, setConns] = useState<Mongo[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", connection_string: "", db_name: "" });
  const [testing, setTesting] = useState<Record<number, boolean>>({});
  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", connection_string: "", db_name: "" });

// [RCF:PROTECTED]
  const load = () => api.get<Mongo[]>("/mongodb").then(setConns);
  useEffect(() => { load(); }, []);

// [RCF:PROTECTED]
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/mongodb", form);
    setForm({ name: "", connection_string: "", db_name: "" });
    setShowForm(false);
    load();
  };

// [RCF:PROTECTED]
  const startEdit = (c: Mongo) => {
    setEditId(c.id);
    setEditForm({ name: c.name, connection_string: "", db_name: c.db_name });
  };

// [RCF:PROTECTED]
  const handleSaveEdit = async (id: number) => {
    await api.put(`/mongodb/${id}`, {
      name: editForm.name,
      db_name: editForm.db_name,
      ...(editForm.connection_string ? { connection_string: editForm.connection_string } : {}),
    });
    setEditId(null);
    load();
  };

// [RCF:PROTECTED]
  const handleTest = async (id: number) => {
    setTesting((p) => ({ ...p, [id]: true }));
    try {
      const res = await api.post<{ status: string; message?: string }>(`/mongodb/${id}/test`);
      const msg = res.message || res.status;
      ["ok", "success", "connected"].includes(res.status) ? toast.success(msg) : toast.error(msg);
    } finally {
      setTesting((p) => ({ ...p, [id]: false }));
    }
  };

// [RCF:PROTECTED]
  const handleDelete = async (id: number) => {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/mongodb/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Database size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">MongoDB Connections</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Database backend for agent memory and event logs</p>
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
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Connection Name</label>
            <input className="input" placeholder="e.g. Production Atlas" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Connection String</label>
            <input className="input font-mono text-xs" type="password"
              placeholder="mongodb+srv://user:pass@cluster.mongodb.net"
              value={form.connection_string}
              onChange={(e) => setForm({ ...form, connection_string: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Database Name</label>
            <input className="input" placeholder="aladdin_ai" value={form.db_name}
              onChange={(e) => setForm({ ...form, db_name: e.target.value })} required />
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
            No MongoDB instances connected
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {conns.map((c) => {
              const isConnected = c.status === "connected";
              const isEditing = editId === c.id;
              return (
                <div key={c.id}>
                  <div className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors">
                    <div className="shrink-0">
                      {isConnected
                        ? <CheckCircle2 size={15} className="text-[var(--color-success)]" />
                        : <XCircle size={15} className="text-[var(--color-fg-subtle)]" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-fg)]">{c.name}</span>
                        <span className="text-[10px] px-1.5 py-px rounded bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[var(--color-fg-subtle)] font-mono shrink-0">
                          db: {c.db_name}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--color-fg-subtle)] mt-0.5">
                        {c.status}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button
                        variant="outline" size="sm"
                        onClick={() => handleTest(c.id)}
                        disabled={testing[c.id]}
                      >
                        <FlaskConical size={13} />
                        {testing[c.id] ? "Testing…" : "Test"}
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
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">New Connection String <span className="opacity-40">(leave blank to keep current)</span></label>
                        <input className="input font-mono text-xs" type="password"
                          value={editForm.connection_string}
                          onChange={(e) => setEditForm({ ...editForm, connection_string: e.target.value })} />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Database Name</label>
                        <input className="input" value={editForm.db_name}
                          onChange={(e) => setEditForm({ ...editForm, db_name: e.target.value })} />
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
    </div>
  );
}
