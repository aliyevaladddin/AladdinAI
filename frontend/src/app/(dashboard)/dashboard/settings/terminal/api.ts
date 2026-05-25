/**
 * Thin client + adapter between this page's view models (InstalledProvider /
 * CustomProviderDraft) and the backend contract under /api/terminal/providers.
 *
 * Keeping all wire-format knowledge here means the page component doesn't have
 * to know that the backend says `set_active` while we say `activate`, or that
 * `ProviderResponse` lacks `slug`/`active`/`updated_at` and we derive them.
 *
 * When we switch to OpenAPI-generated types (next step), this file becomes the
 * one place to delete.
 */

import { api } from "@/lib/api";
import type {
  InstalledProvider,
  CustomProviderDraft,
  TerminalProviderType,
  TerminalProviderStatus,
} from "./types";

/** Backend `ProviderResponse` — mirrors backend/app/schemas/terminal.py */
interface BackendProvider {
  id: number;
  name: string;
  type: string;
  source: string;
  image: string;
  internal_port: number;
  requires_ssh_proxy: boolean;
  is_active: boolean;
  status: string;
  container_id?: string | null;
  last_health_at?: string | null;
  last_error?: string | null;
  created_at: string;
}

function adaptProvider(b: BackendProvider): InstalledProvider {
  const status: TerminalProviderStatus =
    b.status === "running" || b.status === "stopped" || b.status === "error" || b.status === "installing"
      ? (b.status as TerminalProviderStatus)
      : "stopped";

  return {
    id: b.id,
    slug: b.type,
    name: b.name,
    type: (b.type as TerminalProviderType),
    status,
    endpoint: "",
    url_template: "",
    active: b.is_active,
    updated_at: b.last_health_at ?? b.created_at,
    error: b.last_error ?? undefined,
  };
}

export async function listProviders(): Promise<InstalledProvider[]> {
  const res = await api.get<BackendProvider[]>("/terminal/providers");
  return Array.isArray(res) ? res.map(adaptProvider) : [];
}

export async function installPreset(presetType: string, name?: string, vmId?: number): Promise<InstalledProvider> {
  const res = await api.post<BackendProvider>("/terminal/providers", {
    type: presetType,
    name,
    vm_id: vmId,
  });
  return adaptProvider(res);
}

export async function installCustom(draft: CustomProviderDraft): Promise<InstalledProvider> {
  // Backend reads image/internal_port from the YAML manifest keyed by `type`.
  // Until a real `custom` manifest exists we send the user fields under config
  // and let the backend ignore unknown keys (config is `Dict[str, Any]`).
  const res = await api.post<BackendProvider>("/terminal/providers", {
    type: "custom",
    name: draft.name,
    config: {
      image: draft.image,
      internal_port: draft.internal_port,
      external_port: draft.external_port,
      url_template: draft.url_template,
      healthcheck: draft.healthcheck,
      env: draft.env,
    },
  });
  return adaptProvider(res);
}

export async function startProvider(id: number): Promise<InstalledProvider> {
  const res = await api.post<BackendProvider>(`/terminal/providers/${id}/start`);
  return adaptProvider(res);
}

export async function stopProvider(id: number): Promise<InstalledProvider> {
  const res = await api.post<BackendProvider>(`/terminal/providers/${id}/stop`);
  return adaptProvider(res);
}

export async function activateProvider(id: number): Promise<InstalledProvider> {
  const res = await api.post<BackendProvider>(`/terminal/providers/${id}/set_active`);
  return adaptProvider(res);
}

export async function uninstallProvider(id: number): Promise<void> {
  await api.delete(`/terminal/providers/${id}`);
}

/**
 * Drawer "Quick Setup" — get the user from an empty state to a working
 * terminal with one click. We pick whichever provider best matches "ready
 * to run with no extra config", and walk it through install → start →
 * activate. Steps that already match are skipped, so the same call works
 * whether the user has nothing, has it installed but stopped, or has it
 * stopped+inactive.
 *
 * Returns the final InstalledProvider (running + active) on success.
 */
export async function quickSetupDefault(preferredType = "ttyd"): Promise<InstalledProvider> {
  const list = await listProviders();
  let provider = list.find((p) => p.type === preferredType) ?? null;

  if (!provider) {
    provider = await installPreset(preferredType);
  }

  if (provider.status !== "running") {
    provider = await startProvider(provider.id);
  }

  if (!provider.active) {
    provider = await activateProvider(provider.id);
  }

  return provider;
}
