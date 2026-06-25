// NOTICE: This file is protected under RCF-PL
/**
 * Shared types for the terminal-providers marketplace.
 * These mirror the backend shapes (see endpoint spec in this folder's README).
 */


export type TerminalProviderType = "ttyd" | "wetty" | "guacamole" | "sshwifty" | "custom";

export type TerminalProviderStatus = "running" | "stopped" | "error" | "installing";


export interface InstalledProvider {
  id: number;
  /** Stable slug — matches marketplace id for built-ins, or user-given slug for custom. */
  slug: string;
  name: string;
  type: TerminalProviderType;
  status: TerminalProviderStatus;
  /** Resolved base URL of the provider container (post-port mapping). */
  endpoint: string;
  /** Template still containing {vm_id}/{token} placeholders. */
  url_template: string;
  /** Whether this is the active provider used by the in-app terminal drawer. */
  active: boolean;
  /** ISO timestamp of last status transition. */
  updated_at: string;
  /** Last error message if status === "error". */
  error?: string;
}


export interface InstallStep {
  key: "pull" | "create" | "start" | "healthcheck";
  label: string;
  status: "pending" | "running" | "done" | "error";
  detail?: string;
}


export interface CustomProviderDraft {
  name: string;
  image: string;
  internal_port: number;
  external_port: number;
  url_template: string;
  healthcheck: string;
  env: Array<{ key: string; value: string }>;
}
