// NOTICE: This file is protected under RCF-PL
"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, clearApiCache } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SegmentedTabs } from "@/components/ui/segmented-tabs";
import {
  Plug, Plus, X, Loader2, Trash2, RefreshCw, CheckCircle2,
  XCircle, Store, ChevronDown, ChevronUp, Power,
} from "lucide-react";

interface McpToolInfo {
  name: string;
  description?: string;
}

interface McpServer {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  timeout_seconds: number;
  header_names: string[];
  tools: McpToolInfo[];
  last_checked_at: string | null;
}

interface CatalogEntry {
  name: string;
  url: string;
  category: string;
  description: string;
  headers_hint: Record<string, string>;
}

interface TestResult {
  status: "success" | "error";
  tools?: string[];
  message?: string;
}

const EMPTY_FORM = {
  name: "",
  url: "",
  timeout_seconds: "30",
  headers: [] as HeaderRow[],
};

interface HeaderRow {
  id: string;
  key: string;
  value: string;
  /** Shown as the value-input placeholder (e.g. catalog token hints). */
  hint?: string;
}

const newHeaderRow = (key = "", value = "", hint?: string): HeaderRow => ({
  id: Math.random().toString(36).slice(2),
  key,
  value,
  hint,
});

export function McpSettings() {
  const [view, setView] = useState<"servers" | "catalog">("servers");
  const [servers, setServers] = useState<McpServer[]>([]);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<number, boolean>>({});
  const [tests, setTests] = useState<Record<number, TestResult>>({});
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoadError(null);
    // Catalog is static — its failure must not block the servers list.
    Promise.all([
      api.get<McpServer[]>("/mcp/servers", { bypassCache: true }),
      api.get<CatalogEntry[]>("/mcp/catalog").catch(() => [] as CatalogEntry[]),
    ])
      .then(([serverList, catalogList]) => {
        setServers(serverList);
        setCatalog(catalogList);
      })
      .catch((err) =>
        setLoadError(err instanceof Error ? err.message : "Failed to load"),
      );
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggleEnabled = async (s: McpServer) => {
    setBusy((p) => ({ ...p, [s.id]: true }));
    try {
      await api.patch(`/mcp/servers/${s.id}`, { enabled: !s.enabled });
      clearApiCache("/mcp");
      load();
    } finally {
      setBusy((p) => ({ ...p, [s.id]: false }));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this MCP server? Agents will lose access to its tools.")) return;
    await api.delete(`/mcp/servers/${id}`);
    clearApiCache("/mcp");
    load();
  };

  const handleTest = async (id: number) => {
    setBusy((p) => ({ ...p, [id]: true }));
    // Drop any previous result so the stale badge doesn't linger mid-test.
    setTests((p) => {
      const next = { ...p };
      delete next[id];
      return next;
    });
    try {
      const res = await api.post<TestResult>(`/mcp/servers/${id}/test`);
      setTests((p) => ({ ...p, [id]: res }));
      clearApiCache("/mcp");
      load();
    } catch {
      setTests((p) => ({ ...p, [id]: { status: "error", message: "Test request failed" } }));
    } finally {
      setBusy((p) => ({ ...p, [id]: false }));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFormError(null);
    try {
      const headers: Record<string, string> = {};
      for (const h of form.headers) {
        if (h.key.trim() && h.value.trim()) headers[h.key.trim()] = h.value.trim();
      }

      await api.post("/mcp/servers", {
        name: form.name,
        url: form.url,
        timeout_seconds: parseInt(form.timeout_seconds) || 30,
        headers: Object.keys(headers).length ? headers : null,
      });
      clearApiCache("/mcp");
      setForm(EMPTY_FORM);
      setShowForm(false);
      setView("servers");
      load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to add server");
    } finally {
      setSaving(false);
    }
  };

  /** Catalog install: servers needing auth open a prefilled form instead. */
  const handleInstall = (entry: CatalogEntry) => {
    if (Object.keys(entry.headers_hint).length > 0) {
      setForm({
        name: entry.name,
        url: entry.url,
        timeout_seconds: "30",
        // Hint values go into placeholders — the user types their real token.
        headers: Object.entries(entry.headers_hint).map(([key, hint]) =>
          newHeaderRow(key, "", hint),
        ),
      });
      setShowForm(true);
      setView("servers");
      return;
    }
    api.post("/mcp/servers", { name: entry.name, url: entry.url })
      .then(() => {
        clearApiCache("/mcp");
        setView("servers");
        load();
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : "Install failed"));
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Plug size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">MCP Servers</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">
              Connect external tool servers (Model Context Protocol) and give agents thousands of ready tools
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => { setShowForm(!showForm); setFormError(null); }} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Server</>}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Name</label>
              <input className="input" placeholder="e.g. DeepWiki" value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Timeout (seconds)</label>
              <input className="input" type="number" min={5} max={300} value={form.timeout_seconds}
                onChange={(e) => setForm({ ...form, timeout_seconds: e.target.value })} />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Streamable HTTP URL</label>
            <input className="input font-mono text-[12px]" placeholder="https://example.com/mcp" value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Headers <span className="opacity-40">(optional — auth tokens, stored encrypted)</span></label>
              <button type="button" className="text-[11px] text-[var(--color-accent)] hover:underline flex items-center gap-1"
                onClick={() => setForm({ ...form, headers: [...form.headers, newHeaderRow()] })}>
                <Plus size={11} /> Add header
              </button>
            </div>
            {form.headers.length === 0 && (
              <p className="text-[11px] text-[var(--color-fg-subtle)]">No custom headers</p>
            )}
            {form.headers.map((h) => (
              <div key={h.id} className="flex gap-2">
                <input className="input font-mono text-[12px]" placeholder="Authorization" value={h.key}
                  onChange={(e) => {
                    const next = form.headers.map((r) =>
                      r.id === h.id ? { ...r, key: e.target.value } : r,
                    );
                    setForm({ ...form, headers: next });
                  }} />
                <input className="input font-mono text-[12px]" placeholder={h.hint || "Bearer …"} value={h.value}
                  onChange={(e) => {
                    const next = form.headers.map((r) =>
                      r.id === h.id ? { ...r, value: e.target.value } : r,
                    );
                    setForm({ ...form, headers: next });
                  }} />
                <Button type="button" variant="ghost" size="icon-sm" title="Remove header"
                  onClick={() => setForm({ ...form, headers: form.headers.filter((r) => r.id !== h.id) })}>
                  <X size={12} />
                </Button>
              </div>
            ))}
          </div>
          {formError && (
            <p className="text-xs px-2 py-1 rounded-md bg-[var(--color-danger-soft)] text-[var(--color-danger)] w-fit">{formError}</p>
          )}
          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => { setShowForm(false); setFormError(null); }}>Cancel</Button>
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Plug size={13} />} Add Server
            </Button>
          </div>
        </form>
      )}

      {/* View switch */}
      <SegmentedTabs
        tabs={[
          { id: "servers", label: "My Servers", count: servers.length },
          { id: "catalog", label: "Catalog", icon: Store },
        ]}
        active={view}
        onChange={setView}
      />

      {view === "servers" && loadError && (
        <div className="flex items-center gap-3 text-xs px-3 py-2 rounded-lg bg-[var(--color-danger-soft)] text-[var(--color-danger)] w-fit">
          <XCircle size={13} />
          Failed to load MCP servers: {loadError}
          <button type="button" className="underline font-medium" onClick={load}>
            Retry
          </button>
        </div>
      )}

      {view === "servers" && !loadError && (
        <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
          {servers.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <p className="text-xs text-[var(--color-fg-subtle)]">No MCP servers connected yet</p>
              <button className="text-xs text-[var(--color-accent)] hover:underline"
                onClick={() => setView("catalog")}>
                Browse the catalog →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[var(--color-border)]">
              {servers.map((s) => {
                const isBusy = busy[s.id];
                const test = tests[s.id];
                const isOpen = expanded[s.id];
                return (
                  <div key={s.id} className="px-4 py-3 hover:bg-[var(--color-surface-2)] transition-colors">
                    <div className="flex items-center gap-3">
                      {/* Enabled indicator */}
                      <div className="shrink-0">
                        {isBusy ? (
                          <Loader2 size={15} className="animate-spin text-[var(--color-fg-subtle)]" />
                        ) : s.enabled ? (
                          <CheckCircle2 size={15} className="text-[var(--color-success)]" />
                        ) : (
                          <XCircle size={15} className="text-[var(--color-fg-subtle)]" />
                        )}
                      </div>

                      {/* Info */}
                      <button type="button" className="flex-1 min-w-0 text-left"
                        onClick={() => setExpanded((p) => ({ ...p, [s.id]: !p[s.id] }))}>
                        <span className="text-sm font-medium text-[var(--color-fg)]">{s.name}</span>
                        <span className={`ml-2 text-[10px] uppercase tracking-wide ${s.enabled ? "text-[var(--color-success)]" : "text-[var(--color-fg-subtle)]"}`}>
                          {s.enabled ? "enabled" : "disabled"}
                        </span>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-xs text-[var(--color-fg-subtle)] font-mono truncate">{s.url}</span>
                          <span className="text-xs text-[var(--color-fg-subtle)]">
                            · {s.tools.length} tool{s.tools.length === 1 ? "" : "s"}
                            {isOpen ? <ChevronUp size={11} className="inline ml-1" /> : <ChevronDown size={11} className="inline ml-1" />}
                          </span>
                        </div>
                      </button>

                      {/* Actions */}
                      <div className="flex items-center gap-1.5 shrink-0">
                        <Button variant="outline" size="sm" onClick={() => handleTest(s.id)} disabled={isBusy}>
                          <RefreshCw size={13} className={isBusy ? "animate-spin" : ""} /> Test
                        </Button>
                        <Button
                          variant="ghost" size="icon-sm"
                          onClick={() => toggleEnabled(s)} disabled={isBusy}
                          title={s.enabled ? "Disable for all agents" : "Enable"}
                          className="text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"
                        >
                          <Power size={13} />
                        </Button>
                        <Button
                          variant="ghost" size="icon-sm"
                          onClick={() => handleDelete(s.id)} disabled={isBusy} title="Delete"
                          className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                        >
                          <Trash2 size={13} />
                        </Button>
                      </div>
                    </div>

                    {/* Expanded details */}
                    {isOpen && (
                      <div className="mt-3 ml-7 p-3 rounded-lg bg-[var(--color-surface-2)] border border-[var(--color-border)] space-y-2">
                        {test && (
                          <div className={`text-xs px-2 py-1 rounded-md w-fit ${test.status === "success"
                            ? "bg-[var(--color-success-soft)] text-[var(--color-success)]"
                            : "bg-[var(--color-danger-soft)] text-[var(--color-danger)]"}`}>
                            {test.status === "success"
                              ? `✓ Live — ${test.tools?.length ?? 0} tools`
                              : `✗ ${test.message || "Connection failed"}`}
                          </div>
                        )}
                        {s.header_names.length > 0 && (
                          <p className="text-[11px] text-[var(--color-fg-muted)]">
                            Headers: {s.header_names.map((n) => (
                              <code key={n} className="font-mono text-[10px] px-1 py-0.5 mx-0.5 rounded bg-[var(--color-surface)]">{n}</code>
                            ))} <span className="opacity-50">(values hidden)</span>
                          </p>
                        )}
                        <p className="text-[11px] text-[var(--color-fg-subtle)]">
                          Timeout: {s.timeout_seconds}s · Last checked: {s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "never"}
                        </p>
                        {s.tools.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {s.tools.map((t) => (
                              <span key={t.name} title={t.description || t.name}
                                className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-fg-muted)]">
                                {t.name}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {view === "catalog" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {catalog.map((entry) => {
            const installed = servers.some(
              (s) => s.url.replace(/\/+$/, "") === entry.url.replace(/\/+$/, ""),
            );
            return (
              <div key={entry.name} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-[var(--color-fg)]">{entry.name}</h4>
                      <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-fg-muted)]">
                        {entry.category}
                      </span>
                    </div>
                  </div>
                </div>
                <p className="text-xs leading-relaxed text-[var(--color-fg-muted)] flex-1">{entry.description}</p>
                <div className="flex items-center justify-between pt-1">
                  <code className="text-[10px] font-mono text-[var(--color-fg-subtle)] truncate max-w-[60%]">{entry.url}</code>
                  <Button size="sm" variant={installed ? "ghost" : "outline"} disabled={installed}
                    onClick={() => handleInstall(entry)}>
                    {installed ? "Installed" : <><Plug size={12} /> Install</>}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* How agents use this */}
      <p className="text-[11px] leading-relaxed text-[var(--color-fg-subtle)]">
        After testing a server, enable it per agent on the agent&apos;s <b>Tools</b> tab.
        Tools appear to the model as <code className="font-mono">mcp__&lt;server&gt;__&lt;tool&gt;</code>.
      </p>
    </div>
  );
}
