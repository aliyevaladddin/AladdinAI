// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Plus, X, Trash2, Webhook } from "lucide-react";


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
  { id: "deal_created", label: "Deal Created" },
  { id: "deal_updated", label: "Deal Updated" },
  { id: "contact_created", label: "Contact Created" },
];


export function WebhooksPanel() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", secret: "", events: [] as string[], is_active: true });


  const load = () => api.get<WebhookItem[]>("/webhooks/outgoing").then(setWebhooks);
  useEffect(() => { load(); }, []);


  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/webhooks/outgoing", form);
    setForm({ name: "", url: "", secret: "", events: [], is_active: true });
    setShowForm(false);
    load();
  };


  const handleDelete = async (id: number) => {
    if (!confirm("Delete this webhook?")) return;
    await api.delete(`/webhooks/outgoing/${id}`);
    load();
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
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Webhook</>}
        </Button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
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
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Secret <span className="opacity-40">(optional)</span></label>

            <input className="input" type="password" placeholder="Signature secret" value={form.secret}
              onChange={(e) => setForm({ ...form, secret: e.target.value })} />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" size="sm">Create Webhook</Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {webhooks.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">No outgoing webhooks configured</div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {webhooks.map((w) => (
              <div key={w.id} className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--color-fg)]">{w.name}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${w.is_active ? "bg-green-500/15 text-green-400" : "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]"}`}>
                      {w.is_active ? "Active" : "Inactive"}
                    </span>
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
                <Button variant="ghost" size="icon-sm" onClick={() => handleDelete(w.id)}
                  className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)] shrink-0">
                  <Trash2 size={13} />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
