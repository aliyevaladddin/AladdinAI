"use client";

import { useEffect, useState } from "react";
import { Bot, TrendingUp, Users, Activity } from "lucide-react";
import { api } from "@/lib/api";

interface ActivityItem {
  id: number;
  type: string;
  channel: string | null;
  content: string;
  created_at: string;
}

interface Stats {
  active_agents: number;
  deals_in_progress: number;
  total_contacts: number;
  recent_activities: ActivityItem[];
  system_status: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<Stats>("/dashboard/stats")
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      label: "Active agents",
      value: stats?.active_agents ?? 0,
      icon: Bot,
      hint: "Currently running",
    },
    {
      label: "Deals in progress",
      value: stats?.deals_in_progress ?? 0,
      icon: TrendingUp,
      hint: "Open opportunities",
    },
    {
      label: "Contacts",
      value: stats?.total_contacts ?? 0,
      icon: Users,
      hint: "Total in your CRM",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">Overview</h1>
        <p className="text-[13px] mt-1" style={{ color: "var(--color-fg-muted)" }}>
          A summary of your workspace activity.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="card p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p
                    className="text-[12px] font-medium"
                    style={{ color: "var(--color-fg-muted)" }}
                  >
                    {c.label}
                  </p>
                  <p className="text-[28px] font-semibold mt-2 tracking-tight tabular-nums">
                    {loading ? "—" : c.value.toLocaleString()}
                  </p>
                  <p
                    className="text-[12px] mt-1"
                    style={{ color: "var(--color-fg-subtle)" }}
                  >
                    {c.hint}
                  </p>
                </div>
                <div
                  className="w-8 h-8 rounded-md flex items-center justify-center"
                  style={{
                    background: "var(--color-accent-soft)",
                    color: "var(--color-accent)",
                  }}
                >
                  <Icon size={16} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="card overflow-hidden">
        <div
          className="flex items-center justify-between px-5 py-3 border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          <div className="flex items-center gap-2">
            <Activity size={14} style={{ color: "var(--color-fg-muted)" }} />
            <h2 className="text-[13px] font-medium">Recent activity</h2>
          </div>
          <span className="text-[11px]" style={{ color: "var(--color-fg-subtle)" }}>
            Last 5 events
          </span>
        </div>

        {loading ? (
          <div className="px-5 py-12 text-center text-[13px]" style={{ color: "var(--color-fg-muted)" }}>
            Loading…
          </div>
        ) : !stats?.recent_activities?.length ? (
          <div
            className="px-5 py-12 text-center text-[13px]"
            style={{ color: "var(--color-fg-subtle)" }}
          >
            No activity yet. Connect a channel or create a contact to get started.
          </div>
        ) : (
          <table className="w-full text-[13px]">
            <thead>
              <tr style={{ color: "var(--color-fg-subtle)" }}>
                <th className="text-left font-medium px-5 py-2 text-[11px] uppercase tracking-wider">
                  Time
                </th>
                <th className="text-left font-medium px-5 py-2 text-[11px] uppercase tracking-wider">
                  Type
                </th>
                <th className="text-left font-medium px-5 py-2 text-[11px] uppercase tracking-wider">
                  Channel
                </th>
                <th className="text-left font-medium px-5 py-2 text-[11px] uppercase tracking-wider">
                  Content
                </th>
              </tr>
            </thead>
            <tbody>
              {stats.recent_activities.map((a) => (
                <tr key={a.id} className="table-row transition-colors">
                  <td
                    className="px-5 py-2.5 tabular-nums"
                    style={{ color: "var(--color-fg-muted)" }}
                  >
                    {new Date(a.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="px-5 py-2.5">
                    <span className="badge">{a.type.replace("_", " ")}</span>
                  </td>
                  <td className="px-5 py-2.5" style={{ color: "var(--color-fg-muted)" }}>
                    {a.channel || "—"}
                  </td>
                  <td className="px-5 py-2.5 truncate max-w-md">{a.content}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
