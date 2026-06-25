// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";


interface MemoryEntry {
  id: string;
  fact: string;
  tags: string[];
  agent_id: number | null;
  visibility: "private" | "shared";
  created_at: string | null;
  session_id: number | null;
}

type Scope = "private" | "shared" | "both";


export function AgentMemoryPanel({ agentId }: { agentId: number }) {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [scope, setScope] = useState<Scope>("both");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [draftFact, setDraftFact] = useState("");
  const [draftVis, setDraftVis] = useState<"private" | "shared">("private");
  const [draftTags, setDraftTags] = useState("");


  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ scope, limit: "100" });
      if (q.trim()) params.set("q", q.trim());
      const r = await api.get<MemoryEntry[]>(
        `/agents/${agentId}/memories?${params.toString()}`,
      );
      setEntries(r);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load memories");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [agentId, scope]);


  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    load();
  };


  const onDelete = async (id: string) => {
    if (!confirm("Delete this memory?")) return;
    setBusyId(id);
    try {
      await api.delete(`/agents/${agentId}/memories/${id}`);
      setEntries((prev) => prev.filter((m) => m.id !== id));
      toast.success("Memory deleted");
    } catch (e) {
      console.error(e);
      toast.error("Delete failed");
    } finally {
      setBusyId(null);
    }
  };


  const onAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const fact = draftFact.trim();
    if (!fact) return;
    const tags = draftTags
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    setAdding(true);
    try {
      await api.post(`/agents/${agentId}/memories`, {
        fact,
        visibility: draftVis,
        tags,
      });
      setDraftFact("");
      setDraftTags("");
      toast.success("Memory added");
      await load();
    } catch (e) {
      console.error(e);
      toast.error("Add failed");
    } finally {
      setAdding(false);
    }
  };

  const counts = useMemo(() => {
    const p = entries.filter((m) => m.visibility === "private").length;
    const s = entries.filter((m) => m.visibility === "shared").length;
    return { p, s };
  }, [entries]);

  return (
    <div className="mt-4 border-t border-border pt-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">
          Memory{" "}
          <span className="text-xs text-muted-foreground font-normal">
            ({counts.p} private, {counts.s} shared)
          </span>
        </p>
        <div className="flex items-center gap-1 text-xs">
          {(["both", "private", "shared"] as Scope[]).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setScope(s)}
              className={`px-2 py-1 rounded ${scope === s
                  ? "bg-foreground text-background"
                  : "bg-muted text-muted-foreground"
                }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={onSearch} className="flex items-center gap-2">
        <input
          type="text"
          className="flex-1 rounded border border-border bg-background px-2 py-1 text-sm"
          placeholder="Search facts or tags…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Button type="submit" variant="outline" size="sm" disabled={loading}>
          Search
        </Button>
      </form>

      <form
        onSubmit={onAdd}
        className="rounded border border-border p-3 space-y-2"
      >
        <p className="text-xs font-medium">Add manually</p>
        <textarea
          className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
          rows={2}
          placeholder="Fact text…"
          value={draftFact}
          onChange={(e) => setDraftFact(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <select
            className="rounded border border-border bg-background px-2 py-1 text-xs"
            value={draftVis}
            onChange={(e) =>
              setDraftVis(e.target.value as "private" | "shared")
            }
          >
            <option value="private">private</option>
            <option value="shared">shared</option>
          </select>
          <input
            type="text"
            className="flex-1 rounded border border-border bg-background px-2 py-1 text-xs"
            placeholder="tags (comma separated)"
            value={draftTags}
            onChange={(e) => setDraftTags(e.target.value)}
          />
          <Button
            type="submit"
            size="sm"
            disabled={adding || !draftFact.trim()}
          >
            {adding ? "Adding…" : "Add"}
          </Button>
        </div>
      </form>

      {loading ? (
        <p className="text-xs text-muted-foreground">Loading…</p>
      ) : entries.length === 0 ? (
        <p className="text-xs text-muted-foreground">No memories yet.</p>
      ) : (
        <ul className="space-y-2 max-h-96 overflow-y-auto">
          {entries.map((m) => (
            <li
              key={m.id}
              className="rounded border border-border p-2 text-xs space-y-1"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`px-1.5 rounded ${m.visibility === "shared"
                      ? "bg-blue-500/20 text-blue-400"
                      : "bg-zinc-500/20 text-zinc-400"
                    }`}
                >
                  {m.visibility}
                </span>
                {m.created_at && (
                  <span className="text-muted-foreground">
                    {new Date(m.created_at).toLocaleString()}
                  </span>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="ml-auto h-6 px-2"
                  disabled={busyId === m.id}
                  onClick={() => onDelete(m.id)}
                >
                  Delete
                </Button>
              </div>
              <p className="whitespace-pre-wrap">{m.fact}</p>
              {Array.isArray(m.tags) && m.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {m.tags.map((t) => (
                    <span
                      key={t}
                      className="px-1.5 rounded bg-muted text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
