"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Deal {
  id: number;
  contact_id: number;
  title: string;
  stage: string;
  amount: number | null;
  currency: string;
  probability: number;
  assigned_agent_id: number | null;
  created_at: string;
}

interface Contact {
  id: number;
  name: string;
}

const STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"];
const STAGE_COLORS: Record<string, string> = {
  lead: "bg-blue-500/20 text-blue-400",
  qualified: "bg-yellow-500/20 text-yellow-400",
  proposal: "bg-purple-500/20 text-purple-400",
  negotiation: "bg-orange-500/20 text-orange-400",
  won: "bg-green-500/20 text-green-400",
  lost: "bg-red-500/20 text-red-400",
};

export default function DealsPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ contact_id: "", title: "", amount: "", currency: "USD" });

  const load = () => api.get<Deal[]>("/crm/deals").then(setDeals);
  useEffect(() => {
    load();
    api.get<Contact[]>("/crm/contacts").then(setContacts);
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/crm/deals", {
      contact_id: parseInt(form.contact_id),
      title: form.title,
      amount: form.amount ? parseFloat(form.amount) : null,
      currency: form.currency,
    });
    setForm({ contact_id: "", title: "", amount: "", currency: "USD" });
    setShowForm(false);
    load();
  };

  const handleMoveStage = async (dealId: number, stage: string) => {
    await api.put(`/crm/deals/${dealId}/stage?stage=${stage}`);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this deal?")) return;
    await api.delete(`/crm/deals/${id}`);
    load();
  };

  const contactName = (id: number) => contacts.find((c) => c.id === id)?.name || `#${id}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Deals Pipeline</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "New Deal"}</Button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <select value={form.contact_id} onChange={(e) => setForm({ ...form, contact_id: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required>
              <option value="">Select contact...</option>
              {contacts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input placeholder="Deal title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Amount" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" type="number" />
            <input placeholder="Currency" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <Button type="submit">Create Deal</Button>
        </form>
      )}

      {/* Pipeline view */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {STAGES.map((stage) => {
          const stageDeals = deals.filter((d) => d.stage === stage);
          const total = stageDeals.reduce((s, d) => s + (d.amount || 0), 0);
          return (
            <div key={stage} className="text-center p-3 rounded-lg border border-border">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">{stage}</p>
              <p className="text-xl font-bold">{stageDeals.length}</p>
              {total > 0 && <p className="text-xs text-muted-foreground">${total.toLocaleString()}</p>}
            </div>
          );
        })}
      </div>

      <div className="space-y-3">
        {deals.map((d) => (
          <div key={d.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{d.title}</p>
              <p className="text-sm text-muted-foreground">
                {contactName(d.contact_id)}
                {d.amount ? ` · ${d.currency} ${d.amount.toLocaleString()}` : ""}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={d.stage}
                onChange={(e) => handleMoveStage(d.id, e.target.value)}
                className={`text-xs px-2 py-1 rounded border-0 ${STAGE_COLORS[d.stage] || "bg-zinc-500/20 text-zinc-400"}`}
              >
                {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              <Button variant="outline" size="sm" onClick={() => handleDelete(d.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {deals.length === 0 && <p className="text-muted-foreground text-sm">No deals yet.</p>}
      </div>
    </div>
  );
}
