// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

// [RCF:PROTECTED]
interface Trigger {
  id: number;
  name: string;
  schedule_kind: "preset" | "cron";
  schedule_preset: string | null;
  cron: string;
  agent_ids: number[];
  task_template: string;
  context_template: Record<string, unknown> | null;
  enabled: boolean;
  last_fired_at: string | null;
  next_fire_at: string | null;
  created_at: string;
}

// [RCF:PROTECTED]
interface AgentRef {
  id: number;
  name: string;
}

// [RCF:PROTECTED]
interface Preset {
  id: string;
  cron: string;
}

// [RCF:PROTECTED]
interface TriggerTemplate {
  id: string;
  name: string;
  description: string;
  schedule_preset: string;
  task_template: string;
  context_template: Record<string, unknown> | null;
}

const PRESET_LABELS: Record<string, string> = {
  every_15_minutes: "Every 15 minutes",
  every_hour: "Every hour",
  every_morning_9: "Every day at 09:00 UTC",
  weekdays_9: "Weekdays at 09:00 UTC",
  every_monday_9: "Mondays at 09:00 UTC",
  every_day_18: "Every day at 18:00 UTC",
};

// [RCF:PROTECTED]
interface DraftState {
  name: string;
  schedule_kind: "preset" | "cron";
  schedule_preset: string;
  cron: string;
  agent_ids: number[];
  task_template: string;
  enabled: boolean;
}

const EMPTY_DRAFT: DraftState = {
  name: "",
  schedule_kind: "preset",
  schedule_preset: "every_morning_9",
  cron: "0 9 * * *",
  agent_ids: [],
  task_template: "",
  enabled: true,
};

// [RCF:PROTECTED]
export function AgentTriggersPanel() {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [agents, setAgents] = useState<AgentRef[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [templates, setTemplates] = useState<TriggerTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | "new" | null>(null);
  const [draft, setDraft] = useState<DraftState>(EMPTY_DRAFT);
  const [preview, setPreview] = useState<string | null>(null);
  const [showTemplates, setShowTemplates] = useState(false);

// [RCF:PROTECTED]
  const load = async () => {
    setLoading(true);
    try {
      const [t, a, p, tmpl] = await Promise.all([
        api.get<Trigger[]>("/triggers"),
        api.get<AgentRef[]>("/agents"),
        api.get<Preset[]>("/triggers/presets"),
        api.get<TriggerTemplate[]>("/triggers/templates"),
      ]);
      setTriggers(t);
      setAgents(a);
      setPresets(p);
      setTemplates(tmpl);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load triggers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

// [RCF:PROTECTED]
  const startNew = () => {
    setDraft(EMPTY_DRAFT);
    setEditingId("new");
    setPreview(null);
  };

// [RCF:PROTECTED]
  const startFromTemplate = (tmpl: TriggerTemplate) => {
    setDraft({
      name: tmpl.name,
      schedule_kind: "preset",
      schedule_preset: tmpl.schedule_preset,
      cron: presets.find((p) => p.id === tmpl.schedule_preset)?.cron ?? "0 9 * * *",
      agent_ids: [],
      task_template: tmpl.task_template,
      enabled: true,
    });
    setEditingId("new");
    setPreview(null);
    setShowTemplates(false);
  };

// [RCF:PROTECTED]
  const startEdit = (t: Trigger) => {
    setDraft({
      name: t.name,
      schedule_kind: t.schedule_kind,
      schedule_preset: t.schedule_preset ?? "every_morning_9",
      cron: t.cron,
      agent_ids: t.agent_ids,
      task_template: t.task_template,
      enabled: t.enabled,
    });
    setEditingId(t.id);
    setPreview(null);
  };

// [RCF:PROTECTED]
  const cancelEdit = () => {
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
    setPreview(null);
  };

// [RCF:PROTECTED]
  const previewCron = async () => {
    if (draft.schedule_kind !== "cron") return;
    try {
      const r = await api.get<{ next_fire_at: string }>(
        `/triggers/preview?cron=${encodeURIComponent(draft.cron)}`,
      );
      setPreview(new Date(r.next_fire_at).toLocaleString());
    } catch (e) {
      console.error(e);
      setPreview(null);
      toast.error("Invalid cron expression");
    }
  };

// [RCF:PROTECTED]
  const save = async () => {
    if (!draft.name.trim()) return toast.error("Name is required");
    if (!draft.task_template.trim()) return toast.error("Task is required");
    if (draft.agent_ids.length === 0) return toast.error("Pick at least one agent");

    const body = {
      name: draft.name.trim(),
      schedule_kind: draft.schedule_kind,
      schedule_preset:
        draft.schedule_kind === "preset" ? draft.schedule_preset : null,
      cron: draft.schedule_kind === "cron" ? draft.cron : null,
      agent_ids: draft.agent_ids,
      task_template: draft.task_template.trim(),
      enabled: draft.enabled,
    };

    try {
      if (editingId === "new") {
        await api.post("/triggers", body);
        toast.success("Trigger created");
      } else if (typeof editingId === "number") {
        await api.patch(`/triggers/${editingId}`, body);
        toast.success("Trigger updated");
      }
      cancelEdit();
      await load();
    } catch (e) {
      console.error(e);
      toast.error("Save failed");
    }
  };

// [RCF:PROTECTED]
  const toggleEnabled = async (t: Trigger) => {
    setBusyId(t.id);
    try {
      await api.patch(`/triggers/${t.id}`, { enabled: !t.enabled });
      await load();
    } catch (e) {
      console.error(e);
      toast.error("Toggle failed");
    } finally {
      setBusyId(null);
    }
  };

// [RCF:PROTECTED]
  const remove = async (t: Trigger) => {
    if (!confirm(`Delete trigger "${t.name}"?`)) return;
    setBusyId(t.id);
    try {
      await api.delete(`/triggers/${t.id}`);
      await load();
    } catch (e) {
      console.error(e);
      toast.error("Delete failed");
    } finally {
      setBusyId(null);
    }
  };

// [RCF:PROTECTED]
  const runNow = async (t: Trigger) => {
    setBusyId(t.id);
    try {
      const r = await api.post<{ message_ids: number[] }>(
        `/triggers/${t.id}/run`,
      );
      toast.success(`Queued ${r.message_ids.length} agent message(s)`);
    } catch (e) {
      console.error(e);
      toast.error("Run failed");
    } finally {
      setBusyId(null);
    }
  };

// [RCF:PROTECTED]
  const toggleAgent = (id: number) => {
    setDraft((d) => ({
      ...d,
      agent_ids: d.agent_ids.includes(id)
        ? d.agent_ids.filter((x) => x !== id)
        : [...d.agent_ids, id],
    }));
  };

// [RCF:PROTECTED]
  const agentName = (id: number) =>
    agents.find((a) => a.id === id)?.name ?? `#${id}`;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Triggers</h3>
          <p className="text-xs text-muted-foreground">
            Cron-scheduled tasks delivered to one or more agents.
          </p>
        </div>
        {editingId === null && (
          <div className="flex items-center gap-2">
            <Button onClick={() => setShowTemplates(!showTemplates)} variant="outline" size="sm">
              {showTemplates ? "Hide templates" : "Browse templates"}
            </Button>
            <Button onClick={startNew} size="sm">
              New trigger
            </Button>
          </div>
        )}
      </div>

      {showTemplates && editingId === null && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {templates.map((tmpl) => (
            <div
              key={tmpl.id}
              className="rounded-lg border border-border p-4 space-y-2 hover:border-accent transition-colors cursor-pointer"
              onClick={() => startFromTemplate(tmpl)}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h4 className="font-medium text-sm">{tmpl.name}</h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    {tmpl.description}
                  </p>
                </div>
                <span className="text-[10px] px-2 py-1 rounded bg-accent/10 text-accent shrink-0">
                  {PRESET_LABELS[tmpl.schedule_preset] ?? tmpl.schedule_preset}
                </span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2 italic">
                "{tmpl.task_template.slice(0, 120)}..."
              </p>
            </div>
          ))}
        </div>
      )}

      {editingId !== null && (
        <div className="rounded-lg border border-border p-4 space-y-3">
          <p className="text-sm font-medium">
            {editingId === "new" ? "New trigger" : "Edit trigger"}
          </p>

          <div>
            <label className="block text-xs text-muted-foreground mb-1">Name</label>
            <input
              type="text"
              className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </div>

          <div>
            <div className="flex items-center gap-2 mb-1">
              <label className="text-xs text-muted-foreground">Schedule</label>
              <div className="ml-auto flex items-center gap-1 text-xs">
                {(["preset", "cron"] as const).map((k) => (
                  <button
                    key={k}
                    type="button"
                    className={`px-2 py-0.5 rounded ${
                      draft.schedule_kind === k
                        ? "bg-foreground text-background"
                        : "bg-muted text-muted-foreground"
                    }`}
                    onClick={() => setDraft({ ...draft, schedule_kind: k })}
                  >
                    {k}
                  </button>
                ))}
              </div>
            </div>
            {draft.schedule_kind === "preset" ? (
              <select
                className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
                value={draft.schedule_preset}
                onChange={(e) =>
                  setDraft({ ...draft, schedule_preset: e.target.value })
                }
              >
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {PRESET_LABELS[p.id] ?? p.id} ({p.cron})
                  </option>
                ))}
              </select>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  className="flex-1 rounded border border-border bg-background px-2 py-1 text-sm font-mono"
                  placeholder="*/15 * * * *"
                  value={draft.cron}
                  onChange={(e) => setDraft({ ...draft, cron: e.target.value })}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={previewCron}
                >
                  Preview
                </Button>
              </div>
            )}
            {preview && (
              <p className="text-xs text-muted-foreground mt-1">
                Next fire: {preview}
              </p>
            )}
          </div>

          <div>
            <label className="block text-xs text-muted-foreground mb-1">
              Agents (click to toggle)
            </label>
            <div className="flex flex-wrap gap-1">
              {agents.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No agents available.
                </p>
              ) : (
                agents.map((a) => {
                  const on = draft.agent_ids.includes(a.id);
                  return (
                    <button
                      key={a.id}
                      type="button"
                      className={`text-xs px-2 py-1 rounded ${
                        on
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-muted text-muted-foreground"
                      }`}
                      onClick={() => toggleAgent(a.id)}
                    >
                      {a.name}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs text-muted-foreground mb-1">
              Task (sent verbatim to each agent)
            </label>
            <textarea
              className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
              rows={3}
              value={draft.task_template}
              onChange={(e) =>
                setDraft({ ...draft, task_template: e.target.value })
              }
            />
          </div>

          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            />
            Enabled
          </label>

          <div className="flex items-center gap-2">
            <Button onClick={save} size="sm">
              Save
            </Button>
            <Button onClick={cancelEdit} variant="outline" size="sm">
              Cancel
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-xs text-muted-foreground">Loading…</p>
      ) : triggers.length === 0 && editingId === null ? (
        <p className="text-xs text-muted-foreground">No triggers yet.</p>
      ) : (
        <ul className="space-y-2">
          {triggers.map((t) => (
            <li
              key={t.id}
              className="rounded-lg border border-border p-3 space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <p className="font-medium truncate">{t.name}</p>
                  <span
                    className={`text-[10px] px-1.5 rounded ${
                      t.enabled
                        ? "bg-green-500/20 text-green-400"
                        : "bg-zinc-500/20 text-zinc-400"
                    }`}
                  >
                    {t.enabled ? "enabled" : "disabled"}
                  </span>
                  <code className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                    {t.cron}
                  </code>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === t.id}
                    onClick={() => runNow(t)}
                  >
                    Run now
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === t.id}
                    onClick={() => toggleEnabled(t)}
                  >
                    {t.enabled ? "Disable" : "Enable"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === t.id}
                    onClick={() => startEdit(t)}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === t.id}
                    onClick={() => remove(t)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {t.task_template}
              </p>
              <div className="flex items-center gap-2 flex-wrap text-[11px] text-muted-foreground">
                <span>Agents:</span>
                {t.agent_ids.map((id) => (
                  <span
                    key={id}
                    className="px-1.5 rounded bg-muted text-muted-foreground"
                  >
                    {agentName(id)}
                  </span>
                ))}
                {t.next_fire_at && (
                  <span className="ml-auto">
                    Next: {new Date(t.next_fire_at).toLocaleString()}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
