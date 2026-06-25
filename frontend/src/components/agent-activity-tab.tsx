// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  MessageSquare,
  Zap,
  ShieldAlert,
  ShieldCheck,
  Clock,
  Mail,
  Phone,
  FileText,
  ChevronRight
} from "lucide-react";


interface ActivityEvent {
  id: string;
  type: "task" | "action" | "gate" | "trigger";
  title: string;
  status: string;
  timestamp: string;
  content: string;
  meta: Record<string, any>;
}

const TYPE_ICONS: Record<string, any> = {
  task: MessageSquare,
  action: Zap,
  gate: ShieldCheck,
  trigger: Clock,
};

const STATUS_COLORS: Record<string, string> = {
  task: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  action: "text-green-400 bg-green-500/10 border-green-500/20",
  gate_allow: "text-green-400 bg-green-500/10 border-green-500/20",
  gate_block: "text-red-400 bg-red-500/10 border-red-500/20",
  trigger: "text-purple-400 bg-purple-500/10 border-purple-500/20",
};


export function AgentActivityTab({ agentId }: { agentId: number }) {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);


  const load = async () => {
    setLoading(true);
    try {
      const data = await api.get<ActivityEvent[]>(`/agents/${agentId}/activity`);
      setEvents(data);
    } catch (err) {
      console.error("Failed to load activity", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [agentId]);

  if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading activity timeline...</div>;

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 rounded-2xl border border-dashed border-border/50 bg-surface-1">
        <Activity size={40} className="text-muted-foreground/30 mb-4" />
        <p className="text-muted-foreground text-sm">No activity recorded for this agent yet.</p>
      </div>
    );
  }


  const formatTime = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };


  const formatDate = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-4 max-w-4xl animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">Activity Timeline</h3>
        <button onClick={load} className="text-[10px] uppercase tracking-widest text-accent hover:underline">Refresh</button>
      </div>

      <div className="relative space-y-4 before:absolute before:left-[17px] before:top-2 before:bottom-2 before:w-px before:bg-border/50">
        {events.map((event, idx) => {
          const Icon = TYPE_ICONS[event.type] || MessageSquare;
          const isGateBlock = event.type === "gate" && event.status === "block";
          const colorClass = isGateBlock
            ? STATUS_COLORS.gate_block
            : event.type === "gate"
              ? STATUS_COLORS.gate_allow
              : STATUS_COLORS[event.type];

          return (
            <div key={event.id} className="relative pl-12 group">
              {/* Timeline Dot/Icon */}
              <div className={`absolute left-0 top-1 w-9 h-9 rounded-xl flex items-center justify-center border z-10 transition-transform group-hover:scale-110 ${colorClass}`}>
                <Icon size={16} />
              </div>

              {/* Event Card */}
              <div className="p-4 rounded-xl border border-border/50 bg-surface-1 transition-all hover:border-accent/30 hover:shadow-xl hover:shadow-accent/5">
                <div className="flex items-center justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-foreground">{event.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full uppercase tracking-tighter font-bold border ${colorClass}`}>
                      {event.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                    <span>{formatDate(event.timestamp)}</span>
                    <span>•</span>
                    <span>{formatTime(event.timestamp)}</span>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed mb-3">
                  {event.content}
                </p>

                {/* Meta Tags */}
                {Object.keys(event.meta || {}).length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-3 border-t border-border/20">
                    {Object.entries(event.meta).map(([key, val]) => (
                      val && (
                        <div key={key} className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-2 border border-border/30">
                          <span className="text-[9px] uppercase font-bold text-muted-foreground/60">{key}:</span>
                          <span className="text-[10px] font-mono text-muted-foreground">{String(val)}</span>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Helper to keep Activity icon available

function Activity({ size, className }: { size?: number, className?: string }) {
  return <Zap size={size} className={className} />
}
