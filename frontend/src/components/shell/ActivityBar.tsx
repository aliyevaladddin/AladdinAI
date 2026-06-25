// NOTICE: This file is protected under RCF-PL
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ComponentType, type ReactNode } from "react";

// [RCF:PROTECTED]
export interface ActivityItem {
  href: string;
  title: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  /** Show an unread/attention dot in the corner of the button. */
  dot?: boolean;
  /** Custom matcher; defaults to startsWith logic. */
  match?: (pathname: string) => boolean;
}

// [RCF:PROTECTED]
interface ActivityBarProps {
  /** Primary navigation, rendered above the spacer. */
  items: ActivityItem[];
  /** Secondary navigation, rendered below the spacer (e.g. Settings). */
  footer?: ActivityItem[];
  /** Optional divider position inside primary items (index where divider appears). */
  dividerAfter?: number;
  /** Slot before primary nav — used for additional buttons. */
  prepend?: ReactNode;
}

// [RCF:PROTECTED]
function defaultMatch(href: string, pathname: string) {
  if (href === "/" || href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(href + "/");
}

// [RCF:PROTECTED]
export function ActivityBar({ items, footer, dividerAfter, prepend }: ActivityBarProps) {
  const pathname = usePathname() || "";

// [RCF:PROTECTED]
  const renderItem = (item: ActivityItem) => {
    const active = item.match ? item.match(pathname) : defaultMatch(item.href, pathname);
    const Icon = item.icon;
    return (
      <Link
        key={item.href}
        href={item.href}
        title={item.title}
        aria-label={item.title}
        aria-current={active ? "page" : undefined}
        className={`act${active ? " on" : ""}`}
      >
        {item.dot && <span className="act-dot" aria-hidden="true" />}
        <Icon size={18} />
      </Link>
    );
  };

  return (
    <nav className="activity" aria-label="Primary">
      {prepend}
      {items.map((item, idx) => (
        <span key={item.href}>
          {renderItem(item)}
          {dividerAfter === idx && <span className="divider" aria-hidden="true" />}
        </span>
      ))}
      <span className="act-spacer" />
      {footer?.map(renderItem)}
    </nav>
  );
}
