// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Plus, X, Trash2, Webhook, Pencil, Zap, Loader2, Check, CircleAlert } from "lucide-react";


interface WebhookItem {
  id: number;
  name: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}

const AVAILABLE_EVENTS = [
  { id: "message_received", label: "Message Received" },
  { id: "message_sent", label: "Message Sent" },
  { id: "contact_created", label: "Contact Created" },
  { id: "deal_created", label: "Deal Created" },
  { id: "deal_updated", label: "Deal Updated" },
  { id: "order_created", label: "Order Created" },
  { id: "order_status_changed", label: "Order Status Changed" },
];

const EMPTY_FORM = {
  name: "",
  url: "",
  secret: "",
  events: [] as string[],
  is_active: true,
  removeSecret: false,
};

type TestState = "loading" | "ok" | "fail";


export function WebhooksPanel() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [testState, setTestState] = useState<Record<number, TestState>>({});
  const [saving, setSaving] = useState(false);


  const load = () => api.get<WebhookItem[]>("/webhooks/outgoing", { bypassCache: true }).then(setWebhooks);
  useEffect(() => { load(); }, []);


  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
  };


  const startEdit = (w: WebhookItem) => {
    setForm({ name: w.name, url: w.url, secret: "", events: w.events, is_active: w.is_active, removeSecret: false });
    setEditingId(w.id);
    setShowForm(true);
  };


  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId !== null) {
        const body: Record<string, unknown> = {
          name: form.name,
          url: form.url,
          events: form.events,
          is_active: form.is_active,
        };
        // Secret is three-state on update: omitted → keep current,
        // empty string → remove signing, value → rotate.
        if (form.removeSecret) body.secret = "";
        else if (form.secret) body.secret = form.secret;
        await api.put(`/webhooks/outgoing/${editingId}`, body);
      } else {
        await api.post("/webhooks/outgoing", {
          name: form.name,
          url: form.url,
          secret: form.secret || undefined,
          events: form.events,
          is_active: form.is_active,
        });
      }
      closeForm();
      load();
    } finally {
      setSaving(false);
    }
  };


  const handleDelete = async (id: number) => {
    if (!confirm("Delete this webhook?")) return;
    await api.delete(`/webhooks/outgoing/${id}`);
    load();
  };


  const handleTest = async (id: number) => {
    setTestState((prev) => ({ ...prev, [id]: "loading" }));
    try {
      await api.post(`/webhooks/outgoing/${id}/test`);
      setTestState((prev) => ({ ...prev, [id]: "ok" }));
    } catch {
      setTestState((prev) => ({ ...prev, [id]: "fail" }));
    }
    setTimeout(() => {
      setTestState((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }, 5000);
  };


  const toggleEvent = (eventId: string) => {
    setForm((prev) => ({
      ...prev,
      events: prev.events.includes(eventId)
        ? prev.events.filter((id) => id !== eventId)
        : [...prev.events, eventId],
    }));
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Webhook size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">Outgoing Webhooks</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Send real-time notifications to external systems</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => (showForm ? closeForm() : setShowForm(true))} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Webhook</>}
        </Button>
      </div>

      {/* Form (create + edit) */}
      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
          <div className="text-xs font-semibold text-[var(--color-fg-muted)] uppercase tracking-wide">
            {editingId !== null ? "Edit Webhook" : "New Webhook"}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
              <input className="input" placeholder="e.g. My Zapier Hook" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Webhook URL</label>
              <input className="input" type="url" placeholder="https://hooks.zapier.com/..." value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })} required />
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Events</label>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_EVENTS.map((event) => (
                <label key={event.id} className="flex items-center gap-2 p-2 rounded-lg border border-[var(--color-border)] hover:bg-[var(--color-surface)] cursor-pointer text-xs">
                  <input type="checkbox" checked={form.events.includes(event.id)} onChange={() => toggleEvent(event.id)} className="rounded" />
                  {event.label}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">
              Secret <span className="opacity-40">(optional — needed only for RCF signature verification; Zapier hooks work without it)</span>
            </label>
            <input className="input" type="password" value={form.secret}
              placeholder={editingId !== null ? "•••••• (leave empty to keep current)" : "Signature secret"}
              onChange={(e) => setForm({ ...form, secret: e.target.value })} />
            {editingId !== null && (
              <label className="flex items-center gap-2 text-xs text-[var(--color-fg-muted)] cursor-pointer">
                <input type="checkbox" checked={form.removeSecret}
                  onChange={(e) => setForm({ ...form, removeSecret: e.target.checked, secret: "" })} className="rounded" />
                Remove secret (deliver without RCF signing)
              </label>
            )}
          </div>
          <label className="flex items-center gap-2 text-xs text-[var(--color-fg-muted)] cursor-pointer">
            <input type="checkbox" checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="rounded" />
            Active (inactive webhooks are skipped by automatic events and agent sends)
          </label>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={closeForm}>Cancel</Button>
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? <Loader2 size={13} className="animate-spin" /> : null}
              {editingId !== null ? "Save Changes" : "Create Webhook"}
            </Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {webhooks.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">No outgoing webhooks configured</div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {webhooks.map((w) => {
              const state = testState[w.id];
              return (
                <div key={w.id} className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-fg)]">{w.name}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${w.is_active ? "bg-green-500/15 text-green-400" : "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]"}`}>
                        {w.is_active ? "Active" : "Inactive"}
                      </span>
                      {state === "ok" && (
                        <span className="flex items-center gap-1 text-[10px] text-green-400"><Check size={11} /> delivered</span>
                      )}
                      {state === "fail" && (
                        <span className="flex items-center gap-1 text-[10px] text-[var(--color-danger)]"><CircleAlert size={11} /> delivery failed</span>
                      )}
                    </div>
                    <p className="text-xs font-mono text-[var(--color-fg-subtle)] truncate mt-0.5">{w.url}</p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {w.events.map((ev) => (
                        <span key={ev} className="text-[9px] bg-[var(--color-surface-2)] border border-[var(--color-border)] px-1.5 py-0.5 rounded font-mono text-[var(--color-fg-muted)] uppercase">
                          {ev.replace("_", " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="icon-sm" onClick={() => handleTest(w.id)} disabled={state === "loading"}
                      title="Send a test event to this webhook"
                      className="text-[var(--color-fg-subtle)] hover:text-[var(--color-accent)]">
                      {state === "loading" ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => startEdit(w)}
                      title="Edit webhook"
                      className="text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]">
                      <Pencil size={13} />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDelete(w.id)}
                      className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]">
                      <Trash2 size={13} />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
