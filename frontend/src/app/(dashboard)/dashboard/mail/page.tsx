"use client";

import { useEffect, useState } from "react";
import { Inbox, Send, Archive, Search, Mail, Loader2, Star, Clock, UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import MessageModal from "@/components/crm/MessageModal";

interface Activity {
  id: number;
  type: string;
  channel: string | null;
  subject: string | null;
  content: string | null;
  created_at: string;
  contact_id: number | null;
  metadata_json?: {
    from_name?: string;
    from_email?: string;
    to_name?: string;
    to_email?: string;
    attachments?: any[];
  } | null;
}

export default function MailPage() {
  const [emails, setEmails] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEmail, setSelectedEmail] = useState<Activity | null>(null);
  const [folder, setFolder] = useState<"inbox" | "sent" | "all">("inbox");
  const [search, setSearch] = useState("");
  const [addingToCrm, setAddingToCrm] = useState(false);

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    setLoading(true);
    try {
      // Fetch both incoming and outgoing emails
      const data = await api.get<Activity[]>("/crm/activities?type=email_in,email_out&limit=200");
      setEmails(data);
    } catch (err) {
      toast.error("Failed to load emails");
    } finally {
      setLoading(false);
    }
  };

  // Helper to safely parse metadata
  const getMetaData = (email: Activity) => {
    if (!email.metadata_json) return {};
    if (typeof email.metadata_json === "string") {
      try { return JSON.parse(email.metadata_json); } catch { return {}; }
    }
    return email.metadata_json;
  };

  const handleAddToCrm = async (email: Activity) => {
    const meta = getMetaData(email);
    const targetEmail = email.type === "email_out" ? meta.to_email : meta.from_email;
    
    if (!targetEmail) {
      toast.error("Cannot add to CRM: missing email address");
      return;
    }
    setAddingToCrm(true);
    try {
      // 1. Create contact
      const contact = await api.post("/crm/contacts", {
        name: (email.type === "email_out" ? meta.to_name : meta.from_name) || targetEmail,
        email: targetEmail,
        phone: null,
        company: null,
        source: "email",
      });
      // 2. Link activity to contact
      await api.patch(`/crm/activities/${email.id}`, {
        contact_id: contact.id,
      });
      
      toast.success("Added to CRM successfully");
      
      // Update local state
      setEmails(emails.map(e => e.id === email.id ? { ...e, contact_id: contact.id } : e));
      if (selectedEmail?.id === email.id) {
        setSelectedEmail({ ...selectedEmail, contact_id: contact.id });
      }
    } catch (err) {
      toast.error("Failed to add to CRM");
    } finally {
      setAddingToCrm(false);
    }
  };

  // Filter emails based on folder and search
  const filteredEmails = emails.filter((email) => {
    // Search
    if (search) {
      const meta = getMetaData(email);
      const term = search.toLowerCase();
      const subject = (email.subject || "").toLowerCase();
      const from = (meta.from_name || meta.from_email || "").toLowerCase();
      if (!subject.includes(term) && !from.includes(term)) return false;
    }
    // Folder
    if (folder === "inbox") return email.type === "email_in";
    if (folder === "sent") return email.type === "email_out";
    return true; // all
  });

  const getSenderName = (email: Activity) => {
    const meta = getMetaData(email);
    if (email.type === "email_out") return "To: " + (meta.to_name || meta.to_email || "Unknown");
    return meta.from_name || meta.from_email || "Unknown Sender";
  };

  return (
    <div className="h-full flex flex-col sm:flex-row border rounded-xl overflow-hidden" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
      
      {/* ── Left Sidebar (Folders) ───────────────────────── */}
      <div className="w-full sm:w-48 shrink-0 border-r flex flex-col" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
        <div className="p-4 font-semibold text-sm border-b" style={{ borderColor: "var(--color-border)" }}>
          Mailbox
        </div>
        <div className="flex-1 p-2 space-y-1">
          <button
            onClick={() => setFolder("inbox")}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
            style={{ 
              background: folder === "inbox" ? "var(--color-accent)" : "transparent",
              color: folder === "inbox" ? "#fff" : "var(--color-fg-muted)"
            }}
          >
            <Inbox size={14} /> Inbox
          </button>
          <button
            onClick={() => setFolder("sent")}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
            style={{ 
              background: folder === "sent" ? "var(--color-accent)" : "transparent",
              color: folder === "sent" ? "#fff" : "var(--color-fg-muted)"
            }}
          >
            <Send size={14} /> Sent
          </button>
          <button
            onClick={() => setFolder("all")}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
            style={{ 
              background: folder === "all" ? "var(--color-accent)" : "transparent",
              color: folder === "all" ? "#fff" : "var(--color-fg-muted)"
            }}
          >
            <Archive size={14} /> All Mail
          </button>
        </div>
      </div>

      {/* ── Middle Column (Email List) ───────────────────── */}
      <div className="w-full sm:w-80 shrink-0 border-r flex flex-col" style={{ borderColor: "var(--color-border)" }}>
        <div className="p-3 border-b" style={{ borderColor: "var(--color-border)" }}>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--color-fg-muted)" }} />
            <input
              type="text"
              placeholder="Search emails..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-transparent border rounded-lg pl-8 pr-3 py-1.5 text-xs outline-none focus:border-[var(--color-accent)] transition-colors"
              style={{ borderColor: "var(--color-border)", color: "var(--color-fg)" }}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center p-8">
              <Loader2 size={16} className="animate-spin text-muted" />
            </div>
          ) : filteredEmails.length === 0 ? (
            <div className="text-center p-8 text-xs italic" style={{ color: "var(--color-fg-subtle)" }}>
              No emails found.
            </div>
          ) : (
            <div className="flex flex-col">
              {filteredEmails.map((email) => {
                const isSelected = selectedEmail?.id === email.id;
                const sender = getSenderName(email);
                const isCrm = email.contact_id !== null;
                
                return (
                  <button
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className="flex flex-col text-left p-3 border-b transition-colors"
                    style={{ 
                      borderColor: "var(--color-border)",
                      background: isSelected ? "var(--color-surface-2)" : "transparent",
                    }}
                  >
                    <div className="flex items-center justify-between w-full mb-1">
                      <span className="font-semibold text-xs truncate pr-2" style={{ color: "var(--color-fg)" }}>
                        {sender}
                      </span>
                      <span className="text-[10px] whitespace-nowrap shrink-0" style={{ color: "var(--color-fg-muted)" }}>
                        {new Date(email.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <span className="font-medium text-xs truncate w-full mb-1" style={{ color: "var(--color-fg)" }}>
                      {email.subject || "(no subject)"}
                    </span>
                    <span className="text-[10px] truncate w-full" style={{ color: "var(--color-fg-muted)" }}>
                      {email.content ? email.content.replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").trim().substring(0, 60) : "..."}
                    </span>
                    {isCrm && (
                      <div className="mt-1 flex items-center">
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)", color: "var(--color-accent)" }}>
                          In CRM
                        </span>
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── Right Column (Reading Pane) ──────────────────── */}
      <div className="flex-1 flex flex-col bg-transparent relative">
        {selectedEmail ? (
          <div className="flex-1 h-full w-full overflow-hidden flex flex-col">
            {/* Top Toolbar */}
            <div className="p-4 border-b flex items-center justify-between shrink-0" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold uppercase" style={{ background: "var(--color-accent)", color: "#fff" }}>
                  {getSenderName(selectedEmail).charAt(0)}
                </div>
                <div>
                  <h3 className="text-sm font-semibold leading-tight">{selectedEmail.subject || "(no subject)"}</h3>
                  <p className="text-xs" style={{ color: "var(--color-fg-muted)" }}>
                    {getSenderName(selectedEmail)} • {new Date(selectedEmail.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {selectedEmail.contact_id ? (
                  <span className="text-xs font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-lg border" style={{ borderColor: "var(--color-border)", color: "var(--color-accent)" }}>
                    <Star size={12} fill="currentColor" /> CRM Lead
                  </span>
                ) : (
                  <button
                    onClick={() => handleAddToCrm(selectedEmail)}
                    disabled={addingToCrm || selectedEmail.type === "email_out"}
                    className="text-xs font-medium flex items-center gap-1.5 px-3 py-1.5 rounded-lg border hover:opacity-80 transition-opacity disabled:opacity-50"
                    style={{ borderColor: "var(--color-border)", color: "var(--color-fg)" }}
                  >
                    {addingToCrm ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />}
                    Add to CRM
                  </button>
                )}
              </div>
            </div>

            {/* Email Body & Reply using MessageModal as inline */}
            <div className="flex-1 overflow-hidden relative">
              <MessageModal 
                activity={{...selectedEmail, metadata_json: getMetaData(selectedEmail)} as any} 
                contactEmail={selectedEmail.type === "email_out" ? getMetaData(selectedEmail).to_email || null : getMetaData(selectedEmail).from_email || null} 
                onClose={() => setSelectedEmail(null)}
                inline={true}
              />
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center" style={{ color: "var(--color-fg-muted)" }}>
            <Mail size={40} className="mb-4 opacity-20" />
            <p className="text-sm">Select an email to read</p>
          </div>
        )}
      </div>

    </div>
  );
}
