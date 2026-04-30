"use client";

import { useEffect, useState, useRef, FormEvent, MouseEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

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
  const messagesEnd = useRef<HTMLDivElement>(null);

  // Загрузка агентов и сессий при старте
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
    setActiveSession(null);
    setMessages([]);
    setInput("");
  };

  const deleteSession = async (id: number, e: MouseEvent): Promise<void> => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    await api.delete(`/chat/sessions/${id}`);
    if (activeSession?.id === id) newChat();
    loadSessions();
  };

  const handleSend = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    if (!input.trim() || !selectedAgentId) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev: Message[]) => [...prev, userMsg]);
    const sentInput = input;
    setInput("");
    setLoading(true);

    try {
      const res = await api.post<{
        response: string;
        agent_name: string;
        model: string;
        session_id: number;
      }>("/chat", {
        message: sentInput,
        agent_id: parseInt(selectedAgentId),
        session_id: activeSession?.id ?? null,
      });

      // Если это была новая сессия — загружаем её данные
      if (!activeSession) {
        const sessions = await api.get<Session[]>("/chat/sessions");
        setSessions(sessions);
        const newSession = sessions.find((s) => s.id === res.session_id);
        if (newSession) setActiveSession(newSession);
      } else {
        loadSessions(); // обновляем updated_at
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

  const agentName = (agentId: number): string =>
    agents.find((a: Agent) => a.id === agentId)?.name ?? `Agent #${agentId}`;

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    return isToday
      ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleDateString([], { month: "short", day: "numeric" });
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0 -mx-6 -my-6">
      {/* Sidebar — история сессий */}
      <aside className="w-64 border-r border-border flex flex-col shrink-0">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="font-semibold text-sm">Chats</h2>
          <Button size="sm" variant="outline" onClick={newChat}>+ New</Button>
        </div>

        {/* Новый чат — выбор агента */}
        {!activeSession && (
          <div className="p-3 border-b border-border">
            <select
              value={selectedAgentId}
              onChange={(e) => setSelectedAgentId(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs"
            >
              <option value="">Select agent...</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>{a.name} ({a.role})</option>
              ))}
            </select>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s)}
              className={`w-full text-left px-4 py-3 border-b border-border/50 hover:bg-accent transition-colors group ${
                activeSession?.id === s.id ? "bg-accent" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <p className="text-sm font-medium truncate flex-1">{s.title}</p>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive text-xs shrink-0"
                >
                  ✕
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {agentName(s.agent_id)} · {formatTime(s.updated_at)}
              </p>
            </button>
          ))}
          {sessions.length === 0 && (
            <p className="text-xs text-muted-foreground p-4">No chats yet. Start a new one.</p>
          )}
        </div>
      </aside>

      {/* Main — сообщения */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center gap-3 shrink-0">
          {activeSession ? (
            <>
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <div>
                <p className="font-medium text-sm">{activeSession.title}</p>
                <p className="text-xs text-muted-foreground">{agentName(activeSession.agent_id)}</p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              {selectedAgentId
                ? `New chat with ${agentName(parseInt(selectedAgentId))}`
                : "Select an agent to start chatting"}
            </p>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {loadingMessages ? (
            <div className="flex justify-center py-8">
              <p className="text-sm text-muted-foreground animate-pulse">Loading messages...</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
              <p className="text-4xl mb-3">💬</p>
              <p className="text-sm">
                {selectedAgentId ? "Send a message to start the conversation" : "Select an agent first"}
              </p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[72%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-card border border-border rounded-bl-sm"
                  }`}
                >
                  {msg.model && (
                    <p className="text-[10px] text-muted-foreground mb-1 opacity-70">{msg.model}</p>
                  )}
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  {msg.created_at && (
                    <p className="text-[10px] opacity-50 mt-1 text-right">{formatTime(msg.created_at)}</p>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-card border border-border rounded-2xl rounded-bl-sm px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEnd} />
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="px-6 py-4 border-t border-border shrink-0">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                !selectedAgentId
                  ? "Select an agent first..."
                  : "Type your message..."
              }
              disabled={!selectedAgentId}
              className="flex-1 rounded-xl border border-input bg-background px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as FormEvent);
                }
              }}
            />
            <Button type="submit" disabled={loading || !selectedAgentId || !input.trim()}>
              Send
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
