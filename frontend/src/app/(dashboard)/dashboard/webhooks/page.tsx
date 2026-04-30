// NOTICE: This file is protected under RCF-PL v1.2.8
// [RCF:PROTECTED]
"use client";

import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Webhook {
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

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    url: "",
    secret: "",
    events: [] as string[],
    is_active: true,
  });

  const load = () => api.get<Webhook[]>("/webhooks/outgoing").then(setWebhooks);
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    if (form.events.length === 0) {
      alert("Please select at least one event.");
      return;
    }
    await api.post("/webhooks/outgoing", form);
    setForm({ name: "", url: "", secret: "", events: [], is_active: true });
    setShowForm(false);
    load();
  };

  const handleDelete = async (id: number): Promise<void> => {
    if (!confirm("Delete this webhook integration?")) return;
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
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Outgoing Webhooks</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Send real-time notifications to your external systems
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "Add Webhook"}
        </Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-5 space-y-4 max-w-2xl">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Integration Name</label>
              <input
                placeholder="e.g. My Zapier Hook"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Webhook URL</label>
              <input
                placeholder="https://hooks.zapier.com/..."
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                required
                type="url"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Events to Subscribe</label>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_EVENTS.map((event) => (
                <label key={event.id} className="flex items-center gap-2 p-2 rounded-md border border-border hover:bg-accent cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.events.includes(event.id)}
                    onChange={() => toggleEvent(event.id)}
                    className="rounded border-input text-primary"
                  />
                  <span className="text-sm">{event.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Secret (Optional)</label>
            <input
              placeholder="Signature secret"
              value={form.secret}
              onChange={(e) => setForm({ ...form, secret: e.target.value })}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              type="password"
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              Used to sign payloads for security verification.
            </p>
          </div>

          <Button type="submit">Create Integration</Button>
        </form>
      )}

      <div className="space-y-3">
        {webhooks.map((w) => (
          <div key={w.id} className="rounded-lg border border-border p-4 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <p className="font-medium">{w.name}</p>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${w.is_active ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>
                  {w.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground truncate max-w-md">{w.url}</p>
              <div className="flex flex-wrap gap-1 mt-1">
                {w.events.map((e) => (
                  <span key={e} className="text-[9px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground uppercase font-mono">
                    {e.replace("_", " ")}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => handleDelete(w.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {webhooks.length === 0 && (
          <p className="text-muted-foreground text-sm py-8 text-center border border-dashed rounded-lg">
            No outgoing webhooks configured.
          </p>
        )}
      </div>
    </div>
  );
}
