// NOTICE: This file is protected under RCF-PL
"use client";

/* Slide-over AI assistant for the Files workspace.
   Thin client over the existing POST /chat streaming endpoint — agents keep
   running server-side in the orchestrator, nothing heavy ships to the browser
   here. The panel injects the current space/folder/file as context so the
   agent answers about what the user is looking at. */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Bot, Send, Square, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";

export interface AssistantContext {
  space: string | null;
  folder: string | null;
  file: string | null;
}

interface AgentLite {
  id: number;
  name: string;
}

interface Msg {
  role: "user" | "assistant";
  content: string;
}

interface StreamEvent {
  type: string;
  text?: string;
  message?: string;
  session_id?: number;
}

export default function AssistantPanel({ context }: { context: AssistantContext }) {
  const [open, setOpen] = useState(false);
  const [agents, setAgents] = useState<AgentLite[]>([]);
  const [agentId, setAgentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [thought, setThought] = useState<string | null>(null);

  const sessionIdRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  /* Load agents the first time the panel opens. */
  useEffect(() => {
    if (!open || agents.length > 0) return;
    fetch(`${API_URL}/agents`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
      },
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((list: AgentLite[]) => {
        setAgents(list);
        setAgentId((prev) => prev ?? list[0]?.id ?? null);
      })
      .catch(() => toast.error("Failed to load agents"));
  }, [open, agents.length]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, thought]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming) return;
    if (agentId == null) {
      toast.error("Pick an agent first");
      return;
    }

    const ctxLine = [
      context.space && `space "${context.space}"`,
      context.folder && `folder "${context.folder}"`,
      context.file && `selected file "${context.file}"`,
    ]
      .filter(Boolean)
      .join(", ");
    const payloadMessage = ctxLine ? `[User is viewing ${ctxLine}.]\n\n${text}` : text;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setStreaming(true);
    setThought("Thinking…");

    const controller = new AbortController();
    abortRef.current = controller;
    let reply = "";

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
        },
        signal: controller.signal,
        body: JSON.stringify({
          message: payloadMessage,
          agent_id: agentId,
          session_id: sessionIdRef.current,
          stream: true,
        }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`Request failed (${res.status})`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          let event: StreamEvent;
          try {
            event = JSON.parse(line) as StreamEvent;
          } catch {
            continue;
          }
          if (event.type === "token" && event.text) {
            reply += event.text;
            setMessages((m) => {
              const last = m[m.length - 1];
              if (last?.role === "assistant") {
                return [...m.slice(0, -1), { role: "assistant", content: reply }];
              }
              return [...m, { role: "assistant", content: reply }];
            });
          } else if (event.type === "thought" && event.message) {
            setThought(event.message);
          } else if (event.type === "done") {
            if (event.session_id) sessionIdRef.current = event.session_id;
          } else if (event.type === "error") {
            throw new Error(event.message || "Agent error");
          }
        }
      }
      if (!reply) {
        setMessages((m) => [...m, { role: "assistant", content: "(no answer)" }]);
      }
    } catch (e: unknown) {
      if ((e as Error).name !== "AbortError") {
        toast.error(e instanceof Error ? e.message : "Agent request failed");
      }
    } finally {
      setStreaming(false);
      setThought(null);
      abortRef.current = null;
    }
  }, [agentId, context, input, streaming]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return (
    <>
      {/* Floating launcher */}
      <button
        onClick={() => setOpen((v) => !v)}
        title="AI Assistant"
        className="fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105"
      >
        <Bot size={22} />
      </button>

      {open && (
        <aside className="fixed bottom-20 right-6 z-40 flex h-[560px] w-[380px] max-w-[calc(100vw-3rem)] flex-col rounded-2xl border border-border bg-surface shadow-xl">
          {/* Header */}
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Bot size={16} className="text-primary" />
            <span className="flex-1 text-sm font-medium">Assistant</span>
            <select
              value={agentId ?? ""}
              onChange={(e) => {
                setAgentId(Number(e.target.value));
                sessionIdRef.current = null;
                setMessages([]);
              }}
              className="max-w-[150px] rounded-lg border border-border bg-surface-1 px-2 py-1 text-xs"
            >
              {agents.length === 0 && <option value="">no agents</option>}
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <button
              onClick={() => setOpen(false)}
              className="rounded p-1 text-muted-foreground hover:text-foreground"
              title="Close"
            >
              <X size={15} />
            </button>
          </div>

          {/* Context chips */}
          {(context.space || context.folder || context.file) && (
            <div className="flex flex-wrap gap-1 border-b border-border px-3 py-1.5">
              {[context.space, context.folder, context.file]
                .filter((c): c is string => Boolean(c))
                .map((c) => (
                  <span
                    key={c}
                    className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] text-muted-foreground"
                  >
                    {c}
                  </span>
                ))}
            </div>
          )}

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.length === 0 && (
              <p className="pt-10 text-center text-xs text-muted-foreground">
                Ask about the files you are working with — the agent sees your
                current space, folder and selected file.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "mr-0 bg-primary text-primary-foreground"
                    : "mr-auto max-w-[85%] bg-surface-2 text-foreground ml-0"
                }`}
              >
                {m.content}
              </div>
            ))}
            {streaming && thought && (
              <p className="text-xs italic text-muted-foreground">🤔 {thought}</p>
            )}
          </div>

          {/* Input */}
          <div className="flex items-end gap-2 border-t border-border p-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
              rows={2}
              placeholder="Ask the agent…"
              className="max-h-28 flex-1 resize-none rounded-lg border border-border bg-surface-1 px-2 py-1.5 text-sm outline-none focus:border-ring"
            />
            {streaming ? (
              <Button variant="destructive" size="icon" onClick={stop} title="Stop">
                <Square size={14} />
              </Button>
            ) : (
              <Button size="icon" onClick={() => void send()} title="Send">
                <Send size={14} />
              </Button>
            )}
          </div>
        </aside>
      )}
    </>
  );
}
