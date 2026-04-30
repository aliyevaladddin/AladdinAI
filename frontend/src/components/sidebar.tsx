"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";

const nav = [
  { href: "/dashboard", label: "Dashboard", section: "" },
  { href: "/dashboard/channels", label: "Channels", section: "Communication" },
  { href: "/dashboard/crm", label: "Contacts", section: "CRM" },
  { href: "/dashboard/deals", label: "Deals", section: "CRM" },
  { href: "/dashboard/agents", label: "Agents", section: "AI" },
  { href: "/dashboard/router", label: "Router", section: "AI" },
  { href: "/dashboard/chat", label: "Chat", section: "AI" },
  { href: "/dashboard/vms", label: "Cloud VMs", section: "Infrastructure" },
  { href: "/dashboard/providers", label: "LLM Providers", section: "Infrastructure" },
  { href: "/dashboard/mongodb", label: "MongoDB", section: "Infrastructure" },
  { href: "/dashboard/bentoml", label: "BentoML", section: "Infrastructure" },
  { href: "/dashboard/webhooks", label: "Webhooks", section: "Infrastructure" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold">AladdinAI</h1>
        <p className="text-xs text-muted-foreground mt-1">AI Agent Platform</p>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {nav.map((item, i) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const showSection = item.section && (i === 0 || nav[i - 1].section !== item.section);
          return (
            <div key={item.href}>
              {showSection && (
                <p className="px-3 pt-4 pb-1 text-[10px] uppercase tracking-wider text-muted-foreground/60">{item.section}</p>
              )}
              <Link
                href={item.href}
                className={`block px-3 py-2 rounded-md text-sm transition-colors ${
                  active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                {item.label}
              </Link>
            </div>
          );
        })}
      </nav>
      <div className="p-4 border-t border-border">
        <p className="text-sm truncate">{user?.name}</p>
        <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        <button onClick={logout} className="mt-2 text-xs text-destructive hover:underline">
          Sign out
        </button>
      </div>
    </aside>
  );
}
