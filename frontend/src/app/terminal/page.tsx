"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { api } from "@/lib/api";
import { ArrowLeft, Terminal as TerminalIcon, Shield, Loader2 } from "lucide-react";
import Link from "next/link";

// XTerm imports - dynamic import for SSR compatibility
import type { Terminal as XTermType } from "xterm";
import "xterm/css/xterm.css";

interface VM {
  id: number;
  name: string;
  host: string;
  port: number;
  username: string;
}

export default function SovereignTerminal() {
  console.log("!!! ALADDIN SOVEREIGN TERMINAL V3 LOADED !!!");
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTermType | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [activeVM, setActiveVM] = useState<VM | null>(null);
  const [vms, setVms] = useState<VM[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [termSize, setTermSize] = useState({ cols: 80, rows: 24 });

  useEffect(() => {
    let isMounted = true;
    console.log("ALADDIN-DEBUG-V4: Terminal Mount");
    
    if (typeof window === "undefined" || !terminalRef.current) return;

    const initXterm = async () => {
      const { Terminal } = await import("xterm");
      const { FitAddon } = await import("xterm-addon-fit");

      if (!isMounted) return;
      
      // Force cleanup any existing content
      if (terminalRef.current) {
        terminalRef.current.innerHTML = "";
      }
      if (xtermRef.current) {
        xtermRef.current.dispose();
      }

      const term = new Terminal({
        cursorBlink: true,
        fontSize: 12,
        lineHeight: 1,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        theme: {
          background: "#09090b",
          foreground: "#fafafa",
          cursor: "#ffffff",
          selectionBackground: "rgba(255, 255, 255, 0.3)",
          black: "#09090b",
          red: "#ef4444",
          green: "#22c55e",
          yellow: "#eab308",
          blue: "#3b82f6",
          magenta: "#a855f7",
          cyan: "#06b6d4",
          white: "#fafafa",
        },
      });

      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(terminalRef.current!);
      fitAddon.fit();
      term.focus();

      xtermRef.current = term;

      // Handle user input
      let commandBuffer = "";
      term.onData((data) => {
        // Always send escape sequences (arrows, etc) directly to SSH
        if (data.startsWith('\x1b')) {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "data", data }));
          }
          return;
        }

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "data", data }));
        } else {
          // Local command handling (simplified for local mode)
          if (data === "\r") { // Enter
            term.write("\r\n");
            handleLocalCommand(commandBuffer);
            commandBuffer = "";
          } else if (data === "\u007f") { // Backspace
            if (commandBuffer.length > 0) {
              commandBuffer = commandBuffer.slice(0, -1);
              term.write("\b \b");
            }
          } else {
            commandBuffer += data;
            term.write(data);
          }
        }
      });

      // Fit terminal on load and resize
      let resizeTimeout: any;
      const fit = () => {
        try {
          if (!isMounted || !term || !terminalRef.current || !term.element) return;
          fitAddon.fit();

          // Force update terminal size state for footer
          if (term.cols > 0 && term.rows > 0 && term.rows < 1000) {
            setTermSize({ cols: term.cols, rows: term.rows });
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
              if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                  type: "resize",
                  cols: term.cols,
                  rows: term.rows
                }));
              }
            }, 100);
          }
        } catch (e) {
          console.warn("Fit error:", e);
        }
      };

      const resizeObserver = new ResizeObserver(() => fit());
      if (terminalRef.current) resizeObserver.observe(terminalRef.current);
      window.addEventListener("resize", fit);

      // Fetch initial VMs and auto-connect
      try {
        const list = await api.get<VM[]>("/vms");
        setVms(list);
        if (list.length === 1) {
          connectToVM(list[0]);
        }
      } catch (err) {
        console.warn("ALADDIN-DEBUG: Failed to fetch initial VMs", err);
      }

      return () => {
        resizeObserver.disconnect();
        window.removeEventListener("resize", fit);
        term?.dispose();
      };
    };

    const cleanupPromise = initXterm();
    
    return () => {
      isMounted = false;
      console.log("ALADDIN-DEBUG-V4: Terminal Unmount Cleanup");
      wsRef.current?.close();
      xtermRef.current?.dispose();
      xtermRef.current = null;
    };
  }, [user]);

  const handleLocalCommand = (cmd: string) => {
    const term = xtermRef.current;
    if (!term) return;

    const parts = cmd.trim().split(/\s+/);
    const action = parts[0].toLowerCase();

    if (action === "help") {
      term.writeln("Local Commands:");
      term.writeln("  vms           - List available machines");
      term.writeln("  connect <id>  - Enter SSH mode");
      term.writeln("  clear         - Clear terminal");
      term.writeln("  exit          - Return to dashboard");
    } else if (action === "vms") {
      if (vms.length === 0) {
        term.writeln("No machines configured.");
      } else {
        vms.forEach(v => term.writeln(`[${v.id}] ${v.name} (${v.username}@${v.host})`));
      }
    } else if (action === "connect") {
      const target = vms.find(v => v.id.toString() === parts[1]);
      if (target) connectToVM(target);
      else term.writeln("Machine not found.");
    } else if (action === "clear") {
      term.clear();
    } else if (action === "exit") {
      router.push("/dashboard");
    } else if (cmd.trim()) {
      term.writeln(`Unknown local command: ${action}`);
    }

    if (!wsRef.current) term.write("$ ");
  };

  const connectToVM = (vm: VM) => {
    const term = xtermRef.current;
    if (!term) return;

    setConnecting(true);
    setActiveVM(vm);
    term.writeln(`\r\n\x1b[33mConnecting to ${vm.name} SSH...\x1b[0m`);

    const token = localStorage.getItem("access_token");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host === "localhost:3000" ? "localhost:8000" : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/terminal/${vm.id}?token=${token}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnecting(false);
      term.write('\x1b[2J\x1b[H');
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "data") {
        term.write(msg.data);
        term.scrollToBottom();
      } else if (msg.type === "error") {
        term.writeln(`\r\n\x1b[31mSSH ERROR: ${msg.message}\x1b[0m`);
        disconnect();
      }
    };

    ws.onclose = () => {
      term.writeln("\r\n\x1b[31mSSH Connection Closed.\x1b[0m");
      disconnect();
    };
  };

  const disconnect = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setActiveVM(null);
    setConnecting(false);
    xtermRef.current?.write("\r\n$ ");
  };

  if (authLoading || !user) return null;

  return (
    <div className="flex flex-col w-full h-screen bg-[#09090b] text-white overflow-hidden">
      <header className="h-12 shrink-0 flex items-center gap-3 px-4 border-b border-white/10 bg-[#121214]">
        <Link href="/dashboard" className="p-1.5 hover:bg-white/5 rounded-md transition-colors text-zinc-400">
          <ArrowLeft size={16} />
        </Link>
        <div className="flex items-center gap-2">
          <TerminalIcon size={16} className="text-accent" />
          <span className="text-[13px] font-semibold">AladdinAI Sovereign Terminal</span>
        </div>

        {activeVM && (
          <div className="ml-4 flex items-center gap-2 px-2.5 py-1 rounded-full border border-green-500/30 bg-green-500/5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] font-mono font-bold text-green-500 uppercase tracking-widest">
              ACTIVE SESSION: {activeVM.name}
            </span>
          </div>
        )}

        {connecting && (
          <div className="ml-4 flex items-center gap-2 text-zinc-400 text-[11px] animate-pulse">
            <Loader2 size={12} className="animate-spin" />
            Connecting...
          </div>
        )}

        <div className="ml-auto flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-zinc-400 font-mono">{user?.email}</span>
            <span className="text-[9px] text-zinc-600 font-mono tracking-tighter uppercase">
              {activeVM ? "Encrypted TTY" : "Local Shell"}
            </span>
          </div>
          <Shield size={16} className={activeVM ? "text-green-500" : "text-zinc-700"} />
        </div>
      </header>

      <main
        className="flex-1 overflow-hidden relative bg-[#09090b]"
        onClick={() => xtermRef.current?.focus()}
      >
        <style dangerouslySetInnerHTML={{
          __html: `
          .xterm-viewport { padding: 0 !important; margin: 0 !important; }
          .xterm-decoration-container { top: 0 !important; }
          .terminal-glass {
            border: 1px solid rgba(255, 255, 255, 0.06);
            box-shadow:
              0 0 0 1px rgba(255, 255, 255, 0.03),
              0 4px 24px rgba(0, 0, 0, 0.4),
              0 1px 3px rgba(0, 0, 0, 0.3),
              inset 0 1px 0 rgba(255, 255, 255, 0.04);
            background: #0c0c0e;
          }
        ` }} />
        <div className="flex flex-col w-full h-full max-w-6xl mx-auto px-6 py-4">
          {/* Terminal Area - fills all available space */}
          <div className="terminal-glass rounded-lg overflow-hidden flex-1">
            <div ref={terminalRef} className="w-full h-full p-2" />
          </div>
        </div>
      </main>

      <footer className="h-7 shrink-0 flex items-center px-4 border-t border-white/10 bg-[#121214] text-[10px] font-mono text-zinc-500">
        <div className="flex items-center gap-4">
          <span>{activeVM ? "SSH" : "LOCAL"}</span>
          <span>{termSize.cols}x{termSize.rows}</span>
          <span>UTF-8</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[9px] uppercase tracking-widest opacity-50">Sovereign OS Environment</span>
        </div>
      </footer>
    </div>
  );
}

