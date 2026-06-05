"use client";

import { useState, useEffect, useRef } from "react";
import { Play, Database, Loader2, Download, History, BookOpen, Save, Trash2, Copy, Clock, X, ChevronDown, ChevronUp, Wand2, Share2, Keyboard, Pin, PinOff, BarChart3, Plus, Table2 } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { format } from "sql-formatter";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

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
  // Tabs
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
    setTabs((prev) =>
      prev.map((t) => (t.id === activeTabId ? { ...t, query: newQuery } : t))
    );
  };

  const setResult = (newResult: QueryResult | null) => {
    setTabs((prev) =>
      prev.map((t) => (t.id === activeTabId ? { ...t, result: newResult } : t))
    );
  };

  // Other state
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

  // Load saved queries and schema from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("sql_saved_queries");
    if (saved) {
      try {
        setSavedQueries(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load saved queries", e);
      }
    }

    const hist = localStorage.getItem("sql_history");
    if (hist) {
      try {
        setHistory(JSON.parse(hist));
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }

    const tabsData = localStorage.getItem("sql_tabs");
    if (tabsData) {
      try {
        setTabs(JSON.parse(tabsData));
      } catch (e) {
        console.error("Failed to load tabs", e);
      }
    }

    // Load schema
    loadSchema();
  }, []);

  // Save tabs to localStorage
  useEffect(() => {
    localStorage.setItem("sql_tabs", JSON.stringify(tabs));
  }, [tabs]);

  // Load query from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const encodedQuery = params.get("q");
    if (encodedQuery) {
      try {
        const decoded = atob(encodedQuery);
        setQuery(decoded);
        toast.success("Query loaded from share link");
      } catch (err) {
        toast.error("Invalid share link");
      }
    }
  }, []);

  const loadSchema = async () => {
    try {
      const data = await api.get<{ tables: TableSchema[] }>("/sql/schema");
      setSchema(data.tables);
    } catch (err) {
      console.error("Failed to load schema", err);
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Enter to execute
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        executeQuery();
      }
      // Ctrl/Cmd + S to save
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        setShowSaveDialog(true);
      }
      // Ctrl/Cmd + K to show shortcuts
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setShowKeyboardShortcuts(true);
      }
      // Ctrl/Cmd + Shift + F to format
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "F") {
        e.preventDefault();
        formatQuery();
      }
      // Ctrl/Cmd + Shift + S to share
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "S") {
        e.preventDefault();
        shareQuery();
      }
      // Ctrl/Cmd + T to new tab
      if ((e.ctrlKey || e.metaKey) && e.key === "t") {
        e.preventDefault();
        addNewTab();
      }
      // Ctrl/Cmd + W to close tab
      if ((e.ctrlKey || e.metaKey) && e.key === "w") {
        e.preventDefault();
        closeTab(activeTabId);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [query, activeTabId, tabs]);

  const executeQuery = async () => {
    if (!query.trim()) {
      toast.error("Query cannot be empty");
      return;
    }

    setLoading(true);
    const startTime = performance.now();
    try {
      const res = await api.post<QueryResult>("/sql/execute", {
        query,
        read_only: true,
        limit: 100,
      });

      const executionTime = performance.now() - startTime;
      const resultWithTime = { ...res, execution_time: executionTime };
      setResult(resultWithTime);

      if (res.success) {
        toast.success(
          res.message || `Query executed successfully. ${res.row_count} rows returned.`
        );
        // Add to history
        const newHistory = [query, ...history.filter(q => q !== query).slice(0, 19)];
        setHistory(newHistory);
        localStorage.setItem("sql_history", JSON.stringify(newHistory));
      } else {
        toast.error(res.error || "Query failed");
      }
    } catch (err) {
      const executionTime = performance.now() - startTime;
      toast.error("Failed to execute query");
      setResult({
        success: false,
        rows: [],
        columns: [],
        row_count: 0,
        error: err instanceof Error ? err.message : "Unknown error",
        execution_time: executionTime,
      });
    } finally {
      setLoading(false);
    }
  };

  const saveQuery = () => {
    if (!saveName.trim()) {
      toast.error("Please enter a name for the query");
      return;
    }

    const newQuery: SavedQuery = {
      id: Date.now().toString(),
      name: saveName,
      query,
      created_at: Date.now(),
    };

    const updated = [newQuery, ...savedQueries];
    setSavedQueries(updated);
    localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    setSaveName("");
    setShowSaveDialog(false);
    toast.success("Query saved successfully");
  };

  const deleteSavedQuery = (id: string) => {
    const updated = savedQueries.filter((q) => q.id !== id);
    setSavedQueries(updated);
    localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    toast.success("Query deleted");
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem("sql_history");
    toast.success("History cleared");
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const exportCSV = () => {
    if (!result || !result.rows.length) return;

    const csv = [
      result.columns.join(","),
      ...result.rows.map((row) =>
        result.columns.map((col) => JSON.stringify(row[col] ?? "")).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `query-result-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV exported");
  };

  const exportJSON = () => {
    if (!result || !result.rows.length) return;

    const json = JSON.stringify(result.rows, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `query-result-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("JSON exported");
  };

  const exportExcel = () => {
    if (!result || !result.rows.length) return;

    const ws = XLSX.utils.json_to_sheet(result.rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, `query-result-${Date.now()}.xlsx`);
    toast.success("Excel exported");
  };

  const exportPDF = () => {
    if (!result || !result.rows.length) return;

    const doc = new jsPDF();
    doc.text("SQL Query Results", 14, 15);

    autoTable(doc, {
      head: [result.columns],
      body: result.rows.map((row) => result.columns.map((col) => String(row[col] ?? ""))),
      startY: 25,
      styles: { fontSize: 8 },
    });

    doc.save(`query-result-${Date.now()}.pdf`);
    toast.success("PDF exported");
  };

  const formatQuery = () => {
    try {
      const formatted = format(query, {
        language: "postgresql",
        tabWidth: 2,
        keywordCase: "upper",
      });
      setQuery(formatted);
      toast.success("Query formatted");
    } catch (err) {
      toast.error("Failed to format query");
    }
  };

  const shareQuery = () => {
    const encoded = btoa(query);
    const url = `${window.location.origin}${window.location.pathname}?q=${encoded}`;
    navigator.clipboard.writeText(url);
    toast.success("Share link copied to clipboard");
  };

  const togglePin = (id: string) => {
    const updated = savedQueries.map((q) =>
      q.id === id ? { ...q, pinned: !q.pinned } : q
    );
    setSavedQueries(updated);
    localStorage.setItem("sql_saved_queries", JSON.stringify(updated));
    toast.success("Query pin toggled");
  };

  const addNewTab = () => {
    const newId = Date.now().toString();
    const newTab: QueryTab = {
      id: newId,
      name: `Query ${tabs.length + 1}`,
      query: "",
      result: null,
    };
    setTabs([...tabs, newTab]);
    setActiveTabId(newId);
  };

  const closeTab = (id: string) => {
    if (tabs.length === 1) {
      toast.error("Cannot close last tab");
      return;
    }
    const idx = tabs.findIndex((t) => t.id === id);
    const newTabs = tabs.filter((t) => t.id !== id);
    setTabs(newTabs);
    if (id === activeTabId) {
      setActiveTabId(newTabs[Math.max(0, idx - 1)].id);
    }
  };

  const renameTab = (id: string, name: string) => {
    setTabs((prev) => prev.map((t) => (t.id === id ? { ...t, name } : t)));
  };

  const handleTextareaKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Simple autocomplete on Tab key
    if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const cursorPos = textarea.selectionStart;
      const textBeforeCursor = query.substring(0, cursorPos);
      const lastWord = textBeforeCursor.split(/\s/).pop() || "";

      if (lastWord.length < 2) return;

      // Try to match table names
      const tableNames = schema.map((t) => t.table_name);
      const matchingTable = tableNames.find((t) => t.startsWith(lastWord.toLowerCase()));

      if (matchingTable) {
        const newQuery =
          query.substring(0, cursorPos - lastWord.length) +
          matchingTable +
          query.substring(cursorPos);
        setQuery(newQuery);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd =
            cursorPos - lastWord.length + matchingTable.length;
        }, 0);
        return;
      }

      // Try to match column names from all tables
      const allColumns = schema.flatMap((t) =>
        t.columns.map((c) => `${t.table_name}.${c.column_name}`)
      );
      const matchingColumn = allColumns.find((c) =>
        c.toLowerCase().includes(lastWord.toLowerCase())
      );

      if (matchingColumn) {
        const newQuery =
          query.substring(0, cursorPos - lastWord.length) +
          matchingColumn +
          query.substring(cursorPos);
        setQuery(newQuery);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd =
            cursorPos - lastWord.length + matchingColumn.length;
        }, 0);
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsResizing(true);
    e.preventDefault();
  };

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = e.clientY - 240; // Adjust based on header height
      if (newHeight >= 150 && newHeight <= 600) {
        setEditorHeight(newHeight);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const examples = [
    {
      label: "All Agents",
      query: "SELECT id, name, status, created_at FROM agents ORDER BY created_at DESC LIMIT 10;",
    },
    {
      label: "Active Providers",
      query: "SELECT id, name, type, base_url FROM llm_providers WHERE is_active = true;",
    },
    {
      label: "Recent Messages",
      query:
        "SELECT am.id, am.content, a.name as agent_name, am.created_at\nFROM agent_messages am\nJOIN agents a ON am.agent_id = a.id\nORDER BY am.created_at DESC\nLIMIT 20;",
    },
    {
      label: "User Settings",
      query: "SELECT user_id, media_storage_backend, created_at FROM system_settings;",
    },
    {
      label: "Message Stats",
      query: "SELECT a.name, COUNT(am.id) as message_count\nFROM agents a\nLEFT JOIN agent_messages am ON a.id = am.agent_id\nGROUP BY a.id, a.name\nORDER BY message_count DESC;",
    },
  ];

  return (
    <div className="h-screen flex gap-4 p-6 overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 flex flex-col gap-4 shrink-0 overflow-y-auto">
        {/* Saved Queries */}
        <div className="border rounded-xl overflow-hidden flex flex-col" style={{ borderColor: "var(--color-border)" }}>
          <div
            className="px-4 py-2 border-b flex items-center justify-between"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
          >
            <button
              onClick={() => setShowSaved(!showSaved)}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <Save size={12} />
              <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                Saved Queries ({savedQueries.length})
              </span>
              {showSaved ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
          {showSaved && (
            <div className="p-2 space-y-1 max-h-96 overflow-y-auto">
              {savedQueries.length === 0 ? (
                <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>
                  No saved queries yet
                </p>
              ) : (
                <>
                  {savedQueries.filter(sq => sq.pinned).length > 0 && (
                    <>
                      <div className="text-xs font-bold uppercase px-2 py-1" style={{ color: "var(--color-fg-muted)" }}>
                        Pinned
                      </div>
                      {savedQueries.filter(sq => sq.pinned).map((sq) => (
                        <div
                          key={sq.id}
                          className="group flex items-center gap-2 p-2 rounded-lg hover:bg-[var(--color-surface-2)] transition-colors"
                        >
                          <button
                            onClick={() => setQuery(sq.query)}
                            className="flex-1 text-left min-w-0"
                          >
                            <div className="text-xs font-medium truncate" style={{ color: "var(--color-fg)" }}>
                              {sq.name}
                            </div>
                            <div className="text-xs font-mono truncate" style={{ color: "var(--color-fg-muted)" }}>
                              {sq.query.split("\n")[0]}
                            </div>
                          </button>
                          <button
                            onClick={() => togglePin(sq.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-yellow-500/10 transition-all"
                            title="Unpin"
                          >
                            <PinOff size={12} className="text-yellow-500" />
                          </button>
                          <button
                            onClick={() => deleteSavedQuery(sq.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 transition-all"
                            title="Delete"
                          >
                            <Trash2 size={12} className="text-red-500" />
                          </button>
                        </div>
                      ))}
                    </>
                  )}
                  {savedQueries.filter(sq => !sq.pinned).length > 0 && (
                    <>
                      {savedQueries.filter(sq => sq.pinned).length > 0 && (
                        <div className="text-xs font-bold uppercase px-2 py-1 mt-2" style={{ color: "var(--color-fg-muted)" }}>
                          Other
                        </div>
                      )}
                      {savedQueries.filter(sq => !sq.pinned).map((sq) => (
                        <div
                          key={sq.id}
                          className="group flex items-center gap-2 p-2 rounded-lg hover:bg-[var(--color-surface-2)] transition-colors"
                        >
                          <button
                            onClick={() => setQuery(sq.query)}
                            className="flex-1 text-left min-w-0"
                          >
                            <div className="text-xs font-medium truncate" style={{ color: "var(--color-fg)" }}>
                              {sq.name}
                            </div>
                            <div className="text-xs font-mono truncate" style={{ color: "var(--color-fg-muted)" }}>
                              {sq.query.split("\n")[0]}
                            </div>
                          </button>
                          <button
                            onClick={() => togglePin(sq.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-yellow-500/10 transition-all"
                            title="Pin"
                          >
                            <Pin size={12} className="text-yellow-500" />
                          </button>
                          <button
                            onClick={() => deleteSavedQuery(sq.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 transition-all"
                            title="Delete"
                          >
                            <Trash2 size={12} className="text-red-500" />
                          </button>
                        </div>
                      ))}
                    </>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Examples */}
        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
          <div className="px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
            <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
              Examples
            </span>
          </div>
          <div className="p-2 space-y-1">
            {examples.map((ex) => (
              <button
                key={ex.label}
                onClick={() => setQuery(ex.query)}
                className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-[var(--color-surface-2)] transition-colors"
                style={{ color: "var(--color-fg-muted)" }}
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>

        {/* Query History */}
        <div className="border rounded-xl overflow-hidden flex flex-col flex-1 min-h-0" style={{ borderColor: "var(--color-border)" }}>
          <div
            className="px-4 py-2 border-b flex items-center justify-between"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
          >
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <History size={12} />
              <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                History ({history.length})
              </span>
              {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {history.length > 0 && (
              <button
                onClick={clearHistory}
                className="p-1 rounded hover:bg-red-500/10 transition-colors"
                title="Clear history"
              >
                <Trash2 size={12} className="text-red-500" />
              </button>
            )}
          </div>
          {showHistory && (
            <div className="p-2 space-y-1 overflow-y-auto flex-1">
              {history.length === 0 ? (
                <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>
                  No history yet
                </p>
              ) : (
                history.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setQuery(q)}
                    className="w-full text-left px-3 py-1.5 rounded-lg text-xs font-mono truncate hover:bg-[var(--color-surface-2)] transition-colors"
                    style={{ color: "var(--color-fg-muted)" }}
                    title={q}
                  >
                    {q.split("\n")[0]}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Schema Browser */}
        <div className="border rounded-xl overflow-hidden flex flex-col flex-1 min-h-0" style={{ borderColor: "var(--color-border)" }}>
          <div
            className="px-4 py-2 border-b flex items-center justify-between"
            style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}
          >
            <button
              onClick={() => setShowSchema(!showSchema)}
              className="flex items-center gap-2 hover:opacity-80 transition-opacity"
            >
              <Table2 size={12} />
              <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                Schema ({schema.length} tables)
              </span>
              {showSchema ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
          {showSchema && (
            <div className="p-2 space-y-1 overflow-y-auto flex-1">
              {schema.length === 0 ? (
                <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>
                  Loading schema...
                </p>
              ) : (
                schema.map((table) => (
                  <details key={table.table_name} className="group">
                    <summary className="cursor-pointer px-3 py-2 rounded-lg text-xs hover:bg-[var(--color-surface-2)] transition-colors list-none">
                      <span className="font-medium" style={{ color: "var(--color-fg)" }}>
                        {table.table_name}
                      </span>
                      <span className="ml-2" style={{ color: "var(--color-fg-muted)" }}>
                        ({table.columns.length} cols)
                      </span>
                    </summary>
                    <div className="ml-4 mt-1 space-y-1">
                      {table.columns.map((col) => (
                        <div
                          key={col.column_name}
                          className="px-3 py-1 text-xs font-mono"
                          style={{ color: "var(--color-fg-muted)" }}
                          title={`${col.data_type}${col.nullable ? ", nullable" : ", not null"}${col.default ? `, default: ${col.default}` : ""}`}
                        >
                          <span style={{ color: "var(--color-fg)" }}>{col.column_name}</span>
                          <span className="ml-2 opacity-60">{col.data_type}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col gap-4 min-w-0 min-h-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{ background: "var(--color-accent)", color: "#fff" }}
            >
              <Database size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold">SQL Playground</h1>
              <p className="text-sm" style={{ color: "var(--color-fg-muted)" }}>
                Query Postgres database directly with SQL
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowKeyboardShortcuts(true)}
              className="gap-2"
            >
              <Keyboard size={14} /> Shortcuts
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={formatQuery}
              className="gap-2"
              disabled={!query.trim()}
            >
              <Wand2 size={14} /> Format
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={shareQuery}
              className="gap-2"
              disabled={!query.trim()}
            >
              <Share2 size={14} /> Share
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSaveDialog(true)}
              className="gap-2"
              disabled={!query.trim()}
            >
              <Save size={14} /> Save
            </Button>
            {result?.rows && result.rows.length > 0 && (
              <>
                <Button variant="outline" size="sm" onClick={exportCSV} className="gap-2">
                  <Download size={14} /> CSV
                </Button>
                <Button variant="outline" size="sm" onClick={exportJSON} className="gap-2">
                  <Download size={14} /> JSON
                </Button>
                <Button variant="outline" size="sm" onClick={exportExcel} className="gap-2">
                  <Download size={14} /> Excel
                </Button>
                <Button variant="outline" size="sm" onClick={exportPDF} className="gap-2">
                  <Download size={14} /> PDF
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b" style={{ borderColor: "var(--color-border)" }}>
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`group flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors border-b-2 ${
                tab.id === activeTabId ? "border-[var(--color-accent)]" : "border-transparent hover:border-[var(--color-border)]"
              }`}
              onClick={() => setActiveTabId(tab.id)}
            >
              <span
                className="text-xs font-medium"
                style={{ color: tab.id === activeTabId ? "var(--color-fg)" : "var(--color-fg-muted)" }}
              >
                {tab.name}
              </span>
              {tabs.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tab.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/10 transition-all"
                >
                  <X size={12} className="text-red-500" />
                </button>
              )}
            </div>
          ))}
          <button
            onClick={addNewTab}
            className="p-2 rounded hover:bg-[var(--color-surface-2)] transition-colors"
            title="New tab (Ctrl+T)"
          >
            <Plus size={14} style={{ color: "var(--color-fg-muted)" }} />
          </button>
        </div>

        {/* Editor */}
        <div className="flex flex-col border rounded-xl overflow-hidden shrink-0" style={{ borderColor: "var(--color-border)", height: `${editorHeight}px` }}>
          <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                SQL Query
              </span>
              <button
                onClick={() => copyToClipboard(query)}
                className="p-1 rounded hover:bg-[var(--color-surface)] transition-colors"
                title="Copy query"
              >
                <Copy size={12} />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-surface)", color: "var(--color-fg-muted)" }}>
                Ctrl+Enter to run
              </span>
              <Button
                onClick={executeQuery}
                disabled={loading}
                size="sm"
                className="gap-2"
              >
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Execute
              </Button>
            </div>
          </div>
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleTextareaKeyDown}
            className="flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none"
            style={{ background: "var(--color-surface)", color: "var(--color-fg)" }}
            placeholder="Enter SQL query... (Tab for autocomplete)"
            spellCheck={false}
          />
          <div
            className="h-1 cursor-row-resize hover:bg-[var(--color-accent)] transition-colors"
            style={{ background: isResizing ? "var(--color-accent)" : "transparent" }}
            onMouseDown={handleMouseDown}
          />
        </div>

        {/* Results */}
        {result && (
          <div className="flex-1 flex flex-col border rounded-xl overflow-hidden min-h-0" style={{ borderColor: "var(--color-border)" }}>
            <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
                  Results {result.success && `(${result.row_count} rows)`}
                </span>
                {result.execution_time && (
                  <span className="flex items-center gap-1 text-xs px-2 py-1 rounded" style={{ background: "var(--color-surface)", color: "var(--color-fg-muted)" }}>
                    <Clock size={10} />
                    {result.execution_time.toFixed(0)}ms
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {result.success && result.rows.length > 0 && (
                  <div className="flex items-center gap-1 p-1 rounded" style={{ background: "var(--color-surface)" }}>
                    <button
                      onClick={() => setVisualizationType("table")}
                      className={`p-1 rounded transition-colors ${visualizationType === "table" ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-surface-2)]"}`}
                      title="Table view"
                    >
                      <Database size={12} />
                    </button>
                    <button
                      onClick={() => setVisualizationType("bar")}
                      className={`p-1 rounded transition-colors ${visualizationType === "bar" ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-surface-2)]"}`}
                      title="Bar chart"
                    >
                      <BarChart3 size={12} />
                    </button>
                    <button
                      onClick={() => setVisualizationType("line")}
                      className={`p-1 rounded transition-colors ${visualizationType === "line" ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-surface-2)]"}`}
                      title="Line chart"
                    >
                      <BarChart3 size={12} style={{ transform: "rotate(90deg)" }} />
                    </button>
                    <button
                      onClick={() => setVisualizationType("pie")}
                      className={`p-1 rounded transition-colors ${visualizationType === "pie" ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-surface-2)]"}`}
                      title="Pie chart"
                    >
                      <BarChart3 size={12} style={{ transform: "rotate(45deg)" }} />
                    </button>
                  </div>
                )}
                {result.success ? (
                  <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-accent)", color: "#fff" }}>
                    Success
                  </span>
                ) : (
                  <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-danger)", color: "#fff" }}>
                    Error
                  </span>
                )}
              </div>
            </div>

            {result.error ? (
              <div className="p-4 space-y-3">
                <div className="flex items-start gap-2 p-3 rounded-lg border" style={{ borderColor: "var(--color-danger)", background: "rgba(239, 68, 68, 0.05)" }}>
                  <X size={16} className="text-red-500 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-red-500 mb-1">Query Error</div>
                    <pre className="text-xs font-mono text-red-400 whitespace-pre-wrap break-words">{result.error}</pre>
                  </div>
                </div>
              </div>
            ) : result.rows.length === 0 ? (
              <div className="flex-1 flex items-center justify-center p-8">
                <p className="text-sm italic" style={{ color: "var(--color-fg-muted)" }}>
                  {result.message || "No rows returned"}
                </p>
              </div>
            ) : visualizationType === "table" ? (
              <div className="flex-1 overflow-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0" style={{ background: "var(--color-surface-2)" }}>
                    <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
                      <th className="px-4 py-2 text-left font-bold uppercase w-12" style={{ color: "var(--color-fg-muted)" }}>
                        #
                      </th>
                      {result.columns.map((col) => (
                        <th
                          key={col}
                          className="px-4 py-2 text-left font-bold uppercase"
                          style={{ color: "var(--color-fg-muted)" }}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--color-border)" }}>
                    {result.rows.map((row, i) => (
                      <tr key={i} className="hover:bg-[var(--color-surface-2)] transition-colors group">
                        <td className="px-4 py-2 text-right" style={{ color: "var(--color-fg-muted)" }}>
                          {i + 1}
                        </td>
                        {result.columns.map((col) => (
                          <td
                            key={col}
                            className="px-4 py-2 font-mono max-w-md truncate"
                            style={{ color: "var(--color-fg)" }}
                            title={typeof row[col] === "object" ? JSON.stringify(row[col]) : String(row[col] ?? "")}
                          >
                            {typeof row[col] === "object"
                              ? JSON.stringify(row[col])
                              : String(row[col] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex-1 overflow-auto p-4">
                <ResponsiveContainer width="100%" height="100%">
                  {visualizationType === "bar" ? (
                    <BarChart data={result.rows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={result.columns[0]} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {result.columns.slice(1).map((col, i) => (
                        <Bar key={col} dataKey={col} fill={`hsl(${i * 60}, 70%, 50%)`} />
                      ))}
                    </BarChart>
                  ) : visualizationType === "line" ? (
                    <LineChart data={result.rows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey={result.columns[0]} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {result.columns.slice(1).map((col, i) => (
                        <Line key={col} type="monotone" dataKey={col} stroke={`hsl(${i * 60}, 70%, 50%)`} />
                      ))}
                    </LineChart>
                  ) : (
                    <PieChart>
                      <Pie
                        data={result.rows}
                        dataKey={result.columns[1] || result.columns[0]}
                        nameKey={result.columns[0]}
                        cx="50%"
                        cy="50%"
                        outerRadius={120}
                        label
                      >
                        {result.rows.map((_, i) => (
                          <Cell key={i} fill={`hsl(${i * 360 / result.rows.length}, 70%, 50%)`} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  )}
                </ResponsiveContainer>
              </div>
            )}
          </div>
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
          <div
            className="w-full max-w-md p-6 rounded-xl border"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-bold mb-4">Save Query</h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase mb-2 block" style={{ color: "var(--color-fg-muted)" }}>
                  Query Name
                </label>
                <input
                  type="text"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  placeholder="e.g. Active users report"
                  className="w-full px-3 py-2 rounded-lg border text-sm focus:outline-none focus:border-[var(--color-accent)]"
                  style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg)" }}
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveQuery();
                    if (e.key === "Escape") setShowSaveDialog(false);
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-bold uppercase mb-2 block" style={{ color: "var(--color-fg-muted)" }}>
                  Query Preview
                </label>
                <pre className="text-xs font-mono p-3 rounded-lg border max-h-32 overflow-auto" style={{ background: "var(--color-surface-2)", borderColor: "var(--color-border)", color: "var(--color-fg-muted)" }}>
                  {query}
                </pre>
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
                  Cancel
                </Button>
                <Button onClick={saveQuery} disabled={!saveName.trim()}>
                  Save Query
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Keyboard Shortcuts Modal */}
      {showKeyboardShortcuts && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowKeyboardShortcuts(false)}>
          <div
            className="w-full max-w-lg p-6 rounded-xl border"
            style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">Keyboard Shortcuts</h2>
              <button
                onClick={() => setShowKeyboardShortcuts(false)}
                className="p-1 rounded hover:bg-[var(--color-surface-2)] transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Execute query</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+Enter
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Save query</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+S
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Format query</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+Shift+F
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Share query</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+Shift+S
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Show shortcuts</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+K
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>New tab</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+T
                </kbd>
              </div>
              <div className="flex items-center justify-between py-2" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-sm" style={{ color: "var(--color-fg)" }}>Close tab</span>
                <kbd className="px-2 py-1 rounded text-xs font-mono" style={{ background: "var(--color-surface-2)", color: "var(--color-fg-muted)" }}>
                  Ctrl+W
                </kbd>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
