"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  MessageSquare,
  Bot,
  Webhook,
  Network,
  Cloud,
  Database,
  Cpu,
  Sparkles,
  Settings,
  Terminal,
} from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
};

type NavSection = {
  label: string | null;
  items: NavItem[];
};

const sections: NavSection[] = [
  {
    label: null,
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
    ],
  },
  {
    label: "CRM",
    items: [
      { href: "/dashboard/crm", label: "Contacts", icon: Users },
      { href: "/dashboard/deals", label: "Deals", icon: TrendingUp },
    ],
  },
  {
    label: "Communication",
    items: [
      { href: "/dashboard/comms", label: "Inbox", icon: MessageSquare },
      { href: "/dashboard/channels", label: "Channels", icon: Network },
      { href: "/dashboard/webhooks", label: "Webhooks", icon: Webhook },
      { href: "/terminal", label: "Terminal", icon: Terminal },
    ],
  },
  {
    label: "AI",
    items: [
      { href: "/dashboard/agents", label: "Agents", icon: Bot },
      { href: "/dashboard/chat", label: "Playground", icon: Sparkles },
      { href: "/dashboard/router", label: "Routing", icon: Settings },
    ],
  },
  {
    label: "Infrastructure",
    items: [
      { href: "/dashboard/providers", label: "LLM Providers", icon: Cpu },
      { href: "/dashboard/vms", label: "Cloud VMs", icon: Cloud },
      { href: "/dashboard/mongodb", label: "MongoDB", icon: Database },
      { href: "/dashboard/bentoml", label: "BentoML", icon: Cpu },
    ],
  },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex flex-col w-60 shrink-0 h-full border-r"
      style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="px-5 py-4 flex items-center gap-2.5">
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center text-sm font-semibold"
          style={{ background: "var(--color-fg)", color: "var(--color-bg)" }}
        >
          A
        </div>
        <span className="text-[15px] font-semibold tracking-tight">AladdinAI</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-5">
        {sections.map((section, idx) => (
          <div key={idx}>
            {section.label && (
              <p
                className="px-2 mb-1.5 text-[11px] font-medium uppercase tracking-wider"
                style={{ color: "var(--color-fg-subtle)" }}
              >
                {section.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active =
                  pathname === item.href ||
                  (item.href !== "/dashboard" && pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="flex items-center gap-2.5 px-2 py-1.5 rounded-md text-[13px] transition-colors"
                      style={{
                        background: active ? "var(--color-surface-2)" : "transparent",
                        color: active ? "var(--color-fg)" : "var(--color-fg-muted)",
                      }}
                    >
                      <Icon size={15} />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
