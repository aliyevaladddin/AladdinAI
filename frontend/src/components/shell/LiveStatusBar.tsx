// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusBar, type StatusItem } from "./StatusBar";

/* Live status bar — polls the backend and renders real state instead of the
   static default items. Falls back to the static items when the API is
   unreachable (or the user is signed out), so the chrome never looks broken. */

interface StatsResponse {
  agents: { total: number; top5: { status: string }[] };
  channels: {
    messaging: { connected: number; errors: number };
    email: { connected: number; errors: number };
  };
  gate_decisions_24h: { pass: number; block: number };
  messages_24h: { total: number };
  system_status?: string;
}

const POLL_MS = 30000;

function liveItems(stats: StatsResponse | null, reached: boolean): StatusItem[] {
  const agentsRunning = (stats?.agents.top5 ?? []).filter((a) =>
    ["running", "active"].includes(a.status),
  ).length;
  const agentsTotal = stats?.agents.total ?? 0;
  const channelsOk =
    (stats?.channels.messaging.connected ?? 0) + (stats?.channels.email.connected ?? 0);
  const channelsErr =
    (stats?.channels.messaging.errors ?? 0) + (stats?.channels.email.errors ?? 0);
  const gatePass = stats?.gate_decisions_24h.pass ?? 0;
  const gateBlock = stats?.gate_decisions_24h.block ?? 0;

  return [
    {
      id: "orch",
      dot: reached ? "ok" : "amber",
      label: "Orchestrator",
      code: reached ? "up" : stats ? "degraded" : "…",
    },
    {
      id: "agents",
      dot: agentsTotal > 0 && agentsRunning === 0 ? "amber" : "ok",
      label: "Agents",
      code: `${agentsRunning}/${agentsTotal} run`,
    },
    {
      id: "channels",
      dot: channelsErr > 0 ? "amber" : "ok",
      label: "Channels",
      code: channelsErr > 0 ? `${channelsOk} ok · ${channelsErr} err` : `${channelsOk} ok`,
    },
    { id: "rcf", dot: "violet", label: "RCF", code: "chain", variant: "rcf" as const },
  ];
}

export function LiveStatusBar({ rightExtra }: { rightExtra?: React.ReactNode }) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [reached, setReached] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      try {
        const data = await api.get<StatsResponse>("/dashboard/stats", {
          bypassCache: true,
          ttlMs: POLL_MS,
        });
        if (cancelled) return;
        setStats(data);
        setReached(true);
      } catch {
        // Signed out or API down — keep previous stats, status bar stays graceful.
        if (!cancelled) setReached(false);
      }
    };

    void tick();
    const interval = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const items = liveItems(stats, reached);

  return <StatusBar items={items} rightExtra={rightExtra} />;
}
