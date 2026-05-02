"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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

const TYPE_LABEL: Record<string, string> = {
  telegram: "Telegram",
  whatsapp: "WhatsApp",
  sms: "SMS",
};

export default function CommsPage() {
  const [emails, setEmails] = useState<EmailAccount[]>([]);
  const [channels, setChannels] = useState<MessagingChannel[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [e, c] = await Promise.all([
        api.get<EmailAccount[]>("/channels/email"),
        api.get<MessagingChannel[]>("/channels/messaging"),
      ]);
      setEmails(e);
      setChannels(c);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleTestChannel = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(
      `/channels/messaging/${id}/test`
    );
    alert(res.message);
    load();
  };

  const handleSyncEmail = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(
      `/channels/email/${id}/sync`
    );
    alert(res.message);
  };

  const handleTestEmail = async (id: number) => {
    const res = await api.post<{ status: string; message: string }>(
      `/channels/email/${id}/test`
    );
    alert(res.message);
    load();
  };

  const totalConnected =
    channels.filter((c) => c.status === "connected").length +
    emails.filter((e) => e.status === "connected").length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Communications</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {totalConnected} connected source{totalConnected === 1 ? "" : "s"}
          </p>
        </div>
        <Link href="/dashboard/channels">
          <Button>Manage Channels</Button>
        </Link>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : (
        <>
          <section className="mb-8">
            <h3 className="text-lg font-semibold mb-4">Messaging</h3>
            <div className="space-y-3">
              {channels.map((c) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4"
                >
                  <div>
                    <p className="font-medium">{c.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {TYPE_LABEL[c.type] ?? c.type}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        c.status === "connected"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-zinc-500/20 text-zinc-400"
                      }`}
                    >
                      {c.status}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestChannel(c.id)}
                    >
                      Test
                    </Button>
                  </div>
                </div>
              ))}
              {channels.length === 0 && (
                <p className="text-muted-foreground text-sm">
                  No messaging channels connected yet.
                </p>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-4">Email</h3>
            <div className="space-y-3">
              {emails.map((e) => (
                <div
                  key={e.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4"
                >
                  <div>
                    <p className="font-medium">{e.email}</p>
                    <p className="text-sm text-muted-foreground">
                      {e.provider.toUpperCase()}
                      {e.last_synced_at
                        ? ` — synced ${new Date(
                            e.last_synced_at
                          ).toLocaleString()}`
                        : ""}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        e.status === "connected"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-zinc-500/20 text-zinc-400"
                      }`}
                    >
                      {e.status}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestEmail(e.id)}
                    >
                      Test
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSyncEmail(e.id)}
                    >
                      Sync
                    </Button>
                  </div>
                </div>
              ))}
              {emails.length === 0 && (
                <p className="text-muted-foreground text-sm">
                  No email accounts connected yet.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
