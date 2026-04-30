"use client";

import { useState, useRef, useEffect } from "react";
import { Search, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";

export function AppHeader() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((s) => s[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "U";

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
    </header>
  );
}
