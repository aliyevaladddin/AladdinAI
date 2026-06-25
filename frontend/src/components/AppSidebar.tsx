// NOTICE: This file is protected under RCF-PL
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Mailbox,
  Bot,
  Zap,
  Settings,
  Sparkles,
} from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
};

const mainNav: NavItem[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/comms", label: "Conversations", icon: MessageSquare },
  { href: "/dashboard/mail", label: "Mail", icon: Mailbox },
  { href: "/dashboard/agents", label: "Agents", icon: Bot },
  { href: "/dashboard/automations", label: "Automations", icon: Zap },
  { href: "/dashboard/crm", label: "CRM", icon: Users },
  { href: "/dashboard/chat", label: "Playground", icon: Sparkles },
];


export function AppSidebar() {
  const pathname = usePathname();


  const isActive = (href: string) =>
    href === "/dashboard"
      ? pathname === "/dashboard"
      : pathname.startsWith(href);

  return (
    <aside
      className="flex flex-col w-56 shrink-0 h-full border-r"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      {/* Logo */}
      <div className="px-4 py-4 flex items-center gap-2.5 border-b" style={{ borderColor: "var(--color-border)" }}>
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-bold"
          style={{ background: "var(--color-accent)", color: "#fff" }}
        >
          A
        </div>
        <span className="text-[15px] font-semibold tracking-tight">AladdinAI</span>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        <ul className="space-y-0.5">
          {mainNav.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
                  style={{
                    background: active ? "var(--color-surface-2)" : "transparent",
                    color: active ? "var(--color-fg)" : "var(--color-fg-muted)",
                  }}
                >
                  <Icon
                    size={15}
                    className={active ? "text-[var(--color-accent)]" : ""}
                  />
                  <span>{item.label}</span>
                  {active && (
                    <span
                      className="ml-auto w-1.5 h-1.5 rounded-full"
                      style={{ background: "var(--color-accent)" }}
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Divider + Settings */}
      <div className="px-3 pb-4 border-t pt-3" style={{ borderColor: "var(--color-border)" }}>
        <Link
          href="/dashboard/settings"
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all"
          style={{
            background: isActive("/dashboard/settings") ? "var(--color-surface-2)" : "transparent",
            color: isActive("/dashboard/settings") ? "var(--color-fg)" : "var(--color-fg-muted)",
          }}
        >
          <Settings size={15} className={isActive("/dashboard/settings") ? "text-[var(--color-accent)]" : ""} />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
