// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState, FormEvent } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Network, Plus, X, Trash2, ToggleLeft, ToggleRight, Pencil, Check } from "lucide-react";


interface RouterCfg {
  id: number;
  name: string;
  type: string;
  config: Record<string, unknown>;
  is_active: boolean;
}


interface Agent { id: number; name: string; role: string; }

const TYPE_INFO: Record<string, { label: string; description: string }> = {
  keyword: { label: "Keyword", description: "Routes based on keywords in messages." },
  llm_classifier: { label: "LLM Classifier", description: "Uses AI to detect intent and route." },
  hybrid: { label: "Hybrid", description: "Keyword matching with LLM as fallback." },
};


export function RouterSettings() {
  const [configs, setConfigs] = useState<RouterCfg[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState("keyword");
  const [formName, setFormName] = useState("");
  const [rules, setRules] = useState([{ keywords: "", agent_id: "" }]);
  const [fallbackAgentId, setFallbackAgentId] = useState("");

  const [editId, setEditId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", type: "", rules: [{ keywords: "", agent_id: "" }], fallback_agent_id: "" });


  const load = () => api.get<RouterCfg[]>("/router").then(setConfigs);
  useEffect(() => {
    load();
    api.get<Agent[]>("/agents").then(setAgents);
  }, []);


  const buildConfig = (type: string, rls: any[], fallbackId: string) => {
    if (type === "keyword" || type === "hybrid") {
      return {
        rules: rls.map((r) => ({
          keywords: r.keywords.split(",").map((k: string) => k.trim()).filter(Boolean),
          agent_id: r.agent_id ? parseInt(r.agent_id) : null,
        })),
        fallback_agent_id: fallbackId ? parseInt(fallbackId) : null,
      };
    }
    if (type === "llm_classifier") {
      return {
        fallback_agent_id: fallbackId ? parseInt(fallbackId) : null,
        agents: agents.map((a) => ({ id: a.id, name: a.name, role: a.role })),
      };
    }
    return {};
  };


  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/router", { name: formName, type: formType, config: buildConfig(formType, rules, fallbackAgentId), is_active: false });
    setFormName(""); setRules([{ keywords: "", agent_id: "" }]); setFallbackAgentId("");
    setShowForm(false); load();
  };


  const startEdit = (c: RouterCfg) => {
    setEditId(c.id);
    const cfg = c.config || {};

    const rulesFromConfig = (cfg.rules as any[])?.map((r: any) => ({
      keywords: (r.keywords as string[]).join(", "),
      agent_id: r.agent_id ? r.agent_id.toString() : "",
    })) || [{ keywords: "", agent_id: "" }];

    setEditForm({
      name: c.name,
      type: c.type,
      rules: rulesFromConfig,
      fallback_agent_id: cfg.fallback_agent_id ? cfg.fallback_agent_id.toString() : "",
    });
  };


  const handleSaveEdit = async (id: number) => {
    await api.put(`/router/${id}`, {
      name: editForm.name,
      type: editForm.type,
      config: buildConfig(editForm.type, editForm.rules, editForm.fallback_agent_id),
    });
    setEditId(null);
    load();
  };


  const handleToggle = async (cfg: RouterCfg) => {
    await api.put(`/router/${cfg.id}`, { is_active: !cfg.is_active });
    load();
  };


  const handleDelete = async (id: number) => {
    if (!confirm("Delete this router config?")) return;
    await api.delete(`/router/${id}`);
    load();
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <Network size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">Smart Routing</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Define how incoming messages are routed to agents</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)} className="shrink-0">
          {showForm ? <><X size={13} /> Cancel</> : <><Plus size={13} /> Add Config</>}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleCreate} className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-2)] p-4 space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Configuration Name</label>
            <input className="input" placeholder="e.g. Main Router" value={formName}
              onChange={(e) => setFormName(e.target.value)} required />
          </div>

          {/* Type selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">Router Type</label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(TYPE_INFO).map(([key, info]) => (
                <button
                  key={key} type="button" onClick={() => setFormType(key)}
                  className={`text-left p-3 rounded-lg border text-xs transition-colors ${formType === key
                      ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-fg-muted)] hover:border-[var(--color-border-strong)]"
                    }`}
                >
                  <div className="font-semibold mb-1">{info.label}</div>
                  <div className="text-[10px] leading-relaxed opacity-70">{info.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Keyword Rules */}
          {(formType === "keyword" || formType === "hybrid") && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-[var(--color-fg-muted)]">Routing Rules</label>
              {rules.map((rule, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <input className="input flex-1" placeholder="Keywords, comma-separated"
                    value={rule.keywords}
                    onChange={(e) => { const n = [...rules]; n[i].keywords = e.target.value; setRules(n); }} />
                  <select className="input flex-1" value={rule.agent_id}
                    onChange={(e) => { const n = [...rules]; n[i].agent_id = e.target.value; setRules(n); }}>
                    <option value="">Select agent…</option>
                    {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                  {rules.length > 1 && (
                    <Button type="button" variant="ghost" size="icon-sm"
                      onClick={() => setRules(rules.filter((_, j) => j !== i))}
                      className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)]">
                      <X size={13} />
                    </Button>
                  )}
                </div>
              ))}
              <Button type="button" variant="ghost" size="sm"
                onClick={() => setRules([...rules, { keywords: "", agent_id: "" }])}>
                + Add Rule
              </Button>
            </div>
          )}

          {/* Fallback */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--color-fg-muted)]">
              Fallback Agent <span className="opacity-40">(when no rule matches)</span>
            </label>
            <select className="input" value={fallbackAgentId} onChange={(e) => setFallbackAgentId(e.target.value)}>
              <option value="">None</option>
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}
            </select>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" size="sm">Save Configuration</Button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
        {configs.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--color-fg-subtle)]">
            No routing configurations defined
          </div>
        ) : (
          <div className="divide-y divide-[var(--color-border)]">
            {configs.map((c) => {
              const isEditing = editId === c.id;
              return (
                <div key={c.id}>
                  <div className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--color-surface-2)] transition-colors group">
                    {/* Active indicator */}
                    <div className="shrink-0">
                      {c.is_active
                        ? <ToggleRight size={18} className="text-[var(--color-success)]" />
                        : <ToggleLeft size={18} className="text-[var(--color-fg-subtle)]" />}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--color-fg)]">{c.name}</span>
                        <span className="text-[10px] px-1.5 py-px rounded bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[var(--color-fg-subtle)] font-mono uppercase shrink-0">
                          {TYPE_INFO[c.type]?.label ?? c.type}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--color-fg-subtle)] mt-0.5">
                        {c.is_active ? "Active — routing messages now" : "Inactive"}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Button variant="outline" size="sm" onClick={() => handleToggle(c)}>
                        {c.is_active ? <><ToggleLeft size={13} /> Deactivate</> : <><ToggleRight size={13} /> Activate</>}
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => isEditing ? setEditId(null) : startEdit(c)}
                        title="Edit"
                        className={isEditing ? "text-[var(--color-accent)]" : "text-[var(--color-fg-subtle)] hover:text-[var(--color-fg)]"}
                      >
                        <Pencil size={13} />
                      </Button>
                      <Button
                        variant="ghost" size="icon-sm"
                        onClick={() => handleDelete(c.id)}
                        className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)] hover:bg-[var(--color-danger-soft)]"
                      >
                        <Trash2 size={13} />
                      </Button>
                    </div>
                  </div>

                  {/* Inline edit */}
                  {isEditing && (
                    <div className="px-4 py-3 bg-[var(--color-surface-2)] border-t border-[var(--color-border)] space-y-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Configuration Name</label>
                        <input className="input" value={editForm.name}
                          onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                      </div>

                      {/* Keyword Rules */}
                      {(editForm.type === "keyword" || editForm.type === "hybrid") && (
                        <div className="space-y-2">
                          <label className="text-xs font-medium text-[var(--color-fg-muted)]">Routing Rules</label>
                          {editForm.rules.map((rule, i) => (
                            <div key={i} className="flex gap-2 items-center">
                              <input className="input flex-1" placeholder="Keywords, comma-separated"
                                value={rule.keywords}
                                onChange={(e) => {
                                  const n = [...editForm.rules];
                                  n[i].keywords = e.target.value;
                                  setEditForm({ ...editForm, rules: n });
                                }} />
                              <select className="input flex-1" value={rule.agent_id}
                                onChange={(e) => {
                                  const n = [...editForm.rules];
                                  n[i].agent_id = e.target.value;
                                  setEditForm({ ...editForm, rules: n });
                                }}>
                                <option value="">Select agent…</option>
                                {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                              </select>
                              {editForm.rules.length > 1 && (
                                <Button type="button" variant="ghost" size="icon-sm"
                                  onClick={() => setEditForm({ ...editForm, rules: editForm.rules.filter((_, j) => j !== i) })}
                                  className="text-[var(--color-fg-subtle)] hover:text-[var(--color-danger)]">
                                  <X size={13} />
                                </Button>
                              )}
                            </div>
                          ))}
                          <Button type="button" variant="ghost" size="sm"
                            onClick={() => setEditForm({ ...editForm, rules: [...editForm.rules, { keywords: "", agent_id: "" }] })}>
                            + Add Rule
                          </Button>
                        </div>
                      )}

                      {/* Fallback */}
                      <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[var(--color-fg-muted)]">Fallback Agent</label>
                        <select className="input" value={editForm.fallback_agent_id}
                          onChange={(e) => setEditForm({ ...editForm, fallback_agent_id: e.target.value })}>
                          <option value="">None</option>
                          {agents.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.role})</option>)}
                        </select>
                      </div>

                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => setEditId(null)}>Cancel</Button>
                        <Button size="sm" onClick={() => handleSaveEdit(c.id)}>
                          <Check size={13} /> Save
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
