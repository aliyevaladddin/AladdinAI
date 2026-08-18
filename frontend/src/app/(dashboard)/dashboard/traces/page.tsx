"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
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
  ThumbsDown,
  ThumbsUp,
  Wrench,
  XCircle,
} from "lucide-react";

interface TraceSummary {
  id: string;
  agent_id: number;
  agent_name?: string;
  created_at: string;
  model?: string;
  outcome?: string;
  quality_label?: string;
  reward?: number | null;
  iterations?: number;
  tool_error_count?: number;
  input_user_text?: string;
  final_text?: string;
  human_labeled?: boolean;
  tool_calls?: { name: string; arguments: Record<string, any>; is_error?: boolean }[];
}

interface TraceDetail extends TraceSummary {
  messages?: { role: string; content: string }[];
}

interface TracesResponse {
  total: number;
  offset: number;
  limit: number;
  items: TraceSummary[];
}

const OUTCOME_META: Record<string, { label: string; cls: string }> = {
  completed_no_tools: { label: "completed", cls: "text-success bg-success-soft border-success/20" },
  completed_with_tools: { label: "completed + tools", cls: "text-success bg-success-soft border-success/20" },
  egress_blocked: { label: "egress blocked", cls: "text-danger bg-danger-soft border-danger/20" },
  ingress_blocked: { label: "ingress blocked", cls: "text-danger bg-danger-soft border-danger/20" },
  max_iterations_exhausted: { label: "max iterations", cls: "text-warning bg-warning-soft border-warning/20" },
  llm_error: { label: "llm error", cls: "text-warning bg-warning-soft border-warning/20" },
};

const LABEL_META: Record<string, { label: string; cls: string }> = {
  good: { label: "good", cls: "text-success bg-success-soft border-success/20" },
  neutral: { label: "neutral", cls: "text-muted-foreground bg-muted border-muted" },
  bad: { label: "bad", cls: "text-danger bg-danger-soft border-danger/20" },
  excluded: { label: "excluded", cls: "text-fg-subtle bg-muted border-border" },
};

const fmtTime = (ts?: string) => {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
};

const truncate = (s: string, n = 160) => (s.length > n ? `${s.slice(0, n)}…` : s);

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [details, setDetails] = useState<Record<string, TraceDetail | null>>({});
  const [limit, setLimit] = useState(50);
  const [traceFeedback, setTraceFeedback] = useState<Record<string, { reward: number | null; quality_label: string | null }>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = outcomeFilter ? `&outcome=${encodeURIComponent(outcomeFilter)}` : "";
      const data = await api.get<TracesResponse>(`/traces?limit=${limit}&offset=0${q}`, { bypassCache: true });
      setTraces(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load traces");
    } finally {
      setLoading(false);
    }
  }, [outcomeFilter, limit]);

  useEffect(() => { load(); }, [load]);

  const sendFeedback = async (traceId: string, agentId: number, value: "thumbs_up" | "thumbs_down") => {
    const prev = traceFeedback[traceId];
    const reward = value === "thumbs_up" ? 1.0 : -1.0;
    const label = value === "thumbs_up" ? "good" : "bad";
    setTraceFeedback((p) => ({ ...p, [traceId]: { reward, quality_label: label } }));
    try {
      await api.post(`/agents/${agentId}/traces/${traceId}/feedback`, { value });
    } catch {
      setTraceFeedback((p) => {
        const next = { ...p };
        if (prev) next[traceId] = prev;
        else delete next[traceId];
        return next;
      });
    }
  };

  const toggleExpand = async (trace: TraceSummary) => {
    const id = trace.id;
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
    if (details[id] === undefined) {
      try {
        const full = await api.get<TraceDetail>(`/agents/${trace.agent_id}/traces/${id}`, { bypassCache: true });
        setDetails((prev) => ({ ...prev, [id]: full }));
      } catch {
        setDetails((prev) => ({ ...prev, [id]: null }));
      }
    }
  };

  if (loading && traces.length === 0) {
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading traces…</div>;
  }

  if (error && traces.length === 0) {
    return <EmptyState icon={<XCircle size={40} />} title="Failed to load traces" description={error} />;
  }

  if (traces.length === 0) {
    return (
      <EmptyState
        icon={<Activity size={40} />}
        title="No traces recorded yet."
        description="Enable trace capture on individual agents to start recording turns."
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">Agent Traces</h1>
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
            {Object.keys(OUTCOME_META).map((o) => (
              <option key={o} value={o}>{OUTCOME_META[o].label}</option>
            ))}
          </select>
          <button onClick={load} className="text-[10px] uppercase tracking-widest text-accent hover:underline flex items-center gap-1">
            <RefreshCw size={11} /> Refresh
          </button>
        </div>
      </div>

      {/* Trace list */}
      <div className="space-y-3">
        {traces.map((trace) => {
          const meta = OUTCOME_META[trace.outcome || ""] || { label: trace.outcome || "unknown", cls: "text-muted-foreground bg-muted border-border" };
          const label = trace.quality_label ? LABEL_META[trace.quality_label] || LABEL_META.excluded : null;
          const isOpen = !!expanded[trace.id];
          const full = details[trace.id];

          return (
            <div key={trace.id} className="rounded-xl border border-border/50 bg-surface-1 overflow-hidden transition-colors hover:border-accent/30">
              <button onClick={() => toggleExpand(trace)} className="w-full text-left p-4 flex items-start gap-3">
                <div className="mt-0.5 text-muted-foreground/60">
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    {/* Agent name */}
                    <Link
                      href={`/dashboard/agents/${trace.agent_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="flex items-center gap-1 text-[11px] font-semibold text-primary hover:underline"
                    >
                      <Bot size={12} />
                      {trace.agent_name || `Agent #${trace.agent_id}`}
                    </Link>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border ${meta.cls}`}>
                      {meta.label}
                    </span>
                    {label && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border ${label.cls}`}>
                        {label.label}
                      </span>
                    )}
                    {trace.human_labeled && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border text-primary bg-primary/10 border-primary/20">
                        human
                      </span>
                    )}
                    {typeof trace.reward === "number" && (
                      <span className="text-[10px] font-mono text-muted-foreground">
                        reward {trace.reward.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-foreground line-clamp-1">
                    {trace.input_user_text || "(no user text)"}
                  </p>
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed mt-0.5">
                    {truncate(trace.final_text || "") || "—"}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-muted-foreground/70 flex-wrap">
                    {trace.model && (
                      <span className="flex items-center gap-1"><Cpu size={10} /> {trace.model}</span>
                    )}
                    {typeof trace.iterations === "number" && (
                      <span className="flex items-center gap-1"><Hash size={10} /> {trace.iterations} iters</span>
                    )}
                    {(trace.tool_calls?.length || 0) > 0 && (
                      <span className="flex items-center gap-1"><Wrench size={10} /> {(trace.tool_calls || []).length} tools</span>
                    )}
                    {typeof trace.tool_error_count === "number" && trace.tool_error_count > 0 && (
                      <span className="flex items-center gap-1 text-danger"><XCircle size={10} /> {trace.tool_error_count} errors</span>
                    )}
                    {/* Feedback buttons */}
                    <span className="flex items-center gap-0.5 ml-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); sendFeedback(trace.id, trace.agent_id, "thumbs_up"); }}
                        className={`p-1 rounded transition-all hover:bg-muted ${(traceFeedback[trace.id]?.quality_label === "good" || trace.quality_label === "good") ? "text-success" : "text-muted-foreground"}`}
                        title="Good response"
                      >
                        <ThumbsUp size={12} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); sendFeedback(trace.id, trace.agent_id, "thumbs_down"); }}
                        className={`p-1 rounded transition-all hover:bg-muted ${(traceFeedback[trace.id]?.quality_label === "bad" || trace.quality_label === "bad") ? "text-danger" : "text-muted-foreground"}`}
                        title="Bad response"
                      >
                        <ThumbsDown size={12} />
                      </button>
                    </span>
                    <span className="flex items-center gap-1"><Clock size={10} /> {fmtTime(trace.created_at)}</span>
                  </div>
                </div>
              </button>

              {/* Expanded detail */}
              {isOpen && (
                <div className="px-4 pb-4 pt-1 border-t border-border/30 animate-in fade-in duration-200">
                  {full === null ? (
                    <p className="text-xs text-danger py-2">Failed to load full trace.</p>
                  ) : !full ? (
                    <div className="py-4 text-center text-xs text-muted-foreground animate-pulse">Loading full trace…</div>
                  ) : (
                    <div className="space-y-4">
                      {(full.tool_calls || []).length > 0 && (
                        <div>
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
                            <Wrench size={12} /> Tool Calls
                          </p>
                          <div className="space-y-2">
                            {(full.tool_calls || []).map((tc, i) => (
                              <div key={i} className={`rounded-lg border p-3 font-mono text-xs ${tc.is_error ? "border-danger/20 bg-danger-soft" : "border-border/40 bg-surface-2"}`}>
                                <div className="flex items-center justify-between mb-1.5">
                                  <span className="font-bold text-foreground flex items-center gap-1.5"><Wrench size={11} /> {tc.name}</span>
                                  {tc.is_error && <span className="text-[10px] text-danger uppercase font-bold">error</span>}
                                </div>
                                <pre className="whitespace-pre-wrap break-words text-muted-foreground leading-relaxed max-h-40 overflow-y-auto">
                                  {JSON.stringify(tc.arguments ?? {}, null, 2)}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {(full.messages || []).length > 0 && (
                        <div>
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-2">Conversation</p>
                          <div className="space-y-2">
                            {(full.messages || []).map((m, i) => (
                              <div key={i} className="rounded-lg border border-border/40 bg-surface-2 p-3 text-xs">
                                <span className="text-[10px] uppercase font-bold text-muted-foreground/70 mr-2">{m.role}</span>
                                <span className="text-muted-foreground whitespace-pre-wrap break-words leading-relaxed">{m.content || "—"}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {(full.final_text || "") !== "" && (
                        <div className="rounded-lg border border-accent/20 bg-accent/5 p-3">
                          <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1.5 flex items-center gap-1.5">
                            <Bot size={12} /> Final Answer
                          </p>
                          <p className="text-xs text-foreground whitespace-pre-wrap break-words leading-relaxed">{full.final_text}</p>
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
          <button onClick={() => setLimit((l) => l + 50)} className="text-[11px] uppercase tracking-widest text-accent hover:underline px-4 py-2">
            Load more ({total - traces.length} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
