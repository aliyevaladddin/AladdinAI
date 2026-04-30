const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function getAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
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

// Compatibility object for existing code with full CRUD support
export const api = {
  getStats: fetchStats,
  getAgents: fetchAgents,
  getDeals: fetchDeals,
  
  get: async <T = any>(path: string): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, { headers });
    if (!res.ok) throw new Error(`Failed to fetch ${path}`);
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
    return res.json();
  },

  delete: async <T = any>(path: string): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) throw new Error(`Failed to DELETE ${path}`);
    return res.json();
  }
};
