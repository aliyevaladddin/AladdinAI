// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState, useRef, useCallback, FormEvent, MouseEvent, KeyboardEvent } from "react";
import { api, API_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Bot,
  Globe,
  Paperclip,
  X,
  Menu,
  Sparkles,
  Copy,
  Check,
  Mic,
  Square,
  Volume2,
  VolumeX,
  ThumbsUp,
  ThumbsDown,
  Play,
  Pause,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";


interface Attachment {
  filename: string;
  path: string;
  mime: string;
  kind: string;
}


// ── Premium Voice Message Player (Telegram-style) ─────────────────────────
function VoicePlayer({ src, isUser }: { src: string; isUser?: boolean }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const toggle = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) { audio.pause(); } else { audio.play(); }
    setPlaying(!playing);
  }, [playing]);

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    setCurrentTime(audio.currentTime);
    setProgress((audio.currentTime / audio.duration) * 100);
  };
  const handleLoadedMetadata = () => { if (audioRef.current) setDuration(audioRef.current.duration); };
  const handleEnded = () => { setPlaying(false); setProgress(0); setCurrentTime(0); };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.currentTime = ratio * audio.duration;
    setProgress(ratio * 100);
  };

  const fmt = (s: number) => {
    if (!isFinite(s) || s === 0) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  // Organic-looking waveform heights
  const bars = [3, 6, 10, 15, 20, 14, 18, 8, 22, 16, 10, 18, 12, 20, 7, 15, 22, 11, 17, 9, 14, 20, 6, 12, 18];

  return (
    <div
      className={`flex items-center gap-3 px-3.5 py-3 rounded-2xl max-w-[280px] shadow-lg ${
        isUser
          ? "bg-white/15 backdrop-blur-md border border-white/20"
          : "bg-gradient-to-r from-violet-500/10 via-blue-500/10 to-cyan-500/10 border border-violet-500/20 backdrop-blur-sm"
      }`}
    >
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        className="hidden"
      />

      {/* Play / Pause button with glow */}
      <button
        onClick={toggle}
        className={`relative w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-all duration-200 hover:scale-110 active:scale-95 ${
          isUser
            ? "bg-white/90 text-violet-600 shadow-[0_0_16px_rgba(255,255,255,0.4)]"
            : "bg-gradient-to-br from-violet-500 to-blue-600 text-white shadow-[0_0_16px_rgba(139,92,246,0.5)]"
        }`}
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? (
          <Pause size={16} className="shrink-0" />
        ) : (
          <Play size={16} className="shrink-0 translate-x-0.5" />
        )}
        {/* Ripple on play */}
        {playing && (
          <span className={`absolute inset-0 rounded-full animate-ping opacity-30 ${
            isUser ? "bg-white" : "bg-violet-400"
          }`} />
        )}
      </button>

      {/* Waveform + seeker */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Animated waveform bars */}
        <div
          className="flex items-center gap-[2px] h-6 cursor-pointer"
          onClick={handleSeek}
        >
          {bars.map((h, i) => {
            const barProgress = (i / bars.length) * 100;
            const isPast = barProgress <= progress;
            const isNearCurrent = Math.abs(barProgress - progress) < 8 && playing;
            return (
              <div
                key={i}
                className={`rounded-full w-[2.5px] flex-shrink-0 transition-all duration-150 ${
                  isPast
                    ? isUser
                      ? "bg-white"
                      : "bg-violet-400"
                    : isUser
                    ? "bg-white/35"
                    : "bg-muted-foreground/25"
                }`}
                style={{
                  height: `${h}px`,
                  transform: isNearCurrent ? "scaleY(1.3)" : "scaleY(1)",
                  animationDelay: `${i * 40}ms`,
                }}
              />
            );
          })}
        </div>

        {/* Time row */}
        <div className={`flex items-center justify-between text-[10px] font-mono ${
          isUser ? "text-white/70" : "text-muted-foreground"
        }`}>
          <span>{fmt(currentTime)}</span>
          <span className={`text-[9px] uppercase tracking-wide font-semibold ${
            isUser ? "text-white/50" : "text-violet-400/70"
          }`}>Voice</span>
          <span>{fmt(duration || 0)}</span>
        </div>
      </div>
    </div>
  );
}


function AuthAttachment({ filename, mime, kind, isUser }: { filename: string; mime?: string; kind?: string; isUser?: boolean }) {
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
      .catch(() => { });
    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [filename]);

  if (!src) {
    return <div className="w-[280px] h-16 rounded-2xl bg-muted/60 animate-pulse" />;
  }

  const isImg = kind === "image" || (mime && mime.startsWith("image/")) || filename.match(/\.(jpeg|jpg|gif|png|webp)$/i);
  const isAudio = kind === "audio" || (mime && mime.startsWith("audio/")) || filename.match(/\.(webm|ogg|wav|mp3|m4a)$/i);

  if (isImg) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={filename} className="max-w-xs max-h-80 rounded-xl border border-border shadow-sm" />;
  }

  if (isAudio) {
    return <VoicePlayer src={src} isUser={isUser} />;
  }

  return (
    <a
      href={src}
      download={filename}
      className="flex items-center gap-2 px-3 py-2 bg-muted/80 hover:bg-muted border border-border rounded-lg text-xs font-medium text-foreground transition-colors max-w-sm"
    >
      <span className="shrink-0 text-primary">📄</span>
      <span className="truncate flex-1">{filename}</span>
      <span className="text-[10px] text-muted-foreground uppercase">{mime?.split("/")[1] || "DOC"}</span>
    </a>
  );
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
  feedback?: string | null;  // this user's saved reaction: thumbs_up | thumbs_down
}

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  // message_id -> "thumbs_up" | "thumbs_down": which reaction the user gave
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
      // Restore saved 👍/👎 so the highlight survives reloads / session switches.
      const saved: Record<number, string> = {};
      for (const m of msgs) {
        if (m.id && m.feedback) saved[m.id] = m.feedback;
      }
      setFeedback(saved);
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

      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers,
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
            } else if (event.type === "token") {
              streamedReply += event.text;
              setAssistantStreaming(true);
              if (!assistantMessageAdded) {
                setMessages((prev: Message[]) => [
                  ...prev,
                  {
                    role: "assistant",
                    content: streamedReply,
                    model: null,
                  },
                ]);
                assistantMessageAdded = true;
              } else {
                setMessages((prev: Message[]) =>
                  prev.map((m, idx) =>
                    idx === prev.length - 1 ? { ...m, content: streamedReply } : m
                  )
                );
              }
            } else if (event.type === "tool_start") {
              const argStr = event.arguments ? JSON.stringify(event.arguments) : "";
              setCurrentThought(`Running tool '${event.name}' ${argStr.length > 50 ? argStr.slice(0, 50) + "..." : argStr}`);
            } else if (event.type === "tool_end") {
              const name = event.name;
              setThoughtHistory((prev) => [...prev, `Tool '${name}' executed successfully.`]);
            } else if (event.type === "done") {
              setAssistantStreaming(false);
              if (assistantMessageAdded) {
                setMessages((prev: Message[]) =>
                  prev.map((m, idx) =>
                    idx === prev.length - 1
                      ? {
                          ...m,
                          id: event.message_id,
                          content: event.response,
                          model: event.model,
                          attachments: event.attachments ?? null,
                        }
                      : m
                  )
                );
              } else {
                setMessages((prev: Message[]) => [
                  ...prev,
                  {
                    id: event.message_id,
                    role: "assistant",
                    content: event.response,
                    model: event.model,
                    attachments: event.attachments ?? null,
                  },
                ]);
              }

              if (!activeSession && selectedAgentId !== "unified") {
                const next = await api.get<Session[]>("/chat/sessions");
                setSessions(next);
                const newSession = next.find((s) => s.id === event.session_id);
                if (newSession) {
                  setActiveSession(newSession);
                  setComposingNew(false);
                }
              } else {
                loadSessions();
              }
              setCurrentThought(null);
            } else if (event.type === "error") {
              throw new Error(event.message);
            }
          } catch (jsonErr) {
            console.error("Failed to parse stream line:", line, jsonErr);
          }
        }
      }
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
      setAssistantStreaming(false);
      setCurrentThought(null);
    }
  };


  const agentName = (agentId: number | string): string => {
    if (agentId === "unified") return "Unified";
    return agents.find((a: Agent) => a.id === agentId)?.name ?? `Agent #${agentId}`;
  };

  // Send a 👍/👎 on an assistant reply. Clicking the active reaction clears it.
  const sendFeedback = async (messageId: number, value: string) => {
    const next = feedback[messageId] === value ? undefined : value;
    // Optimistic: reflect the click immediately, roll back on failure.
    setFeedback((prev) => {
      const copy = { ...prev };
      if (next) copy[messageId] = next;
      else delete copy[messageId];
      return copy;
    });
    if (!next) return; // no clear-endpoint yet; local un-highlight only
    try {
      await api.post(`/chat/messages/${messageId}/feedback`, { value: next });
    } catch {
      setFeedback((prev) => {
        const copy = { ...prev };
        if (feedback[messageId]) copy[messageId] = feedback[messageId];
        else delete copy[messageId];
        return copy;
      });
    }
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
    <div className="flex h-[calc(100vh-4rem)] -mx-8 -my-6 overflow-hidden bg-background">
      {/* Premium Sidebar */}
      <aside
        className={`${sidebarOpen ? "w-64" : "w-0"
          } border-r border-border/50 flex flex-col shrink-0 transition-all duration-300 ease-in-out overflow-hidden bg-muted/10`}
      >
        <div className="p-4 border-b border-border/50">
          <Button
            size="sm"
            variant="ghost"
            onClick={newChat}
            className="w-full justify-start gap-2.5 h-10 rounded-xl hover:bg-muted/80 font-medium"
          >
            <Plus size={18} />
            <span className="text-sm">New chat</span>
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          <button
            onClick={openGeneralChat}
            className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-left transition-all text-sm ${isGeneralChat
                ? "bg-muted/80 font-semibold shadow-sm border border-border/50"
                : "hover:bg-muted/50"
              }`}
          >
            <Globe size={16} className="shrink-0 opacity-70" />
            <span className="truncate">General Chat</span>
          </button>

          {sessions.length > 0 && (
            <div className="pt-4 pb-2">
              <p className="text-[10px] font-bold text-muted-foreground px-3 py-1 uppercase tracking-wider">
                Recent
              </p>
            </div>
          )}

          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => openSession(s)}
              className={`w-full text-left px-3 py-2.5 rounded-xl transition-all group cursor-pointer relative ${activeSession?.id === s.id
                  ? "bg-muted/80 font-semibold shadow-sm border border-border/50"
                  : "hover:bg-muted/50 border border-transparent"
                }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm truncate flex-1">{s.title}</p>
                <button
                  onClick={(e) => deleteSession(s.id, e)}
                  className="p-1.5 rounded-lg hover:bg-background/80 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  aria-label="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Main Content - Centered Gemini Layout */}
      <div className="flex-1 flex flex-col relative">
        {/* Minimal Header */}
        <header className="h-14 px-6 flex items-center justify-between shrink-0 border-b border-border/40 bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="rounded-xl w-9 h-9 hover:bg-muted/80"
            >
              <Menu size={18} />
            </Button>
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center">
                <Sparkles size={14} className="text-primary" />
              </div>
              <span className="font-semibold text-sm">
                {activeSession?.title || (isGeneralChat ? "General Chat" : "AladdinAI")}
              </span>
            </div>
          </div>
        </header>

        {!activeSession && !isGeneralChat && !composingNew ? (
          /* Empty State - Premium style */
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
            {/* Messages - Premium Chat Style */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
                {loadingMessages ? (
                  <p className="text-center text-sm text-muted-foreground py-12">
                    Loading messages…
                  </p>
                ) : (
                  messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                    >
                      {/* Avatar */}
                      <div className="shrink-0 mt-1">
                        {msg.role === "user" ? (
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-sm">
                            <span className="text-[11px] text-white font-semibold">You</span>
                          </div>
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 border border-primary/20 flex items-center justify-center">
                            <Sparkles size={16} className="text-primary" />
                          </div>
                        )}
                      </div>

                      {/* Message bubble */}
                      <div className={`flex-1 min-w-0 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
                        {/* Header */}
                        <div className={`flex items-center gap-2 mb-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                          <span className="text-xs font-semibold text-foreground">
                            {msg.role === "user" ? "You" : "AladdinAI"}
                          </span>
                          {msg.model && (
                            <span className="text-[10px] text-muted-foreground">· {msg.model}</span>
                          )}
                          {msg.created_at && (
                            <span className="text-[10px] text-muted-foreground">
                              · {formatTime(msg.created_at)}
                            </span>
                          )}
                        </div>

                        {/* Audio attachments — rendered OUTSIDE the bubble to avoid gradient conflict */}
                        {msg.attachments && msg.attachments.some(a => a.kind === "audio" || a.mime?.startsWith("audio/")) && (
                          <div className={`flex flex-wrap gap-2 mb-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            {msg.attachments
                              .filter(a => a.kind === "audio" || a.mime?.startsWith("audio/"))
                              .map((att) => (
                                <AuthAttachment key={att.filename} filename={att.filename} mime={att.mime} kind={att.kind} isUser={msg.role === "user"} />
                              ))}
                          </div>
                        )}

                        {/* Content bubble — only shown if there's text OR non-audio attachments */}
                        {(msg.content || (msg.attachments && msg.attachments.some(a => a.kind !== "audio" && !a.mime?.startsWith("audio/")))) && (
                        <div
                          className={`rounded-2xl px-4 py-3 ${msg.role === "user"
                              ? "bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-md"
                              : "bg-muted/50 border border-border/50"
                            }`}
                        >
                          {msg.attachments && msg.attachments.some(a => a.kind !== "audio" && !a.mime?.startsWith("audio/")) && (
                            <div className="flex flex-wrap gap-2 mb-3">
                              {msg.attachments
                                .filter(a => a.kind !== "audio" && !a.mime?.startsWith("audio/"))
                                .map((att) => (
                                  <AuthAttachment key={att.filename} filename={att.filename} mime={att.mime} kind={att.kind} isUser={msg.role === "user"} />
                                ))}
                            </div>
                          )}
                          {msg.content && (
                            <div className={`prose prose-sm max-w-none ${msg.role === "user"
                                ? "prose-invert prose-headings:text-white prose-p:text-white/95 prose-strong:text-white prose-code:text-white/90"
                                : "dark:prose-invert"
                              } prose-pre:my-3 prose-pre:bg-background/95 dark:prose-pre:bg-[#1e1e1e] prose-pre:border prose-pre:border-border/50 prose-pre:shadow-sm prose-code:text-sm prose-p:leading-relaxed prose-headings:font-semibold`}>
                              <ReactMarkdown
                                components={{
                                  code({ node, className, children, ...props }) {
                                    const match = /language-(\w+)/.exec(className || "");
                                    const codeString = String(children).replace(/\n$/, "");
                                    const isCopied = copiedCode === codeString;
                                    // Блочный код имеет language-класс; без него — инлайн
                                    const isBlock = Boolean(match);

                                    return isBlock ? (
                                      <div className="relative group my-3 not-prose">
                                        <div className="absolute top-3 right-3 z-10">
                                          <button
                                            onClick={() => copyToClipboard(codeString)}
                                            className="p-2 rounded-lg bg-background/90 hover:bg-background text-foreground transition-all shadow-sm border border-border/50"
                                            aria-label="Copy code"
                                          >
                                            {isCopied ? <Check size={14} /> : <Copy size={14} />}
                                          </button>
                                        </div>
                                        <SyntaxHighlighter
                                          style={oneDark}
                                          language={match![1]}
                                          PreTag="div"
                                          className="rounded-xl !mt-0 !mb-0 !bg-background/95 dark:!bg-[#1e1e1e] border border-border/50 shadow-sm"
                                          {...(props as object)}
                                        >
                                          {codeString}
                                        </SyntaxHighlighter>
                                      </div>
                                    ) : (
                                      <code className={`${msg.role === "user"
                                          ? "bg-white/20 text-white"
                                          : "bg-muted/80 dark:bg-muted/60 text-foreground"
                                        } px-1.5 py-0.5 rounded text-[13px] font-mono`} {...props}>
                                        {children}
                                      </code>
                                    );
                                  },
                                }}
                              >
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                        )}

                        {/* Feedback — the strong training signal for the self-forging loop */}
                        {msg.role === "assistant" && msg.id && (
                          <div className="flex items-center gap-1 mt-1.5">
                            <button
                              onClick={() => sendFeedback(msg.id!, "thumbs_up")}
                              aria-label="Good response"
                              className={`p-1.5 rounded-lg transition-all hover:bg-muted ${feedback[msg.id] === "thumbs_up" ? "text-green-500" : "text-muted-foreground"}`}
                            >
                              <ThumbsUp size={14} />
                            </button>
                            <button
                              onClick={() => sendFeedback(msg.id!, "thumbs_down")}
                              aria-label="Bad response"
                              className={`p-1.5 rounded-lg transition-all hover:bg-muted ${feedback[msg.id] === "thumbs_down" ? "text-red-500" : "text-muted-foreground"}`}
                            >
                              <ThumbsDown size={14} />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
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
                      
                      <div className="rounded-2xl p-4 bg-muted/30 border border-border/50 max-w-xl space-y-2 text-xs font-mono">
                        <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold border-b border-border/40 pb-1.5 mb-1.5 flex items-center justify-between">
                          <span>Agent Thought Process</span>
                          <span className="flex gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-ping" />
                          </span>
                        </div>
                        {thoughtHistory.map((step, idx) => (
                          <div key={idx} className="text-muted-foreground flex items-start gap-1.5">
                            <span className="text-emerald-500 font-bold">✓</span>
                            <span>{step}</span>
                          </div>
                        ))}
                        {currentThought && (
                          <div className="text-foreground font-medium animate-pulse flex items-start gap-1.5">
                            <span className="text-blue-500 font-bold">▶</span>
                            <span>{currentThought}</span>
                          </div>
                        )}
                        {!currentThought && thoughtHistory.length === 0 && (
                          <div className="flex gap-1.5 py-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEnd} />
              </div>
            </div>

            {/* Input Area - Premium Style */}
            <div className="px-6 py-4 border-t border-border/50 bg-background/95 backdrop-blur-sm">
              <div className="max-w-4xl mx-auto space-y-3">
                {pendingAttachments.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {pendingAttachments.map((att) => (
                      <div key={att.filename} className="relative group">
                        <AuthAttachment filename={att.filename} mime={att.mime} kind={att.kind} />
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
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all ${
                        voiceReply
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
                        className={`rounded-xl w-10 h-10 shrink-0 transition-all ${
                          isRecording
                            ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
                            : "hover:bg-muted/80 text-muted-foreground hover:text-foreground"
                        }`}
                        aria-label={isRecording ? "Stop recording" : "Record voice"}
                      >
                        {isRecording ? <Square size={16} /> : <Mic size={18} />}
                      </Button>
                    )}

                    <Button
                      type="submit"
                      disabled={
                        loading ||
                        !selectedAgentId ||
                        (!input.trim() && pendingAttachments.length === 0)
                      }
                      size="icon"
                      className="rounded-xl w-10 h-10 shrink-0 bg-gradient-to-br from-blue-500 to-violet-600 hover:from-blue-600 hover:to-violet-700 shadow-md disabled:opacity-50 disabled:from-muted disabled:to-muted"
                    >
                      <Send size={18} />
                    </Button>
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
