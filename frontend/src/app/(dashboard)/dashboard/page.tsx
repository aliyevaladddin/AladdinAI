"use client";

import { useEffect, useState } from "react";
import { fetchStats } from "@/lib/api";

export default function CommandCenter() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-cyan-400 font-mono text-sm uppercase tracking-widest">
          Synchronizing_With_Neural_OS...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-stack-lg animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex justify-between items-end border-b border-white/5 pb-4">
        <div>
          <span className="text-[10px] font-mono text-cyan-400 tracking-[0.2em] uppercase">System Online</span>
          <h1 className="text-4xl font-black font-header tracking-widest text-on-background mt-1">COMMAND_CENTER</h1>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-mono text-white/40">TS: {Date.now()}</p>
          <p className="text-[10px] font-mono text-white/40">NODE: ALD-PRIME-01</p>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
        {/* Active Agents */}
        <div className="glass-panel p-6 relative group hover:border-cyan-400/30 transition-all">
          <div className="flex justify-between items-start mb-4">
            <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">Active Agents</span>
            <span className="text-[10px] font-mono text-white/30">IDX-01</span>
          </div>
          <div className="flex items-baseline gap-4">
            <span className="text-5xl font-black font-header tracking-tighter">{stats?.active_agents || 0}</span>
            <span className="text-cyan-400 text-sm font-bold font-mono">+100%</span>
          </div>
        </div>

        {/* Deals In Progress */}
        <div className="glass-panel p-6 relative group hover:border-cyan-400/30 transition-all">
          <div className="flex justify-between items-start mb-4">
            <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">Deals In Progress</span>
            <span className="text-[10px] font-mono text-white/30">IDX-02</span>
          </div>
          <div className="flex items-baseline gap-4">
            <span className="text-5xl font-black font-header tracking-tighter">{stats?.deals_in_progress || 0}</span>
          </div>
        </div>

        {/* Total Contacts */}
        <div className="glass-panel p-6 relative group hover:border-cyan-400/30 transition-all border-cyan-400/50">
          <div className="flex justify-between items-start mb-4">
            <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">Total Contacts</span>
            <span className="text-[10px] font-mono text-white/30">IDX-03</span>
          </div>
          <div className="flex items-baseline gap-4">
            <span className="text-5xl font-black font-header tracking-tighter">
              {stats?.total_contacts >= 1000 ? `${(stats.total_contacts/1000).toFixed(1)}K` : stats?.total_contacts || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Secondary Grid: Activity & Security */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        {/* Neural Net Activity Chart */}
        <div className="lg:col-span-2 glass-panel p-6">
          <div className="flex justify-between items-center mb-8">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-cyan-400 text-lg">analytics</span>
              <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest">Neural Net Activity</span>
            </div>
            <span className="text-[10px] font-mono text-white/20 uppercase">SYS-PULSE</span>
          </div>
          
          <div className="h-48 flex items-end gap-1 px-2">
            {[40, 60, 45, 90, 65, 30, 50, 75, 40, 85, 30, 45, 60, 35, 70].map((height, i) => (
              <div 
                key={i} 
                className="flex-1 bg-cyan-400/20 border-t border-cyan-400/40 relative group"
                style={{ height: `${height}%` }}
              >
                <div className="absolute inset-0 bg-cyan-400 opacity-0 group-hover:opacity-20 transition-opacity"></div>
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-4 text-[9px] font-mono text-white/20 uppercase">
            <span>T-00:15:00</span>
            <span>T-00:00:00 (NOW)</span>
          </div>
        </div>

        {/* RCF Framework Security Status */}
        <div className="glass-panel p-6 flex flex-col items-center justify-center text-center space-y-4">
          <span className="text-[10px] font-mono text-white/50 uppercase tracking-widest self-start">RCF Framework</span>
          
          <div className="relative">
            <div className="w-24 h-24 rounded-full border-2 border-cyan-400/20 flex items-center justify-center relative">
              <span className="material-symbols-outlined text-cyan-400 text-5xl cyan-text-glow">shield</span>
              <div className="absolute inset-0 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin duration-[3s]"></div>
            </div>
          </div>

          <div className="space-y-1">
            <h3 className="text-xl font-black font-header tracking-widest text-cyan-400 cyan-text-glow">{stats?.system_status || "SECURE"}</h3>
            <p className="text-[10px] font-mono text-cyan-400/60 uppercase">Active_State</p>
          </div>

          <div className="w-full pt-4 border-t border-white/5 flex justify-between text-[10px] font-mono">
            <div className="text-left">
              <p className="text-white/20 uppercase">Encryption</p>
              <p className="text-white/60">AES-256-GCM</p>
            </div>
            <div className="text-right">
              <p className="text-white/20 uppercase">Threat Lvl</p>
              <p className="text-red-400/60">0.001%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Event Log */}
      <div className="glass-panel overflow-hidden">
        <div className="p-4 border-b border-white/10 flex justify-between items-center bg-white/[0.02]">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/50 uppercase tracking-widest">
            <span className="material-symbols-outlined text-sm">list_alt</span>
            System Event Log
          </div>
          <button className="text-[10px] font-mono text-white/40 hover:text-cyan-400 transition-colors flex items-center gap-1">
            <span className="material-symbols-outlined text-[12px]">download</span> EXPORT
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-white/30 text-left border-b border-white/5">
                <th className="px-6 py-3 font-medium uppercase tracking-widest">Timestamp</th>
                <th className="px-6 py-3 font-medium uppercase tracking-widest">Source</th>
                <th className="px-6 py-3 font-medium uppercase tracking-widest">Event_Signature</th>
                <th className="px-6 py-3 font-medium uppercase tracking-widest text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.02]">
              {stats?.recent_activities?.map((activity: any) => (
                <tr key={activity.id} className="hover:bg-cyan-400/5 transition-colors">
                  <td className="px-6 py-3 text-cyan-400/60">{new Date(activity.created_at).toLocaleTimeString()}</td>
                  <td className="px-6 py-3 text-white/60">SYS_CORE</td>
                  <td className="px-6 py-3 text-white/80">{activity.content.toUpperCase()}</td>
                  <td className="px-6 py-3 text-right">
                    <span className="text-cyan-400 bg-cyan-400/10 px-1.5 py-0.5 border border-cyan-400/30 uppercase">
                      Verified
                    </span>
                  </td>
                </tr>
              ))}
              {(!stats?.recent_activities || stats.recent_activities.length === 0) && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-white/20 uppercase tracking-[0.2em]">
                    No recent events logged
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
