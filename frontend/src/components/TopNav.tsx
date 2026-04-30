"use client";

export function TopNav() {
  return (
    <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-6 h-16 bg-black/40 backdrop-blur-xl border-b border-white/10 shadow-[0_0_15px_rgba(0,255,255,0.15)]">
      <div className="flex items-center gap-4">
        <span className="text-xl font-black text-cyan-400 tracking-widest font-header uppercase">SOVEREIGN_CMD</span>
      </div>

      <div className="flex items-center gap-6">
        {/* Search Bar */}
        <div className="relative flex items-center group">
          <span className="material-symbols-outlined absolute left-3 text-white/40 group-focus-within:text-cyan-400 transition-colors text-sm">search</span>
          <input 
            className="w-64 bg-surface-plate border-b border-white/10 focus:border-cyan-400 focus:ring-0 text-cyan-400 font-mono text-[12px] pl-9 pr-4 py-1.5 outline-none transition-all placeholder:text-white/20" 
            placeholder="QUERY_NETWORK..." 
            type="text"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-4 border-l border-white/10 pl-6">
          <button className="text-white/60 hover:text-cyan-300 hover:bg-cyan-400/10 active:scale-95 duration-200 ease-in-out p-1.5 rounded transition-colors relative">
            <span className="material-symbols-outlined">notifications</span>
            <span className="absolute top-1 right-1 w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-[0_0_5px_rgba(0,255,255,0.8)]"></span>
          </button>
          <button className="text-white/60 hover:text-cyan-300 hover:bg-cyan-400/10 active:scale-95 duration-200 ease-in-out p-1.5 rounded transition-colors">
            <span className="material-symbols-outlined">security</span>
          </button>
          <button className="text-white/60 hover:text-cyan-300 hover:bg-cyan-400/10 active:scale-95 duration-200 ease-in-out p-1.5 rounded transition-colors">
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>

        {/* Primary Action */}
        <button className="ml-4 bg-cyan-400 text-black font-header text-[12px] font-bold px-4 py-1.5 hover:bg-cyan-300 active:scale-95 transition-all shadow-[0_0_10px_rgba(0,255,255,0.3)] tracking-widest uppercase">
          DEPLOY_AGENT
        </button>

        {/* Profile */}
        <div className="ml-2 w-8 h-8 rounded-full border border-cyan-400/50 overflow-hidden bg-black flex items-center justify-center">
          <span className="material-symbols-outlined text-white/40 text-lg">person</span>
        </div>
      </div>
    </nav>
  );
}
