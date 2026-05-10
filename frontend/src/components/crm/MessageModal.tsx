"use client";

import { useEffect, useState } from "react";
import { X, Mail, Reply, Send, Loader2, Paperclip, FileText, FileImage, FileArchive, Download } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

/* ── Types ───────────────────────────────────────────────────────── */
interface Activity {
  id: number; type: string; channel: string | null;
  contact_id: number | null;
  subject: string | null; content: string | null; created_at: string;
  metadata_json?: { attachments?: Attachment[]; message_id?: string } | null;
}
interface Attachment {
  filename: string; content_type: string; size: number;
}
interface EmailAccount {
  id: number; email: string; provider: string; status: string;
}

interface Props {
  activity: Activity;
  contactEmail: string | null;
  onClose: () => void;
  inline?: boolean;
}

function stripHtml(html: string): string {
  if (!html) return "";
  
  // If it doesn't look like HTML, just return it
  if (!html.includes("<")) return html.trim();

  return html
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<\/(p|div|h[1-6]|li|tr)>/gi, "\n") // Add newline after block elements
    .replace(/<br\s*\/?>/gi, "\n") // Replace <br> with newline
    .replace(/<[^>]+>/g, " ") // Strip other tags
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/[ \t]{2,}/g, " ") // Collapse multiple spaces (but preserve newlines)
    .replace(/\n\s*\n/g, "\n\n") // Collapse multiple empty lines into max 2
    .trim();
}

/* ── Component ───────────────────────────────────────────────────── */
export default function MessageModal({ activity, contactEmail, onClose, inline = false }: Props) {
  const [showReply, setShowReply] = useState(false);
  const [emailAccounts, setEmailAccounts] = useState<EmailAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [sending, setSending] = useState(false);

  const isEmail = activity.type.startsWith("email");
  const plainText = stripHtml(activity.content ?? "");
  const attachments: Attachment[] = activity.metadata_json?.attachments ?? [];

  useEffect(() => {
    if (isEmail) {
      api.get<EmailAccount[]>("/channels/email")
        .then((accounts) => {
          const connected = accounts.filter((a) => a.status === "connected");
          setEmailAccounts(connected);
          if (connected.length > 0) setSelectedAccount(connected[0].id);
        })
        .catch(() => {});
    }
    
    if (!inline) {
      // Prevent scroll on body only if it's a modal
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = ""; };
    }
  }, [isEmail, inline]);

  const handleSend = async () => {
    if (!selectedAccount || !contactEmail) {
      toast.error("No connected email account or contact email missing");
      return;
    }
    if (!replyBody.trim()) {
      toast.error("Please write a reply first");
      return;
    }
    setSending(true);
    try {
      const subject = activity.subject
        ? (activity.subject.startsWith("Re:") ? activity.subject : `Re: ${activity.subject}`)
        : "Re: (no subject)";
      await api.post(`/channels/email/${selectedAccount}/send`, {
        to_email: contactEmail,
        subject,
        body: replyBody,
        contact_id: activity.contact_id,
      });
      toast.success("Reply sent successfully");
      setShowReply(false);
      setReplyBody("");
    } catch {
      toast.error("Failed to send reply. Check your SMTP settings.");
    } finally {
      setSending(false);
    }
  };

  // Close on backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  const content = (
    <div
      className={`flex flex-col w-full h-full overflow-hidden ${!inline ? "sm:max-w-2xl rounded-t-3xl sm:rounded-3xl" : ""}`}
      style={{
        background: inline ? "transparent" : "var(--color-surface)",
        border: inline ? "none" : "1px solid var(--color-border)",
        maxHeight: inline ? "100%" : "90vh",
      }}
    >
      {/* ── Header (Only for modal) ─────────────────────────── */}
      {!inline && (
        <div
          className="flex items-start justify-between gap-4 px-6 py-5 shrink-0 border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border"
                style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}
              >
                {activity.type.replace(/_/g, " ")}
              </span>
              {activity.channel && (
                <span
                  className="text-[9px] font-mono uppercase px-2 py-0.5 rounded border"
                  style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}
                >
                  {activity.channel}
                </span>
              )}
            </div>
            <h2 className="text-base font-semibold leading-tight">
              {activity.subject || "(no subject)"}
            </h2>
            <p className="text-xs mt-1" style={{ color: "var(--color-fg-muted)" }}>
              {new Date(activity.created_at).toLocaleString()}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 hover:opacity-70 transition-opacity"
            style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* ── Body ────────────────────────────────────────────── */}
        <div className="flex-1 overflow-hidden relative">
          {activity.content ? (
            <iframe 
              srcDoc={`
                <!DOCTYPE html>
                <html>
                  <head>
                    <meta charset="utf-8">
                    <style>
                      html, body {
                        background-color: #ffffff !important;
                        color: #000000 !important;
                      }
                      body { 
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        font-size: 14px;
                        line-height: 1.5;
                        margin: 0; 
                        padding: 20px 24px;
                        word-wrap: break-word;
                      }
                      a { color: #2563eb !important; text-decoration: underline; }
                      /* Support plain text gracefully */
                      pre { font-family: inherit; white-space: pre-wrap; margin: 0; }
                    </style>
                  </head>
                  <body>
                    ${activity.content.includes('<') && activity.content.includes('>') ? activity.content : `<pre>${activity.content}</pre>`}
                  </body>
                </html>
              `}
              sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin"
              className="w-full h-full border-none bg-white"
              style={{ background: "#ffffff" }}
            />
          ) : (
            <div className="px-6 py-5">
              <p className="text-xs italic" style={{ color: "var(--color-fg-subtle)" }}>No content</p>
            </div>
          )}
        </div>

        {/* ── Attachments ─────────────────────────────────────── */}
        {attachments.length > 0 && (
          <div
            className="shrink-0 border-t px-6 py-4"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
          >
            <p className="text-[10px] font-bold uppercase mb-3" style={{ color: "var(--color-fg-muted)" }}>
              <Paperclip size={10} className="inline mr-1" />
              {attachments.length} attachment{attachments.length > 1 ? "s" : ""}
            </p>
            <div className="flex flex-wrap gap-2">
              {attachments.map((att) => {
                const isImage = att.content_type.startsWith("image/");
                const isPdf   = att.content_type === "application/pdf";
                const isZip   = att.content_type.includes("zip") || att.content_type.includes("archive");
                const Icon    = isImage ? FileImage : isZip ? FileArchive : FileText;
                const sizeKb  = (att.size / 1024).toFixed(1);
                
                const handleDownload = async (e: React.MouseEvent) => {
                  e.preventDefault();
                  try {
                    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/crm/activities/${activity.id}/attachments/${encodeURIComponent(att.filename)}`;
                    const token = localStorage.getItem("access_token");
                    const res = await fetch(url, {
                      headers: token ? { Authorization: `Bearer ${token}` } : {}
                    });
                    if (!res.ok) throw new Error("Not authenticated");
                    const blob = await res.blob();
                    const blobUrl = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = blobUrl;
                    a.download = att.filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
                  } catch (err) {
                    toast.error("Failed to download file");
                  }
                };

                return (
                  <button
                    key={att.filename}
                    onClick={handleDownload}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border text-xs hover:opacity-80 transition-opacity cursor-pointer"
                    style={{ background: "var(--color-surface)", borderColor: "var(--color-border)", textAlign: "left" }}
                  >
                    <Icon size={14} style={{ color: "var(--color-accent)", flexShrink: 0 }} />
                    <span className="max-w-[120px] truncate font-medium">{att.filename}</span>
                    <span style={{ color: "var(--color-fg-subtle)", flexShrink: 0 }}>{sizeKb}KB</span>
                    <Download size={11} style={{ color: "var(--color-fg-subtle)", flexShrink: 0 }} />
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Reply form ──────────────────────────────────────── */}
        {isEmail && (
          <div
            className="shrink-0 border-t px-6 py-4"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface-1)" }}
          >
            {!showReply ? (
              <div className="flex items-center justify-between gap-3">
                {contactEmail ? (
                  <p className="text-xs" style={{ color: "var(--color-fg-muted)" }}>
                    Reply to: <span className="font-mono">{contactEmail}</span>
                  </p>
                ) : (
                  <p className="text-xs italic" style={{ color: "var(--color-fg-subtle)" }}>
                    No email on this contact — can't reply
                  </p>
                )}
                {contactEmail && (
                  <Button variant="outline" size="sm" onClick={() => setShowReply(true)} className="gap-1.5 shrink-0">
                    <Reply size={13} /> Reply
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {/* Account selector */}
                {emailAccounts.length > 1 && (
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                      Send from
                    </label>
                    <select
                      className="input text-sm"
                      value={selectedAccount ?? ""}
                      onChange={(e) => setSelectedAccount(Number(e.target.value))}
                    >
                      {emailAccounts.map((a) => (
                        <option key={a.id} value={a.id}>{a.email}</option>
                      ))}
                    </select>
                  </div>
                )}
                {emailAccounts.length === 0 && (
                  <p className="text-xs text-amber-400">
                    No connected email accounts. Connect and test one in Channels settings first.
                  </p>
                )}
                {/* Compose */}
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                    Message
                  </label>
                  <textarea
                    className="input resize-none"
                    rows={5}
                    placeholder="Write your reply…"
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    autoFocus
                  />
                </div>
                <div className="flex items-center justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => { setShowReply(false); setReplyBody(""); }}>
                    Cancel
                  </Button>
                  <Button size="sm" onClick={handleSend} disabled={sending || emailAccounts.length === 0} className="gap-1.5">
                    {sending ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                    {sending ? "Sending…" : "Send reply"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
    </div>
  );

  if (inline) {
    return content;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6"
      style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)" }}
      onClick={handleBackdropClick}
    >
      {content}
    </div>
  );
}
