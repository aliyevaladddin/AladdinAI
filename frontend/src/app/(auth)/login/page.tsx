// NOTICE: This file is protected under RCF-PL
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/providers/auth-provider";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="mb-7">

        <h1 className="text-[22px] font-semibold tracking-tight">Sign in</h1>
        <p className="text-[13px] mt-1.5" style={{ color: "var(--color-fg-muted)" }}>
          Welcome back. Enter your credentials to continue.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        {error && (
          <div
            className="rounded-md px-3 py-2 text-[12px]"
            style={{
              background: "var(--color-danger-soft)",
              color: "var(--color-danger)",
            }}
          >
            {error}
          </div>
        )}
        <div>
          <label
            htmlFor="email"
            className="block text-[12px] font-medium mb-1.5"
            style={{ color: "var(--color-fg-muted)" }}
          >
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            required
            autoFocus
          />
        </div>
        <div>
          <label
            htmlFor="password"
            className="block text-[12px] font-medium mb-1.5"
            style={{ color: "var(--color-fg-muted)" }}
          >
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            required
          />
        </div>
        <button type="submit" className="btn btn-primary w-full mt-4" disabled={loading}>

          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p
        className="text-center text-[13px] mt-6"
        style={{ color: "var(--color-fg-muted)" }}
      >
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium"
          style={{ color: "var(--color-fg)" }}
        >
          Create one
        </Link>
      </p>
    </div>
  );
}
