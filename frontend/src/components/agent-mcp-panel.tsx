// NOTICE: This file is protected under RCF-PL
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Check, ExternalLink, Loader2, Plug } from "lucide-react";

interface McpToolInfo {
  name: string;
  description?: string;
}

interface McpServer {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  tools: McpToolInfo[];
}

export function AgentMcpPanel({ agentId }: { agentId: number }) {
  const [servers, setServers] = useState<McpServer[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [baseCfg, setBaseCfg] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoadError(null);
    let cancelled = false;
    Promise.all([
      api.get<McpServer[]>("/mcp/servers", { bypassCache: true }),
      api.get<{ tools_config?: Record<string, unknown> | null }>(`/agents/${agentId}`),
    ])
      .then(([serverList, agent]) => {
        if (cancelled) return;
        setServers(serverList);
        const cfg = agent.tools_config || {};
        setBaseCfg(cfg);
        const ids = Array.isArray(cfg.mcp_servers) ? cfg.mcp_servers : [];
        setSelected(new Set(ids.map(Number)));
      })
      .catch((e) => {
        if (cancelled) return;
        console.error("Failed to load MCP config", e);
        setLoadError(e instanceof Error ? e.message : "Failed to load");
      });
    return () => {
      cancelled = true;
    };
  }, [agentId]);

  useEffect(() => load(), [load]);

  const toggle = (id: number, disabled: boolean) => {
    if (disabled) return;
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const save = useCallback(async () => {
    setSaving(true);
    try {
      // The agents router exposes PUT (exclude_unset semantics), not PATCH.
      await api.put(`/agents/${agentId}`, {
        tools_config: { ...baseCfg, mcp_servers: Array.from(selected) },
      });
      setBaseCfg((prev) => ({ ...prev, mcp_servers: Array.from(selected) }));
      toast.success("MCP servers updated");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }, [agentId, baseCfg, selected]);

  if (servers === null) {
    if (loadError) {
      return (
        <div className="p-6 rounded-2xl bg-surface-1 border border-border/50 flex items-center gap-3 text-sm text-muted-foreground">
          Failed to load MCP config: {loadError}
          <Button variant="outline" size="sm" onClick={load}>Retry</Button>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground p-6">
        <Loader2 size={14} className="animate-spin" /> Loading MCP servers…
      </div>
    );
  }

  const enabledServers = servers.filter((s) => s.enabled);
  const disabledServers = servers.filter((s) => !s.enabled);

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="p-6 rounded-2xl bg-surface-1 border border-border/50">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">MCP Servers</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Pick which connected tool servers this agent can call. Tools show up to the model
              as <code className="font-mono">mcp__&lt;server&gt;__&lt;tool&gt;</code>.
            </p>
          </div>
          <Link href="/dashboard/settings?tab=mcp" className="shrink-0">
            <Button variant="outline" size="sm">
              <ExternalLink size={12} /> Manage
            </Button>
          </Link>
        </div>

        {servers.length === 0 ? (
          <div className="py-8 text-center space-y-2">
            <Plug size={20} className="mx-auto text-muted-foreground" />
            <p className="text-xs text-muted-foreground">
              No MCP servers configured. Connect one in Settings → MCP Servers.
            </p>
            <Link href="/dashboard/settings?tab=mcp">
              <Button size="sm" variant="outline">Open MCP Settings</Button>
            </Link>
          </div>
        ) : (
          <div className="rounded-xl border border-border overflow-hidden divide-y divide-border">
            {enabledServers.map((s) => {
              const isOn = selected.has(s.id);
              return (
                <button key={s.id} type="button"
                  onClick={() => toggle(s.id, false)}
                  className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors ${isOn ? "bg-accent/5" : "hover:bg-surface-2"}`}>
                  <span className={`mt-0.5 flex items-center justify-center w-4 h-4 rounded border shrink-0 ${isOn ? "bg-accent border-accent text-white" : "border-input"}`}>
                    {isOn && <Check size={11} strokeWidth={3} />}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm font-medium">{s.name}</span>
                    <span className="block text-[11px] text-muted-foreground font-mono truncate mt-0.5">
                      {s.url} · {s.tools.length} tool{s.tools.length === 1 ? "" : "s"}
                    </span>
                  </span>
                </button>
              );
            })}
            {disabledServers.map((s) => {
              const wasOn = selected.has(s.id);
              return (
                <div key={s.id} className="flex items-center gap-3 px-4 py-3 opacity-40 cursor-not-allowed"
                  title="Server is disabled in Settings → MCP Servers">
                  <span className={`mt-0.5 flex items-center justify-center w-4 h-4 rounded border shrink-0 ${wasOn ? "bg-accent border-accent text-white" : "border-input"}`}>
                    {wasOn && <Check size={11} strokeWidth={3} />}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className={`block text-sm font-medium ${wasOn ? "" : "line-through"}`}>{s.name}</span>
                    <span className="block text-[11px] text-muted-foreground mt-0.5">
                      Disabled server{wasOn ? " — selection kept, inactive until re-enabled" : ""}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {enabledServers.length > 0 && (
          <div className="flex items-center justify-end gap-2 mt-4">
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? <Loader2 size={12} className="animate-spin mr-1" /> : null}
              Save Selection
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
