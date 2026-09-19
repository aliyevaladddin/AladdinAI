// NOTICE: This file is protected under RCF-PL
"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, API_URL, authedFetch } from "@/lib/api";


interface User {
  id: number;
  email: string;
  name: string;
}


interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);


export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      api.setToken(token);
      authedFetch(`${API_URL}/auth/me`)
        .then(async (res) => {
          // Only clear tokens on definitive auth failure — transient 5xx
          // (backend blip, proxy hiccup) should not log the user out.
          if (res.status === 401 || res.status === 403) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            return;
          }
          if (!res.ok) return;
          setUser(await res.json());
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);


  const login = async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/login", { email, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    api.setToken(data.access_token);
    api.clearCache("/auth/me");
    const me = await api.get<User>("/auth/me", { bypassCache: true });
    setUser(me);
  };


  const register = async (email: string, password: string, name: string) => {
    const data = await api.post<{ access_token: string; refresh_token: string }>("/auth/register", { email, password, name });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    api.setToken(data.access_token);
    api.clearCache("/auth/me");
    const me = await api.get<User>("/auth/me", { bypassCache: true });
    setUser(me);
  };


  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    api.setToken(null);
    setUser(null);
  };

  return <AuthContext value={{ user, loading, login, register, logout }}>{children}</AuthContext>;
}


export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
