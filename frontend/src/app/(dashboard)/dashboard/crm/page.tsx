"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
  notes: string | null;
  created_at: string;
}

const EMPTY_FORM = {
  name: "",
  email: "",
  phone: "",
  company: "",
  source: "",
  tags: "",
  notes: "",
};

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [search, setSearch] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.get<Contact[]>("/crm/contacts");
      setContacts(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const tags = form.tags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    await api.post("/crm/contacts", {
      name: form.name,
      email: form.email || null,
      phone: form.phone || null,
      company: form.company || null,
      source: form.source || null,
      tags: tags.length ? tags : null,
      notes: form.notes || null,
    });
    setForm(EMPTY_FORM);
    setShowForm(false);
    load();
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this contact?")) return;
    await api.delete(`/crm/contacts/${id}`);
    load();
  };

  const filtered = contacts.filter((c) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      (c.email ?? "").toLowerCase().includes(q) ||
      (c.company ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Contacts</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {contacts.length} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/dashboard/deals">
            <Button variant="outline">Deals</Button>
          </Link>
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "New Contact"}
          </Button>
        </div>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-6 rounded-lg border border-border p-4 space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              required
            />
            <input
              placeholder="Company"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <input
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Source (e.g. website, referral)"
              value={form.source}
              onChange={(e) => setForm({ ...form, source: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <input
              placeholder="Tags (comma separated)"
              value={form.tags}
              onChange={(e) => setForm({ ...form, tags: e.target.value })}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <textarea
            placeholder="Notes"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            rows={3}
          />
          <Button type="submit">Create Contact</Button>
        </form>
      )}

      <div className="mb-4">
        <input
          placeholder="Search by name, email, or company…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
        />
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-border p-4"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium truncate">{c.name}</p>
                  {c.company && (
                    <span className="text-xs text-muted-foreground">
                      · {c.company}
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground truncate">
                  {[c.email, c.phone].filter(Boolean).join(" · ") || "—"}
                </p>
                {c.tags && c.tags.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {c.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {c.source && (
                  <span className="text-xs px-2 py-1 rounded bg-zinc-500/20 text-zinc-400">
                    {c.source}
                  </span>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(c.id)}
                >
                  Delete
                </Button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-muted-foreground text-sm">
              {contacts.length === 0
                ? "No contacts yet."
                : "No contacts match your search."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
