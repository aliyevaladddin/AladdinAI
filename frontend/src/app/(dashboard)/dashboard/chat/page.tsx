"use client";

import { useEffect, useState, useRef, FormEvent, MouseEvent, KeyboardEvent } from "react";
import { api, API_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  User,
  Bot,
  Globe,
  Paperclip,
  X,
} from "lucide-react";

interface Attachment {
  filename: string;
  path: string;
  mime: string;
  kind: string;
}

function AuthImage({ filename }: { filename: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let revoke: string | null = null;
    let cancelled = false;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    fetch(`${API_URL}/chat/media/${filename}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => (r.ok ? r.blob() : null))
      .then((blob) => {
        if (!blob || cancelled) return;
        const url = URL.createObjectURL(blob);
        revoke = url;
        setSrc(url);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [filename]);
  if (!src) {
    return <div className="w-40 h-40 rounded-md bg-muted animate-pulse" />;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={filename} className="max-w-xs max-h-80 rounded-md border border-border" />;
}

interface Agent {
  id: number;
  name: string;
  role: string;
}

interface Session {
  id: number;
  agent_id: number;
  title: string;
  updated_at: string;
}

interface Message {
  id?: number;
  role: "user" | "assistant";
  content: string;
  model?: string | null;
  attachments?: Attachment[] | null;
  created_at?: string;
}

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isGeneralChat, setIsGeneralChat] = useState(false);
  const [composingNew, setComposingNew] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 240)}px`;
  }, [input]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) form.requestSubmit();
    }
  };

  useEffect(() => {
    api.get<Agent[]>("/agents").then(setAgents);
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadSessions = async () => {
    const data = await api.get<Session[]>("/chat/sessions");
    setSessions(data);
  };

  const openSession = async (session: Session): Promise<void> => {
    setIsGeneralChat(false);
    setComposingNew(false);
    setActiveSession(session);
    setSelectedAgentId(String(session.agent_id));
    setLoadingMessages(true);
    try {
      const msgs = await api.get<Message[]>(`/chat/sessions/${session.id}/messages`);
      setMessages(msgs);
    } finally {
      setLoadingMessages(false);
    }
  };

  const newChat = () => {
    setIsGeneralChat(false);
    setActiveSession(null);
    setMessages([]);
    setInput("");
    setSelectedAgentId("");
    setComposingNew(false);
    setPendingAttachments([]);
  };

  const startNewChatWithAgent = (agentId: number) => {
    setIsGeneralChat(false);
    setActiveSession(null);
    setMessages([]);
    setInput("");
    setSelectedAgentId(String(agentId));
    setComposingNew(true);
  };

  const openGeneralChat = () => {
    setIsGeneralChat(true);
    setComposingNew(false);
    setActiveSession(null);
    setMessages([]);
    setInput("");
    setSelectedAgentId("unified");
  };

  const deleteSession = async (id: number, e: MouseEvent): Promise<void> => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    await api.delete(`/chat/sessions/${id}`);
    if (activeSession?.id === id) newChat();
    loadSessions();
  };

  const handleAttachClick = () => {
    if (uploading) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (!files.length) return;
    setUploading(true);
    try {
      for (const file of files) {
        try {
          const saved = await api.upload<Attachment>("/chat/upload", file);
          setPendingAttachments((prev) => [...prev, saved]);
        } catch (err) {
          console.error("upload failed", err);
        }
      }
    } finally {
      setUploading(false);
    }
  };

  const removePending = (filename: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.filename !== filename));
  };

  const handleSend = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    const hasText = input.trim().length > 0;
    const hasAttachments = pendingAttachments.length > 0;
    if ((!hasText && !hasAttachments) || !selectedAgentId) return;

    const sentAttachments = pendingAttachments;
    const userMsg: Message = {
      role: "user",
      content: input,
      attachments: sentAttachments.length ? sentAttachments : null,
    };
    setMessages((prev: Message[]) => [...prev, userMsg]);
    const sentInput = input;
    setInput("");
    setPendingAttachments([]);
    setLoading(true);

    try {
      const agentId = selectedAgentId === "unified" ? 1 : parseInt(selectedAgentId);

      const res = await api.post<{
        response: string;
        agent_name: string;
        model: string;
        session_id: number;
      }>("/chat", {
        message: sentInput,
        agent_id: agentId,
        session_id: activeSession?.id ?? null,
        attachments: sentAttachments.length ? sentAttachments : undefined,
      });

      if (!activeSession && selectedAgentId !== "unified") {
        const next = await api.get<Session[]>("/chat/sessions");
        setSessions(next);
        const newSession = next.find((s) => s.id === res.session_id);
        if (newSession) {
          setActiveSession(newSession);
          setComposingNew(false);
        }
      } else {
        loadSessions();
      }

      setMessages((prev: Message[]) => [
        ...prev,
        { role: "assistant", content: res.response, model: res.model },
      ]);
    } catch (err) {
      setMessages((prev: Message[]) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const agentName = (agentId: number | string): string => {
    if (agentId === "unified") return "Unified";
    return agents.find((a: Agent) => a.id === agentId)?.name ?? `Agent #${agentId}`;
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    return isToday
      ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-6 overflow-hidden">
      <aside className="w-72 border-r border-border flex flex-col shrink-0">
        <div className="p-4 border-b border-border space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold flex items-center gap-2">
              <MessageSquare size={16} className="text-muted-foreground" />
              Chats
            </h2>
            <Button size="sm" variant="outline" onClick={newChat}>
              <Plus size={14} className="mr-1" />
              New
            </Button>
          </div>

          <button
            onClick={openGeneralChat}
            className={`flex items-center gap-3 w-full p-3 rounded-md border text-left transition-colors ${
              isGeneralChat
                ? "border-border bg-muted"
                : "border-border hover:bg-muted/50"
            }`}
          >
            <Globe size={16} className="text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-medium">General Chat</p>
              <p className="text-xs text-muted-foreground truncate">
                Global knowledge access
              </p>
            </div>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <p className="text-[10px] font-medium text-muted-foreground px-2 py-1 uppercase tracking-wide">
            Recent
          </p>
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => openSession(s)}
              className={`w-full text-left p-3 rounded-md border transition-colors group cursor-pointer ${
                activeSession?.id === s.id
                  ? "bg-muted border-border"
                  : "border-transparent hover:bg-muted/50"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{s.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground uppercase tracking-wide">
                      {agentName(s.agent_id)}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {formatTime(s.updated_at)}
                    </span>
                  </div>
                </div>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="p-1 rounded hover:bg-muted text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  aria-label="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-muted-foreground py-6 text-center">
              No conversations yet
            </p>
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="h-14 px-6 border-b border-border flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center shrink-0">
              {isGeneralChat ? (
                <Globe size={16} className="text-muted-foreground" />
              ) : (
                <Bot size={16} className="text-muted-foreground" />
              )}
            </div>
            <div className="min-w-0">
              <p className="font-medium text-sm truncate">
                {activeSession
                  ? activeSession.title
                  : isGeneralChat
                  ? "General Chat"
                  : "Select an agent"}
              </p>
              <p className="text-xs text-muted-foreground">
                {selectedAgentId
                  ? agentName(
                      selectedAgentId === "unified" ? "unified" : parseInt(selectedAgentId)
                    )
                  : "—"}
              </p>
            </div>
          </div>
        </header>

        {!activeSession && !isGeneralChat && !composingNew ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-16 h-16 rounded-lg bg-muted flex items-center justify-center mb-4">
              <Bot size={28} className="text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-1">Start a conversation</h3>
            <p className="text-sm text-muted-foreground max-w-md mb-6">
              Pick an agent to start a new chat, or open General Chat from the sidebar.
            </p>
            {agents.length === 0 ? (
              <p className="text-xs text-muted-foreground">No agents yet — create one in /dashboard/agents.</p>
            ) : (
              <div className="grid grid-cols-2 gap-2 w-full max-w-md">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => startNewChatWithAgent(agent.id)}
                    className="p-3 rounded-md border border-border hover:bg-muted/50 transition-colors text-left cursor-pointer"
                  >
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                      {agent.role}
                    </p>
                    <p className="text-sm font-medium truncate">{agent.name}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
              {loadingMessages ? (
                <p className="text-center text-sm text-muted-foreground py-12">
                  Loading messages…
                </p>
              ) : (
                messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`flex gap-3 ${
                        msg.role === "user" ? "flex-row-reverse" : "flex-row"
                      }`}
                    >
                      <div className="w-7 h-7 rounded-md shrink-0 flex items-center justify-center bg-muted text-muted-foreground">
                        {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
                      </div>
                      <div
                        className={`flex flex-col gap-1 ${
                          msg.role === "user" ? "items-end" : "items-start"
                        }`}
                      >
                        <div
                          className={`inline-block max-w-[640px] px-4 py-2.5 rounded-lg text-sm ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "border border-border"
                          }`}
                        >
                          {msg.model && (
                            <p className="text-[10px] uppercase tracking-wide opacity-70 mb-1">
                              {msg.model}
                            </p>
                          )}
                          {msg.attachments && msg.attachments.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                              {msg.attachments.map((att) => (
                                <AuthImage key={att.filename} filename={att.filename} />
                              ))}
                            </div>
                          )}
                          {msg.content && (
                            <p className="leading-relaxed whitespace-pre-wrap break-words">
                              {msg.content}
                            </p>
                          )}
                        </div>
                        {msg.created_at && (
                          <p className="text-[10px] text-muted-foreground">
                            {formatTime(msg.created_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex justify-start">
                  <div className="flex gap-3 items-center">
                    <div className="w-7 h-7 rounded-md bg-muted text-muted-foreground flex items-center justify-center">
                      <Bot size={14} />
                    </div>
                    <div className="flex gap-1 px-3 py-2 rounded-lg border border-border">
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.3s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce [animation-delay:-0.15s]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEnd} />
            </div>

            <div className="px-6 py-4 border-t border-border">
              <div className="max-w-4xl mx-auto space-y-2">
                {pendingAttachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {pendingAttachments.map((att) => (
                      <div key={att.filename} className="relative">
                        <AuthImage filename={att.filename} />
                        <button
                          type="button"
                          onClick={() => removePending(att.filename)}
                          className="absolute top-1 right-1 p-1 rounded-full bg-background border border-border text-muted-foreground hover:text-foreground"
                          aria-label="Remove attachment"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <form onSubmit={handleSend} className="flex items-end gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleAttachClick}
                    disabled={!selectedAgentId || uploading || loading}
                    aria-label="Attach image"
                  >
                    <Paperclip size={14} />
                  </Button>
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                    placeholder={
                      !selectedAgentId ? "Select an agent to start…" : "Type a message…"
                    }
                    disabled={!selectedAgentId || loading}
                    className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm leading-relaxed disabled:opacity-50 max-h-60 overflow-y-auto"
                  />
                  <Button
                    type="submit"
                    disabled={
                      loading ||
                      !selectedAgentId ||
                      (!input.trim() && pendingAttachments.length === 0)
                    }
                  >
                    <Send size={14} className="mr-1" />
                    Send
                  </Button>
                </form>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
