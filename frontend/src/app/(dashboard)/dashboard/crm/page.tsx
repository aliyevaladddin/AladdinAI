"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Contact {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  tags: string[] | null;
  source: string | null;
  created_at: string;
}

export default function CRMPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", company: "", source: "" });

  const load = () => api.get<Contact[]>(`/crm/contacts${search ? `?search=${search}` : ""}`).then(setContacts);
  useEffect(() => { load(); }, [search]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/crm/contacts", {
      ...form,
      email: form.email || null,
      phone: form.phone || null,
      company: form.company || null,
      source: form.source || null,
    });
    setForm({ name: "", email: "", phone: "", company: "", source: "" });
    setShowForm(false);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this contact?")) return;
    await api.delete(`/crm/contacts/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Contacts</h2>
        <Button onClick={() => setShowForm(!showForm)}>{showForm ? "Cancel" : "Add Contact"}</Button>
      </div>

      <input
        placeholder="Search contacts..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mb-4"
      />

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border border-border p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
            <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
            <input placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
            <input placeholder="Source" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
          </div>
          <Button type="submit">Create</Button>
        </form>
      )}

      <div className="space-y-3">
        {contacts.map((c) => (
          <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-sm text-muted-foreground">
                {[c.email, c.phone, c.company].filter(Boolean).join(" · ") || "No details"}
              </p>
              {c.tags && c.tags.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {c.tags.map((t) => (
                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">{t}</span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-2">
              {c.source && <span className="text-xs text-muted-foreground">{c.source}</span>}
              <Button variant="outline" size="sm" onClick={() => handleDelete(c.id)}>Delete</Button>
            </div>
          </div>
        ))}
        {contacts.length === 0 && <p className="text-muted-foreground text-sm">No contacts yet.</p>}
      </div>
    </div>
  );
}
