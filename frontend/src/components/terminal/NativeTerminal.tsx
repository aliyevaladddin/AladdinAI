// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from "react";
import { Terminal, ITheme } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { API_URL } from "@/lib/api";
import { Loader2, RefreshCw, Copy, Trash2, Maximize2, Minimize2 } from "lucide-react";

export type TerminalThemePreset = "aladdin" | "dracula" | "monokai" | "cyberpunk" | "jetbrains" | "matrix";

export const TERMINAL_THEMES: Record<TerminalThemePreset, { name: string; theme: ITheme }> = {
  aladdin: {
    name: "Aladdin Dark",
    theme: {
      background: "#0b0d14",
      foreground: "#f1f5f9",
      cursor: "#38bdf8",
      cursorAccent: "#0b0d14",
      selectionBackground: "rgba(56, 189, 248, 0.35)",
      black: "#1e293b",
      red: "#f87171",
      green: "#4ade80",
      yellow: "#facc15",
      blue: "#60a5fa",
      magenta: "#c084fc",
      cyan: "#38bdf8",
      white: "#f8fafc",
      brightBlack: "#475569",
      brightRed: "#fca5a5",
      brightGreen: "#86efac",
      brightYellow: "#fde047",
      brightBlue: "#93c5fd",
      brightMagenta: "#e9d5ff",
      brightCyan: "#7dd3fc",
      brightWhite: "#ffffff",
    },
  },
  dracula: {
    name: "Dracula",
    theme: {
      background: "#282a36",
      foreground: "#f8f8f2",
      cursor: "#ff79c6",
      cursorAccent: "#282a36",
      selectionBackground: "rgba(68, 71, 90, 0.5)",
      black: "#21222c",
      red: "#ff5555",
      green: "#50fa7b",
      yellow: "#f1fa8c",
      blue: "#bd93f9",
      magenta: "#ff79c6",
      cyan: "#8be9fd",
      white: "#f8f8f2",
      brightBlack: "#6272a4",
      brightRed: "#ff6e6e",
      brightGreen: "#69ff94",
      brightYellow: "#ffffa5",
      brightBlue: "#d6acff",
      brightMagenta: "#ff92d0",
      brightCyan: "#a4ffff",
      brightWhite: "#ffffff",
    },
  },
  monokai: {
    name: "Monokai",
    theme: {
      background: "#272822",
      foreground: "#f8f8f2",
      cursor: "#f92672",
      cursorAccent: "#272822",
      selectionBackground: "rgba(73, 72, 62, 0.7)",
      black: "#272822",
      red: "#f92672",
      green: "#a6e22e",
      yellow: "#e6db74",
      blue: "#66d9ef",
      magenta: "#ae81ff",
      cyan: "#a1efe4",
      white: "#f8f8f2",
      brightBlack: "#75715e",
      brightRed: "#f92672",
      brightGreen: "#a6e22e",
      brightYellow: "#e6db74",
      brightBlue: "#66d9ef",
      brightMagenta: "#ae81ff",
      brightCyan: "#a1efe4",
      brightWhite: "#f8f8f2",
    },
  },
  cyberpunk: {
    name: "Cyberpunk",
    theme: {
      background: "#120024",
      foreground: "#00ff9f",
      cursor: "#ff0055",
      cursorAccent: "#120024",
      selectionBackground: "rgba(255, 0, 85, 0.4)",
      black: "#1a0933",
      red: "#ff0055",
      green: "#00ff9f",
      yellow: "#ffe600",
      blue: "#00b8ff",
      magenta: "#d600ff",
      cyan: "#00f0ff",
      white: "#e0e0e0",
      brightBlack: "#4d2975",
      brightRed: "#ff3377",
      brightGreen: "#33ffb2",
      brightYellow: "#ffeb33",
      brightBlue: "#33c6ff",
      brightMagenta: "#de33ff",
      brightCyan: "#33f3ff",
      brightWhite: "#ffffff",
    },
  },
  jetbrains: {
    name: "JetBrains Dark",
    theme: {
      background: "#1e1e1e",
      foreground: "#bbbbbb",
      cursor: "#045757",
      cursorAccent: "#ffffff",
      selectionBackground: "rgba(33, 66, 131, 0.6)",
      black: "#000000",
      red: "#cd3131",
      green: "#0dbc79",
      yellow: "#e5e510",
      blue: "#2472c8",
      magenta: "#bc3fbc",
      cyan: "#11a8cd",
      white: "#e5e5e5",
      brightBlack: "#666666",
      brightRed: "#f14c4c",
      brightGreen: "#23d18b",
      brightYellow: "#f5f543",
      brightBlue: "#3b8ee0",
      brightMagenta: "#d670d6",
      brightCyan: "#29b8db",
      brightWhite: "#e5e5e5",
    },
  },
  matrix: {
    name: "Matrix",
    theme: {
      background: "#050d08",
      foreground: "#00ff41",
      cursor: "#00ff41",
      cursorAccent: "#050d08",
      selectionBackground: "rgba(0, 255, 65, 0.3)",
      black: "#0d2b14",
      red: "#008000",
      green: "#00ff41",
      yellow: "#80ff00",
      blue: "#00ff80",
      magenta: "#00b33c",
      cyan: "#00ffbf",
      white: "#d0ffd6",
      brightBlack: "#1a5228",
      brightRed: "#33cc33",
      brightGreen: "#66ff66",
      brightYellow: "#b3ff66",
      brightBlue: "#66ffb3",
      brightMagenta: "#4dff88",
      brightCyan: "#80ffdf",
      brightWhite: "#ffffff",
    },
  },
};

export interface NativeTerminalRef {
  focus: () => void;
  sendInput: (data: string) => void;
  clear: () => void;
  copySelection: () => void;
}

interface NativeTerminalProps {
  vmId?: number | null;
  themePreset?: TerminalThemePreset;
  onConnected?: () => void;
  onError?: (msg: string) => void;
}

export const NativeTerminal = forwardRef<NativeTerminalRef, NativeTerminalProps>(
  ({ vmId, themePreset = "aladdin", onConnected, onError }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const terminalRef = useRef<Terminal | null>(null);
    const fitAddonRef = useRef<FitAddon | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    const [status, setStatus] = useState<"connecting" | "connected" | "error">("connecting");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const focusTerminal = () => {
      if (terminalRef.current) {
        terminalRef.current.focus();
      }
    };

    useImperativeHandle(ref, () => ({
      focus: focusTerminal,
      sendInput: (data: string) => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "data", data }));
          focusTerminal();
        }
      },
      clear: () => {
        if (terminalRef.current) {
          terminalRef.current.clear();
          focusTerminal();
        }
      },
      copySelection: () => {
        if (terminalRef.current) {
          const selection = terminalRef.current.getSelection();
          if (selection) {
            navigator.clipboard.writeText(selection);
          }
        }
      },
    }));

    const connect = () => {
      if (!containerRef.current) return;
      setStatus("connecting");
      setErrorMessage(null);

      // Clean up previous terminal instance if reconnecting
      if (terminalRef.current) {
        terminalRef.current.dispose();
        terminalRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      const activeTheme = TERMINAL_THEMES[themePreset]?.theme || TERMINAL_THEMES.aladdin.theme;

      const term = new Terminal({
        cursorBlink: true,
        cursorStyle: "block",
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, monospace",
        fontSize: 13,
        lineHeight: 1.2,
        theme: activeTheme,
      });

      const fitAddon = new FitAddon();
      term.loadAddon(fitAddon);
      term.open(containerRef.current);

      // Custom key handler for Copy/Paste
      term.attachCustomKeyEventHandler((arg: KeyboardEvent) => {
        if (arg.type !== "keydown") return true;
        const key = arg.key.toLowerCase();

        // Copy: Cmd+C or Ctrl+C
        if ((arg.metaKey || arg.ctrlKey) && key === "c") {
          if (term.hasSelection()) {
            const text = term.getSelection();
            
            // Try modern API
            if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
              navigator.clipboard.writeText(text).catch(() => {});
            }

            // Always synchronously execute fallback. If modern API is blocked or fails async,
            // this synchronous call (which is valid inside a keyboard event) will succeed.
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            textArea.style.left = "-9999px";
            document.body.appendChild(textArea);
            textArea.select();
            try { document.execCommand("copy"); } catch (e) {}
            document.body.removeChild(textArea);

            term.clearSelection(); // Clear selection to indicate copy success
            return false; // Prevent sending SIGINT if it was Ctrl+C
          }
          return true; // No selection, allow SIGINT or native browser copy
        }

        // Paste: Cmd+V or Ctrl+V
        if ((arg.metaKey || arg.ctrlKey) && key === "v") {
          if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.readText) {
            navigator.clipboard.readText().then((text) => {
              if (text && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: "data", data: text }));
              }
            }).catch(() => {});
            return false;
          }
          return true; // Fallback to native browser paste event in xterm
        }

        return true;
      });


      // Patch xterm renderService & viewport to prevent uncaught dimensions crash on unrendered tabs
      const core = (term as any)._core;
      if (core) {
        if (core._renderService) {
          const rs = core._renderService;
          const proto = Object.getPrototypeOf(rs);
          const descriptor = Object.getOwnPropertyDescriptor(proto, "dimensions");
          if (descriptor && descriptor.get) {
            const origGet = descriptor.get;
            Object.defineProperty(rs, "dimensions", {
              configurable: true,
              get() {
                try {
                  const res = origGet.call(this);
                  if (res) return res;
                } catch { /* fallback below */ }
                return {
                  css: { cell: { width: 9, height: 17 }, canvas: { width: 800, height: 600 } },
                  device: { cell: { width: 9, height: 17 }, canvas: { width: 800, height: 600 } },
                };
              },
            });
          }
        }
        if (core._viewport) {
          const vp = core._viewport;
          const origRefresh = vp._innerRefresh?.bind(vp);
          if (origRefresh) {
            vp._innerRefresh = () => {
              try {
                origRefresh();
              } catch { /* ignore refresh error when DOM container is unmounted or hidden */ }
            };
          }
        }
      }

      const safeFit = () => {
        if (!containerRef.current || containerRef.current.clientWidth === 0 || containerRef.current.clientHeight === 0) return;
        if (fitAddonRef.current && terminalRef.current) {
          try {
            fitAddonRef.current.fit();
          } catch { /* ignore if renderer uninitialized */ }
        }
      };

      // Delay fit slightly to ensure DOM dimensions are ready
      setTimeout(() => {
        safeFit();
      }, 100);

      terminalRef.current = term;
      fitAddonRef.current = fitAddon;

      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : "";
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";

      let wsHost = window.location.host;
      try {
        const url = new URL(API_URL);
        wsHost = url.host;
      } catch { /* use location host */ }

      const endpoint = vmId ? `/api/ws/terminal/${vmId}` : "/api/ws/terminal/local";
      const wsUrl = `${wsProtocol}//${wsHost}${endpoint}?token=${encodeURIComponent(token || "")}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        if (onConnected) onConnected();

        // Instant autofocus upon connection
        setTimeout(() => {
          term.focus();
        }, 100);

        // Send initial size safely
        if (containerRef.current && containerRef.current.clientWidth > 0 && containerRef.current.clientHeight > 0) {
          try {
            const dims = fitAddon.proposeDimensions();
            if (dims && dims.cols > 0 && dims.rows > 0) {
              ws.send(JSON.stringify({ type: "resize", cols: dims.cols, rows: dims.rows }));
            }
          } catch { /* ignore uninitialized renderer */ }
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "data" && msg.data) {
            term.write(msg.data);
          } else if (msg.type === "error") {
            setErrorMessage(msg.message || "Terminal error");
            setStatus("error");
            if (onError) onError(msg.message);
          }
        } catch {
          term.write(event.data);
        }
      };

      ws.onerror = () => {
        const err = "Failed to connect to Terminal WebSocket server.";
        setErrorMessage(err);
        setStatus("error");
        if (onError) onError(err);
      };

      ws.onclose = () => {
        if (status !== "error") {
          setStatus("error");
          setErrorMessage("Connection closed.");
        }
      };

      term.onData((data) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "data", data }));
        }
      });

      term.onResize(({ cols, rows }) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "resize", cols, rows }));
        }
      });
    };

    // Update theme dynamically
    useEffect(() => {
      if (terminalRef.current) {
        const activeTheme = TERMINAL_THEMES[themePreset]?.theme || TERMINAL_THEMES.aladdin.theme;
        terminalRef.current.options.theme = activeTheme;
      }
    }, [themePreset]);

    useEffect(() => {
      connect();

      const handleResize = () => {
        if (!containerRef.current || containerRef.current.clientWidth === 0 || containerRef.current.clientHeight === 0) return;
        if (fitAddonRef.current && terminalRef.current) {
          try {
            fitAddonRef.current.fit();
          } catch { /* ignore if unmounted or renderer uninitialized */ }
        }
      };

      const observer = new ResizeObserver(() => handleResize());
      if (containerRef.current) {
        observer.observe(containerRef.current);
      }
      window.addEventListener("resize", handleResize);

      return () => {
        observer.disconnect();
        window.removeEventListener("resize", handleResize);
        if (wsRef.current) {
          wsRef.current.close();
        }
        if (terminalRef.current) {
          terminalRef.current.dispose();
        }
      };
    }, [vmId]);

    const activeBg = TERMINAL_THEMES[themePreset]?.theme.background || "#0b0d14";

    return (
      <div
        className="relative w-full h-full overflow-hidden flex flex-col justify-center items-center cursor-text"
        style={{ backgroundColor: activeBg }}
        onClick={focusTerminal}
      >
        {status === "connecting" && (
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center backdrop-blur-sm text-slate-400 gap-2"
            style={{ backgroundColor: `${activeBg}e6` }}
          >
            <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
            <span className="text-xs font-medium tracking-wide">Connecting to native Aladdin terminal…</span>
          </div>
        )}

        {status === "error" && (
          <div
            className="absolute inset-0 z-10 flex flex-col items-center justify-center text-red-400 p-4 gap-3 text-center"
            style={{ backgroundColor: activeBg }}
          >
            <div className="text-sm font-semibold">{errorMessage || "Terminal Disconnected"}</div>
            <button
              onClick={connect}
              type="button"
              className="flex items-center gap-2 px-3.5 py-1.5 text-xs bg-sky-600/20 text-sky-300 hover:bg-sky-600/30 border border-sky-500/30 rounded-lg transition-all cursor-pointer shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Reconnect
            </button>
          </div>
        )}

        <div ref={containerRef} className="w-full h-full p-2" />
      </div>
    );
  }
);

NativeTerminal.displayName = "NativeTerminal";

