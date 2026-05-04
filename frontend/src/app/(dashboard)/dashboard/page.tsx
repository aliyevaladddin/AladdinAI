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
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Overview</h2>
        <p className="text-sm text-muted-foreground mt-1">
          A summary of your workspace activity.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="rounded-lg border border-border p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground">
                    {c.label}
                  </p>
                  <p className="text-2xl font-semibold mt-2 tabular-nums">
                    {loading ? "—" : c.value.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{c.hint}</p>
                </div>
                <div className="w-8 h-8 rounded-md flex items-center justify-center bg-muted text-muted-foreground">
                  <Icon size={16} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-muted-foreground" />
            <h3 className="text-sm font-medium">Recent activity</h3>
          </div>
          <span className="text-xs text-muted-foreground">Last 5 events</span>
        </div>

        {loading ? (
          <p className="px-5 py-12 text-center text-sm text-muted-foreground">
            Loading…
          </p>
        ) : !stats?.recent_activities?.length ? (
          <p className="px-5 py-12 text-center text-sm text-muted-foreground">
            No activity yet. Connect a channel or create a contact to get started.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted-foreground">
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
                <tr key={a.id} className="border-t border-border">
                  <td className="px-5 py-2.5 tabular-nums text-muted-foreground">
                    {new Date(a.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="px-5 py-2.5">
                    <span className="text-[10px] px-2 py-0.5 rounded bg-muted text-muted-foreground uppercase tracking-wide">
                      {a.type.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-5 py-2.5 text-muted-foreground">
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
