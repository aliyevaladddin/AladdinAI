"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search, LogOut, User as UserIcon, Bell, Zap, Mail, Info, Check } from "lucide-react";
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

export function AppHeader() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotifItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLDivElement>(null);

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
    const interval = setInterval(fetchUnread, 15000); // poll every 15s
    return () => clearInterval(interval);
  }, [fetchUnread]);

  useEffect(() => {
    if (bellOpen) fetchNotifs();
  }, [bellOpen, fetchNotifs]);

  useEffect(() => {
    if (!menuOpen && !bellOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setBellOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen, bellOpen]);

  const markRead = async (id: number) => {
    await api.post(`/notifications/${id}/read`);
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    setUnreadCount((c) => Math.max(0, c - 1));
  };

  const markAllRead = async () => {
    await api.post("/notifications/read-all");
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((s) => s[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "U";

  const categoryIcon = (cat: string) => {
    switch (cat) {
      case "trigger": return <Zap size={12} className="text-orange-400" />;
      case "email": return <Mail size={12} className="text-blue-400" />;
      default: return <Info size={12} className="text-[var(--color-fg-muted)]" />;
    }
  };

  return (
    <header
      className="h-14 shrink-0 flex items-center justify-between px-5 border-b"
      style={{ background: "var(--color-bg)", borderColor: "var(--color-border)" }}
    >
      <div className="relative flex-1 max-w-md">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2"
          style={{ color: "var(--color-fg-subtle)" }}
        />
        <input
          placeholder="Search contacts, deals, conversations..."
          className="w-full pl-9 pr-3 py-1.5 text-[13px] rounded-md outline-none transition-colors"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-fg)",
          }}
        />
      </div>

      <div className="flex items-center gap-2">
        {/* Notification Bell */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen(!bellOpen)}
            className="relative p-2 rounded-md transition-colors hover:bg-[var(--color-surface)]"
          >
            <Bell size={18} style={{ color: "var(--color-fg-muted)" }} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center text-[9px] font-bold rounded-full bg-red-500 text-white px-1">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {bellOpen && (
            <div
              className="absolute right-0 top-full mt-1 w-80 rounded-xl shadow-2xl overflow-hidden z-50"
              style={{
                background: "var(--color-surface-1)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "var(--color-border)" }}>
                <span className="text-[11px] font-bold uppercase tracking-widest" style={{ color: "var(--color-fg-muted)" }}>
                  Notifications
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="text-[10px] font-bold uppercase text-[var(--color-accent)] hover:underline flex items-center gap-1"
                  >
                    <Check size={10} /> Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center">
                    <Bell size={20} className="mx-auto mb-2 opacity-20" />
                    <p className="text-[11px] italic" style={{ color: "var(--color-fg-subtle)" }}>
                      No notifications yet
                    </p>
                  </div>
                ) : (
                  notifications.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => {
                        if (!n.is_read) markRead(n.id);
                        if (n.link) window.location.href = n.link;
                      }}
                      className="w-full text-left px-4 py-3 flex gap-3 transition-colors hover:bg-[var(--color-surface-2)] border-b"
                      style={{
                        borderColor: "var(--color-border)",
                        opacity: n.is_read ? 0.5 : 1,
                      }}
                    >
                      <div className="mt-0.5 shrink-0">{categoryIcon(n.category)}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-semibold truncate">{n.title}</p>
                        <p className="text-[11px] mt-0.5 line-clamp-2" style={{ color: "var(--color-fg-muted)" }}>
                          {n.body}
                        </p>
                        {n.created_at && (
                          <p className="text-[9px] mt-1 font-mono" style={{ color: "var(--color-fg-subtle)" }}>
                            {new Date(n.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                          </p>
                        )}
                      </div>
                      {!n.is_read && (
                        <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] shrink-0 mt-1.5" />
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-md transition-colors"
            style={{
              background: menuOpen ? "var(--color-surface)" : "transparent",
            }}
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold"
              style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
            >
              {initials}
            </div>
            <div className="text-left hidden sm:block">
              <p className="text-[12px] leading-tight">{user?.name}</p>
              <p
                className="text-[11px] leading-tight"
                style={{ color: "var(--color-fg-subtle)" }}
              >
                {user?.email}
              </p>
            </div>
          </button>

          {menuOpen && (
            <div
              className="absolute right-0 top-full mt-1 w-48 rounded-md shadow-lg overflow-hidden z-50"
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
              }}
            >
              <button
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-left transition-colors hover:bg-[var(--color-surface-2)]"
                style={{ color: "var(--color-fg-muted)" }}
              >
                <UserIcon size={14} /> Profile
              </button>
              <button
                onClick={logout}
                className="w-full flex items-center gap-2 px-3 py-2 text-[13px] text-left transition-colors border-t hover:bg-[var(--color-surface-2)]"
                style={{ color: "var(--color-danger)", borderColor: "var(--color-border)" }}
              >
                <LogOut size={14} /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
