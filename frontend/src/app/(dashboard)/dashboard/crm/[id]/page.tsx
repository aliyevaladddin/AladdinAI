// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Mail, Phone, Building2, Tag,
  MessageSquare, TrendingUp, StickyNote, Clock,
  CircleDot, Pencil, Trash2, Check, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import MessageModal from "@/components/crm/MessageModal";

/* ── Types ───────────────────────────────────────────────────────── */

interface Contact {
  id: number; name: string; email: string | null; phone: string | null;
  company: string | null; tags: string[] | null; source: string | null;
  notes: string | null; created_at: string; updated_at: string;
}

interface Activity {
  id: number; type: string; channel: string | null;
  contact_id: number | null;
  subject: string | null; content: string | null; created_at: string;
}

interface Deal {
  id: number; title: string; stage: string; amount: number | null;
  currency: string; probability: number; notes: string | null;
  updated_at: string;
}
type TabId = "overview" | "messages" | "deals";

const STAGE_COLORS: Record<string, string> = {
  lead: "text-blue-400   bg-blue-500/10   border-blue-500/20",
  qualified: "text-cyan-400   bg-cyan-500/10   border-cyan-500/20",
  proposal: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  negotiation: "text-orange-400 bg-orange-500/10 border-orange-500/20",
  won: "text-green-400  bg-green-500/10  border-green-500/20",
  lost: "text-red-400    bg-red-500/10    border-red-500/20",
};

const ACTIVITY_ICON: Record<string, any> = {
  message_in: MessageSquare, message_out: MessageSquare,
  email_in: Mail, email_out: Mail, note: StickyNote, call: Phone,
};

/** Strip HTML tags and decode entities for plain-text preview */

function stripHtml(html: string): string {
  const doc = new DOMParser().parseFromString(html, "text/html");

  doc.querySelectorAll("script,style,noscript,template").forEach((node) => {
    node.remove();
  });

  return (doc.body.textContent || "")
    .replace(/\u00a0/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

/* ── Page ────────────────────────────────────────────────────────── */
export default function ContactPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [contact, setContact] = useState<Contact | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const [loading, setLoading] = useState(true);

  // Edit state
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "", email: "", phone: "", company: "", source: "", tags: "", notes: "",
  });
  const [saving, setSaving] = useState(false);


  const load = () => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      api.get<Contact>(`/crm/contacts/${id}`),
      api.get<Activity[]>(`/crm/contacts/${id}/activities`),
      api.get<Deal[]>(`/crm/contacts/${id}/deals`),
    ])
      .then(([c, a, d]) => {
        setContact(c); setActivities(a); setDeals(d);
        setEditForm({
          name: c.name ?? "",
          email: c.email ?? "",
          phone: c.phone ?? "",
          company: c.company ?? "",
          source: c.source ?? "",
          tags: (c.tags ?? []).join(", "),
          notes: c.notes ?? "",
        });
      })
      .catch(() => router.push("/dashboard/crm"))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);


  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await api.put(`/crm/contacts/${id}`, {
        name: editForm.name || undefined,
        email: editForm.email || null,
        phone: editForm.phone || null,
        company: editForm.company || null,
        source: editForm.source || null,
        tags: editForm.tags ? editForm.tags.split(",").map((t) => t.trim()).filter(Boolean) : null,
        notes: editForm.notes || null,
      });
      setEditing(false);
      load();
    } finally {
      setSaving(false);
    }
  };


  const handleDelete = async () => {
    if (!id || !confirm(`Delete contact "${contact?.name}"? This cannot be undone.`)) return;
    await api.delete(`/crm/contacts/${id}`);
    router.push("/dashboard/crm");
  };

  if (loading || !contact) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-6 h-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full" />
      </div>
    );
  }

  const initials = contact.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "overview", label: "Overview" },
    { id: "messages", label: "Messages", count: activities.length },
    { id: "deals", label: "Deals", count: deals.length },
  ];
  const pipelineValue = deals
    .filter((d) => !["won", "lost"].includes(d.stage))
    .reduce((s, d) => s + (d.amount ?? 0), 0);

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link
        href="/dashboard/crm"
        className="inline-flex items-center gap-1.5 text-xs font-medium transition-colors"
        style={{ color: "var(--color-fg-muted)" }}
      >
        <ArrowLeft size={13} /> Back to Contacts
      </Link>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <div
        className="rounded-2xl border p-6"
        style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}
      >
        {editing ? (
          /* ── Edit form ──────────────────────────────────────── */
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-bold">Edit contact</h2>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => setEditing(false)} disabled={saving}>
                  <X size={13} /> Cancel
                </Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  <Check size={13} /> {saving ? "Saving…" : "Save"}
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Name *</label>
                <input className="input" value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} required />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Company</label>
                <input className="input" value={editForm.company}
                  onChange={(e) => setEditForm({ ...editForm, company: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Email</label>
                <input className="input" type="email" value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Phone</label>
                <input className="input" value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Source</label>
                <input className="input" placeholder="website, referral…" value={editForm.source}
                  onChange={(e) => setEditForm({ ...editForm, source: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Tags <span className="opacity-40">(comma separated)</span></label>
                <input className="input" placeholder="vip, partner…" value={editForm.tags}
                  onChange={(e) => setEditForm({ ...editForm, tags: e.target.value })} />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Notes</label>
              <textarea className="input" rows={3} value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} />
            </div>
          </div>
        ) : (
          /* ── View mode ──────────────────────────────────────── */
          <div className="flex items-start gap-5">
            {/* Avatar */}
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center text-lg font-bold shrink-0"
              style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
            >
              {initials}
            </div>

            {/* Main info */}
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold">{contact.name}</h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1.5">
                {contact.company && (
                  <span className="flex items-center gap-1 text-xs" style={{ color: "var(--color-fg-muted)" }}>
                    <Building2 size={12} /> {contact.company}
                  </span>
                )}
                {contact.email && (
                  <a href={`mailto:${contact.email}`} className="flex items-center gap-1 text-xs hover:underline" style={{ color: "var(--color-fg-muted)" }}>
                    <Mail size={12} /> {contact.email}
                  </a>
                )}
                {contact.phone && (
                  <a href={`tel:${contact.phone}`} className="flex items-center gap-1 text-xs hover:underline" style={{ color: "var(--color-fg-muted)" }}>
                    <Phone size={12} /> {contact.phone}
                  </a>
                )}
              </div>
              {contact.tags && contact.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {contact.tags.map((t) => (
                    <span
                      key={t}
                      className="flex items-center gap-1 text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border"
                      style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}
                    >
                      <Tag size={8} /> {t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Right meta + actions */}
            <div className="shrink-0 flex flex-col items-end gap-3 text-right">
              <div className="flex items-center gap-1.5">
                <Button variant="outline" size="sm" onClick={() => setEditing(true)} className="gap-1.5">
                  <Pencil size={12} /> Edit
                </Button>
                <Button
                  variant="ghost" size="sm"
                  onClick={handleDelete}
                  className="gap-1.5 text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                >
                  <Trash2 size={12} /> Delete
                </Button>
              </div>
              {contact.source && (
                <span
                  className="text-[9px] font-bold uppercase px-2 py-1 rounded-lg border"
                  style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}
                >
                  {contact.source}
                </span>
              )}
              <p className="flex items-center gap-1 text-[10px]" style={{ color: "var(--color-fg-subtle)" }}>
                <Clock size={10} /> {new Date(contact.created_at).toLocaleDateString()}
              </p>
              <div className="flex gap-3 mt-1">
                {[
                  { label: "msgs", value: activities.length, color: "" },
                  { label: "deals", value: deals.length, color: "" },
                  { label: "won", value: deals.filter((d) => d.stage === "won").length, color: "var(--color-success)" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="text-center">
                    <p className="text-base font-bold" style={color ? { color } : {}}>{value}</p>
                    <p className="text-[9px] uppercase font-bold" style={{ color: "var(--color-fg-subtle)" }}>{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Tabs ───────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-1 p-1 rounded-xl w-fit"
        style={{ background: "var(--color-surface-2)", border: "1px solid var(--color-border)" }}
      >
        {tabs.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all"
              style={{
                background: active ? "var(--color-surface)" : "transparent",
                color: active ? "var(--color-fg)" : "var(--color-fg-muted)",
                boxShadow: active ? "0 1px 4px rgba(0,0,0,0.15)" : "none",
              }}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className="text-[10px] font-bold px-1.5 py-0.5 rounded-full"
                  style={{
                    background: active ? "var(--color-accent-soft)" : "var(--color-surface)",
                    color: active ? "var(--color-accent)" : "var(--color-fg-muted)",
                  }}
                >
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Overview ───────────────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-4">
          {pipelineValue > 0 && (
            <div
              className="rounded-2xl border p-5"
              style={{ background: "var(--color-accent-soft)", borderColor: "var(--color-accent)" }}
            >
              <p className="text-[10px] font-bold uppercase" style={{ color: "var(--color-accent)" }}>Active pipeline value</p>
              <p className="text-2xl font-bold mt-1">
                {deals.find((d) => !["won", "lost"].includes(d.stage))?.currency ?? "USD"}{" "}
                {pipelineValue.toLocaleString()}
              </p>
            </div>
          )}
          <div
            className="rounded-2xl border p-5"
            style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}
          >
            <h3 className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--color-fg-muted)" }}>Notes</h3>
            {contact.notes ? (
              <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--color-fg-muted)" }}>{contact.notes}</p>
            ) : (
              <p className="text-xs italic" style={{ color: "var(--color-fg-subtle)" }}>
                No notes yet.{" "}
                <button onClick={() => setEditing(true)} className="underline hover:opacity-80">Add one</button>
              </p>
            )}
          </div>
          {deals.length > 0 && (
            <div
              className="rounded-2xl border p-5"
              style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}
            >
              <h3 className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--color-fg-muted)" }}>Latest deal</h3>
              <DealRow deal={deals[0]} />
            </div>
          )}
          {deals.length === 0 && activities.length === 0 && !contact.notes && (
            <div
              className="rounded-2xl border p-10 text-center"
              style={{ borderColor: "var(--color-border)", borderStyle: "dashed" }}
            >
              <p className="text-sm font-medium mb-1">No activity yet</p>
              <p className="text-xs" style={{ color: "var(--color-fg-muted)" }}>
                Messages, deals and notes will appear here once created.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Messages ───────────────────────────────────────────── */}
      {activeTab === "messages" && (
        <div
          className="rounded-2xl border overflow-hidden"
          style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}
        >
          {activities.length === 0 ? (
            <div className="py-16 text-center opacity-40">
              <MessageSquare size={32} className="mx-auto mb-2 stroke-1" />
              <p className="text-xs italic">No messages with this contact yet</p>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--color-border)" }}>
              {activities.map((a) => {
                const Icon = ACTIVITY_ICON[a.type] ?? CircleDot;
                const isInbound = a.type.endsWith("_in");
                const plainContent = stripHtml(a.content ?? "");
                return (
                  <button
                    key={a.id}
                    onClick={() => setSelectedActivity(a)}
                    className="w-full flex gap-4 px-5 py-4 text-left hover:bg-[var(--color-surface-2)] transition-colors group"
                  >
                    <div className={`mt-0.5 w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${isInbound ? "bg-blue-500/10 text-blue-400" : "bg-green-500/10 text-green-400"}`}>
                      <Icon size={13} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[9px] font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                          {a.type.replace(/_/g, " ")}
                        </span>
                        {a.channel && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded font-mono uppercase border"
                            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}>
                            {a.channel}
                          </span>
                        )}
                      </div>
                      {a.subject && <p className="text-sm font-medium">{a.subject}</p>}
                      {plainContent && (
                        <p className="text-xs mt-0.5 line-clamp-2" style={{ color: "var(--color-fg-muted)" }}>
                          {plainContent}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      <p className="text-[10px] font-mono" style={{ color: "var(--color-fg-subtle)" }}>
                        {new Date(a.created_at).toLocaleDateString()}
                      </p>
                      <span className="text-[9px] opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--color-accent)" }}>
                        open →
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Deals ──────────────────────────────────────────────── */}
      {activeTab === "deals" && (
        <div className="space-y-3">
          {deals.length === 0 ? (
            <div className="rounded-2xl border py-16 text-center"
              style={{ borderColor: "var(--color-border)", borderStyle: "dashed" }}>
              <TrendingUp size={32} className="mx-auto mb-2 stroke-1 opacity-30" />
              <p className="text-xs italic" style={{ color: "var(--color-fg-muted)" }}>No deals linked to this contact</p>
            </div>
          ) : (
            deals.map((d) => (
              <div key={d.id} className="rounded-2xl border p-5"
                style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}>
                <DealRow deal={d} />
              </div>
            ))
          )}
        </div>
      )}

      {/* ── Message Modal ──────────────────────────────────────── */}
      {selectedActivity && (
        <MessageModal
          activity={selectedActivity}
          contactEmail={contact.email}
          onClose={() => setSelectedActivity(null)}
        />
      )}
    </div>
  );
}

/* ── Deal row ────────────────────────────────────────────────────── */

function DealRow({ deal }: { deal: Deal }) {
  const stageClass = STAGE_COLORS[deal.stage] ?? "";
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="font-medium text-sm">{deal.title}</p>
        {deal.notes && <p className="text-xs mt-0.5 line-clamp-1" style={{ color: "var(--color-fg-muted)" }}>{deal.notes}</p>}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {deal.amount != null && (
          <span className="text-sm font-bold font-mono">{deal.currency} {deal.amount.toLocaleString()}</span>
        )}
        <span className={`text-[9px] font-bold uppercase px-2 py-1 rounded-lg border ${stageClass}`}>{deal.stage}</span>
        {deal.probability > 0 && (
          <span className="text-[10px]" style={{ color: "var(--color-fg-muted)" }}>{deal.probability}%</span>
        )}
      </div>
    </div>
  );
}
