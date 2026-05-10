"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Terminal as TerminalIcon, Shield, Loader2 } from "lucide-react";

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

export function TerminalSettings() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTermType | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [activeVM, setActiveVM] = useState<VM | null>(null);
  const [vms, setVms] = useState<VM[]>([]);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    if (typeof window === "undefined" || !terminalRef.current) return;

    const initXterm = async () => {
      const { Terminal } = await import("xterm");
      const { FitAddon } = await import("xterm-addon-fit");

      if (!isMounted) return;
      if (terminalRef.current) terminalRef.current.innerHTML = "";
      if (xtermRef.current) xtermRef.current.dispose();

      const term = new Terminal({
        cursorBlink: true,
        fontSize: 13,
        fontFamily: "'JetBrains Mono', monospace",
        theme: {
          background: "#09090b",
          foreground: "#fafafa",
          cursor: "#ffffff",
        },
      });

      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(terminalRef.current!);
      fitAddon.fit();
      term.focus();
      xtermRef.current = term;

      term.onData((data) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "data", data }));
        } else {
            // Local echo for help
            if (data === "\r") {
                term.write("\r\n$ ");
            } else {
                term.write(data);
            }
        }
      });

      const fit = () => fitAddon.fit();
      window.addEventListener("resize", fit);

      // Fetch VMs
      api.get<VM[]>("/vms").then((list) => {
        if (!isMounted) return;
        setVms(list);
        if (list.length > 0) connectToVM(list[0]);
      });

      return () => {
        window.removeEventListener("resize", fit);
        term.dispose();
      };
    };

    initXterm();

    return () => {
      isMounted = false;
      wsRef.current?.close();
      xtermRef.current?.dispose();
    };
  }, []);

  const connectToVM = (vm: VM) => {
    const term = xtermRef.current;
    if (!term) return;

    setConnecting(true);
    setActiveVM(vm);
    term.writeln(`\r\n\x1b[33mConnecting to ${vm.name}...\x1b[0m`);

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
      if (msg.type === "data") term.write(msg.data);
    };

    ws.onclose = () => {
      term.writeln("\r\n\x1b[31mSSH Connection Closed.\x1b[0m");
      setActiveVM(null);
      setConnecting(false);
    };
  };

  return (
    <div className="space-y-5 h-full flex flex-col">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
            <TerminalIcon size={16} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--color-fg)]">Infrastructure Console</h3>
            <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">Direct SSH access to your sovereign nodes</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {activeVM && (
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-[var(--color-success)] bg-[var(--color-success-soft)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse" />
              <span className="text-[10px] font-bold text-[var(--color-success)] uppercase tracking-wider">
                {activeVM.name}
              </span>
            </div>
          )}
          <Shield size={16} className={activeVM ? "text-[var(--color-success)]" : "text-[var(--color-fg-subtle)]"} />
        </div>
      </div>

      <div className="grid grid-cols-[220px_1fr] gap-5 flex-1 min-h-0">
        <div className="space-y-1.5 overflow-y-auto">
            <p className="text-[10px] font-bold text-[var(--color-fg-subtle)] uppercase tracking-widest px-1 mb-2">Available Nodes</p>
            {vms.map(vm => (
                <button
                    key={vm.id}
                    onClick={() => connectToVM(vm)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                        activeVM?.id === vm.id 
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]" 
                        : "border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-fg-muted)] hover:border-[var(--color-border-strong)]"
                    }`}
                >
                    <p className="text-sm font-medium">{vm.name}</p>
                    <p className="text-[10px] opacity-60 font-mono truncate">{vm.username}@{vm.host}</p>
                </button>
            ))}
        </div>

        <div className="relative rounded-xl border border-[var(--color-border)] overflow-hidden bg-[#09090b] shadow-2xl">
            {connecting && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="flex items-center gap-3 text-white animate-pulse">
                        <Loader2 size={18} className="animate-spin" />
                        <span className="text-sm font-mono uppercase tracking-widest">Establishing Secure Tunnel...</span>
                    </div>
                </div>
            )}
            <div ref={terminalRef} className="w-full h-full p-4" />
        </div>
      </div>
    </div>
  );
}
