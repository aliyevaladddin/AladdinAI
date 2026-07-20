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
} from "lucide-react";
import { api } from "@/lib/api";

/* ── Types ───────────────────────────────────────────────────────── */

interface SearchResult {
  title: string;
  link: string;
  snippet: string;
  source: "duckduckgo" | "wikipedia";
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
  by_source: Record<string, SearchResult[]>;
  errors: Record<string, string>;
  total: number;
}

type Tab = "all" | "duckduckgo" | "wikipedia";

/* ── Helpers ─────────────────────────────────────────────────────── */

function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function SourceBadge({ source }: { source: string }) {
  const isWiki = source === "wikipedia";
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
      style={{
        background: isWiki ? "var(--color-surface-2)" : "rgba(var(--color-accent-rgb, 99,102,241), 0.12)",
        color: isWiki ? "var(--color-fg-muted)" : "var(--color-accent)",
      }}
    >
      {isWiki ? <BookOpen size={9} /> : <Globe size={9} />}
      {isWiki ? "Wikipedia" : "Web"}
    </span>
  );
}

function ResultCard({ r }: { r: SearchResult }) {
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
        <ExternalLink
          size={13}
          className="shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ color: "var(--color-accent)" }}
        />
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
  const [query, setQuery] = useState("");
  const [draftQuery, setDraftQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
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

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setQuery(q);
    setDraftQuery(q);
    setLoading(true);
    setError(null);
    setResults(null);
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [history, lang]);

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
                <h1 className="text-2xl font-bold" style={{ color: "var(--color-fg)" }}>
                  AladdinAI Search
                </h1>
              </div>
              <p className="text-[13px]" style={{ color: "var(--color-fg-muted)" }}>
                Native meta-search · DuckDuckGo + Wikipedia · No external gateway
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
                placeholder="Search the web…"
                className="flex-1 bg-transparent outline-none text-[14px] placeholder:text-[var(--color-fg-muted)]"
                style={{ color: "var(--color-fg)" }}
                autoComplete="off"
              />
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
            <div className="flex flex-wrap gap-2 mt-4">
              <span className="flex items-center gap-1 text-[11px]" style={{ color: "var(--color-fg-muted)" }}>
                <Clock size={11} /> Recent:
              </span>
              {history.map((h) => (
                <button
                  key={h}
                  onClick={() => doSearch(h)}
                  className="px-3 py-1 rounded-full text-[11px] border transition-all hover:border-[var(--color-accent)]"
                  style={{
                    background: "var(--color-surface)",
                    borderColor: "var(--color-border)",
                    color: "var(--color-fg-muted)",
                  }}
                >
                  {h}
                </button>
              ))}
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
              <span className="text-[11px]" style={{ color: "var(--color-fg-muted)" }}>
                {results.total} results · {elapsed}ms
                {Object.keys(results.errors).length > 0 && (
                  <span className="ml-2 text-yellow-500">
                    ⚠ {Object.keys(results.errors).join(", ")} failed
                  </span>
                )}
              </span>
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
