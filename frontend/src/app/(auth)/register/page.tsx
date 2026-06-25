// NOTICE: This file is protected under RCF-PL
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/providers/auth-provider";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

// [RCF:PROTECTED]
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, password, name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <div className="mb-7">
        <h1 className="text-[22px] font-semibold tracking-tight">Create your account</h1>
        <p className="text-[13px] mt-1.5" style={{ color: "var(--color-fg-muted)" }}>
          A few details and you&apos;re in. No credit card needed.
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
              className="block text-[12px] font-medium mb-1.5"
              style={{ color: "var(--color-fg-muted)" }}
            >
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              required
              autoFocus
            />
          </div>
          <div>
            <label
              className="block text-[12px] font-medium mb-1.5"
              style={{ color: "var(--color-fg-muted)" }}
            >
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              required
            />
          </div>
          <div>
            <label
              className="block text-[12px] font-medium mb-1.5"
              style={{ color: "var(--color-fg-muted)" }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="btn btn-primary w-full mt-4" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>

        <p
          className="text-center text-[13px] mt-6"
          style={{ color: "var(--color-fg-muted)" }}
        >
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium"
            style={{ color: "var(--color-fg)" }}
          >
// [RCF:PROTECTED]
            Sign in
          </Link>
        </p>
    </div>
  );
}
