"use client";

import React from "react";
import { COMMANDS_REGISTRY } from "@/lib/commands-registry";
import { Command, Keyboard, Zap, Sparkles } from "lucide-react";

export function ShortcutsSettings() {
  const categories = Array.from(new Set(COMMANDS_REGISTRY.map((c) => c.category)));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-border/50">
        <div>
          <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
            <Keyboard size={18} className="text-primary" />
            <span>Command Palette & Keyboard Shortcuts</span>
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Complete documentation of system hotkeys, navigation shortcuts, and command registry.
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-xs font-mono text-primary font-medium">
          <Command size={14} />
          <span>Press ⌘K or Ctrl+K anywhere</span>
        </div>
      </div>

      <div className="space-y-6">
        {categories.map((cat) => {
          const items = COMMANDS_REGISTRY.filter((c) => c.category === cat);
          return (
            <div key={cat} className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Zap size={13} className="text-primary" />
                <span>{cat} ({items.length})</span>
              </h3>
              <div className="rounded-xl border border-border/70 overflow-hidden bg-card/50">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted/60 text-muted-foreground font-semibold border-b border-border/50">
                    <tr>
                      <th className="px-4 py-2.5">Command</th>
                      <th className="px-4 py-2.5">Description</th>
                      <th className="px-4 py-2.5 text-right">Shortcut</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {items.map((cmd) => (
                      <tr key={cmd.id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3 font-semibold text-foreground flex items-center gap-2">
                          <Sparkles size={13} className="text-primary/70 shrink-0" />
                          <span>{cmd.label}</span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground leading-relaxed">
                          {cmd.description}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {cmd.shortcut ? (
                            <kbd className="px-2.5 py-1 text-[11px] font-mono text-foreground bg-muted rounded-lg border border-border/60 shadow-xs inline-block">
                              {cmd.shortcut}
                            </kbd>
                          ) : (
                            <span className="text-[10px] text-muted-foreground/60">⌘K Menu</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
