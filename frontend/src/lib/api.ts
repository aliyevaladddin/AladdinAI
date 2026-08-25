// NOTICE: This file is protected under RCF-PL
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/* ── Token helpers ───────────────────────────────────────────────── */

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}


function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}


function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ── Auto-refresh logic ──────────────────────────────────────────── */
let refreshPromise: Promise<string | null> | null = null;


async function tryRefresh(): Promise<string | null> {
  // Deduplicate concurrent refresh calls
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);
      return data.access_token as string;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/* ── Core fetch with auto-retry on 401 ──────────────────────────── */

async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  // First attempt
  let res = await fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers as Record<string, string> ?? {}) },
  });

  // If 401 — try refresh and retry once
  if (res.status === 401) {
    const newToken = await tryRefresh();
    if (!newToken) {
      // Refresh failed — clear session and redirect to login
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (typeof window !== "undefined") window.location.href = "/login";
      return res;
    }
    // Retry with new token
    res = await fetch(url, {
      ...init,
      headers: {
        ...{ Authorization: `Bearer ${newToken}` },
        ...(init.headers as Record<string, string> ?? {}),
      },
    });
  }

  return res;
}

/* ── Legacy standalone helpers ───────────────────────────────────── */

export async function fetchStats() {
  const res = await apiFetch(`${API_URL}/dashboard/stats`);
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}


export async function fetchAgents() {
  const res = await apiFetch(`${API_URL}/agents`);
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}


export async function fetchDeals() {
  const res = await apiFetch(`${API_URL}/crm/deals`);
  if (!res.ok) throw new Error("Failed to fetch deals");
  return res.json();
}

/* ── In-Memory SWR Cache ─────────────────────────────────────────── */
//
// CONVENTION: Every mutating method (POST, PUT, PATCH, DELETE) must call
// `apiCache.delete(...)` for the affected resource and its parent list.
// Without this, the frontend serves stale data after edits — e.g.
// changing an agent's model via PUT /agents/{id} leaves the old model
// in GET /agents cache, so the chat page uses the wrong model.
//
// Pattern: for a mutation on `/agents/3`, invalidate both
//   `/agents/3` (the resource) and `/agents` (the list).
//
interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
}
const apiCache = new Map<string, CacheEntry>();
const DEFAULT_CACHE_TTL = 15000; // 15 seconds default

/** Extract the parent list path from a resource path.
 *  `/agents/3/traces` → `/agents/3` (parent of the nested resource)
 *  `/agents/3` → `/agents` (list)
 */
function parentPath(path: string): string {
  return path.replace(/\/\d+(\/|$)/, "/");
}

/** Invalidate cache for a resource and its parent list.
 *  Call after every successful POST/PUT/PATCH/DELETE. */
function invalidateMutated(path: string): void {
  apiCache.delete(path);
  apiCache.delete(parentPath(path));
}

/* ── Main API object ─────────────────────────────────────────────── */
export const api = {
  getStats: fetchStats,
  getAgents: fetchAgents,
  getDeals: fetchDeals,

  setToken: (token: string | null) => {
    if (typeof window === "undefined") return;
    token
      ? localStorage.setItem("access_token", token)
      : localStorage.removeItem("access_token");
  },
  removeToken: () => {
    if (typeof window !== "undefined") localStorage.removeItem("access_token");
  },
  clearCache: (pathPattern?: string) => {
    if (!pathPattern) {
      apiCache.clear();
      return;
    }
    for (const key of apiCache.keys()) {
      if (key.includes(pathPattern)) apiCache.delete(key);
    }
  },

  get: async <T = any>(path: string, options?: { bypassCache?: boolean; ttlMs?: number }): Promise<T> => {
    const ttl = options?.ttlMs ?? DEFAULT_CACHE_TTL;
    const now = Date.now();
    if (!options?.bypassCache && apiCache.has(path)) {
      const entry = apiCache.get(path)!;
      if (now - entry.timestamp < ttl) {
        return entry.data as T;
      }
    }

    const res = await apiFetch(`${API_URL}${path}`);
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      console.error(`[API ERROR] GET ${path} | Status: ${res.status} | Body: ${errorText}`);
      throw new Error(`Failed to fetch ${path} (Status: ${res.status})`);
    }
    const text = await res.text();
    try {
      const data = JSON.parse(text) as T;
      apiCache.set(path, { data, timestamp: now });
      return data;
    } catch (parseErr) {
      console.error(`[API PARSE ERROR] GET ${path} failed to parse JSON. Raw body (length ${text.length}):`, text);
      throw new Error(`Failed to parse GET ${path} JSON response (length ${text.length}): ${parseErr instanceof Error ? parseErr.message : String(parseErr)} | Raw: ${text.slice(0, 500)}`);
    }
  },

  post: async <T = any>(path: string, body?: any): Promise<T> => {
    const res = await apiFetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      throw new Error(`Failed to POST to ${path} (Status: ${res.status}): ${errorText}`);
    }
    invalidateMutated(path);
    if (res.status === 204) return {} as T;
    const text = await res.text();
    try {
      return JSON.parse(text) as T;
    } catch (parseErr) {
      console.error(`[API PARSE ERROR] POST ${path} failed to parse JSON. Raw body (length ${text.length}):`, text);
      throw new Error(`Failed to parse POST ${path} JSON response (length ${text.length}): ${parseErr instanceof Error ? parseErr.message : String(parseErr)} | Raw: ${text.slice(0, 500)}`);
    }
  },

  put: async <T = any>(path: string, body?: any): Promise<T> => {
    const res = await apiFetch(`${API_URL}${path}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      throw new Error(`Failed to PUT to ${path} (Status: ${res.status}): ${errorText}`);
    }
    invalidateMutated(path);
    if (res.status === 204) return {} as T;
    return res.json();
  },

  patch: async <T = any>(path: string, body?: any): Promise<T> => {
    const res = await apiFetch(`${API_URL}${path}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      throw new Error(`Failed to PATCH ${path} (Status: ${res.status}): ${errorText}`);
    }
    invalidateMutated(path);
    if (res.status === 204) return {} as T;
    return res.json();
  },

  upload: async <T = any>(path: string, file: File, extraFields?: Record<string, string>): Promise<T> => {
    const fd = new FormData();
    fd.append("file", file);
    if (extraFields) {
      for (const [key, value] of Object.entries(extraFields)) fd.append(key, value);
    }
    const res = await apiFetch(`${API_URL}${path}`, { method: "POST", body: fd });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      throw new Error(`Failed to upload to ${path} (Status: ${res.status}): ${errorText}`);
    }
    return res.json();
  },

  delete: async <T = any>(path: string): Promise<T> => {
    const res = await apiFetch(`${API_URL}${path}`, { method: "DELETE" });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      throw new Error(`Failed to DELETE ${path} (Status: ${res.status}): ${errorText}`);
    }
    invalidateMutated(path);
    if (res.status === 204) return {} as T;
    return res.json();
  },
};

export function clearApiCache(pathPattern?: string) {
  api.clearCache(pathPattern);
}
