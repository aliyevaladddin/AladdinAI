// NOTICE: This file is protected under RCF-PL
import {
  LayoutDashboard,
  Bot,
  Zap,
  MessageSquare,
  Mailbox,
  Users,
  Sparkles,
  Settings,
  Briefcase,
} from "lucide-react";
import type { ActivityItem } from "./ActivityBar";

/**
 * Activity bar configuration for the authenticated dashboard.
 * Order mirrors the existing AppSidebar — same routes, vertical layout.
 *
 * Providers moved to /dashboard/settings?tab=providers (2026-06-01).
 */
export const DASHBOARD_PRIMARY: ActivityItem[] = [
  { href: "/dashboard",             title: "Overview",     icon: LayoutDashboard },
  { href: "/dashboard/agents",      title: "Agents",       icon: Bot },
  { href: "/dashboard/automations", title: "Automations",  icon: Zap },
  { href: "/dashboard/comms",       title: "Conversations",icon: MessageSquare },
  { href: "/dashboard/mail",        title: "Mail",         icon: Mailbox },
  { href: "/dashboard/crm",         title: "CRM",          icon: Users },
  { href: "/dashboard/deals",       title: "Deals",        icon: Briefcase },
  { href: "/dashboard/chat",        title: "Playground",   icon: Sparkles },
];

export const DASHBOARD_FOOTER: ActivityItem[] = [
  { href: "/dashboard/settings", title: "Settings", icon: Settings },
];
