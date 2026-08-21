// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Activity,
  Bot,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  Hash,
  RefreshCw,
  Settings,
  ThumbsDown,
  ThumbsUp,
  Wrench,
  XCircle,
} from "lucide-react";

interface TraceFeedback {
  reward: number | null;
  quality_label: string | null;
}

interface TracingConfig {
  enabled: boolean;
  redact_pii: boolean;
}

interface TraceToolCall {
  name: string;
  arguments: Record<string, any>;
  is_error?: boolean;
}

interface TraceMessage {
  role: string;
  content: string;
}

interface AgentTrace {
  id: string;
  created_at: string;
  agent_role?: string;
  model?: string;
  provider_type?: string;
  session_id?: number | null;
  input_user_text?: string;
  final_text?: string;
  outcome?: string;
  quality_label?: string;
  reward?: number | null;
  iterations?: number;
  tool_error_count?: number;
  hit_max_iterations?: boolean;
  had_tools?: boolean;
  human_labeled?: boolean;
  tool_calls?: TraceToolCall[];
  messages?: TraceMessage[];
}

interface TraceListResponse {
  total: number;
  offset: number;
  limit: number;
  items: AgentTrace[];
}

const OUTCOME_META: Record<string, { label: string; cls: string }> = {
  completed_no_tools: { label: "completed", cls: "text-green-400 bg-green-500/10 border-green-500/20" },
  completed_with_tools: { label: "completed + tools", cls: "text-green-400 bg-green-500/10 border-green-500/20" },
  egress_blocked: { label: "egress blocked", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
  ingress_blocked: { label: "ingress blocked", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
  max_iterations_exhausted: { label: "max iterations", cls: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  llm_error: { label: "llm error", cls: "text-orange-400 bg-orange-500/10 border-orange-500/20" },
};

const LABEL_META: Record<string, { label: string; cls: string }> = {
  good: { label: "good", cls: "text-green-400 bg-green-500/10 border-green-500/20" },
  neutral: { label: "neutral", cls: "text-zinc-400 bg-zinc-500/10 border-zinc-500/20" },
  bad: { label: "bad", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
  excluded: { label: "excluded", cls: "text-zinc-500 bg-zinc-500/10 border-zinc-500/20" },
};

const fmtTime = (ts?: string) => {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const truncate = (s: string, n = 160) =>
  s.length > n ? `${s.slice(0, n)}…` : s;

export function AgentTracesPanel({ agentId }: { agentId: number }) {
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<string>("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [details, setDetails] = useState<Record<string, AgentTrace | null>>({});
  const [limit, setLimit] = useState(50);
  const [tracingCfg, setTracingCfg] = useState<TracingConfig | null>(null);
  const [savingTracing, setSavingTracing] = useState(false);
  const [traceFeedback, setTraceFeedback] = useState<Record<string, TraceFeedback>>({});

  // Load tracing config on mount
  useEffect(() => {
    api
      .get<TracingConfig>(`/agents/${agentId}/tracing`)
      .then(setTracingCfg)
      .catch(() => {});
  }, [agentId]);

  const toggleTracing = async (enabled: boolean) => {
    setSavingTracing(true);
    try {
      const updated = await api.patch<TracingConfig>(`/agents/${agentId}/tracing`, { enabled });
      setTracingCfg(updated);
    } catch {
      toast.error("Failed to update tracing config");
    } finally {
      setSavingTracing(false);
    }
  };

  const sendFeedback = async (traceId: string, value: "thumbs_up" | "thumbs_down") => {
    // Optimistic: show immediately
    const prev = traceFeedback[traceId];
    const reward = value === "thumbs_up" ? 1.0 : -1.0;
    const label = value === "thumbs_up" ? "good" : "bad";
    setTraceFeedback((p) => ({ ...p, [traceId]: { reward, quality_label: label } }));
    try {
      await api.post(`/agents/${agentId}/traces/${traceId}/feedback`, { value });
    } catch {
      // Roll back
      setTraceFeedback((p) => {
        const next = { ...p };
        if (prev) next[traceId] = prev;
        else delete next[traceId];
        return next;
      });
      toast.error("Failed to save feedback");
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = outcomeFilter ? `&outcome=${encodeURIComponent(outcomeFilter)}` : "";
      const data = await api.get<TraceListResponse>(
        `/agents/${agentId}/traces?limit=${limit}&offset=0${q}`,
        { bypassCache: true },
      );
      setTraces(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load traces");
    } finally {
      setLoading(false);
    }
  }, [agentId, outcomeFilter, limit]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleExpand = async (trace: AgentTrace) => {
    const id = trace.id;
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
    // Lazy-load the full trace (with messages) on first expand.
    if (details[id] === undefined) {
      try {
        const full = await api.get<AgentTrace>(
          `/agents/${agentId}/traces/${id}`,
          { bypassCache: true },
        );
        setDetails((prev) => ({ ...prev, [id]: full }));
      } catch {
        setDetails((prev) => ({ ...prev, [id]: null }));
      }
    }
  };

  const outcomeOptions = Object.keys(OUTCOME_META);

  if (loading && traces.length === 0) {
    return (
      <div className="p-8 text-center text-muted-foreground animate-pulse">
        Loading agent traces...
      </div>
    );
  }

  if (error && traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-border/50 bg-surface-1">
        <XCircle size={40} className="text-red-400/40 mb-4" />
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (traces.length === 0) {
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        {/* Tracing config — prominent when no traces exist */}
        {tracingCfg && (
          <div className="rounded-xl border border-border/50 bg-surface-1 p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-semibold flex items-center gap-2">
                  <Settings size={15} className="text-muted-foreground" />
                  Trace Capture
                </p>
                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                  Record every agent turn (messages, tool calls, outcomes) to MongoDB.
                  Traces are the raw material for fine-tuning and quality evals.
                </p>
              </div>
              <label className="inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={tracingCfg.enabled}
                  disabled={savingTracing}
                  onChange={(e) => toggleTracing(e.target.checked)}
                />
                <div className="w-9 h-5 bg-muted peer-checked:bg-success rounded-full relative transition">
                  <div
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${tracingCfg.enabled ? "translate-x-4" : ""}`}
                  />
                </div>
              </label>
            </div>
          </div>
        )}
        <EmptyState
          icon={<Activity size={40} />}
          title="No traces recorded for this agent yet."
          description={
            tracingCfg?.enabled
              ? "Tracing is enabled. Traces will appear here after the next agent turn."
              : "Toggle trace capture above to start recording agent turns."
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-4xl animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Tracing config bar */}
      {tracingCfg && (
        <div className="flex items-center justify-between gap-4 p-3 rounded-xl border border-border/50 bg-surface-1">
          <div className="flex items-center gap-2 min-w-0">
            <Settings size={14} className="text-muted-foreground shrink-0" />
            <span className="text-xs font-medium">Trace Capture</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${tracingCfg.enabled ? "bg-success-soft text-success border border-success/20" : "bg-muted text-muted-foreground border border-border"}`}>
              {tracingCfg.enabled ? "ON" : "OFF"}
            </span>
          </div>
          <label className="inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={tracingCfg.enabled}
              disabled={savingTracing}
              onChange={(e) => toggleTracing(e.target.checked)}
            />
            <div className="w-9 h-5 bg-muted peer-checked:bg-success rounded-full relative transition">
              <div
                className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition ${tracingCfg.enabled ? "translate-x-4" : ""}`}
              />
            </div>
          </label>
        </div>
      )}

      <div className="flex items-center justify-between gap-4 mb-2 flex-wrap">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">
            Agent Traces
          </h3>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-2 border border-border/40 font-mono text-muted-foreground">
            {total} total
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={outcomeFilter}
            onChange={(e) => setOutcomeFilter(e.target.value)}
            className="text-[11px] rounded-md border border-input bg-background px-2 py-1 text-muted-foreground"
          >
            <option value="">all outcomes</option>
            {outcomeOptions.map((o) => (
              <option key={o} value={o}>
                {OUTCOME_META[o].label}
              </option>
            ))}
          </select>
          <button
            onClick={load}
            className="text-[10px] uppercase tracking-widest text-accent hover:underline flex items-center gap-1"
          >
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {traces.map((trace) => {
          const meta = OUTCOME_META[trace.outcome || ""] || {
            label: trace.outcome || "unknown",
            cls: "text-zinc-400 bg-zinc-500/10 border-zinc-500/20",
          };
          const label = trace.quality_label
            ? LABEL_META[trace.quality_label] || LABEL_META.excluded
            : null;
          const isOpen = !!expanded[trace.id];
          const full = details[trace.id];
          const toolCalls = (full || trace).tool_calls || [];

          return (
            <div
              key={trace.id}
              className="rounded-xl border border-border/50 bg-surface-1 overflow-hidden transition-colors hover:border-accent/30"
            >
              {/* Summary row */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => toggleExpand(trace)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleExpand(trace); } }}
                className="w-full text-left p-4 flex items-start gap-3 cursor-pointer"
              >
                <div className="mt-0.5 text-muted-foreground/60">
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border ${meta.cls}`}>
                      {meta.label}
                    </span>
                    {label && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border ${label.cls}`}>
                        {label.label}
                      </span>
                    )}
                    {trace.human_labeled && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border text-purple-400 bg-purple-500/10 border-purple-500/20">
                        human
                      </span>
                    )}
                    {typeof trace.reward === "number" && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        reward {trace.reward.toFixed(2)}
                      </span>
                    )}
                    {/* Feedback buttons */}
                    <span className="flex items-center gap-0.5 ml-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          sendFeedback(trace.id, "thumbs_up");
                        }}
                        className={`p-1 rounded transition-all hover:bg-muted ${
                          (traceFeedback[trace.id]?.quality_label === "good" || trace.quality_label === "good")
                            ? "text-success"
                            : "text-muted-foreground"
                        }`}
                        title="Good response"
                      >
                        <ThumbsUp size={12} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          sendFeedback(trace.id, "thumbs_down");
                        }}
                        className={`p-1 rounded transition-all hover:bg-muted ${
                          (traceFeedback[trace.id]?.quality_label === "bad" || trace.quality_label === "bad")
                            ? "text-danger"
                            : "text-muted-foreground"
                        }`}
                        title="Bad response"
                      >
                        <ThumbsDown size={12} />
                      </button>
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground/60">
                      {fmtTime(trace.created_at)}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-foreground line-clamp-1">
                    {trace.input_user_text || "(no user text)"}
                  </p>
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mt-0.5">
                    {truncate(trace.final_text || "") || "—"}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-muted-foreground/70 flex-wrap">
                    {trace.model && (
                      <span className="flex items-center gap-1">
                        <Cpu size={10} /> {trace.model}
                      </span>
                    )}
                    {typeof trace.iterations === "number" && (
                      <span className="flex items-center gap-1">
                        <Hash size={10} /> {trace.iterations} iters
                      </span>
                    )}
                    {(trace.tool_calls?.length || 0) > 0 && (
                      <span className="flex items-center gap-1">
                        <Wrench size={10} /> {(trace.tool_calls || []).length} tools
                      </span>
                    )}
                    {typeof trace.tool_error_count === "number" && trace.tool_error_count > 0 && (
                      <span className="flex items-center gap-1 text-red-400">
                        <XCircle size={10} /> {trace.tool_error_count} errors
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock size={10} /> {fmtTime(trace.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Expanded detail */}
              {isOpen && (
                <div className="px-4 pb-4 pt-1 border-t border-border/30 animate-in fade-in duration-200">
                  {full === null ? (
                    <p className="text-xs text-red-400 py-2">Failed to load full trace.</p>
                  ) : !full ? (
                    <div className="py-4 text-center text-xs text-muted-foreground animate-pulse">
                      Loading full trace…
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Tool calls */}
                      {toolCalls.length > 0 && (
                        <div>
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                            <Wrench size={12} /> Tool Calls
                          </p>
                          <div className="space-y-2">
                            {toolCalls.map((tc, i) => (
                              <div
                                key={i}
                                className={`rounded-lg border p-3 font-mono text-xs ${
                                  tc.is_error
                                    ? "border-red-500/20 bg-red-500/5"
                                    : "border-border/40 bg-surface-2"
                                }`}
                              >
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="font-bold text-foreground flex items-center gap-1.5">
                                    <Wrench size={11} /> {tc.name}
                                  </span>
                                  {tc.is_error && (
                                    <span className="text-[10px] text-red-400 uppercase font-bold">error</span>
                                  )}
                                </div>
                                <pre className="whitespace-pre-wrap break-words text-muted-foreground leading-relaxed max-h-40 overflow-y-auto">
                                  {JSON.stringify(tc.arguments ?? {}, null, 2)}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Messages */}
                      {(full.messages || []).length > 0 && (
                        <div>
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-2">
                            Conversation
                          </p>
                          <div className="space-y-2">
                            {(full.messages || []).map((m: TraceMessage, i: number) => (
                              <div key={i} className="rounded-lg border border-border/40 bg-surface-2 p-3 text-xs">
                                <span className="text-[10px] uppercase font-bold text-muted-foreground/70 mr-2">
                                  {m.role}
                                </span>
                                <span className="text-muted-foreground whitespace-pre-wrap break-words leading-relaxed">
                                  {m.content || "—"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Final answer */}
                      {(full.final_text || "") !== "" && (
                        <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5 flex items-center gap-1.5">
                            <Bot size={12} /> Final Answer
                          </p>
                          <p className="text-xs text-foreground whitespace-pre-wrap break-words leading-relaxed">
                            {full.final_text}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Load more */}
      {traces.length < total && (
        <div className="flex justify-center pt-2">
          <button
            onClick={() => setLimit((l) => l + 50)}
            className="text-[11px] uppercase tracking-widest text-accent hover:underline px-4 py-2"
          >
            Load more ({total - traces.length} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
