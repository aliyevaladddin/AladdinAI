"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Stats {
  contacts: number;
  deals: number;
  emails: number;
  channels: number;
  agents: number;
  vms: number;
  providers: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({ contacts: 0, deals: 0, emails: 0, channels: 0, agents: 0, vms: 0, providers: 0 });

  useEffect(() => {
    Promise.all([
      api.get<unknown[]>("/crm/contacts"),
      api.get<unknown[]>("/crm/deals"),
      api.get<unknown[]>("/channels/email"),
      api.get<unknown[]>("/channels/messaging"),
      api.get<unknown[]>("/agents"),
      api.get<unknown[]>("/vms"),
      api.get<unknown[]>("/providers"),
    ]).then(([contacts, deals, emails, channels, agents, vms, providers]) => {
      setStats({
        contacts: contacts.length,
        deals: deals.length,
        emails: emails.length,
        channels: channels.length,
        agents: agents.length,
        vms: vms.length,
        providers: providers.length,
      });
    });
  }, []);

  const sections = [
    {
      title: "CRM",
      cards: [
        { label: "Contacts", value: stats.contacts, href: "/dashboard/crm" },
        { label: "Deals", value: stats.deals, href: "/dashboard/deals" },
      ],
    },
    {
      title: "Communication",
      cards: [
        { label: "Email Accounts", value: stats.emails, href: "/dashboard/channels" },
        { label: "Messaging", value: stats.channels, href: "/dashboard/channels" },
      ],
    },
    {
      title: "AI & Infrastructure",
      cards: [
        { label: "Agents", value: stats.agents, href: "/dashboard/agents" },
        { label: "LLM Providers", value: stats.providers, href: "/dashboard/providers" },
        { label: "Cloud VMs", value: stats.vms, href: "/dashboard/vms" },
      ],
    },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      {sections.map((section) => (
        <div key={section.title} className="mb-8">
          <h3 className="text-sm uppercase tracking-wider text-muted-foreground mb-3">{section.title}</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {section.cards.map((card) => (
              <a
                key={card.label}
                href={card.href}
                className="rounded-lg border border-border bg-card p-6 hover:bg-accent transition-colors"
              >
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <p className="text-3xl font-bold mt-2">{card.value}</p>
              </a>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
