"use client";

import React, { useEffect, useState, useRef, FormEvent, MouseEvent, KeyboardEvent } from "react";
import { api, API_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Send,
  Paperclip,
  X,
  Menu,
  Sparkles,
  Mic,
  Square,
  Volume2,
  VolumeX,
  Download,
  PanelLeftOpen,
} from "lucide-react";
import { VoicePlayer } from "./VoicePlayer";
import { AuthAttachment } from "./AuthAttachment";
import { ChatSidebar, Agent, Session } from "./ChatSidebar";
import { ChatMessageItem, Message, Attachment } from "./ChatMessageItem";

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionQuery, setSessionQuery] = useState("");
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [feedback, setFeedback] = useState<Record<number, string>>({});
  const [input, setInput] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isGeneralChat, setIsGeneralChat] = useState(false);
  const [composingNew, setComposingNew] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [currentThought, setCurrentThought] = useState<string | null>(null);
  const [thoughtHistory, setThoughtHistory] = useState<string[]>([]);
  const [assistantStreaming, setAssistantStreaming] = useState(false);

  const messagesEnd = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voiceReply, setVoiceReply] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<any>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoading(false);
    setAssistantStreaming(false);
    setCurrentThought(null);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const file = new File([audioBlob], "voice.webm", { type: "audio/webm" });
        setUploading(true);
        try {
          const saved = await api.upload<Attachment>("/chat/upload", file);
          setPendingAttachments((prev) => [...prev, { ...saved, kind: "audio" }]);
        } catch (err) {
          console.error("Failed to upload recorded audio:", err);
        } finally {
          setUploading(false);
        }
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      timerIntervalRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Microphone access denied or error:", err);
      alert("Microphone access is required to record voice messages.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }
  };

  const formatDuration = (s: number) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

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
    const pending = sessionStorage.getItem("aladdin_pending_chat_prompt");
    if (pending) {
      setInput(pending);
      sessionStorage.removeItem("aladdin_pending_chat_prompt");
    }
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
      const saved: Record<number, string> = {};
      for (const m of msgs) {
        if (m.id && m.feedback) saved[m.id] = m.feedback;
      }
      setFeedback(saved);
    } finally {
      setLoadingMessages(false);
    }
  };

  const startNewChatWithAgent = (agentId: number) => {
    setIsGeneralChat(false);
    setActiveSession(null);
    setComposingNew(true);
    setMessages([]);
    setInput("");
    setSelectedAgentId(String(agentId));
  };

  const newChat = () => {
    setIsGeneralChat(false);
    setActiveSession(null);
    setComposingNew(true);
    setMessages([]);
    setInput("");
    setSelectedAgentId(agents[0] ? String(agents[0].id) : "1");
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

  const [isDragging, setIsDragging] = useState(false);

  const uploadFileList = async (files: File[]) => {
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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    await uploadFileList(files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files ?? []);
    if (files.length > 0) {
      await uploadFileList(files);
    }
  };

  const removePending = (filename: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.filename !== filename));
  };

  const copyToClipboard = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
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
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };

      const controller = new AbortController();
      abortControllerRef.current = controller;

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers,
        signal: controller.signal,
        body: JSON.stringify({
          message: sentInput,
          agent_id: agentId,
          session_id: activeSession?.id ?? null,
          attachments: sentAttachments.length ? sentAttachments : undefined,
          stream: true,
          voice_reply: voiceReply,
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Request failed with status ${response.status}`);
      }

      if (!response.body) {
        throw new Error("Response body is empty");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      setThoughtHistory([]);
      setCurrentThought("Initializing agent execution...");
      setAssistantStreaming(false);
      let streamedReply = "";
      let assistantMessageAdded = false;
      let lastStreamFrameTime = 0;
      const activeThoughts: string[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const event = JSON.parse(line);
            if (event.type === "thought") {
              setCurrentThought(event.message);
              activeThoughts.push(event.message);
            } else if (event.type === "token") {
              streamedReply += event.text;
              setAssistantStreaming(true);
              const now = Date.now();

              if (!assistantMessageAdded) {
                assistantMessageAdded = true;
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "assistant",
                    content: streamedReply,
                    model: event.model || null,
                    thoughts: [...activeThoughts],
                  },
                ]);
                lastStreamFrameTime = now;
              } else if (now - lastStreamFrameTime > 35) {
                lastStreamFrameTime = now;
                setMessages((prev) => {
                  const copy = [...prev];
                  const lastIndex = copy.length - 1;
                  if (lastIndex >= 0 && copy[lastIndex].role === "assistant") {
                    copy[lastIndex] = {
                      ...copy[lastIndex],
                      content: streamedReply,
                      thoughts: [...activeThoughts],
                    };
                  }
                  return copy;
                });
              }
            } else if (event.type === "done") {
              if (event.session_id && (!activeSession || activeSession.id !== event.session_id)) {
                setActiveSession({
                  id: event.session_id,
                  title: sentInput.slice(0, 30) || "New Chat",
                  agent_id: agentId,
                  created_at: new Date().toISOString(),
                });
                loadSessions();
              }
              if (event.message_id) {
                setMessages((prev) => {
                  const copy = [...prev];
                  const lastIndex = copy.length - 1;
                  if (lastIndex >= 0 && copy[lastIndex].role === "assistant") {
                    copy[lastIndex] = {
                      ...copy[lastIndex],
                      id: event.message_id,
                      content: streamedReply || copy[lastIndex].content,
                      thoughts: [...activeThoughts],
                    };
                  }
                  return copy;
                });
              }
              setCurrentThought(null);
              setAssistantStreaming(false);
            } else if (event.type === "error") {
              throw new Error(event.message);
            }
          } catch (e) {
            // Ignore partial lines
          }
        }
      }

      if (streamedReply) {
        setMessages((prev) => {
          const copy = [...prev];
          const lastIndex = copy.length - 1;
          if (lastIndex >= 0 && copy[lastIndex].role === "assistant") {
            copy[lastIndex] = {
              ...copy[lastIndex],
              content: streamedReply,
              thoughts: [...activeThoughts],
            };
          }
          return copy;
        });
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Chat generation stopped by user");
        return;
      }
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err.message || "Failed to communicate with AladdinAI"}`,
        },
      ]);
    } finally {
      setLoading(false);
      setAssistantStreaming(false);
      setCurrentThought(null);
      abortControllerRef.current = null;
    }
  };

  const sendFeedback = async (messageId: number, type: "thumbs_up" | "thumbs_down") => {
    setFeedback((prev) => ({ ...prev, [messageId]: type }));
    try {
      await api.post(`/chat/messages/${messageId}/feedback`, { type });
    } catch (err) {
      console.error("Failed to post feedback:", err);
    }
  };

  const exportChat = () => {
    if (!messages.length) return;
    const title = activeSession?.title || (isGeneralChat ? "General Chat" : "AladdinAI Chat");
    let markdown = `# ${title}\n*Exported on ${new Date().toLocaleString()}*\n\n---\n\n`;

    for (const msg of messages) {
      const sender = msg.role === "user" ? "User" : "AladdinAI";
      const timeStr = msg.created_at ? ` (${new Date(msg.created_at).toLocaleTimeString()})` : "";
      markdown += `### **${sender}**${timeStr}\n${msg.content}\n\n`;
    }

    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}_export.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatTime = (ts?: string) => {
    if (!ts) return "";
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="flex h-[calc(100vh-80px)] bg-background relative overflow-hidden rounded-2xl border border-border/50 shadow-sm"
    >
      {/* Drag & Drop File Upload Overlay */}
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-background/90 backdrop-blur-md flex flex-col items-center justify-center border-2 border-dashed border-primary animate-in fade-in-50 duration-200">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4 text-primary animate-bounce">
            <Paperclip size={32} />
          </div>
          <p className="text-lg font-semibold text-foreground mb-1">Drop files here to upload</p>
          <p className="text-xs text-muted-foreground">Supports images, audio, docs, code & text</p>
        </div>
      )}

      {/* Sidebar Component */}
      <ChatSidebar
        sidebarOpen={sidebarOpen}
        sidebarCollapsed={sidebarCollapsed}
        sessions={sessions}
        agents={agents}
        sessionQuery={sessionQuery}
        activeSession={activeSession}
        selectedAgentId={selectedAgentId}
        isGeneralChat={isGeneralChat}
        onSetSidebarOpen={setSidebarOpen}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onSetSessionQuery={setSessionQuery}
        onNewChat={newChat}
        onOpenGeneralChat={openGeneralChat}
        onOpenSession={openSession}
        onDeleteSession={deleteSession}
        onSelectAgent={setSelectedAgentId}
      />

      {/* Main Chat Content */}
      <div className="flex-1 flex flex-col min-w-0 bg-background">
        {/* Header bar */}
        <header className="h-14 border-b border-border/50 px-6 flex items-center justify-between shrink-0 bg-background/95 backdrop-blur-sm z-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-muted-foreground hover:text-foreground rounded-lg"
            >
              <Menu size={18} />
            </button>
            {sidebarCollapsed && (
              <button
                onClick={() => setSidebarCollapsed(false)}
                className="hidden lg:flex p-2 text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-xl transition-colors shrink-0"
                title="Show history sidebar"
              >
                <PanelLeftOpen size={18} />
              </button>
            )}
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                <Sparkles size={14} className="text-primary" />
              </div>
              <span className="font-semibold text-sm">
                {activeSession?.title || (isGeneralChat ? "General Chat" : "AladdinAI")}
              </span>
            </div>
          </div>

          {messages.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              onClick={exportChat}
              className="h-8 text-xs gap-1.5 rounded-lg border-border/60 hover:bg-muted/80 transition-all"
              title="Export conversation history to Markdown"
            >
              <Download size={13} />
              <span>Export Chat</span>
            </Button>
          )}
        </header>

        {!activeSession && !isGeneralChat && !composingNew ? (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-3xl mx-auto w-full">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-primary/5 border border-primary/20 flex items-center justify-center mb-8 shadow-sm">
              <Sparkles size={40} className="text-primary" />
            </div>
            <h3 className="text-3xl font-semibold mb-3 bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
              Hello
            </h3>
            <p className="text-sm text-muted-foreground max-w-md mb-10 leading-relaxed">
              How can I help you today?
            </p>
            {agents.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-3xl max-h-80 overflow-y-auto pr-1">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    type="button"
                    onClick={() => startNewChatWithAgent(agent.id)}
                    className="p-5 rounded-2xl border border-border/50 hover:border-primary/30 hover:bg-muted/30 hover:shadow-md transition-all text-left cursor-pointer group"
                  >
                    <p className="text-sm font-semibold mb-1.5 group-hover:text-primary transition-colors">
                      {agent.name}
                    </p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{agent.role}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Messages Feed */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
                {loadingMessages ? (
                  <p className="text-center text-sm text-muted-foreground py-12">
                    Loading messages…
                  </p>
                ) : (
                  messages.map((msg, i) => (
                    <ChatMessageItem
                      key={i}
                      msg={msg}
                      index={i}
                      isLast={i === messages.length - 1}
                      assistantStreaming={assistantStreaming}
                      copiedCode={copiedCode}
                      feedback={feedback}
                      onCopy={copyToClipboard}
                      onEditPrompt={(text) => {
                        setInput(text);
                        textareaRef.current?.focus();
                      }}
                      onSendFeedback={sendFeedback}
                      onSelectSuggestion={(sug) => {
                        setInput(sug);
                        textareaRef.current?.focus();
                      }}
                      formatTime={formatTime}
                    />
                  ))
                )}

                {/* Active Thinking Indicator */}
                {loading && !assistantStreaming && (
                  <div className="flex gap-4" style={{ animation: "mpIn 200ms ease-out both" }}>
                    <div className="shrink-0 mt-1">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center">
                        <Sparkles size={16} className="text-primary animate-pulse" />
                      </div>
                    </div>
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs font-semibold text-foreground">AladdinAI</span>
                      </div>

                      <div className="flex items-center gap-2 py-1.5 px-3 rounded-full bg-card/90 border border-border/80 text-xs font-mono max-w-fit shadow-xs transition-all">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                        </span>
                        <span className="text-foreground font-sans font-semibold text-[11px]">Thinking</span>
                        <span className="text-muted-foreground">•</span>
                        <span className="text-muted-foreground truncate max-w-sm text-[11px]">
                          {currentThought || (thoughtHistory.length > 0 ? thoughtHistory[thoughtHistory.length - 1] : "Analyzing prompt & tools...")}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEnd} />
              </div>
            </div>

            {/* Input Area */}
            <div className="px-6 py-4 border-t border-border/50 bg-background/95 backdrop-blur-sm">
              <div className="max-w-4xl mx-auto space-y-3">
                {pendingAttachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {pendingAttachments.map((att) => (
                      <div key={att.filename} className="relative group">
                        <AuthAttachment filename={att.filename} mime={att.mime} kind={att.kind} compact />
                        <button
                          type="button"
                          onClick={() => removePending(att.filename)}
                          className="absolute -top-2 -right-2 p-1.5 rounded-full bg-red-500 text-white shadow-md opacity-0 group-hover:opacity-100 transition-opacity"
                          aria-label="Remove attachment"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between px-1 text-xs mb-1">
                  <div className="text-muted-foreground">
                    {uploading && <span className="animate-pulse">Uploading attachment...</span>}
                  </div>
                  {selectedAgentId && (
                    <button
                      type="button"
                      onClick={() => setVoiceReply(!voiceReply)}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all ${voiceReply
                          ? "bg-primary/10 border-primary/30 text-primary font-medium shadow-sm"
                          : "bg-muted/30 border-border text-muted-foreground hover:bg-muted/60"
                        }`}
                    >
                      {voiceReply ? <Volume2 size={13} className="animate-bounce" /> : <VolumeX size={13} />}
                      <span>Voice Reply {voiceReply ? "ON" : "OFF"}</span>
                    </button>
                  )}
                </div>

                <form onSubmit={handleSend} className="relative">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,audio/*,text/plain,text/markdown,text/csv,application/json,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/xml"
                    multiple
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <div className="flex items-end gap-3 p-3 rounded-2xl border border-border bg-background shadow-sm hover:border-primary/30 transition-all focus-within:border-primary/50 focus-within:shadow-md focus-within:ring-4 focus-within:ring-primary/10">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={handleAttachClick}
                      disabled={!selectedAgentId || uploading || loading}
                      className="rounded-xl w-10 h-10 shrink-0 hover:bg-muted/80"
                      aria-label="Attach file"
                    >
                      <Paperclip size={18} className="text-muted-foreground" />
                    </Button>

                    {isRecording ? (
                      <div className="flex-1 flex items-center justify-between px-3 py-2 text-[15px] text-red-500 font-medium animate-pulse">
                        <span className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
                          Recording voice message...
                        </span>
                        <span className="font-mono text-sm">{formatDuration(recordingSeconds)}</span>
                      </div>
                    ) : (
                      <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        rows={1}
                        placeholder={
                          !selectedAgentId ? "Select an agent to start…" : "Message AladdinAI"
                        }
                        disabled={!selectedAgentId || loading}
                        className="flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] leading-relaxed disabled:opacity-50 max-h-60 overflow-y-auto focus:outline-none placeholder:text-muted-foreground/50"
                      />
                    )}

                    {selectedAgentId && (
                      <Button
                        type="button"
                        onClick={isRecording ? stopRecording : startRecording}
                        variant="ghost"
                        size="icon"
                        className={`rounded-xl w-10 h-10 shrink-0 transition-all ${isRecording
                            ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
                            : "hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                          }`}
                        aria-label={isRecording ? "Stop recording" : "Record voice"}
                      >
                        {isRecording ? <Square size={16} /> : <Mic size={18} />}
                      </Button>
                    )}

                    {loading || assistantStreaming ? (
                      <Button
                        type="button"
                        onClick={handleStopStreaming}
                        size="icon"
                        className="rounded-xl w-10 h-10 shrink-0 bg-red-500 hover:bg-red-600 text-white shadow-md transition-all animate-pulse"
                        title="Stop generating response"
                        aria-label="Stop generating"
                      >
                        <Square size={16} className="fill-current" />
                      </Button>
                    ) : (
                      <Button
                        type="submit"
                        disabled={
                          !selectedAgentId ||
                          (!input.trim() && pendingAttachments.length === 0)
                        }
                        size="icon"
                        className="rounded-xl w-10 h-10 shrink-0 bg-gradient-to-br from-blue-500 to-violet-600 hover:from-blue-600 hover:to-violet-700 shadow-md disabled:opacity-50 disabled:from-muted disabled:to-muted"
                      >
                        <Send size={18} />
                      </Button>
                    )}
                  </div>
                </form>
                <p className="text-[10px] text-center text-muted-foreground/50">
                  AladdinAI can make mistakes. Check important info.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
