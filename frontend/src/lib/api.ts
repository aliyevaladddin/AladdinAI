const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function getAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

export async function fetchStats() {
  const headers = await getAuthHeader();
  const res = await fetch(`${API_URL}/dashboard/stats`, { headers });
  if (!res.ok) throw new Error("Failed to fetch dashboard stats");
  return res.json();
}

export async function fetchAgents() {
  const headers = await getAuthHeader();
  const res = await fetch(`${API_URL}/agents`, { headers });
  if (!res.ok) throw new Error("Failed to fetch agents");
  return res.json();
}

export async function fetchDeals() {
  const headers = await getAuthHeader();
  const res = await fetch(`${API_URL}/crm/deals`, { headers });
  if (!res.ok) throw new Error("Failed to fetch deals");
  return res.json();
}

// Compatibility object for existing code with full CRUD and Token support
export const api = {
  getStats: fetchStats,
  getAgents: fetchAgents,
  getDeals: fetchDeals,
  
  // Auth state management
  setToken: (token: string | null) => {
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("access_token", token);
      } else {
        localStorage.removeItem("access_token");
      }
    }
  },
  removeToken: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
    }
  },

  get: async <T = any>(path: string): Promise<T> => {
    const headers = await getAuthHeader();
    const url = `${API_URL}${path}`;
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const errorText = await res.text().catch(() => "No error body");
      console.error(`[API ERROR] GET ${path} | Status: ${res.status} | Body: ${errorText}`);
      throw new Error(`Failed to fetch ${path} (Status: ${res.status})`);
    }
    return res.json();
  },

  post: async <T = any>(path: string, body?: any): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`Failed to POST to ${path}`);
    if (res.status === 204) return {} as T;
    return res.json();
  },

  put: async <T = any>(path: string, body?: any): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, {
      method: "PUT",
      headers: { ...headers, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new Error(`Failed to PUT to ${path}`);
    if (res.status === 204) return {} as T;
    return res.json();
  },

  delete: async <T = any>(path: string): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) throw new Error(`Failed to DELETE ${path}`);
    if (res.status === 204) return {} as T;
    return res.json();
  }
};
