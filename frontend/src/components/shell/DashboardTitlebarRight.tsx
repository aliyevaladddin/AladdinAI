"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LogOut,
  User as UserIcon,
  Bell,
  Zap,
  Mail,
  Info,
  Check,
  Users,
  Briefcase,
  MessageSquare,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
import { api } from "@/lib/api";

interface NotifItem {
  id: number;
  title: string;
  body: string;
  category: string;
  is_read: boolean;
  link: string | null;
  created_at: string | null;
}

interface SearchResult {
  kind: "contact" | "deal" | "activity";
  id: number;
  title: string;
  subtitle: string | null;
  snippet: string | null;
  contact_id: number | null;
  activity_type: string | null;
  channel: string | null;
  created_at: string | null;
}

interface SearchResponse {
  contacts: SearchResult[];
  deals: SearchResult[];
  activities: SearchResult[];
  total: number;
}

/**
 * Right-side titlebar cluster for the authenticated dashboard:
 *   [ search ⌘K ] [ bell ] [ avatar ▾ ]
 *
 * Migrated from the legacy AppHeader to live inside the 44px titlebar.
 * Theme picker is rendered separately by Titlebar.tsx.
 */
export function DashboardTitlebarRight() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotifItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLDivElement>(null);

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchUnread = useCallback(() => {
    api.get<{ count: number }>("/notifications/unread-count")
      .then((r) => setUnreadCount(r.count))
      .catch(() => {});
  }, []);

  const fetchNotifs = useCallback(() => {
    api.get<NotifItem[]>("/notifications?limit=10")
      .then(setNotifications)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 15000);
    return () => clearInterval(interval);
  }, [fetchUnread]);

  useEffect(() => {
    if (bellOpen) fetchNotifs();
  }, [bellOpen, fetchNotifs]);

  useEffect(() => {
    if (!menuOpen && !bellOpen && !searchOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuOpen && menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
      if (bellOpen && bellRef.current && !bellRef.current.contains(e.target as Node)) setBellOpen(false);
      if (searchOpen && searchRef.current && !searchRef.current.contains(e.target as Node)) setSearchOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen, bellOpen, searchOpen]);

  useEffect(() => {
    const q = searchQuery.trim();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q) {
      // Async tick — keeps us out of React's set-state-in-effect warning while
      // still resetting state when the user clears the query.
      const tid = setTimeout(() => {
        setSearchResults(null);
        setSearchLoading(false);
      }, 0);
      return () => clearTimeout(tid);
    }
    const loadingTid = setTimeout(() => setSearchLoading(true), 0);
    debounceRef.current = setTimeout(() => {
      api
        .get<SearchResponse>(`/search?q=${encodeURIComponent(q)}&limit=6`)
        .then(setSearchResults)
        .catch(() => setSearchResults({ contacts: [], deals: [], activities: [], total: 0 }))
        .finally(() => setSearchLoading(false));
    }, 220);
    return () => {
      clearTimeout(loadingTid);
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  // ⌘K / Ctrl+K → focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleResult = (r: SearchResult) => {
    setSearchOpen(false);
    setSearchQuery("");
    setSearchResults(null);
    if (r.kind === "contact") router.push(`/dashboard/contacts/${r.id}`);
    else if (r.kind === "deal") router.push("/dashboard/deals");
    else if (r.kind === "activity") {
      if (r.activity_type?.startsWith("email")) router.push("/dashboard/mail");
      else router.push("/dashboard/comms");
    }
  };

  const markAllRead = async () => {
    await api.post("/notifications/read-all");
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  const markRead = async (id: number) => {
    await api.post(`/notifications/${id}/read`);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  };

  const initials = user?.name
    ? user.name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()
    : "U";

  const categoryIcon = (cat: string) => {
    switch (cat) {
      case "trigger": return <Zap size={12} className="text-orange-400" />;
      case "email":   return <Mail size={12} className="text-blue-400" />;
      default:        return <Info size={12} style={{ color: "var(--fg-3)" }} />;
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* Search */}
      <div ref={searchRef} className="relative">
        {!searchOpen ? (
          <button
            type="button"
            className="theme-trigger"
            style={{ width: 220, gap: 8, justifyContent: "flex-start" }}
            onClick={() => {
              setSearchOpen(true);
              setTimeout(() => searchInputRef.current?.focus(), 0);
            }}
            aria-label="Search"
          >
            <Search size={13} style={{ color: "var(--fg-3)" }} />
            <span style={{ color: "var(--fg-3)", flex: 1, textAlign: "left" }}>
              Jump to agent, contact…
            </span>
            <kbd
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10.5,
                color: "var(--fg-4)",
                background: "var(--bg-3)",
                border: "1px solid var(--line)",
                borderRadius: 5,
                padding: "1px 5px",
              }}
            >
              ⌘K
            </kbd>
          </button>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              height: 28,
              width: 280,
              padding: "0 10px",
              background: "var(--bg-2)",
              border: "1px solid var(--violet-line)",
              borderRadius: "var(--r-md)",
              boxShadow: "0 0 0 3px var(--violet-soft)",
            }}
          >
            <Search size={13} style={{ color: "var(--fg-3)" }} />
            <input
              ref={searchInputRef}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setSearchOpen(false);
                  setSearchQuery("");
                  (e.target as HTMLInputElement).blur();
                }
              }}
              placeholder="Jump to agent, contact, deal…"
              style={{
                flex: 1,
                fontSize: 12.5,
                color: "var(--fg)",
                background: "transparent",
                border: 0,
                outline: "none",
              }}
            />
            {searchLoading && <Loader2 size={12} className="animate-spin" style={{ color: "var(--fg-3)" }} />}
          </div>
        )}

        {searchOpen && searchQuery.trim() && (
          <div
            className="theme-menu"
            style={{ width: 360, padding: 0, maxHeight: "60vh" }}
            role="listbox"
          >
            {!searchResults && searchLoading && (
              <div style={{ padding: "20px 16px", textAlign: "center", fontSize: 12, color: "var(--fg-3)" }}>
                Searching…
              </div>
            )}
            {searchResults && searchResults.total === 0 && !searchLoading && (
              <div style={{ padding: "20px 16px", textAlign: "center", fontSize: 12, fontStyle: "italic", color: "var(--fg-3)" }}>
                No results for &quot;{searchQuery.trim()}&quot;
              </div>
            )}
            {searchResults && searchResults.total > 0 && (
              <>
                <SearchGroup label="Contacts" icon={<Users size={11} />} results={searchResults.contacts} onClick={handleResult} />
                <SearchGroup label="Deals" icon={<Briefcase size={11} />} results={searchResults.deals} onClick={handleResult} />
                <SearchGroup label="Conversations" icon={<MessageSquare size={11} />} results={searchResults.activities} onClick={handleResult} />
              </>
            )}
          </div>
        )}
      </div>

      {/* Bell */}
      <div ref={bellRef} className="relative">
        <button
          type="button"
          className="icon-btn"
          aria-label="Notifications"
          aria-haspopup="menu"
          aria-expanded={bellOpen}
          onClick={() => setBellOpen(!bellOpen)}
          style={{ position: "relative" }}
        >
          <Bell size={15} />
          {unreadCount > 0 && (
            <span
              style={{
                position: "absolute",
                top: -2,
                right: -2,
                minWidth: 16,
                height: 14,
                padding: "0 4px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 9,
                fontWeight: 700,
                color: "var(--bg-0)",
                background: "var(--err)",
                borderRadius: 999,
                boxShadow: "0 0 0 2px var(--bg-0)",
              }}
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        {bellOpen && (
          <div className="theme-menu" style={{ width: 320 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "8px 10px 6px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fg-3)" }}>
                Notifications
              </span>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={markAllRead}
                  style={{
                    background: "transparent",
                    border: 0,
                    cursor: "pointer",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "var(--violet)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <Check size={10} /> Mark all read
                </button>
              )}
            </div>
            <div style={{ maxHeight: 320, overflowY: "auto" }}>
              {notifications.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center" }}>
                  <Bell size={18} style={{ opacity: 0.2, margin: "0 auto 6px" }} />
                  <p style={{ fontSize: 11, fontStyle: "italic", color: "var(--fg-3)" }}>No notifications yet</p>
                </div>
              ) : (
                notifications.map((n) => (
                  <button
                    key={n.id}
                    type="button"
                    onClick={() => {
                      if (!n.is_read) markRead(n.id);
                      if (n.link) window.location.href = n.link;
                    }}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "10px 12px",
                      display: "flex",
                      gap: 10,
                      background: "transparent",
                      border: 0,
                      borderBottom: "1px solid var(--line)",
                      cursor: "pointer",
                      opacity: n.is_read ? 0.55 : 1,
                      color: "var(--fg)",
                    }}
                  >
                    <span style={{ marginTop: 2, flexShrink: 0 }}>{categoryIcon(n.category)}</span>
                    <span style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {n.title}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--fg-2)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", marginTop: 2 }}>
                        {n.body}
                      </span>
                      {n.created_at && (
                        <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--fg-3)", display: "block", marginTop: 4 }}>
                          {new Date(n.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                        </span>
                      )}
                    </span>
                    {!n.is_read && <span style={{ width: 7, height: 7, borderRadius: 999, background: "var(--violet)", marginTop: 6, flexShrink: 0 }} />}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Avatar / user menu */}
      <div ref={menuRef} className="relative">
        <button
          type="button"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          aria-label="User menu"
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--violet), var(--amber))",
            color: "#1a1024",
            border: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {initials}
        </button>

        {menuOpen && (
          <div className="theme-menu" style={{ width: 200 }}>
            <div
              style={{
                padding: "8px 10px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--fg)" }}>{user?.name}</div>
              <div style={{ fontSize: 10.5, color: "var(--fg-3)", marginTop: 2 }}>{user?.email}</div>
            </div>
            <button type="button" className="theme-opt" style={{ width: "100%" }}>
              <UserIcon size={14} />
              <span className="name" style={{ marginLeft: 4 }}>Profile</span>
            </button>
            <button
              type="button"
              onClick={logout}
              className="theme-opt"
              style={{ width: "100%", color: "var(--err)" }}
            >
              <LogOut size={14} />
              <span className="name" style={{ marginLeft: 4, color: "var(--err)" }}>Sign out</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SearchGroup({
  label,
  icon,
  results,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  results: SearchResult[];
  onClick: (r: SearchResult) => void;
}) {
  if (results.length === 0) return null;
  return (
    <div style={{ borderBottom: "1px solid var(--line)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 12px",
          fontSize: 10,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "var(--fg-3)",
          background: "var(--bg-3)",
        }}
      >
        {icon}
        {label}
        <span style={{ opacity: 0.6 }}>({results.length})</span>
      </div>
      {results.map((r) => (
        <button
          key={`${r.kind}-${r.id}`}
          type="button"
          onClick={() => onClick(r)}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            width: "100%",
            textAlign: "left",
            padding: "8px 12px",
            background: "transparent",
            border: 0,
            cursor: "pointer",
            color: "var(--fg)",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-3)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <span style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <span style={{ fontSize: 12.5, fontWeight: 500, color: "var(--fg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.title}
            </span>
            {r.subtitle && (
              <span style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--fg-4)", flexShrink: 0 }}>
                {r.subtitle}
              </span>
            )}
          </span>
          {r.snippet && (
            <span style={{ fontSize: 11, color: "var(--fg-2)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {r.snippet}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
