"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Simulating secure handshake
    setTimeout(() => {
      router.push("/dashboard");
    }, 1500);
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
            <h1 className="text-3xl font-black font-header tracking-[0.3em] text-cyan-400 cyan-text-glow uppercase">AladdinAI</h1>
            <p className="text-[10px] font-mono text-white/40 tracking-[0.2em] uppercase">Sovereign Agent Command Center</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest ml-1">Operator_ID</label>
                <input 
                  type="text" 
                  className="w-full bg-surface-plate border-b border-white/20 focus:border-cyan-400 focus:ring-0 text-white font-mono text-sm px-4 py-3 outline-none transition-all"
                  placeholder="IDENTIFY..."
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-mono text-white/30 uppercase tracking-widest ml-1">Secure_Key</label>
                <input 
                  type="password" 
                  className="w-full bg-surface-plate border-b border-white/20 focus:border-cyan-400 focus:ring-0 text-white font-mono text-sm px-4 py-3 outline-none transition-all"
                  placeholder="********"
                  required
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] font-mono">
              <label className="flex items-center gap-2 text-white/40 cursor-pointer hover:text-white transition-colors">
                <input type="checkbox" className="appearance-none w-3 h-3 border border-white/20 checked:bg-cyan-400 transition-all"/>
                REMEMBER_ME
              </label>
              <a href="#" className="text-cyan-400/60 hover:text-cyan-400 transition-colors uppercase tracking-widest">Forgot_Key?</a>
            </div>

            <button 
              disabled={loading}
              className="w-full bg-cyan-400 text-black font-header font-bold py-4 text-xs uppercase tracking-[0.3em] hover:bg-cyan-300 active:scale-[0.98] transition-all shadow-cyan-pulse flex items-center justify-center gap-3"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                  INITIALIZING...
                </>
              ) : (
                "ESTABLISH_CONNECTION"
              )}
            </button>
          </form>

          <div className="pt-6 border-t border-white/5 text-center flex flex-col gap-2">
            <Link href="/register" className="text-[10px] font-mono text-cyan-400/60 hover:text-cyan-400 transition-colors uppercase tracking-widest mb-2">
              New Operator? INITIALIZE_ID
            </Link>
            <span className="text-[9px] font-mono text-white/20 uppercase tracking-widest">
              RCF Protocol v2.0.3 // Secure Handshake Active
            </span>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-8 flex justify-between px-2 opacity-30 font-mono text-[9px] uppercase tracking-widest">
           <span>Lat: 42.129N</span>
           <span>Lng: 18.341E</span>
           <span>ID: ALD-X9-01</span>
        </div>
      </div>
    </div>
  );
}
