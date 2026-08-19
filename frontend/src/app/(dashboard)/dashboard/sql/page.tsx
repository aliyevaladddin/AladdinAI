// NOTICE: This file is protected under RCF-PL
"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Database, Loader2, Download, BookOpen, Save, Copy, Wand2, Share2, Keyboard, Plus, X } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { format } from "sql-formatter";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { SQLSidebar } from "./SQLSidebar";
import { SQLResults } from "./SQLResults";


interface QueryResult {
  success: boolean;
  rows: any[];
  columns: string[];
  row_count: number;
  error?: string;
  message?: string;
  execution_time?: number;
}


interface SavedQuery {
  id: string;
  name: string;
  query: string;
  created_at: number;
  pinned?: boolean;
}


interface QueryTab {
  id: string;
  name: string;
  query: string;
  result: QueryResult | null;
}


interface TableSchema {
  table_name: string;
  columns: Array<{
    column_name: string;
    data_type: string;
    nullable: boolean;
    default: string | null;
  }>;
}

export default function SQLPlaygroundPage() {
  const [tabs, setTabs] = useState<QueryTab[]>([
    {
      id: "1",
      name: "Query 1",
      query: "-- Example: Show all agents\nSELECT id, name, status, created_at FROM agents ORDER BY created_at DESC LIMIT 10;",
      result: null,
    },
  ]);
  const [activeTabId, setActiveTabId] = useState("1");

  const activeTab = tabs.find((t) => t.id === activeTabId) || tabs[0];
  const query = activeTab.query;
  const result = activeTab.result;

  const setQuery = (newQuery: string) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, query: newQuery } : t)));
  };

  const setResult = (newResult: QueryResult | null) => {
    setTabs((prev) => prev.map((t) => (t.id === activeTabId ? { ...t, result: newResult } : t)));
  };

  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [editorHeight, setEditorHeight] = useState(256);
  const [isResizing, setIsResizing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showSaved, setShowSaved] = useState(true);
  const [showSchema, setShowSchema] = useState(false);
  const [schema, setSchema] = useState<TableSchema[]>([]);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [visualizationType, setVisualizationType] = useState<"table" | "bar" | "line" | "pie">("table");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("sql_saved_queries");
      if (saved) { const parsed = JSON.parse(saved); if (Array.isArray(parsed)) setSavedQueries(parsed); }
    } catch (e) { console.error("Failed to load saved queries", e); localStorage.removeItem("sql_saved_queries"); }

    try {
      const hist = localStorage.getItem("sql_history");
      if (hist) { const parsed = JSON.parse(hist); if (Array.isArray(parsed)) setHistory(parsed); }
    } catch (e) { console.error("Failed to load history", e); localStorage.removeItem("sql_history"); }

    try {
      const tabsData = localStorage.getItem("sql_tabs");
      if (tabsData) {
        const parsed = JSON.parse(tabsData);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setTabs(parsed);
          if (!parsed.find((t: QueryTab) => t.id === activeTabId)) setActiveTabId(parsed[0].id);
        }
      }
    } catch (e) { console.error("Failed to load tabs", e); localStorage.removeItem("sql_tabs"); }

    loadSchema();
  }, []);

  useEffect(() => { localStorage.setItem("sql_tabs", JSON.stringify(tabs)); }, [tabs]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const encodedQuery = params.get("q");
    if (encodedQuery) {
      try { setQuery(atob(encodedQuery)); toast.success("Query loaded from share link"); }
      catch { toast.error("Invalid share link"); }
    }
  }, []);

  const loadSchema = async () => {
    try { const data = await api.get<{ tables: TableSchema[] }>("/sql/schema"); setSchema(data.tables); }
    catch (err) { console.error("Failed to load schema", err); }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); executeQuery(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "s") { e.preventDefault(); setShowSaveDialog(true); }
      if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); setShowKeyboardShortcuts(true); }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") { e.preventDefault(); formatQuery(); }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "S") { e.preventDefault(); shareQuery(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "t") { e.preventDefault(); addNewTab(); }
      if ((e.ctrlKey || e.metaKey) && e.key === "w") { e.preventDefault(); closeTab(activeTabId); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [query, activeTabId, tabs]);

  const executeQuery = async () => {
    if (!query.trim()) { toast.error("Query cannot be empty"); return; }
    setLoading(true);
    const startTime = performance.now();
    try {
      const res = await api.post<QueryResult>("/sql/execute", { query, read_only: true, limit: 100 });
      const executionTime = performance.now() - startTime;
      setResult({ ...res, execution_time: executionTime });
      if (res.success) {
        toast.success(res.message || `Query executed successfully. ${res.row_count} rows returned.`);
        const newHistory = [query, ...history.filter(q => q !== query).slice(0, 19)];
        setHistory(newHistory);
        localStorage.setItem("sql_history", JSON.stringify(newHistory));
      } else {
        toast.error(res.error || "Query failed");
      }
    } catch (err) {
      setResult({ success: false, rows: [], columns: [], row_count: 0, error: err instanceof Error ? err.message : "Unknown error", execution_time: performance.now() - startTime });
      toast.error("Failed to execute query");
    } finally { setLoading(false); }
  };

  const saveQuery = () => {
    if (!saveName.trim()) { toast.error("Please enter a name for the query"); return; }
    const newQuery: SavedQuery = { id: Date.now().toString(), name: saveName, query, created_at: Date.now() };
    const updated = [newQuery, ...savedQueries];
    setSavedQueries(updated);
    localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    setSaveName(""); setShowSaveDialog(false);
    toast.success("Query saved successfully");
  };

  const deleteSavedQuery = (id: string) => {
    const updated = savedQueries.filter((q) => q.id !== id);
    setSavedQueries(updated);
    localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    toast.success("Query deleted");
  };

  const clearHistory = () => { setHistory([]); localStorage.removeItem("sql_history"); toast.success("History cleared"); };
  const copyToClipboard = (text: string) => { navigator.clipboard.writeText(text); toast.success("Copied to clipboard"); };

  const exportFile = (data: string, type: string, ext: string) => {
    const blob = new Blob([data], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `query-result-${Date.now()}.${ext}`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportCSV = () => {
    if (!result?.rows.length) return;
    exportFile([result.columns.join(","), ...result.rows.map((row) => result.columns.map((col) => JSON.stringify(row[col] ?? "")).join(","))].join("\n"), "text/csv", "csv");
    toast.success("CSV exported");
  };

  const exportJSON = () => {
    if (!result?.rows.length) return;
    exportFile(JSON.stringify(result.rows, null, 2), "application/json", "json");
    toast.success("JSON exported");
  };

  const exportExcel = () => {
    if (!result?.rows.length) return;
    const ws = XLSX.utils.json_to_sheet(result.rows);
    const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, `query-result-${Date.now()}.xlsx`);
    toast.success("Excel exported");
  };

  const exportPDF = () => {
    if (!result?.rows.length) return;
    const doc = new jsPDF(); doc.text("SQL Query Results", 14, 15);
    autoTable(doc, { head: [result.columns], body: result.rows.map((row) => result.columns.map((col) => String(row[col] ?? ""))), startY: 25, styles: { fontSize: 8 } });
    doc.save(`query-result-${Date.now()}.pdf`);
    toast.success("PDF exported");
  };

  const formatQuery = () => {
    try { setQuery(format(query, { language: "postgresql", tabWidth: 2, keywordCase: "upper" })); toast.success("Query formatted"); }
    catch { toast.error("Failed to format query"); }
  };

  const shareQuery = () => {
    const url = `${window.location.origin}${window.location.pathname}?q=${btoa(query)}`;
    navigator.clipboard.writeText(url); toast.success("Share link copied to clipboard");
  };

  const togglePin = (id: string) => {
    const updated = savedQueries.map((q) => q.id === id ? { ...q, pinned: !q.pinned } : q);
    setSavedQueries(updated); localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    toast.success("Query pin toggled");
  };

  const addNewTab = () => {
    const newId = Date.now().toString();
    setTabs([...tabs, { id: newId, name: `Query ${tabs.length + 1}`, query: "", result: null }]);
    setActiveTabId(newId);
  };

  const closeTab = (id: string) => {
    if (tabs.length === 1) { toast.error("Cannot close last tab"); return; }
    const idx = tabs.findIndex((t) => t.id === id);
    const newTabs = tabs.filter((t) => t.id !== id);
    setTabs(newTabs);
    if (id === activeTabId) setActiveTabId(newTabs[Math.max(0, idx - 1)].id);
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;
      const cursorPos = textarea.selectionStart;
      const lastWord = query.substring(0, cursorPos).split(/\s/).pop() || "";
      if (lastWord.length < 2) return;

      const tableMatch = schema.map((t) => t.table_name).find((t) => t.startsWith(lastWord.toLowerCase()));
      if (tableMatch) {
        const newQuery = query.substring(0, cursorPos - lastWord.length) + tableMatch + query.substring(cursorPos);
        setQuery(newQuery);
        setTimeout(() => { textarea.selectionStart = textarea.selectionEnd = cursorPos - lastWord.length + tableMatch.length; }, 0);
        return;
      }

      const allColumns = schema.flatMap((t) => t.columns.map((c) => `${t.table_name}.${c.column_name}`));
      const colMatch = allColumns.find((c) => c.toLowerCase().includes(lastWord.toLowerCase()));
      if (colMatch) {
        const newQuery = query.substring(0, cursorPos - lastWord.length) + colMatch + query.substring(cursorPos);
        setQuery(newQuery);
        setTimeout(() => { textarea.selectionStart = textarea.selectionEnd = cursorPos - lastWord.length + colMatch.length; }, 0);
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => { setIsResizing(true); e.preventDefault(); };

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => { const h = e.clientY - 240; if (h >= 150 && h <= 600) setEditorHeight(h); };
    const handleMouseUp = () => setIsResizing(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => { document.removeEventListener("mousemove", handleMouseMove); document.removeEventListener("mouseup", handleMouseUp); };
  }, [isResizing]);

  return (
    <div className="h-screen flex gap-4 p-6 overflow-hidden">
      <SQLSidebar
        savedQueries={savedQueries} history={history} schema={schema}
        showSaved={showSaved} showHistory={showHistory} showSchema={showSchema}
        onToggleSaved={() => setShowSaved(!showSaved)} onToggleHistory={() => setShowHistory(!showHistory)} onToggleSchema={() => setShowSchema(!showSchema)}
        onSetQuery={setQuery} onTogglePin={togglePin} onDeleteSaved={deleteSavedQuery} onClearHistory={clearHistory}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col gap-4 min-w-0 min-h-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: "var(--color-accent)", color: "#fff" }}>
              <Database size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">SQL Playground</h1>
              <p className="text-sm" style={{ color: "var(--color-fg-muted)" }}>Query Postgres database directly with SQL</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowKeyboardShortcuts(true)} className="gap-2"><Keyboard size={14} /> Shortcuts</Button>
            <Button variant="outline" size="sm" onClick={formatQuery} className="gap-2" disabled={!query.trim()}><Wand2 size={14} /> Format</Button>
            <Button variant="outline" size="sm" onClick={shareQuery} className="gap-2" disabled={!query.trim()}><Share2 size={14} /> Share</Button>
            <Button variant="outline" size="sm" onClick={() => setShowSaveDialog(true)} className="gap-2" disabled={!query.trim()}><Save size={14} /> Save</Button>
            {result?.rows && result.rows.length > 0 && (
              <>
                <Button variant="outline" size="sm" onClick={exportCSV} className="gap-2"><Download size={14} /> CSV</Button>
                <Button variant="outline" size="sm" onClick={exportJSON} className="gap-2"><Download size={14} /> JSON</Button>
                <Button variant="outline" size="sm" onClick={exportExcel} className="gap-2"><Download size={14} /> Excel</Button>
                <Button variant="outline" size="sm" onClick={exportPDF} className="gap-2"><Download size={14} /> PDF</Button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b" style={{ borderColor: "var(--color-border)" }}>
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`group flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors border-b-2 ${tab.id === activeTabId ? "border-[var(--color-accent)]" : "border-transparent hover:border-[var(--color-border)]"}`}
              onClick={() => setActiveTabId(tab.id)}
            >
              <span className="text-xs font-medium" style={{ color: tab.id === activeTabId ? "var(--color-fg)" : "var(--color-fg-muted)" }}>{tab.name}</span>
              {tabs.length > 1 && (
                <button onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/10 transition-all">
                  <X size={12} className="text-red-500" />
                </button>
              )}
            </div>
          ))}
          <button onClick={addNewTab} className="p-2 rounded hover:bg-[var(--color-surface-2)] transition-colors" title="New tab (Ctrl+T)">
            <Plus size={14} style={{ color: "var(--color-fg-muted)" }} />
          </button>
        </div>

        {/* Editor */}
        <div className="flex flex-col border rounded-xl overflow-hidden shrink-0" style={{ borderColor: "var(--color-border)", height: `${editorHeight}px` }}>
          <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>SQL Query</span>
              <button onClick={() => copyToClipboard(query)} className="p-1 rounded hover:bg-[var(--color-surface)] transition-colors" title="Copy query"><Copy size={12} /></button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-surface)", color: "var(--color-fg-muted)" }}>Ctrl+Enter to run</span>
              <Button onClick={executeQuery} disabled={loading} size="sm" className="gap-2">
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} Execute
              </Button>
            </div>
          </div>
          <textarea
            ref={textareaRef} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={handleTextareaKeyDown}
            className="flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none"
            style={{ background: "var(--color-surface)", color: "var(--color-fg)" }}
            placeholder="Enter SQL query... (Tab for autocomplete)" spellCheck={false}
          />
          <div
            className="h-1 cursor-row-resize hover:bg-[var(--color-accent)] transition-colors"
            style={{ background: isResizing ? "var(--color-accent)" : "transparent" }}
            onMouseDown={handleMouseDown}
          />
        </div>

        {/* Results */}
        {result && (
          <SQLResults result={result} visualizationType={visualizationType} onSetVisualizationType={setVisualizationType} />
        )}

        {/* Info */}
        {!result && (
          <div className="flex items-start gap-2 p-3 rounded-lg border text-xs shrink-0" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
            <BookOpen size={14} className="mt-0.5 shrink-0" style={{ color: "var(--color-accent)" }} />
            <div>
              <p style={{ color: "var(--color-fg-muted)" }}>
                <strong>Read-only mode:</strong> Only SELECT queries are allowed. Limit is automatically applied (max 1000 rows).
                Available tables: agents, agent_messages, llm_providers, system_settings, users, crm_contacts, crm_deals, crm_activities.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Save Query Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowSaveDialog(false)}>
          <div className="w-full max-w-md p-6 rounded-xl border" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }} onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">Save Query</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase mb-2 block" style={{ color: "var(--color-fg-muted)" }}>Query Name</label>
                <input type="text" value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder="e.g. Active users report"
                  className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:border-[var(--color-accent)]"
                  style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg)" }}
                  autoFocus onKeyDown={(e) => { if (e.key === "Enter") saveQuery(); if (e.key === "Escape") setShowSaveDialog(false); }}
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase mb-2 block" style={{ color: "var(--color-fg-muted)" }}>Query Preview</label>
                <pre className="text-xs font-mono p-3 rounded-lg border max-h-32 overflow-auto" style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}>{query}</pre>
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowSaveDialog(false)}>Cancel</Button>
                <Button onClick={saveQuery} disabled={!saveName.trim()}>Save Query</Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Modal */}
      {showKeyboardShortcuts && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowKeyboardShortcuts(false)}>
          <div className="w-full max-w-lg p-6 rounded-xl border" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }} onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Keyboard Shortcuts</h2>
              <button onClick={() => setShowKeyboardShortcuts(false)} className="p-1 rounded hover:bg-[var(--color-surface-2)] transition-colors"><X size={16} /></button>
            </div>
            <div className="space-y-3">
              {[
                ["Execute query", "Ctrl+Enter"],
                ["Save query", "Ctrl+S"],
                ["Format query", "Ctrl+Shift+F"],
                ["Share query", "Ctrl+Shift+S"],
                ["Show shortcuts", "Ctrl+K"],
                ["New tab", "Ctrl+T"],
                ["Close tab", "Ctrl+W"],
              ].map(([label, key]) => (
                <div key={key} className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                  <span className="text-sm" style={{ color: "var(--color-fg)" }}>{label}</span>
                  <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>{key}</kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
