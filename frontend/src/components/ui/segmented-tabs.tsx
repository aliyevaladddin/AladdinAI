// NOTICE: This file is protected under RCF-PL
"use client";

import type { ComponentType, ReactNode } from "react";

/* Shared segmented tab bar. Centralises the tab-bar pattern that pages
   re-implemented with slightly different classes (Automations, Settings,
   agent detail, Terminal settings). Renders a pill-group of tabs with the
   active one highlighted. */

export interface TabDef<T extends string> {
  id: T;
  label: string;
  icon?: ComponentType<{ size?: number; className?: string }>;
  desc?: string;
}

interface SegmentedTabsProps<T extends string> {
  tabs: TabDef<T>[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
}

export function SegmentedTabs<T extends string>({
  tabs,
  active,
  onChange,
  className,
}: SegmentedTabsProps<T>) {
  return (
    <div
      className={`flex items-center gap-1 p-1 rounded-xl w-fit ${className ?? ""}`}
      style={{
        background: "var(--color-surface-2)",
        border: "1px solid var(--color-border)",
      }}
      role="tablist"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all"
            style={{
              background: isActive ? "var(--color-surface)" : "transparent",
              color: isActive ? "var(--color-fg)" : "var(--color-fg-muted)",
              boxShadow: isActive ? "0 1px 4px rgba(0,0,0,0.15)" : "none",
            }}
          >
            {Icon && (
              <Icon size={14} className={isActive ? "text-[var(--color-accent)]" : ""} />
            )}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

/* Convenience wrapper: tab bar + optional description of the active tab. */
export function TabSection<T extends string>({
  tabs,
  active,
  onChange,
  title,
  icon: TitleIcon,
  description,
}: {
  tabs: TabDef<T>[];
  active: T;
  onChange: (id: T) => void;
  title: string;
  icon?: ComponentType<{ size?: number; className?: string }>;
  description?: string;
}) {
  const activeTab = tabs.find((t) => t.id === active);
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-4">
        {TitleIcon && (
          <div
            className="mt-1 w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: "var(--color-accent-soft)", color: "var(--color-accent)" }}
          >
            <TitleIcon size={20} />
          </div>
        )}
        <div>
          <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
          {description && (
            <p className="text-sm mt-1" style={{ color: "var(--color-fg-muted)" }}>
              {description}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <SegmentedTabs tabs={tabs} active={active} onChange={onChange} />
        {activeTab?.desc && (
          <p className="text-xs" style={{ color: "var(--color-fg-subtle)" }}>
            {activeTab.desc}
          </p>
        )}
      </div>
    </div>
  );
}
