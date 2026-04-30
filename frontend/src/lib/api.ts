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

// Compatibility object for existing code
export const api = {
  getStats: fetchStats,
  getAgents: fetchAgents,
  getDeals: fetchDeals,
  // Added Generic support <T> to fix TypeScript errors
  get: async <T = any>(path: string): Promise<T> => {
    const headers = await getAuthHeader();
    const res = await fetch(`${API_URL}${path}`, { headers });
    if (!res.ok) throw new Error(`Failed to fetch ${path}`);
    return res.json();
  }
};
