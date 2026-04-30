"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { name: "Command", icon: "monitoring", href: "/dashboard" },
  { name: "Agents", icon: "smart_toy", href: "/dashboard/agents" },
  { name: "CRM", icon: "view_kanban", href: "/dashboard/crm" },
  { name: "Comms", icon: "forum", href: "/dashboard/comms", activeIcon: true },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col pt-20 pb-6 bg-surface-plate border-r border-white/10 w-64 z-40 justify-between">
      <div>
        {/* Header */}
        <div className="px-6 mb-8 flex flex-col gap-1">
          <h2 className="text-cyan-400 font-black font-header text-lg tracking-widest">NEURAL_OS</h2>
          <span className="text-[10px] text-white/40 font-mono uppercase tracking-widest border border-white/10 inline-block px-1.5 py-0.5 w-max">
            SOVEREIGN_MODE
          </span>
        </div>

        {/* Tabs */}
        <nav className="flex flex-col gap-1 font-header text-xs font-bold uppercase tracking-widest">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-4 px-4 py-3 transition-all cursor-pointer active:brightness-125 ${
                  isActive
                    ? "bg-cyan-400 text-black clip-path-polygon shadow-[0_0_15px_rgba(0,255,255,0.2)]"
                    : "text-white/40 hover:text-cyan-400 hover:bg-white/5 hover:border-l-4 hover:border-cyan-400"
                }`}
              >
                <span className={`material-symbols-outlined ${item.activeIcon && isActive ? 'icon-fill' : ''}`}>
                  {item.icon}
                </span>
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-4 px-4">
        {/* CTA */}
        <button className="w-full border border-cyan-400/50 text-cyan-400 font-mono text-[12px] font-bold py-2 hover:bg-cyan-400/10 active:scale-95 transition-all text-center tracking-widest uppercase">
          NEW_PROTOCOL
        </button>

        {/* Footer Tabs */}
        <div className="flex flex-col gap-1 mt-4 font-header text-xs font-bold uppercase tracking-widest border-t border-white/10 pt-4">
          <Link href="#" className="flex items-center gap-4 text-white/40 px-2 py-2 hover:text-cyan-400 hover:bg-white/5 transition-all cursor-pointer">
            <span className="material-symbols-outlined text-sm">help</span>
            Support
          </Link>
          <Link href="#" className="flex items-center gap-4 text-white/40 px-2 py-2 hover:text-cyan-400 hover:bg-white/5 transition-all cursor-pointer">
            <span className="material-symbols-outlined text-sm">terminal</span>
            Terminal
          </Link>
        </div>
      </div>
    </aside>
  );
}
