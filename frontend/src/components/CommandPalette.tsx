"use client";

import React, { useEffect, useState } from "react";
import { Command } from "cmdk";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import confetti from "canvas-confetti";
import { toast } from "sonner";
import {
  MessageSquare,
  Bot,
  Users,
  BarChart3,
  Settings,
  PlusCircle,
  UserPlus,
  Volume2,
  Download,
  Terminal,
  Key,
  RefreshCw,
  Sparkles,
  HelpCircle,
  Search,
  Zap,
} from "lucide-react";
import { COMMANDS_REGISTRY, PaletteCommand } from "@/lib/commands-registry";
import { clearApiCache } from "@/lib/api";

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  MessageSquare,
  Bot,
  Users,
  BarChart3,
  Settings,
  PlusCircle,
  UserPlus,
  Volume2,
  Download,
  Terminal,
  Key,
  RefreshCw,
  Sparkles,
  HelpCircle,
};

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  const handleCommandSelect = (cmd: PaletteCommand) => {
    setOpen(false);

    if (cmd.actionType === "navigate" && cmd.path) {
      router.push(cmd.path);
      return;
    }

    if (cmd.actionType === "custom") {
      switch (cmd.actionId) {
        case "trigger-confetti":
          confetti({
            particleCount: 120,
            spread: 80,
            origin: { y: 0.6 },
          });
          toast.success("Achievement Celebrated! 🎉");
          break;

        case "copy-token":
          const token = localStorage.getItem("access_token");
          if (token) {
            navigator.clipboard.writeText(token);
            toast.success("JWT Access Token copied to clipboard!");
          } else {
            toast.error("No active session token found");
          }
          break;

        case "clear-cache":
          clearApiCache();
          toast.success("In-memory API Cache flushed successfully!");
          break;

        case "toggle-terminal":
          window.dispatchEvent(new CustomEvent("aladdin:toggle-terminal"));
          toast.info("Terminal Drawer toggled");
          break;

        case "toggle-voice":
          toast.info("Voice Reply mode toggled");
          break;

        default:
          break;
      }
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const code = e.code;
      const key = e.key.toLowerCase();
      const isCmdOrCtrl = e.metaKey || e.ctrlKey;

      // Cmd+K or Ctrl+K -> Command Palette (supports English 'k' and Russian 'л')
      if (isCmdOrCtrl && (code === "KeyK" || key === "k" || key === "л")) {
        e.preventDefault();
        setOpen((prev) => !prev);
        return;
      }

      // Check shortcuts if Cmd/Ctrl+Shift or Alt is pressed (to prevent breaking native Cmd+C, Cmd+V, Cmd+A, etc)
      if ((isCmdOrCtrl && e.shiftKey) || e.altKey) {
        let matchedCmd: PaletteCommand | undefined;

        if (code === "Digit1" || key === "1" || key === "!") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "nav-chat");
        else if (code === "Digit2" || key === "2" || key === "@" || key === '"') matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "nav-agents");
        else if (code === "Digit3" || key === "3" || key === "#" || key === "№") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "nav-crm");
        else if (code === "Digit4" || key === "4" || key === "$" || key === ";") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "nav-dashboard");
        else if (code === "Digit5" || key === "5" || key === "%") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "nav-settings");
        else if (code === "KeyN" || key === "n" || key === "т") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "ai-new-chat");
        else if (code === "KeyT" || key === "t" || key === "е") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "dev-toggle-terminal");
        else if (code === "KeyC" || key === "c" || key === "с") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "util-confetti");
        else if (code === "KeyR" || key === "r" || key === "к") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "dev-clear-cache");
        else if (code === "KeyH" || key === "h" || key === "р") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "util-shortcuts-doc");
        else if (code === "KeyL" || key === "l" || key === "д") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "crm-add-lead");
        else if (code === "KeyA" || key === "a" || key === "ф") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "ai-create-agent");
        else if (code === "KeyV" || key === "v" || key === "м") matchedCmd = COMMANDS_REGISTRY.find((c) => c.id === "ai-voice-toggle");

        if (matchedCmd) {
          e.preventDefault();
          handleCommandSelect(matchedCmd);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [router]);

  const categories = Array.from(new Set(COMMANDS_REGISTRY.map((c) => c.category)));

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 bg-background/80 backdrop-blur-md"
          />

          {/* Command Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="relative w-full max-w-2xl bg-card border border-border/80 rounded-2xl shadow-2xl overflow-hidden z-10"
          >
            <Command className="w-full bg-transparent">
              <div className="flex items-center px-4 border-b border-border/50">
                <Search size={18} className="text-muted-foreground mr-3 shrink-0" />
                <Command.Input
                  placeholder="Type a command or search actions (e.g. chat, terminal, agents)..."
                  className="w-full h-14 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none"
                />
                <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted rounded border border-border/60">
                  ESC
                </kbd>
              </div>

              <Command.List className="max-h-96 overflow-y-auto p-2 space-y-2">
                <Command.Empty className="py-8 text-center text-xs text-muted-foreground">
                  No matching commands found.
                </Command.Empty>

                {categories.map((cat) => {
                  const items = COMMANDS_REGISTRY.filter((c) => c.category === cat);
                  return (
                    <Command.Group
                      key={cat}
                      heading={cat}
                      className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider px-2 py-1"
                    >
                      {items.map((cmd) => {
                        const IconComponent = ICON_MAP[cmd.iconName] || Sparkles;
                        return (
                          <Command.Item
                            key={cmd.id}
                            onSelect={() => handleCommandSelect(cmd)}
                            className="flex items-center justify-between px-3 py-2.5 rounded-xl text-xs text-foreground hover:bg-muted/70 cursor-pointer transition-all aria-selected:bg-primary/10 aria-selected:text-primary group"
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <div className="p-1.5 rounded-lg bg-muted/50 group-aria-selected:bg-primary/20 text-muted-foreground group-aria-selected:text-primary transition-colors">
                                <IconComponent size={15} />
                              </div>
                              <div className="flex flex-col min-w-0">
                                <span className="font-semibold text-foreground group-aria-selected:text-primary transition-colors">
                                  {cmd.label}
                                </span>
                                <span className="text-[11px] text-muted-foreground/80 truncate">
                                  {cmd.description}
                                </span>
                              </div>
                            </div>
                            {cmd.shortcut && (
                              <kbd className="ml-3 px-2 py-0.5 text-[10px] font-mono text-muted-foreground/80 bg-muted/60 rounded border border-border/40 shrink-0">
                                {cmd.shortcut}
                              </kbd>
                            )}
                          </Command.Item>
                        );
                      })}
                    </Command.Group>
                  );
                })}
              </Command.List>

              <div className="px-4 py-2.5 border-t border-border/50 bg-muted/20 flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1.5 font-medium">
                  <Zap size={13} className="text-primary" />
                  <span>AladdinAI Command Registry ({COMMANDS_REGISTRY.length} commands)</span>
                </span>
                <span className="text-[10px]">Press <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-muted rounded border border-border/60">⌘K</kbd> or <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-muted rounded border border-border/60">Alt+1..5</kbd></span>
              </div>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
