"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const formData = new FormData(e.currentTarget);
    const email = formData.get("email");
    const password = formData.get("password");
    const name = formData.get("name");

    try {
      const res = await fetch("http://localhost:8000/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Registration failed");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background bg-grid-pattern relative overflow-hidden">
      {/* Decorative pulse background */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-400/5 rounded-full blur-[120px] animate-pulse"></div>

      <div className="w-full max-w-md p-gutter relative z-10">
        <div className="glass-panel p-8 space-y-8 relative">
          {/* Tech Header */}
          <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-50"></div>
          
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-black font-header tracking-[0.3em] text-cyan-400 cyan-text-glow uppercase">INITIALIZE_ID</h1>
            <p className="text-[10px] font-mono text-white/40 tracking-[0.2em] uppercase">Join the Sovereign Intelligence Network</p>
          </div>

          {error && (
            <div className="bg-red-400/10 border border-red-400/30 p-3 text-[10px] font-mono text-red-400 uppercase tracking-widest text-center">
              Error: {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest ml-1">Operator_Name</label>
                <input 
                  name="name"
                  type="text" 
                  className="w-full bg-surface-plate border-b border-white/20 focus:border-cyan-400 focus:ring-0 text-white font-mono text-sm px-4 py-3 outline-none transition-all"
                  placeholder="EX: ALADDIN_X9"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest ml-1">Email_Identity</label>
                <input 
                  name="email"
                  type="email" 
                  className="w-full bg-surface-plate border-b border-white/20 focus:border-cyan-400 focus:ring-0 text-white font-mono text-sm px-4 py-3 outline-none transition-all"
                  placeholder="USER@SOVEREIGN.IO"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest ml-1">Secure_Key</label>
                <input 
                  name="password"
                  type="password" 
                  className="w-full bg-surface-plate border-b border-white/20 focus:border-cyan-400 focus:ring-0 text-white font-mono text-sm px-4 py-3 outline-none transition-all"
                  placeholder="********"
                  required
                />
              </div>
            </div>

            <button 
              disabled={loading}
              className="w-full bg-cyan-400 text-black font-header font-bold py-4 text-xs uppercase tracking-[0.3em] hover:bg-cyan-300 active:scale-[0.98] transition-all shadow-cyan-pulse flex items-center justify-center gap-3"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                  ENCRYPTING...
                </>
              ) : (
                "CREATE_SOVEREIGN_ID"
              )}
            </button>
          </form>

          <div className="pt-6 border-t border-white/5 text-center">
            <Link href="/login" className="text-[10px] font-mono text-cyan-400/60 hover:text-cyan-400 transition-colors uppercase tracking-widest">
              Already have an ID? RECALL_SESSION
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
