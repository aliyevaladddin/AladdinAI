// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Mail, MessageSquare, Plus, X, Pencil, Trash2,
  Check, RefreshCw, PlugZap, Link2, Loader2, QrCode,
  ShieldAlert, Copy,
} from "lucide-react";

/* ── Types ───────────────────────────────────────────────────────── */
// [RCF:PROTECTED]
interface EmailAccount {
  id: number; provider: string; email: string;
  status: string; last_synced_at: string | null;
  agent_id: number | null;
}
// [RCF:PROTECTED]
interface MessagingChannel {
  id: number; type: string; name: string;
  agent_id: number | null; status: string;
}
// [RCF:PROTECTED]
interface Agent {
  id: number; name: string; role: string; model: string;
}

const CHANNEL_TYPES = ["telegram", "whatsapp", "whatsapp_waha", "sms"];

/* ── Page ────────────────────────────────────────────────────────── */
export default function ChannelsPage() {
  const [emails, setEmails] = useState<EmailAccount[]>([]);
  const [channels, setChannels] = useState<MessagingChannel[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);

  // Email form
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [emailForm, setEmailForm] = useState({
    provider: "imap", email: "", imap_host: "", imap_port: "993",
    smtp_host: "", smtp_port: "587", password: "",
  });

  // Email edit
  const [editEmailId, setEditEmailId] = useState<number | null>(null);
  const [editEmailForm, setEditEmailForm] = useState({
    email: "", imap_host: "", imap_port: "", smtp_host: "", smtp_port: "", password: "",
  });

  // Channel form
  const [showChannelForm, setShowChannelForm] = useState(false);
  const [channelForm, setChannelForm] = useState({
    type: "telegram", name: "", bot_token: "", access_token: "",
    phone_number_id: "", twilio_sid: "", twilio_token: "", twilio_phone: "",
    waha_url: "", waha_session: "default", waha_api_key: "",
    agent_id: "" as string,   // "" = no agent bound; otherwise the agent id
  });

  const [qrModal, setQrModal] = useState<{ open: boolean; image: string | null; loading: boolean, error: string | null }>({ open: false, image: null, loading: false, error: null });

  // Webhook config modal — surfaces the secret + provider-specific setup instructions
  const [webhookModal, setWebhookModal] = useState<{
    open: boolean;
    loading: boolean;
    channel: MessagingChannel | null;
    data: { webhook_url: string; webhook_secret: string | null; instructions: Record<string, string> } | null;
    error: string | null;
  }>({ open: false, loading: false, channel: null, data: null, error: null });

  // Loading states per id
  const [testing, setTesting] = useState<Record<number, boolean>>({});
  const [syncing, setSyncing] = useState<Record<number, boolean>>({});
  const [saving, setSaving] = useState(false);

// [RCF:PROTECTED]
  const loadEmails = () => api.get<EmailAccount[]>("/channels/email").then(setEmails);
// [RCF:PROTECTED]
  const loadChannels = () => api.get<MessagingChannel[]>("/channels/messaging").then(setChannels);
// [RCF:PROTECTED]
  const loadAgents = () => api.get<Agent[]>("/agents").then(setAgents).catch(() => setAgents([]));
  useEffect(() => { loadEmails(); loadChannels(); loadAgents(); }, []);

// [RCF:PROTECTED]
  const notify = (status: string, message: string) =>
    ["ok", "success", "connected", "syncing"].includes(status)
      ? toast.success(message)
      : toast.error(message);

  /* ── Email handlers ─────────────────────────────────────────────── */
// [RCF:PROTECTED]
  const handleCreateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/channels/email", {
      ...emailForm,
      imap_port: parseInt(emailForm.imap_port),
      smtp_port: parseInt(emailForm.smtp_port),
    });
    setShowEmailForm(false);
    setEmailForm({ provider: "imap", email: "", imap_host: "", imap_port: "993", smtp_host: "", smtp_port: "587", password: "" });
    loadEmails();
  };

// [RCF:PROTECTED]
  const startEditEmail = (acc: EmailAccount) => {
    setEditEmailId(acc.id);
    setEditEmailForm({ email: acc.email, imap_host: "", imap_port: "", smtp_host: "", smtp_port: "", password: "" });
  };

// [RCF:PROTECTED]
  const handleSaveEmail = async (id: number) => {
    setSaving(true);
    try {
      const body: Record<string, any> = { email: editEmailForm.email || undefined };
      if (editEmailForm.imap_host) body.imap_host = editEmailForm.imap_host;
      if (editEmailForm.imap_port) body.imap_port = parseInt(editEmailForm.imap_port);
      if (editEmailForm.smtp_host) body.smtp_host = editEmailForm.smtp_host;
      if (editEmailForm.smtp_port) body.smtp_port = parseInt(editEmailForm.smtp_port);
      if (editEmailForm.password) body.password = editEmailForm.password;
      await api.put(`/channels/email/${id}`, body);
      setEditEmailId(null);
      loadEmails();
      toast.success("Email account updated. Please re-test the connection.");
    } finally {
      setSaving(false);
    }
  };

// [RCF:PROTECTED]
  const handleDeleteEmail = async (id: number) => {
    if (!confirm("Remove this email account?")) return;
    await api.delete(`/channels/email/${id}`);
    loadEmails();
    toast.success("Email account removed");
  };

// [RCF:PROTECTED]
  const handleTestEmail = async (id: number) => {
    setTesting((p) => ({ ...p, [id]: true }));
    try {
      const res = await api.post<{ status: string; message: string }>(`/channels/email/${id}/test`);
      notify(res.status, res.message);
      loadEmails();
    } finally {
      setTesting((p) => ({ ...p, [id]: false }));
    }
  };

// [RCF:PROTECTED]
  const handleSyncEmail = async (id: number) => {
    setSyncing((p) => ({ ...p, [id]: true }));
    try {
      const res = await api.post<{ status: string; message: string }>(`/channels/email/${id}/sync`);
      notify(res.status, res.message);
    } finally {
      setSyncing((p) => ({ ...p, [id]: false }));
    }
  };

  /* ── Messaging handlers ─────────────────────────────────────────── */
// [RCF:PROTECTED]
  const handleCreateChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    const config: Record<string, string> = {};
    if (channelForm.type === "telegram") config.bot_token = channelForm.bot_token;
    if (channelForm.type === "whatsapp") { config.access_token = channelForm.access_token; config.phone_number_id = channelForm.phone_number_id; }
    if (channelForm.type === "whatsapp_waha") { config.waha_url = channelForm.waha_url; config.waha_session = channelForm.waha_session; config.waha_api_key = channelForm.waha_api_key; }
    if (channelForm.type === "sms") { config.twilio_sid = channelForm.twilio_sid; config.twilio_token = channelForm.twilio_token; config.twilio_phone = channelForm.twilio_phone; }
    await api.post("/channels/messaging", {
      type: channelForm.type,
      name: channelForm.name,
      config,
      agent_id: channelForm.agent_id ? Number(channelForm.agent_id) : null,
    });
    setShowChannelForm(false);
    loadChannels();
  };

  /* Change which agent answers on an existing channel (PATCH). */
// [RCF:PROTECTED]
  const handleChangeAgent = async (channelId: number, agentId: number | null) => {
    try {
      await api.patch(`/channels/messaging/${channelId}`, { agent_id: agentId });
      setChannels((prev) => prev.map((c) => (c.id === channelId ? { ...c, agent_id: agentId } : c)));
      toast.success("Agent updated");
    } catch {
      toast.error("Failed to update agent");
      loadChannels();
    }
  };

  /* Change which agent handles an email account. */
// [RCF:PROTECTED]
  const handleChangeEmailAgent = async (accountId: number, agentId: number | null) => {
    try {
      await api.patch(`/channels/email/${accountId}/agent`, { agent_id: agentId });
      setEmails((prev) => prev.map((e) => (e.id === accountId ? { ...e, agent_id: agentId } : e)));
      toast.success("Agent updated");
    } catch {
      toast.error("Failed to update agent");
      loadEmails();
    }
  };

// [RCF:PROTECTED]
  const handleTestChannel = async (id: number) => {
    setTesting((p) => ({ ...p, [id]: true }));
    try {
      const res = await api.post<{ status: string; message: string }>(`/channels/messaging/${id}/test`);
      notify(res.status, res.message);
      loadChannels();
    } finally {
      setTesting((p) => ({ ...p, [id]: false }));
    }
  };

// [RCF:PROTECTED]
  const handleShowQr = async (id: number) => {
    setQrModal({ open: true, image: null, loading: true, error: null });
    try {
      const res = await api.get<{ status: string; image?: string; message?: string }>(`/channels/messaging/${id}/waha/qr`);
      if (res.status === "qr" && res.image) {
        setQrModal({ open: true, image: res.image, loading: false, error: null });
      } else {
        setQrModal({ open: true, image: null, loading: false, error: res.message || "Failed to load QR" });
      }
    } catch (e: any) {
      setQrModal({ open: true, image: null, loading: false, error: e.message || "Error fetching QR" });
    }
  };

// [RCF:PROTECTED]
  const handleShowWebhookConfig = async (c: MessagingChannel) => {
    setWebhookModal({ open: true, loading: true, channel: c, data: null, error: null });
    try {
      const res = await api.get<{ webhook_url: string; webhook_secret: string | null; instructions: Record<string, string> }>(`/channels/messaging/${c.id}/webhook-config`);
      // Resolve relative webhook_url to absolute using the dev-port convention
      const base = window.location.origin.replace("3000", "8000");
      const absoluteUrl = res.webhook_url.startsWith("http") ? res.webhook_url : `${base}${res.webhook_url}`;
      setWebhookModal({
        open: true,
        loading: false,
        channel: c,
        data: { ...res, webhook_url: absoluteUrl },
        error: null,
      });
    } catch (e: any) {
      setWebhookModal({ open: true, loading: false, channel: c, data: null, error: e.message || "Failed to fetch webhook config" });
    }
  };

// [RCF:PROTECTED]
  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard?.writeText(text).catch(() => { });
    toast.success(`${label} copied`);
  };

// [RCF:PROTECTED]
  const handleDeleteChannel = async (id: number) => {
    if (!confirm("Remove this messaging channel?")) return;
    await api.delete(`/channels/messaging/${id}`);
    loadChannels();
    toast.success("Channel removed");
  };

// [RCF:PROTECTED]
  const copyWebhookUrl = (c: MessagingChannel) => {
    const base = window.location.origin.replace("3000", "8000");
    const url = `${base}/api/webhooks/${c.type}/${c.id}`;
    navigator.clipboard?.writeText(url).catch(() => { });
    toast.success("Webhook URL copied", { description: url });
  };

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Channels</h2>
        <p className="text-sm mt-1" style={{ color: "var(--color-fg-muted)" }}>
          Manage email accounts and messaging integrations.
        </p>
      </div>

      {/* ── Email Accounts ─────────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Mail size={16} style={{ color: "var(--color-fg-muted)" }} />
            <h3 className="text-sm font-semibold">Email Accounts</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
              {emails.length}
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowEmailForm(!showEmailForm)}>
            {showEmailForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Email</>}
          </Button>
        </div>

        {showEmailForm && (
          <form onSubmit={handleCreateEmail}
            className="rounded-xl border p-4 space-y-3"
            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
          >
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Provider</label>
                <select className="input" value={emailForm.provider} onChange={(e) => setEmailForm({ ...emailForm, provider: e.target.value })}>
                  <option value="imap">IMAP / SMTP</option>
                  <option value="gmail">Gmail (OAuth — coming soon)</option>
                  <option value="outlook">Outlook (OAuth — coming soon)</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Email address</label>
                <input className="input" type="email" placeholder="you@example.com" value={emailForm.email}
                  onChange={(e) => setEmailForm({ ...emailForm, email: e.target.value })} required />
              </div>
            </div>
            {emailForm.provider === "imap" && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>IMAP Host</label>
                    <input className="input" placeholder="imap.gmail.com" value={emailForm.imap_host}
                      onChange={(e) => setEmailForm({ ...emailForm, imap_host: e.target.value })} />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>SMTP Host</label>
                    <input className="input" placeholder="smtp.gmail.com" value={emailForm.smtp_host}
                      onChange={(e) => setEmailForm({ ...emailForm, smtp_host: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>
                    Password / App Password
                    <span className="ml-2 opacity-50 font-normal">For Gmail: use App Password, not your account password</span>
                  </label>
                  <input className="input" type="password" placeholder="••••••••••••••••" value={emailForm.password}
                    onChange={(e) => setEmailForm({ ...emailForm, password: e.target.value })} />
                </div>
              </>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <Button type="button" variant="ghost" size="sm" onClick={() => setShowEmailForm(false)}>Cancel</Button>
              <Button type="submit" size="sm">Connect</Button>
            </div>
          </form>
        )}

        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
          {emails.length === 0 ? (
            <div className="py-12 text-center text-xs" style={{ color: "var(--color-fg-subtle)" }}>
              No email accounts connected yet
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--color-border)" }}>
              {emails.map((acc) => (
                <div key={acc.id}>
                  {/* Row */}
                  <div className="px-4 py-3 flex items-center gap-3" style={{ background: "var(--color-surface-1)" }}>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{acc.email}</p>
                      <p className="text-xs mt-0.5" style={{ color: "var(--color-fg-muted)" }}>
                        {acc.provider.toUpperCase()}
                        {acc.last_synced_at ? ` · synced ${new Date(acc.last_synced_at).toLocaleString()}` : " · never synced"}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {/* Agent selector */}
                      <select
                        value={acc.agent_id ?? ""}
                        onChange={(e) => handleChangeEmailAgent(acc.id, e.target.value ? Number(e.target.value) : null)}
                        className="input text-xs py-1 px-2 h-7 rounded-lg min-w-[120px] max-w-[160px]"
                        title="Which agent handles this email account"
                      >
                        <option value="">No agent</option>
                        {agents.map((a) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                      <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${acc.status === "connected" ? "text-green-400 bg-green-500/10 border-green-500/20" : "border-[var(--color-border)] text-[var(--color-fg-muted)]"}`}>
                        {acc.status}
                      </span>
                      <Button variant="outline" size="sm" onClick={() => handleTestEmail(acc.id)} disabled={testing[acc.id]}>
                        {testing[acc.id] ? <Loader2 size={12} className="animate-spin" /> : <PlugZap size={12} />}
                        Test
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => handleSyncEmail(acc.id)} disabled={syncing[acc.id]}>
                        {syncing[acc.id] ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                        Sync
                      </Button>
                      <Button variant="ghost" size="icon-sm"
                        onClick={() => editEmailId === acc.id ? setEditEmailId(null) : startEditEmail(acc)}
                        className={editEmailId === acc.id ? "text-[var(--color-accent)]" : "text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"}
                      >
                        <Pencil size={13} />
                      </Button>
                      <Button variant="ghost" size="icon-sm"
                        onClick={() => handleDeleteEmail(acc.id)}
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>

                  {/* Inline edit */}
                  {editEmailId === acc.id && (
                    <div className="px-4 py-4 space-y-3 border-t" style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Email</label>
                          <input className="input" type="email" value={editEmailForm.email}
                            onChange={(e) => setEditEmailForm({ ...editEmailForm, email: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>New Password <span className="opacity-40">(leave blank to keep)</span></label>
                          <input className="input" type="password" placeholder="••••••••" value={editEmailForm.password}
                            onChange={(e) => setEditEmailForm({ ...editEmailForm, password: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>IMAP Host</label>
                          <input className="input" placeholder="imap.gmail.com" value={editEmailForm.imap_host}
                            onChange={(e) => setEditEmailForm({ ...editEmailForm, imap_host: e.target.value })} />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>SMTP Host</label>
                          <input className="input" placeholder="smtp.gmail.com" value={editEmailForm.smtp_host}
                            onChange={(e) => setEditEmailForm({ ...editEmailForm, smtp_host: e.target.value })} />
                        </div>
                      </div>
                      <div className="flex items-center justify-end gap-2 pt-1">
                        <Button variant="ghost" size="sm" onClick={() => setEditEmailId(null)}>Cancel</Button>
                        <Button size="sm" onClick={() => handleSaveEmail(acc.id)} disabled={saving}>
                          <Check size={13} /> {saving ? "Saving…" : "Save"}
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── Messaging Channels ─────────────────────────────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare size={16} style={{ color: "var(--color-fg-muted)" }} />
            <h3 className="text-sm font-semibold">Messaging Channels</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
              {channels.length}
            </span>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowChannelForm(!showChannelForm)}>
            {showChannelForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Channel</>}
          </Button>
        </div>

        {showChannelForm && (
          <form onSubmit={handleCreateChannel}
            className="rounded-xl border p-4 space-y-3"
            style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}
          >
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Type</label>
                <select className="input" value={channelForm.type} onChange={(e) => setChannelForm({ ...channelForm, type: e.target.value })}>
                  {CHANNEL_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Channel name</label>
                <input className="input" placeholder="e.g. Support Bot" value={channelForm.name}
                  onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })} required />
              </div>
            </div>
            {channelForm.type === "telegram" && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Bot Token</label>
                <input className="input" type="password" placeholder="1234567890:AAF..." value={channelForm.bot_token}
                  onChange={(e) => setChannelForm({ ...channelForm, bot_token: e.target.value })} required />
              </div>
            )}
            {channelForm.type === "whatsapp" && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Access Token</label>
                  <input className="input" type="password" value={channelForm.access_token}
                    onChange={(e) => setChannelForm({ ...channelForm, access_token: e.target.value })} required />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Phone Number ID</label>
                  <input className="input" value={channelForm.phone_number_id}
                    onChange={(e) => setChannelForm({ ...channelForm, phone_number_id: e.target.value })} required />
                </div>
              </div>
            )}
            {channelForm.type === "whatsapp_waha" && (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>WAHA URL</label>
                  <input className="input" placeholder="https://waha.example.com" value={channelForm.waha_url}
                    onChange={(e) => setChannelForm({ ...channelForm, waha_url: e.target.value })} required />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Session Name</label>
                  <input className="input" placeholder="default" value={channelForm.waha_session}
                    onChange={(e) => setChannelForm({ ...channelForm, waha_session: e.target.value })} required />
                </div>
              </div>
            )}
            {channelForm.type === "sms" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Twilio SID</label>
                    <input className="input" value={channelForm.twilio_sid}
                      onChange={(e) => setChannelForm({ ...channelForm, twilio_sid: e.target.value })} required />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Auth Token</label>
                    <input className="input" type="password" value={channelForm.twilio_token}
                      onChange={(e) => setChannelForm({ ...channelForm, twilio_token: e.target.value })} required />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Twilio Phone</label>
                  <input className="input" placeholder="+1234567890" value={channelForm.twilio_phone}
                    onChange={(e) => setChannelForm({ ...channelForm, twilio_phone: e.target.value })} required />
                </div>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <Button type="button" variant="ghost" size="sm" onClick={() => setShowChannelForm(false)}>Cancel</Button>
              <Button type="submit" size="sm">Connect</Button>
            </div>
          </form>
        )}

        <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
          {channels.length === 0 ? (
            <div className="py-12 text-center text-xs" style={{ color: "var(--color-fg-subtle)" }}>
              No messaging channels connected yet
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: "var(--color-border)" }}>
              {channels.map((c) => (
                <div key={c.id} className="px-4 py-3 flex items-center gap-3" style={{ background: "var(--color-surface-1)" }}>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{c.name}</p>
                    <p className="text-xs mt-0.5 capitalize" style={{ color: "var(--color-fg-muted)" }}>{c.type.replace("_", " ")}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {/* Agent selector */}
                    <select
                      value={c.agent_id ?? ""}
                      onChange={(e) => handleChangeAgent(c.id, e.target.value ? Number(e.target.value) : null)}
                      className="input text-xs py-1 px-2 h-7 rounded-lg min-w-[120px] max-w-[160px]"
                      title="Which agent handles this channel"
                    >
                      <option value="">No agent</option>
                      {agents.map((a) => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                      ))}
                    </select>
                    <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${c.status === "connected" ? "text-green-400 bg-green-500/10 border-green-500/20" : "border-[var(--color-border)] text-[var(--color-fg-muted)]"}`}>
                      {c.status}
                    </span>
                    {c.type === "whatsapp_waha" && (
                      <>
                        <span
                          className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border flex items-center gap-1 text-amber-400 bg-amber-500/10 border-amber-500/20"
// [RCF:PROTECTED]
                          title="WAHA accepts unsigned webhooks by default. Click Webhook setup to harden."
                        >
                          <ShieldAlert size={10} />
// [RCF:PROTECTED]
                          Unsigned by default
                        </span>
                        <Button variant="outline" size="sm" onClick={() => handleShowQr(c.id)}>
                          <QrCode size={12} /> QR Code
                        </Button>
                      </>
                    )}
                    <Button variant="outline" size="sm" onClick={() => handleTestChannel(c.id)} disabled={testing[c.id]}>
                      {testing[c.id] ? <Loader2 size={12} className="animate-spin" /> : <PlugZap size={12} />}
                      Test
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleShowWebhookConfig(c)}
// [RCF:PROTECTED]
                      title="Webhook setup (URL + signing secret)" className="text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]">
                      <ShieldAlert size={13} />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => copyWebhookUrl(c)}
                      title="Copy webhook URL" className="text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]">
                      <Link2 size={13} />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteChannel(c.id)}
                      className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]">
                      <Trash2 size={13} />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Webhook Config Modal */}
      {webhookModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-lg rounded-2xl border p-6 shadow-xl" style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}>
            <Button variant="ghost" size="icon-sm" className="absolute top-3 right-3"
              onClick={() => setWebhookModal({ open: false, loading: false, channel: null, data: null, error: null })}>
              <X size={14} />
            </Button>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <ShieldAlert size={18} style={{ color: "var(--color-fg-muted)" }} />
                  Webhook setup
                </h3>
                <p className="text-xs mt-1" style={{ color: "var(--color-fg-muted)" }}>
                  {webhookModal.channel?.name} · <span className="capitalize">{webhookModal.channel?.type.replace("_", " ")}</span>
                </p>
              </div>

              {webhookModal.loading && <div className="py-6 flex justify-center"><Loader2 className="animate-spin" /></div>}
              {webhookModal.error && <p className="text-sm text-red-500">{webhookModal.error}</p>}

              {webhookModal.data && (
                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Webhook URL</label>
                    <div className="mt-1 flex items-center gap-2">
                      <code className="flex-1 text-xs px-2.5 py-2 rounded border break-all"
                        style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}>
                        {webhookModal.data.webhook_url}
                      </code>
                      <Button variant="outline" size="sm" onClick={() => copyToClipboard(webhookModal.data!.webhook_url, "URL")}>
                        <Copy size={12} />
                      </Button>
                    </div>
                  </div>

                  <div>
// [RCF:PROTECTED]
                    <label className="text-xs font-medium" style={{ color: "var(--color-fg-muted)" }}>Signing secret</label>
                    <div className="mt-1 flex items-center gap-2">
                      <code className="flex-1 text-xs px-2.5 py-2 rounded border break-all font-mono"
                        style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)" }}>
                        {webhookModal.data.webhook_secret || "(not configured)"}
                      </code>
                      {webhookModal.data.webhook_secret && (
                        <Button variant="outline" size="sm"
                          onClick={() => copyToClipboard(webhookModal.data!.webhook_secret!, "Secret")}>
                          <Copy size={12} />
                        </Button>
                      )}
                    </div>
                  </div>

// [RCF:PROTECTED]
                  {webhookModal.data.instructions.signing && (
                    <div className="rounded-md border p-3 text-xs leading-relaxed"
                      style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}>
                      <p className="font-semibold mb-1" style={{ color: "var(--color-fg)" }}>
// [RCF:PROTECTED]
                        How to enable signature verification:
                      </p>
// [RCF:PROTECTED]
                      <p>{webhookModal.data.instructions.signing}</p>
                      {webhookModal.data.instructions.header && (
                        <p className="mt-2"><span className="font-medium">Header:</span> <code>{webhookModal.data.instructions.header}</code></p>
                      )}
// [RCF:PROTECTED]
                      {webhookModal.data.instructions.hmac_algorithm && (
// [RCF:PROTECTED]
                        <p className="mt-1"><span className="font-medium">Algorithm:</span> {webhookModal.data.instructions.hmac_algorithm}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* QR Code Modal */}
      {qrModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-sm rounded-2xl border p-6 shadow-xl" style={{ background: "var(--color-surface-1)", borderColor: "var(--color-border)" }}>
            <Button variant="ghost" size="icon-sm" className="absolute top-3 right-3" onClick={() => setQrModal({ open: false, image: null, loading: false, error: null })}>
              <X size={14} />
            </Button>
            <div className="text-center space-y-4">
              <h3 className="text-lg font-bold">Scan to Connect</h3>
              <p className="text-xs" style={{ color: "var(--color-fg-muted)" }}>Open WhatsApp on your phone and scan this QR code to link the device.</p>

              <div className="flex items-center justify-center p-4 bg-white rounded-xl min-h-[200px]">
                {qrModal.loading ? (
                  <Loader2 className="animate-spin text-black" />
                ) : qrModal.error ? (
                  <p className="text-sm text-red-500 font-medium">{qrModal.error}</p>
                ) : qrModal.image ? (
                  <img src={qrModal.image} alt="WhatsApp QR Code" className="max-w-[200px] max-h-[200px]" />
                ) : null}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
