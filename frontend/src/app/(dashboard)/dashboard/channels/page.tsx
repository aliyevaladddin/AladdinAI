"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface EmailAccount {
  id: number;
  provider: string;
  email: string;
  status: string;
  last_synced_at: string | null;
}

interface MessagingChannel {
  id: number;
  type: string;
  name: string;
  agent_id: number | null;
  status: string;
}

const CHANNEL_TYPES = ["telegram", "whatsapp", "sms"];

export default function ChannelsPage() {
  const [emails, setEmails] = useState<EmailAccount[]>([]);
  const [channels, setChannels] = useState<MessagingChannel[]>([]);
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [showChannelForm, setShowChannelForm] = useState(false);
  const [emailForm, setEmailForm] = useState({ provider: "imap", email: "", imap_host: "", imap_port: "993", smtp_host: "", smtp_port: "587", password: "" });
  const [channelForm, setChannelForm] = useState({ type: "telegram", name: "", bot_token: "", access_token: "", phone_number_id: "", twilio_sid: "", twilio_token: "", twilio_phone: "" });

  const loadEmails = () => api.get<EmailAccount[]>("/channels/email").then(setEmails);
  const loadChannels = () => api.get<MessagingChannel[]>("/channels/messaging").then(setChannels);

  useEffect(() => { loadEmails(); loadChannels(); }, []);

  const handleCreateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post("/channels/email", {
      ...emailForm,
      imap_port: parseInt(emailForm.imap_port),
      smtp_port: parseInt(emailForm.smtp_port),
    });
    setShowEmailForm(false);
    loadEmails();
  };

  const handleCreateChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    const config: Record<string, string> = {};
    if (channelForm.type === "telegram") config.bot_token = channelForm.bot_token;
    if (channelForm.type === "whatsapp") { config.access_token = channelForm.access_token; config.phone_number_id = channelForm.phone_number_id; }
    if (channelForm.type === "sms") { config.twilio_sid = channelForm.twilio_sid; config.twilio_token = channelForm.twilio_token; config.twilio_phone = channelForm.twilio_phone; }
    await api.post("/channels/messaging", { type: channelForm.type, name: channelForm.name, config });
    setShowChannelForm(false);
    loadChannels();
  };

  const handleTestEmail = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(`/channels/email/${id}/test`);
    alert(res.message);
    loadEmails();
  };

  const handleSyncEmail = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(`/channels/email/${id}/sync`);
    alert(res.message);
  };

  const handleTestChannel = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(`/channels/messaging/${id}/test`);
    alert(res.message);
    loadChannels();
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Channels</h2>

      {/* Email Accounts */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Email Accounts</h3>
          <Button onClick={() => setShowEmailForm(!showEmailForm)}>{showEmailForm ? "Cancel" : "Add Email"}</Button>
        </div>

        {showEmailForm && (
          <form onSubmit={handleCreateEmail} className="mb-4 rounded-lg border border-border p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <select value={emailForm.provider} onChange={(e) => setEmailForm({ ...emailForm, provider: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="imap">IMAP/SMTP</option>
                <option value="gmail">Gmail (OAuth)</option>
                <option value="outlook">Outlook (OAuth)</option>
              </select>
              <input placeholder="Email address" value={emailForm.email} onChange={(e) => setEmailForm({ ...emailForm, email: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
            </div>
            {emailForm.provider === "imap" && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <input placeholder="IMAP Host" value={emailForm.imap_host} onChange={(e) => setEmailForm({ ...emailForm, imap_host: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
                  <input placeholder="SMTP Host" value={emailForm.smtp_host} onChange={(e) => setEmailForm({ ...emailForm, smtp_host: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" />
                </div>
                <input placeholder="Password / App Password" value={emailForm.password} onChange={(e) => setEmailForm({ ...emailForm, password: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" />
              </>
            )}
            <Button type="submit">Connect</Button>
          </form>
        )}

        <div className="space-y-3">
          {emails.map((e) => (
            <div key={e.id} className="flex items-center justify-between rounded-lg border border-border p-4">
              <div>
                <p className="font-medium">{e.email}</p>
                <p className="text-sm text-muted-foreground">{e.provider.toUpperCase()}{e.last_synced_at ? ` — synced ${new Date(e.last_synced_at).toLocaleString()}` : ""}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded ${e.status === "connected" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>{e.status}</span>
                <Button variant="outline" size="sm" onClick={() => handleTestEmail(e.id)}>Test</Button>
                <Button variant="outline" size="sm" onClick={() => handleSyncEmail(e.id)}>Sync</Button>
              </div>
            </div>
          ))}
          {emails.length === 0 && <p className="text-muted-foreground text-sm">No email accounts connected.</p>}
        </div>
      </div>

      {/* Messaging Channels */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Messaging Channels</h3>
          <Button onClick={() => setShowChannelForm(!showChannelForm)}>{showChannelForm ? "Cancel" : "Add Channel"}</Button>
        </div>

        {showChannelForm && (
          <form onSubmit={handleCreateChannel} className="mb-4 rounded-lg border border-border p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <select value={channelForm.type} onChange={(e) => setChannelForm({ ...channelForm, type: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm">
                {CHANNEL_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
              </select>
              <input placeholder="Channel name" value={channelForm.name} onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
            </div>
            {channelForm.type === "telegram" && (
              <input placeholder="Bot Token" value={channelForm.bot_token} onChange={(e) => setChannelForm({ ...channelForm, bot_token: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" required />
            )}
            {channelForm.type === "whatsapp" && (
              <div className="grid grid-cols-2 gap-3">
                <input placeholder="Access Token" value={channelForm.access_token} onChange={(e) => setChannelForm({ ...channelForm, access_token: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" required />
                <input placeholder="Phone Number ID" value={channelForm.phone_number_id} onChange={(e) => setChannelForm({ ...channelForm, phone_number_id: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
              </div>
            )}
            {channelForm.type === "sms" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input placeholder="Twilio SID" value={channelForm.twilio_sid} onChange={(e) => setChannelForm({ ...channelForm, twilio_sid: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" required />
                  <input placeholder="Twilio Auth Token" value={channelForm.twilio_token} onChange={(e) => setChannelForm({ ...channelForm, twilio_token: e.target.value })} className="rounded-md border border-input bg-background px-3 py-2 text-sm" type="password" required />
                </div>
                <input placeholder="Twilio Phone Number" value={channelForm.twilio_phone} onChange={(e) => setChannelForm({ ...channelForm, twilio_phone: e.target.value })} className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" required />
              </div>
            )}
            <Button type="submit">Connect</Button>
          </form>
        )}

        <div className="space-y-3">
          {channels.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-lg border border-border p-4">
              <div>
                <p className="font-medium">{c.name}</p>
                <p className="text-sm text-muted-foreground">{c.type.charAt(0).toUpperCase() + c.type.slice(1)}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-1 rounded ${c.status === "connected" ? "bg-green-500/20 text-green-400" : "bg-zinc-500/20 text-zinc-400"}`}>{c.status}</span>
                <Button variant="outline" size="sm" onClick={() => handleTestChannel(c.id)}>Test</Button>
              </div>
            </div>
          ))}
          {channels.length === 0 && <p className="text-muted-foreground text-sm">No messaging channels connected.</p>}
        </div>
      </div>
    </div>
  );
}
