"use client";

import { useEffect, useState, useRef, FormEvent, MouseEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { 
  MessageSquare, 
  Plus, 
  Trash2, 
  Send, 
  User, 
  Bot, 
  Sparkles, 
  Globe,
  Settings,
  MoreVertical
} from "lucide-react";

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
  const [isGeneralChat, setIsGeneralChat] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

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
  };

  const openGeneralChat = () => {
    setIsGeneralChat(true);
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

  const handleSend = async (e: FormEvent): Promise<void> => {
    e.preventDefault();
    if (!input.trim() || !selectedAgentId) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev: Message[]) => [...prev, userMsg]);
    const sentInput = input;
    setInput("");
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
      });

      if (!activeSession && selectedAgentId !== "unified") {
        const sessions = await api.get<Session[]>("/chat/sessions");
        setSessions(sessions);
        const newSession = sessions.find((s) => s.id === res.session_id);
        if (newSession) setActiveSession(newSession);
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
    if (agentId === "unified") return "Unified Intelligence";
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
    <div className="flex h-[calc(100vh-4rem)] bg-[#030712] text-zinc-100 overflow-hidden -mx-6 -my-6">
      {/* Sidebar */}
      <aside className="w-80 border-r border-zinc-800/50 bg-[#0b0f1a]/80 backdrop-blur-xl flex flex-col shrink-0">
        <div className="p-5 border-b border-zinc-800/50 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-lg tracking-tight flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-indigo-500" />
              Intelligence
            </h2>
            <Button 
              size="icon" 
              variant="ghost" 
              onClick={newChat}
              className="rounded-full hover:bg-indigo-500/10 text-indigo-400"
            >
              <Plus className="w-5 h-5" />
            </Button>
          </div>

          <button
            onClick={openGeneralChat}
            className={`flex items-center gap-3 w-full p-3 rounded-xl transition-all border ${
              isGeneralChat 
              ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-400" 
              : "border-transparent hover:bg-white/5 text-zinc-400"
            }`}
          >
            <div className={`p-2 rounded-lg ${isGeneralChat ? "bg-indigo-500/20" : "bg-zinc-800"}`}>
              <Globe className="w-4 h-4" />
            </div>
            <div className="text-left">
              <p className="text-sm font-semibold">General Chat</p>
              <p className="text-[10px] opacity-60">Global knowledge access</p>
            </div>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1">
          <p className="text-[10px] font-bold text-zinc-500 px-3 py-2 uppercase tracking-widest">Recent Activity</p>
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => openSession(s)}
              className={`w-full text-left p-3 rounded-xl transition-all group relative overflow-hidden ${
                activeSession?.id === s.id 
                ? "bg-white/5 border border-white/10 shadow-lg" 
                : "hover:bg-white/5 border border-transparent"
              }`}
            >
              {activeSession?.id === s.id && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-indigo-500 rounded-r-full" />
              )}
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate pr-4 text-zinc-200">{s.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-zinc-500 bg-zinc-800/50 px-1.5 py-0.5 rounded uppercase font-bold tracking-tighter">
                      {agentName(s.agent_id)}
                    </span>
                    <span className="text-[10px] text-zinc-600">{formatTime(s.updated_at)}</span>
                  </div>
                </div>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="p-1.5 rounded-lg hover:bg-red-500/20 text-zinc-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </button>
          ))}
          {sessions.length === 0 && !isGeneralChat && (
            <div className="py-10 text-center opacity-40">
              <Sparkles className="w-8 h-8 mx-auto mb-2" />
              <p className="text-xs">No conversations yet</p>
            </div>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-500/5 via-transparent to-transparent">
        {/* Header */}
        <header className="h-16 px-8 border-b border-zinc-800/50 flex items-center justify-between backdrop-blur-md bg-[#030712]/50">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              {isGeneralChat ? <Globe className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
            </div>
            <div>
              <h3 className="font-bold text-sm leading-tight">
                {activeSession ? activeSession.title : isGeneralChat ? "General Intelligence" : "Select Agent"}
              </h3>
              <p className="text-[10px] text-zinc-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Sovereign System Online
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="icon" variant="ghost" className="rounded-full text-zinc-500"><Settings className="w-4 h-4" /></Button>
            <Button size="icon" variant="ghost" className="rounded-full text-zinc-500"><MoreVertical className="w-4 h-4" /></Button>
          </div>
        </header>

        {/* Chat Body */}
        {!activeSession && !isGeneralChat ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-6">
            <div className="relative">
              <div className="absolute inset-0 bg-indigo-500/20 blur-3xl rounded-full animate-pulse" />
              <div className="relative w-24 h-24 rounded-3xl bg-zinc-900 border border-zinc-800 flex items-center justify-center rotate-12">
                <Bot className="w-12 h-12 text-indigo-400 -rotate-12" />
              </div>
            </div>
            <div className="max-w-md space-y-2">
              <h1 className="text-2xl font-bold tracking-tight text-white">AladdinAI Sovereign Chat</h1>
              <p className="text-zinc-500 text-sm">Select a specialized agent from the history or start a fresh session to begin your sovereign workflow.</p>
            </div>
            <div className="grid grid-cols-2 gap-3 w-full max-w-lg mt-8">
              {agents.slice(0, 4).map(agent => (
                <button 
                  key={agent.id}
                  onClick={() => {
                    setSelectedAgentId(String(agent.id));
                    setActiveSession(null);
                    setMessages([]);
                  }}
                  className="p-4 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all text-left group"
                >
                  <p className="text-xs font-bold text-indigo-400 group-hover:text-indigo-300 mb-1 capitalize">{agent.role}</p>
                  <p className="text-sm font-semibold text-zinc-200">{agent.name}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-8 py-8 space-y-8 custom-scrollbar">
              {loadingMessages ? (
                <div className="flex flex-col items-center justify-center h-full opacity-50">
                  <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
                  <p className="text-xs uppercase tracking-widest font-bold">Synchronizing Memory...</p>
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2`}>
                    <div className={`flex gap-4 max-w-[80%] ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                      <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center border ${
                        msg.role === "user" 
                        ? "bg-zinc-800 border-zinc-700" 
                        : "bg-indigo-600/20 border-indigo-500/30"
                      }`}>
                        {msg.role === "user" ? <User className="w-4 h-4 text-zinc-400" /> : <Bot className="w-4 h-4 text-indigo-400" />}
                      </div>
                      <div className={`space-y-1 ${msg.role === "user" ? "text-right" : "text-left"}`}>
                        <div className={`px-5 py-3 rounded-2xl shadow-sm ${
                          msg.role === "user"
                            ? "bg-gradient-to-br from-indigo-600 to-indigo-700 text-white rounded-tr-none"
                            : "bg-zinc-900/80 backdrop-blur-sm border border-zinc-800 text-zinc-200 rounded-tl-none"
                        }`}>
                          {msg.model && <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-2">{msg.model}</p>}
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        </div>
                        {msg.created_at && (
                          <p className="text-[9px] text-zinc-600 font-medium">{formatTime(msg.created_at)}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
              {loading && (
                <div className="flex justify-start animate-in fade-in duration-300">
                  <div className="flex gap-4 items-center">
                    <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center animate-pulse">
                      <Bot className="w-4 h-4 text-indigo-400" />
                    </div>
                    <div className="flex gap-1.5 p-3 bg-zinc-900/50 rounded-2xl rounded-tl-none border border-zinc-800">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEnd} />
            </div>

            {/* Input Container */}
            <div className="px-8 py-6 bg-gradient-to-t from-[#030712] via-[#030712] to-transparent">
              <form 
                onSubmit={handleSend} 
                className="max-w-4xl mx-auto relative group"
              >
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-500" />
                <div className="relative flex items-center bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden p-2 shadow-2xl">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={!selectedAgentId ? "Synchronize an agent to start..." : "Query your sovereign AI..."}
                    disabled={!selectedAgentId || loading}
                    className="flex-1 bg-transparent px-4 py-3 text-sm outline-none placeholder:text-zinc-600 disabled:opacity-50"
                  />
                  <Button 
                    type="submit" 
                    disabled={loading || !selectedAgentId || !input.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl px-5 h-11 flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
                  >
                    {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Send className="w-4 h-4" />}
                  </Button>
                </div>
              </form>
              <p className="text-[9px] text-center text-zinc-600 mt-3 font-medium uppercase tracking-widest">
                Protected by Restricted Correlation Framework Protocol v2.0.3
              </p>
            </div>
          </>
        )}
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #1f2937;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #374151;
        }
      `}</style>
    </div>
  );
}
