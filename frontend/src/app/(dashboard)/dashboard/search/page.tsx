// NOTICE: This file is protected under RCF-PL
"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Search,
  Globe,
  BookOpen,
  ExternalLink,
  Loader2,
  AlertCircle,
  Clock,
  Sparkles,
  ChevronRight,
  Newspaper,
  GraduationCap,
  Cpu,
  Layers,
  Zap,
  Shield,
  Copy,
  Check,
  Trash2,
  MessageSquare,
  Bot,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";

/* ── Types ───────────────────────────────────────────────────────── */

interface SearchResult {
  title: string;
  link: string;
  snippet: string;
  source: "duckduckgo" | "wikipedia" | "arxiv" | "news";
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  by_source: Record<string, SearchResult[]>;
  errors: Record<string, string>;
  total: number;
}

interface SynthesizeResponse {
  query: string;
  synthesis: string;
  sources: SearchResult[];
  scraped_urls: string[];
  model?: string | null;
}

type Tab = "all" | "duckduckgo" | "wikipedia" | "news" | "arxiv";

/* ── Helpers ─────────────────────────────────────────────────────── */

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function SourceBadge({ source }: { source: string }) {
  const getBadgeStyle = () => {
    switch (source) {
      case "wikipedia":
        return { bg: "var(--color-surface-2)", color: "var(--color-fg-muted)", icon: <BookOpen size={9} />, label: "Wikipedia" };
      case "arxiv":
        return { bg: "rgba(168, 85, 247, 0.12)", color: "#a855f7", icon: <GraduationCap size={9} />, label: "ArXiv" };
      case "news":
        return { bg: "rgba(239, 68, 68, 0.12)", color: "#ef4444", icon: <Newspaper size={9} />, label: "News" };
      default:
        return { bg: "rgba(var(--color-accent-rgb, 99,102,241), 0.12)", color: "var(--color-accent)", icon: <Globe size={9} />, label: "Web" };
    }
  };

  const style = getBadgeStyle();
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
      style={{
        background: style.bg,
        color: style.color,
      }}
    >
      {style.icon}
      {style.label}
    </span>
  );
}

function ResultCard({ r }: { r: SearchResult }) {
  const [copied, setCopied] = useState(false);

  const copyCitation = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const text = `[${r.title}](${r.link}) - ${r.snippet}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <a
      href={r.link}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl p-4 border transition-all duration-200 hover:shadow-md hover:border-[var(--color-accent)] hover:bg-[var(--color-surface-2)]"
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-border)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <SourceBadge source={r.source} />
            <span
              className="text-[11px] truncate max-w-[200px]"
              style={{ color: "var(--color-fg-muted)" }}
            >
              {hostname(r.link)}
            </span>
          </div>
          <h3
            className="text-[14px] font-semibold leading-snug mb-1.5 group-hover:underline"
            style={{ color: "var(--color-accent)" }}
          >
            {r.title}
          </h3>
          {r.snippet && (
            <p
              className="text-[12px] leading-relaxed line-clamp-3"
              style={{ color: "var(--color-fg-muted)" }}
            >
              {r.snippet}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
          <button
            type="button"
            onClick={copyCitation}
            title="Copy link and citation to clipboard"
            className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all hover:bg-muted/60 text-muted-foreground hover:text-foreground"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          </button>
          <ExternalLink
            size={13}
            className="opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: "var(--color-accent)" }}
          />
        </div>
      </div>
    </a>
  );
}

function EmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div
        className="w-12 h-12 rounded-2xl flex items-center justify-center"
        style={{ background: "var(--color-surface-2)" }}
      >
        <Search size={22} style={{ color: "var(--color-fg-muted)" }} />
      </div>
      <div className="text-center">
        <p className="text-[14px] font-medium" style={{ color: "var(--color-fg)" }}>
          No results for &ldquo;{query}&rdquo;
        </p>
        <p className="text-[12px] mt-1" style={{ color: "var(--color-fg-muted)" }}>
          Try a different query or switch engines
        </p>
      </div>
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────── */

export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [synthesis, setSynthesis] = useState<SynthesizeResponse | null>(null);
  const [synthesisLoading, setSynthesisLoading] = useState(false);
  const [deepScrape, setDeepScrape] = useState(false);
  const [synthCopied, setSynthCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("all");
  const [lang, setLang] = useState("en");
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
    const saved = JSON.parse(localStorage.getItem("aladdin_search_history") || "[]");
    setHistory(saved.slice(0, 6));
  }, []);

  const deleteHistoryItem = (hToRemove: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = history.filter((h) => h !== hToRemove);
    setHistory(updated);
    localStorage.setItem("aladdin_search_history", JSON.stringify(updated));
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem("aladdin_search_history");
  };

  const sendToChat = () => {
    if (!query) return;
    const summaryText = synthesis?.synthesis || results?.results.slice(0, 3).map((r) => `- [${r.title}](${r.link}): ${r.snippet}`).join("\n") || "";
    const initialPrompt = `Analyze web search results for "${query}":\n\n${summaryText}`;
    sessionStorage.setItem("aladdin_pending_chat_prompt", initialPrompt);
    router.push("/dashboard/chat");
  };

  const copySynthText = () => {
    if (!synthesis?.synthesis) return;
    navigator.clipboard.writeText(synthesis.synthesis);
    setSynthCopied(true);
    setTimeout(() => setSynthCopied(false), 2000);
  };

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setDraftQuery(q);
    setLoading(true);
    setError(null);
    setResults(null);
    setSynthesis(null);
    setTab("all");
    const t0 = performance.now();

    // Save to history
    const updated = [q, ...history.filter((h) => h !== q)].slice(0, 6);
    setHistory(updated);
    localStorage.setItem("aladdin_search_history", JSON.stringify(updated));

    try {
      const data = await api.get<SearchResponse>(
        `/websearch?q=${encodeURIComponent(q)}&lang=${lang}&limit=15`
      );
      setResults(data);
      setElapsed(Math.round(performance.now() - t0));

      // Trigger AI Synthesis
      setSynthesisLoading(true);
      api.post<SynthesizeResponse>("/websearch/synthesize", {
        query: q,
        deep: deepScrape,
        lang,
      })
        .then((synthData) => setSynthesis(synthData))
        .catch((err) => console.error("AI Synthesis error:", err))
        .finally(() => setSynthesisLoading(false));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [history, lang, deepScrape]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (draftQuery.trim()) doSearch(draftQuery.trim());
  };

  // Filtered results by tab
  const displayed: SearchResult[] = (() => {
    if (!results) return [];
    if (tab === "all") return results.results;
    return results.by_source[tab] ?? [];
  })();

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "all", label: "All", icon: <Sparkles size={12} /> },
    { key: "duckduckgo", label: "Web", icon: <Globe size={12} /> },
    { key: "wikipedia", label: "Wikipedia", icon: <BookOpen size={12} /> },
    { key: "news", label: "News", icon: <Newspaper size={12} /> },
    { key: "arxiv", label: "Research", icon: <GraduationCap size={12} /> },
  ];

  return (
    <div
      className="flex flex-col h-full"
      style={{ background: "var(--color-bg, #0f0f13)" }}
    >
      {/* ── Header / Search bar ────────────────────────────────────── */}
      <div
        className="px-6 pt-8 pb-5 border-b"
        style={{ borderColor: "var(--color-border)" }}
      >
        <div className="max-w-3xl mx-auto">
          {/* Title */}
          {!results && !loading && (
            <div className="text-center mb-8">
              <div className="flex items-center justify-center gap-2 mb-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold"
                  style={{ background: "var(--color-accent)", color: "#fff" }}
                >
                  A
                </div>
                <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: "var(--color-fg)" }}>
                  AladdinAI Search
                  <Shield size={16} className="text-emerald-400 opacity-80" title="RCF Protected Meta-Search Engine" />
                </h1>
              </div>
              <p className="text-[13px]" style={{ color: "var(--color-fg-muted)" }}>
                Native Meta-Search & AI Synthesis Engine · Chromium Deep Scraping Enabled
              </p>
            </div>
          )}

          {/* Search input */}
          <form onSubmit={handleSubmit}>
            <div
              className="flex items-center gap-3 rounded-2xl px-4 py-3 border transition-all"
              style={{
                background: "var(--color-surface)",
                borderColor: "var(--color-border)",
              }}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--color-accent)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor = "var(--color-border)")
              }
            >
              <Search size={17} style={{ color: "var(--color-fg-muted)", flexShrink: 0 }} />
              <input
                ref={inputRef}
                id="search-input"
                type="text"
                value={draftQuery}
                onChange={(e) => setDraftQuery(e.target.value)}
                placeholder="Ask anything or search the web…"
                className="flex-1 bg-transparent outline-none text-[14px] placeholder:text-[var(--color-fg-muted)]"
                style={{ color: "var(--color-fg)" }}
                autoComplete="off"
              />

              {/* Deep Scrape toggle */}
              <button
                type="button"
                onClick={() => setDeepScrape(!deepScrape)}
                title="Deep Web Scraping: uses Playwright Chromium to extract full content from top links"
                className={`flex items-center gap-1 text-[11px] font-medium rounded-lg px-2.5 py-1 border transition-all ${
                  deepScrape
                    ? "bg-purple-950/60 text-purple-300 border-purple-500/50 shadow-sm"
                    : "bg-muted/40 text-muted-foreground border-border/40 hover:text-foreground"
                }`}
              >
                <Cpu size={12} className={deepScrape ? "text-purple-400 animate-pulse" : ""} />
                <span>Deep Scrape</span>
              </button>

              {/* Lang selector */}
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="text-[11px] rounded-lg px-2 py-1 border outline-none cursor-pointer"
                style={{
                  background: "var(--color-surface-2)",
                  borderColor: "var(--color-border)",
                  color: "var(--color-fg-muted)",
                }}
              >
                <option value="en">EN</option>
                <option value="ru">RU</option>
                <option value="de">DE</option>
                <option value="fr">FR</option>
                <option value="es">ES</option>
              </select>
              <button
                type="submit"
                disabled={!draftQuery.trim() || loading}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-[12px] font-semibold transition-all disabled:opacity-40"
                style={{
                  background: "var(--color-accent)",
                  color: "#fff",
                }}
              >
                {loading ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <>Search <ChevronRight size={13} /></>
                )}
              </button>
            </div>
          </form>

          {/* History chips (shown when no results yet) */}
          {!results && !loading && history.length > 0 && (
            <div className="flex items-center justify-between flex-wrap gap-2 mt-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex items-center gap-1 text-[11px]" style={{ color: "var(--color-fg-muted)" }}>
                  <Clock size={11} /> Recent:
                </span>
                {history.map((h) => (
                  <div
                    key={h}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] border transition-all hover:border-[var(--color-accent)]"
                    style={{
                      background: "var(--color-surface)",
                      borderColor: "var(--color-border)",
                      color: "var(--color-fg-muted)",
                    }}
                  >
                    <button onClick={() => doSearch(h)} className="hover:underline">
                      {h}
                    </button>
                    <button
                      onClick={(e) => deleteHistoryItem(h, e)}
                      title="Remove from history"
                      className="ml-0.5 hover:text-red-400 opacity-60 hover:opacity-100 transition-opacity"
                    >
                      <X size={10} />
                    </button>
                  </div>
                ))}
              </div>
              <button
                onClick={clearHistory}
                className="text-[10px] text-muted-foreground hover:text-red-400 flex items-center gap-1 transition-colors"
                title="Clear all search history"
              >
                <Trash2 size={10} /> Clear history
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Results area ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto">

          {/* Meta info + tabs */}
          {results && (
            <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                {tabs.map((t) => {
                  const count =
                    t.key === "all"
                      ? results.total
                      : (results.by_source[t.key]?.length ?? 0);
                  const active = tab === t.key;
                  return (
                    <button
                      key={t.key}
                      onClick={() => setTab(t.key)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-medium border transition-all"
                      style={{
                        background: active ? "var(--color-accent)" : "var(--color-surface)",
                        borderColor: active ? "var(--color-accent)" : "var(--color-border)",
                        color: active ? "#fff" : "var(--color-fg-muted)",
                      }}
                    >
                      {t.icon}
                      {t.label}
                      <span
                        className="text-[10px] font-bold px-1 rounded"
                        style={{
                          background: active ? "rgba(255,255,255,0.2)" : "var(--color-surface-2)",
                        }}
                      >
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px]" style={{ color: "var(--color-fg-muted)" }}>
                  {results.total} results · {elapsed}ms
                  {Object.keys(results.errors).length > 0 && (
                    <span className="ml-2 text-yellow-500">
                      ⚠ {Object.keys(results.errors).join(", ")} failed
                    </span>
                  )}
                </span>
                <button
                  onClick={sendToChat}
                  title="Transfer query and search findings directly into Agent Chat"
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium border bg-indigo-500/10 text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/20 transition-all"
                >
                  <Bot size={12} />
                  <span>Send to Agent</span>
                </button>
              </div>
            </div>
          )}

          {/* AI Synthesis Box */}
          {(synthesisLoading || synthesis) && tab === "all" && (
            <div
              className="rounded-2xl p-5 border mb-6 shadow-lg transition-all"
              style={{
                background: "linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(168, 85, 247, 0.05), rgba(6, 182, 212, 0.05))",
                borderColor: "var(--color-accent)",
              }}
            >
              <div className="flex items-center justify-between border-b pb-3 mb-3" style={{ borderColor: "var(--color-border)" }}>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-sm">
                    <Sparkles size={13} />
                  </div>
                  <span className="text-[13px] font-semibold tracking-wide" style={{ color: "var(--color-fg)" }}>
                    AI Synthesis
                  </span>
                  {synthesis?.model && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-medium" style={{ background: "var(--color-surface-2)", color: "var(--color-accent)" }}>
                      {synthesis.model}
                    </span>
                  )}
                  {synthesis?.scraped_urls && synthesis.scraped_urls.length > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/50 flex items-center gap-1">
                      <Cpu size={10} /> Chromium Scraped ({synthesis.scraped_urls.length})
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {synthesis?.synthesis && (
                    <>
                      <button
                        onClick={copySynthText}
                        title="Copy AI Synthesis answer"
                        className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-surface border text-muted-foreground hover:text-foreground transition-all"
                      >
                        {synthCopied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                        <span>{synthCopied ? "Copied" : "Copy"}</span>
                      </button>
                      <button
                        onClick={sendToChat}
                        title="Discuss this synthesis with an AI Agent in Chat"
                        className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-500 transition-all shadow-sm"
                      >
                        <MessageSquare size={11} />
                        <span>Discuss with Agent</span>
                      </button>
                    </>
                  )}
                  {synthesisLoading && (
                    <div className="flex items-center gap-2 text-xs text-indigo-400 font-medium animate-pulse">
                      <Loader2 size={13} className="animate-spin" />
                      Synthesizing answer...
                    </div>
                  )}
                </div>
              </div>

              {synthesisLoading && !synthesis && (
                <div className="space-y-2 py-2">
                  <div className="h-3.5 rounded w-full animate-pulse" style={{ background: "var(--color-surface-2)" }} />
                  <div className="h-3.5 rounded w-5/6 animate-pulse" style={{ background: "var(--color-surface-2)" }} />
                  <div className="h-3.5 rounded w-4/6 animate-pulse" style={{ background: "var(--color-surface-2)" }} />
                </div>
              )}

              {synthesis && (
                <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed text-[13px]">
                  <ReactMarkdown>{synthesis.synthesis}</ReactMarkdown>
                </div>
              )}
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl p-4 border animate-pulse"
                  style={{
                    background: "var(--color-surface)",
                    borderColor: "var(--color-border)",
                  }}
                >
                  <div className="h-3 rounded w-1/4 mb-3" style={{ background: "var(--color-surface-2)" }} />
                  <div className="h-4 rounded w-3/4 mb-2" style={{ background: "var(--color-surface-2)" }} />
                  <div className="h-3 rounded w-full mb-1" style={{ background: "var(--color-surface-2)" }} />
                  <div className="h-3 rounded w-5/6" style={{ background: "var(--color-surface-2)" }} />
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              className="flex items-center gap-3 rounded-xl p-4 border"
              style={{
                background: "rgba(239,68,68,0.08)",
                borderColor: "rgba(239,68,68,0.3)",
                color: "#ef4444",
              }}
            >
              <AlertCircle size={16} />
              <div>
                <p className="text-[13px] font-semibold">Search failed</p>
                <p className="text-[12px] opacity-80">{error}</p>
              </div>
            </div>
          )}

          {/* Results list */}
          {!loading && results && displayed.length === 0 && (
            <EmptyState query={query} />
          )}

          {!loading && displayed.length > 0 && (
            <div className="space-y-2.5">
              {displayed.map((r, i) => (
                <ResultCard key={`${r.source}-${i}`} r={r} />
              ))}
            </div>
          )}

          {/* Empty landing */}
          {!loading && !results && !error && history.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 gap-3">
              <div
                className="w-16 h-16 rounded-3xl flex items-center justify-center"
                style={{ background: "var(--color-surface)" }}
              >
                <Globe size={30} style={{ color: "var(--color-accent)" }} />
              </div>
              <p className="text-[14px] font-medium" style={{ color: "var(--color-fg)" }}>
                Search the web from AladdinAI
              </p>
              <p className="text-[12px] text-center max-w-xs" style={{ color: "var(--color-fg-muted)" }}>
                Powered by DuckDuckGo and Wikipedia. No external gateway, no API key needed.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
