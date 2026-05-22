/**
 * Built-in terminal-provider marketplace catalog.
 * These are presets the user can "install" — each one materialises into a
 * `terminal_providers` row on the backend with a known docker image and
 * URL template. Custom providers are not in this catalog; they are added
 * via the Custom Provider modal.
 *
 * Keep this file pure data — no React, no side effects — so it can be
 * imported by both client and server components without paying the cost
 * of pulling in the renderer.
 */

export type MarketplaceProviderId =
  | "ttyd"
  | "wetty"
  | "guacamole"
  | "sshwifty";

export interface MarketplaceProvider {
  id: MarketplaceProviderId;
  name: string;
  tagline: string;
  description: string;
  tags: string[];
  /** Single-character / 2-glyph monogram used when an icon SVG is absent. */
  monogram: string;
  /** Tailwind utility for the badge background tint. */
  accent: "violet" | "amber" | "ok" | "info";
  docker: {
    image: string;
    internalPort: number;
    suggestedExternalPort: number;
    /** Tokens: {vm_id}, {host}, {port}, {token} */
    urlTemplate: string;
    /** Optional readiness probe — relative to base URL. */
    healthcheck?: string;
  };
  /** Documentation deep-link, shown in the marketplace detail view. */
  homepage: string;
}

export const MARKETPLACE: MarketplaceProvider[] = [
  {
    id: "ttyd",
    name: "ttyd",
    tagline: "Web terminal for the impatient — single static binary, near-zero overhead.",
    description:
      "ttyd shares the host shell over a tiny websocket bridge. Best for quick exec sessions against a VM without protocol translation. Pairs well with the AladdinAI agent runner that already speaks raw PTY frames.",
    tags: ["lightweight", "websocket", "raw-pty"],
    monogram: "tt",
    accent: "violet",
    docker: {
      image: "tsl0922/ttyd:latest",
      internalPort: 7681,
      suggestedExternalPort: 7681,
      urlTemplate: "http://{host}:{port}/?token={token}",
      healthcheck: "/",
    },
    homepage: "https://github.com/tsl0922/ttyd",
  },
  {
    id: "wetty",
    name: "Wetty",
    tagline: "SSH over xterm.js — terminal in a browser tab, SSH-friendly auth flow.",
    description:
      "Wetty proxies SSH straight to a browser-rendered xterm. Use it when the target VM only exposes an SSH endpoint and you want password / key auth surfaced in the UI. Slightly heavier than ttyd, but the upside is real SSH semantics.",
    tags: ["SSH-friendly", "xterm.js", "auth"],
    monogram: "we",
    accent: "info",
    docker: {
      image: "wettyoss/wetty:latest",
      internalPort: 3000,
      suggestedExternalPort: 3001,
      urlTemplate: "http://{host}:{port}/wetty/ssh/{vm_id}",
      healthcheck: "/wetty",
    },
    homepage: "https://github.com/butlerx/wetty",
  },
  {
    id: "guacamole",
    name: "Apache Guacamole",
    tagline: "Clientless RDP / VNC / SSH gateway with session recording and audit.",
    description:
      "Guacamole goes wider than a terminal — it brokers RDP, VNC and SSH through a single web frontend, records every session, and pipes audit events into its own database. Pick this when compliance / multi-protocol matters more than weight.",
    tags: ["multi-protocol", "audit", "RDP", "VNC"],
    monogram: "gc",
    accent: "amber",
    docker: {
      image: "guacamole/guacamole:1.5",
      internalPort: 8080,
      suggestedExternalPort: 8082,
      urlTemplate: "http://{host}:{port}/guacamole/#/client/{vm_id}",
      healthcheck: "/guacamole/",
    },
    homepage: "https://guacamole.apache.org/",
  },
  {
    id: "sshwifty",
    name: "SSHwifty",
    tagline: "SSH & Telnet client with built-in multi-session tabs and presets.",
    description:
      "SSHwifty is a self-hosted SSH/Telnet web client with first-class multi-session tabs and saved presets. A nice middle ground between ttyd's minimalism and Guacamole's enterprise feel — and it ships its own preset/secret manager out of the box.",
    tags: ["SSH-friendly", "multi-session", "presets"],
    monogram: "sw",
    accent: "ok",
    docker: {
      image: "niruix/sshwifty:latest",
      internalPort: 8182,
      suggestedExternalPort: 8182,
      urlTemplate: "http://{host}:{port}/sshwifty/#{vm_id}",
      healthcheck: "/sshwifty/",
    },
    homepage: "https://github.com/nirui/sshwifty",
  },
];

export function getMarketplaceProvider(
  id: string,
): MarketplaceProvider | undefined {
  return MARKETPLACE.find((m) => m.id === id);
}
