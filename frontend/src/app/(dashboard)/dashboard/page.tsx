// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  MessageSquare,
  Zap,
  Database,
  ShieldCheck,
  Share2,
  Plus,
  ArrowRight,
  Cpu,
  Network,
  RefreshCw,
  Mail,
  History,
  Inbox,
  Search,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";
import { Button } from "@/components/ui/button";
import Link from "next/link";

/* ── Types aligned with dashboard.py response ─────────────────────── */

interface ActivityItem {
  id: number;
  type: string;
  channel: string | null;
  subject: string | null;
  content: string;
  created_at: string;
}


function stripHtmlPreview(html: string): string {
  if (!html) return "";

  if (typeof window !== "undefined" && typeof DOMParser !== "undefined") {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      doc.querySelectorAll("script, style").forEach((el) => el.remove());
      const text = doc.body.textContent || "";
      return text.replace(/\s{2,}/g, " ").trim().slice(0, 120);
    } catch (e) {
      // Fallback to regex if parsing fails
    }
  }

  // Regex fallback for SSR or environments without DOMParser
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s{2,}/g, " ")
    .trim()
    .slice(0, 120);
}


interface TopAgent {
  id: number;
  name: string;
  status: string;
  responses_24h: number;
}


interface FiredTrigger {
  id: number;
  name: string;
  last_fired_at: string | null;
  next_fire_at: string | null;
}


interface Stats {
  messages_24h: { total: number; breakdown: Record<string, number> };
  agents: { total: number; top5: TopAgent[] };
  trigger_fires_24h: { count: number; recent: FiredTrigger[] };
  recent_shared_memory: { fact: string; tags: string[]; created_at: string }[];
  gate_decisions_24h: {
    total: number;
    pass: number;
    block: number;
    rerank: number;
    by_gate: Record<string, Record<string, number>>;
  };
  channels: {
    messaging: { total: number; connected: number; errors: number; list: any[] };
    email: { total: number; connected: number; errors: number; list: any[] };
  };
  total_providers: number;
  total_memories: number;
  recent_activities: ActivityItem[];
  system_status: string;
}

/* ── Page ─────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] ?? "there";
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);


  const load = () => {
    setLoading(true);
    api
      .get<Stats>("/dashboard/stats")
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const isNewUser =
    stats && stats.total_providers === 0 && stats.agents.total === 0;

  if (loading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
        <p className="text-sm font-mono uppercase tracking-widest animate-pulse">
          Syncing AI Hub...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 p-8 rounded-3xl bg-gradient-to-br from-[var(--color-accent-soft)] to-transparent border border-[var(--color-border)] relative overflow-hidden group">
        <div className="relative z-10">
          <h1 className="text-3xl font-bold tracking-tight">
            Welcome back,{" "}
            <span className="text-[var(--color-accent)]">{firstName}</span>
          </h1>
          <p className="text-sm text-[var(--color-fg-muted)] mt-2 max-w-md">
            Your sovereign AI ecosystem is {stats?.system_status ?? "initializing"}.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 relative z-10">
          <Link href="/dashboard/agents/new">
            <Button size="sm" className="gap-2">
              <Plus size={14} /> New Agent
            </Button>
          </Link>
          <Link href="/dashboard/channels">
            <Button variant="outline" size="sm" className="gap-2">
              <Network size={14} /> Connect Channel
            </Button>
          </Link>
          <Link href="/dashboard/search">
            <Button variant="outline" size="sm" className="gap-2">
              <Search size={14} /> Web Search
            </Button>
          </Link>
          <Link href="/dashboard/mail">
            <Button variant="outline" size="sm" className="gap-2">
              <Inbox size={14} /> View Inbox
            </Button>
          </Link>
          <Button
            variant="ghost"
            size="sm"
            onClick={load}
            disabled={loading}
            className="rounded-full px-2"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--color-accent)]/5 rounded-full blur-3xl -mr-32 -mt-32 group-hover:opacity-70 transition-opacity" />
      </div>

      {/* Onboarding or Metric Grid */}
      {isNewUser ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <OnboardingCard step={1} title="Connect Provider" desc="Link your NVIDIA NIM, OpenAI or Anthropic keys." href="/dashboard/settings" icon={Cpu} btn="Setup Keys" />
          <OnboardingCard step={2} title="Create Agent" desc="Define your agent's role, persona and system instructions." href="/dashboard/agents/new" icon={Bot} btn="Create Agent" />
          <OnboardingCard step={3} title="Connect Channel" desc="Connect WhatsApp, Email or Telegram to start tasks." href="/dashboard/channels" icon={Share2} btn="Link Channel" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {/* 1. Today's Messages */}
          <MetricCard
            title="Today's Messages"
            value={stats?.messages_24h.total ?? 0}
            icon={MessageSquare}
            color="text-blue-400"
            bg="bg-blue-500/10"
            footer={
              <div className="flex flex-wrap gap-2 mt-4">
                {Object.entries(stats?.messages_24h.breakdown ?? {}).map(([ch, cnt]) => (
                  <div key={ch} className="flex flex-col px-2 py-1 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)]">
                    <span className="text-[9px] uppercase font-bold text-[var(--color-fg-muted)]">{ch}</span>
                    <span className="text-xs font-bold">{cnt}</span>
                  </div>
                ))}
                {!stats?.messages_24h.total && (
                  <span className="text-[10px] text-[var(--color-fg-subtle)] italic">No traffic yet</span>
                )}
              </div>
            }
          />

          {/* 2. Active Agents — Top-5 by responses */}
          <MetricCard
            title="Active Agents"
            value={stats?.agents.total ?? 0}
            icon={Bot}
            color="text-green-400"
            bg="bg-green-500/10"
            footer={
              <div className="mt-4 space-y-1.5">
                <p className="text-[9px] font-bold text-[var(--color-fg-muted)] uppercase">Top by responses (24h)</p>
                {(stats?.agents.top5 ?? []).slice(0, 3).map((a) => (
                  <div key={a.id} className="flex items-center justify-between text-[11px]">
                    <span className="truncate max-w-[130px] opacity-70">{a.name}</span>
                    <span className="font-mono font-bold text-green-400">{a.responses_24h}</span>
                  </div>
                ))}
                {!stats?.agents.top5.length && (
                  <span className="text-[10px] italic opacity-50">No responses yet</span>
                )}
              </div>
            }
          />

          {/* 3. Trigger Fires (24h) */}
          <MetricCard
            title="Trigger Fires (24h)"
            value={stats?.trigger_fires_24h.count ?? 0}
            icon={Zap}
            color="text-orange-400"
            bg="bg-orange-500/10"
            footer={
              <div className="mt-4 space-y-1.5">
                <p className="text-[9px] font-bold text-[var(--color-fg-muted)] uppercase">Recent fires</p>
                {(stats?.trigger_fires_24h.recent ?? []).slice(0, 3).map((t) => (
                  <div key={t.id} className="flex items-center justify-between text-[11px]">
                    <span className="truncate max-w-[130px] opacity-70">{t.name}</span>
                    <span className="font-mono opacity-50 text-[10px]">
                      {t.last_fired_at ? new Date(t.last_fired_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}
                    </span>
                  </div>
                ))}
                {!stats?.trigger_fires_24h.count && (
                  <span className="text-[10px] italic opacity-50">No fires yet</span>
                )}
                <Link href="/dashboard/triggers" className="flex items-center gap-1 text-[10px] font-bold text-[var(--color-accent)] uppercase mt-1 hover:gap-1.5 transition-all">
                  View all <ArrowRight size={9} />
                </Link>
              </div>
            }
          />

          {/* 4. Recent Shared Memory — wide */}
          <div className="col-span-1 md:col-span-2 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6 flex flex-col">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                  <Database size={20} />
                </div>
                <h3 className="font-bold text-sm uppercase tracking-widest">Recent Shared Memory</h3>
              </div>
              <span className="text-[9px] font-bold text-[var(--color-fg-muted)] bg-[var(--color-surface-2)] px-2 py-1 rounded">Last 5 facts</span>
            </div>
            <div className="space-y-2 flex-1">
              {(stats?.recent_shared_memory ?? []).length ? (
                stats!.recent_shared_memory.map((m, i) => (
                  <div key={i} className="p-3 rounded-xl bg-[var(--color-surface-2)] border border-[var(--color-border)] text-xs flex gap-3 hover:border-[var(--color-accent)]/30 transition-colors">
                    <span className="font-mono opacity-25 mt-0.5 shrink-0">#{i + 1}</span>
                    <p className="flex-1 line-clamp-2 opacity-80">{m.fact}</p>
                    {Array.isArray(m.tags) && m.tags.length > 0 && (
                      <span className="shrink-0 text-[9px] opacity-40">{m.tags.join(", ")}</span>
                    )}
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-8 opacity-30">
                  <Share2 size={28} className="mb-2 stroke-1" />
                  <p className="text-xs italic">No shared knowledge yet</p>
                </div>
              )}
            </div>
          </div>

          {/* 5. Gate Decisions (24h) */}
          <MetricCard
            title="Gate Decisions (24h)"
            value={stats?.gate_decisions_24h.total ?? 0}
            icon={ShieldCheck}
            color="text-cyan-400"
            bg="bg-cyan-500/10"
            footer={
              <div className="mt-4 space-y-2">
                <div className="grid grid-cols-3 gap-2">
                  <div className="px-2 py-2 rounded-xl bg-green-500/5 border border-green-500/20 flex flex-col items-center">
                    <p className="text-[8px] font-bold text-green-400 uppercase">Pass</p>
                    <p className="text-lg font-bold">{stats?.gate_decisions_24h.pass ?? 0}</p>
                  </div>
                  <div className="px-2 py-2 rounded-xl bg-red-500/5 border border-red-500/20 flex flex-col items-center">
                    <p className="text-[8px] font-bold text-red-400 uppercase">Block</p>
                    <p className="text-lg font-bold">{stats?.gate_decisions_24h.block ?? 0}</p>
                  </div>
                  <div className="px-2 py-2 rounded-xl bg-yellow-500/5 border border-yellow-500/20 flex flex-col items-center">
                    <p className="text-[8px] font-bold text-yellow-400 uppercase">Rerank</p>
                    <p className="text-lg font-bold">{stats?.gate_decisions_24h.rerank ?? 0}</p>
                  </div>
                </div>
                {Object.entries(stats?.gate_decisions_24h.by_gate ?? {}).map(([gate, counts]) => (
                  <div key={gate} className="flex items-center justify-between text-[10px]">
                    <span className="font-mono opacity-50">{gate}</span>
                    <span className="opacity-70">
                      {Object.entries(counts).map(([k, v]) => `${k}:${v}`).join(" · ")}
                    </span>
                  </div>
                ))}
              </div>
            }
          />

          {/* 6. Channels Status */}
          <MetricCard
            title="Channels Status"
            value={(stats?.channels.messaging.total ?? 0) + (stats?.channels.email.total ?? 0)}
            icon={Network}
            color="text-pink-400"
            bg="bg-pink-500/10"
            footer={
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-[11px]">
                  <div className="flex items-center gap-2 opacity-60">
                    <MessageSquare size={11} /> Messaging
                  </div>
                  <div className="flex gap-2">
                    <span className="text-green-400 font-bold">{stats?.channels.messaging.connected ?? 0} ok</span>
                    {(stats?.channels.messaging.errors ?? 0) > 0 && (
                      <span className="text-red-400 font-bold">{stats?.channels.messaging.errors} err</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <div className="flex items-center gap-2 opacity-60">
                    <Mail size={11} /> Email
                  </div>
                  <div className="flex gap-2">
                    <span className="text-green-400 font-bold">{stats?.channels.email.connected ?? 0} ok</span>
                    {(stats?.channels.email.errors ?? 0) > 0 && (
                      <span className="text-red-400 font-bold">{stats?.channels.email.errors} err</span>
                    )}
                  </div>
                </div>
                <Link href="/dashboard/channels" className="flex items-center gap-1 text-[10px] font-bold text-[var(--color-accent)] uppercase mt-1 hover:gap-1.5 transition-all">
                  Manage <ArrowRight size={9} />
                </Link>
              </div>
            }
          />

          {/* Global Activity Feed — full width */}
          <div className="col-span-1 md:col-span-3 rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface-1)] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--color-border)]/50">
              <div className="flex items-center gap-2">
                <History size={16} className="text-[var(--color-accent)]" />
                <h3 className="font-bold text-sm uppercase tracking-widest">Global Activity Feed</h3>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[9px] font-bold text-[var(--color-fg-muted)] uppercase border-b border-[var(--color-border)]/30">
                    <th className="text-left px-6 py-3">Time</th>
                    <th className="text-left px-6 py-3">Event</th>
                    <th className="text-left px-6 py-3">Channel</th>
                    <th className="text-left px-6 py-3">Preview</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border)]/10">
                  {(stats?.recent_activities ?? []).map((a) => (
                    <tr key={a.id} className="hover:bg-[var(--color-accent)]/5 transition-colors group">
                      <td className="px-6 py-3 font-mono text-[10px] text-[var(--color-fg-muted)]">
                        {new Date(a.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </td>
                      <td className="px-6 py-3">
                        <span className="px-2 py-0.5 rounded-full bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[9px] font-bold uppercase">
                          {a.type.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-[11px] font-medium text-[var(--color-fg-muted)]">
                        {a.channel || "SYSTEM"}
                      </td>
                      <td className="px-6 py-3 text-[11px] opacity-60 truncate max-w-xs group-hover:opacity-100 transition-opacity">
                        {a.type.startsWith("email") && a.subject
                          ? a.subject
                          : stripHtmlPreview(a.content)}
                      </td>
                    </tr>
                  ))}
                  {!stats?.recent_activities?.length && (
                    <tr>
                      <td colSpan={4} className="px-6 py-10 text-center text-xs italic text-[var(--color-fg-subtle)]">
                        No events recorded yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

/* ── Reusable components ─────────────────────────────────────────── */

function MetricCard({
  title,
  value,
  icon: Icon,
  color,
  bg,
  footer,
}: {
  title: string;
  value: number;
  icon: any;
  color: string;
  bg: string;
  footer?: React.ReactNode;
}) {
  return (
    <div className="group rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6 flex flex-col hover:border-[var(--color-accent)]/30 hover:shadow-xl hover:shadow-[var(--color-accent)]/5 transition-all">
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${bg} ${color} group-hover:scale-110 transition-transform`}>
          <Icon size={20} />
        </div>
        <div className="text-right">
          <p className="text-[9px] font-bold uppercase tracking-widest text-[var(--color-fg-muted)] group-hover:text-[var(--color-accent)] transition-colors">
            {title}
          </p>
          <p className="text-3xl font-bold mt-1 tabular-nums">{value.toLocaleString()}</p>
        </div>
      </div>
      {footer && <div className="mt-auto">{footer}</div>}
    </div>
  );
}


function OnboardingCard({
  step,
  title,
  desc,
  href,
  icon: Icon,
  btn,
}: {
  step: number;
  title: string;
  desc: string;
  href: string;
  icon: any;
  btn: string;
}) {
  return (
    <div className="group p-8 rounded-3xl bg-[var(--color-surface-1)] border border-[var(--color-border)] hover:border-[var(--color-accent)]/30 transition-all flex flex-col relative overflow-hidden">
      <div className="absolute -top-4 -right-4 text-6xl font-black text-[var(--color-accent)]/5 select-none">
        0{step}
      </div>
      <div className="w-14 h-14 rounded-2xl bg-[var(--color-accent)]/10 text-[var(--color-accent)] flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
        <Icon size={28} />
      </div>
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <p className="text-sm text-[var(--color-fg-muted)] mb-8 leading-relaxed">{desc}</p>
      <div className="mt-auto">
        <Link href={href}>
          <Button size="sm" className="w-full gap-2 group/btn">
            {btn}{" "}
            <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
          </Button>
        </Link>
      </div>
    </div>
  );
}
