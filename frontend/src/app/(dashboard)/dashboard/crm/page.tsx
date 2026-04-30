"use client";

const columns = [
  {
    id: "NEW_LEAD",
    title: "NEW_LEAD",
    count: 2,
    deals: [
      { id: "DL-8942", title: "Nexus Corp Integration", amount: "$145,000", probability: 32, contact: "A. CHEN" },
    ]
  },
  {
    id: "DISCOVERY",
    title: "DISCOVERY",
    count: 1,
    deals: [
      { id: "DL-9011", title: "Aegis Defense Systems", amount: "$850,000", probability: 68, contact: "S. VANCE" },
    ]
  },
  {
    id: "PROPOSAL",
    title: "PROPOSAL",
    count: 0,
    deals: []
  }
];

export default function CRMPage() {
  return (
    <div className="space-y-stack-lg animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex justify-between items-end border-b border-white/5 pb-4 bg-surface-plate/40 p-4 rounded-t-lg">
        <div>
          <h1 className="text-3xl font-black font-header tracking-[0.2em] text-on-background uppercase">DEAL_MATRIX</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-[10px] font-mono text-cyan-400 flex items-center gap-1">
              <span className="material-symbols-outlined text-[12px]">security</span> END-TO-END ENCRYPTED
            </span>
            <span className="text-[10px] font-mono text-white/30 uppercase">// SOVEREIGN DATA ACTIVE</span>
          </div>
        </div>
        <div className="flex gap-4">
          <button className="flex items-center gap-2 text-[10px] font-header font-bold text-white/60 hover:text-white border border-white/10 px-4 py-2 uppercase tracking-widest transition-all">
            <span className="material-symbols-outlined text-sm">filter_alt</span> Filter
          </button>
          <button className="flex items-center gap-2 bg-cyan-400 text-black font-header font-bold px-4 py-2 uppercase tracking-widest text-[10px] hover:bg-cyan-300 transition-all shadow-cyan-pulse">
            <span className="material-symbols-outlined text-sm">add</span> New_Deal
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter h-[calc(100vh-250px)]">
        {columns.map(column => (
          <div key={column.id} className="flex flex-col gap-4">
            <div className="flex justify-between items-center bg-surface-plate/60 border border-white/10 p-3">
              <span className="text-xs font-header font-bold tracking-widest uppercase">{column.title}</span>
              <span className="text-[10px] font-mono text-white/30 bg-white/5 px-1.5 py-0.5">{column.count.toString().padStart(2, '0')}</span>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto pr-2">
              {column.deals.map(deal => (
                <div key={deal.id} className="glass-panel p-4 hover:border-cyan-400/50 transition-all cursor-pointer group relative">
                   <div className="flex justify-between items-start mb-4">
                      <span className="text-[9px] font-mono text-cyan-400/60 uppercase tracking-widest">ID: {deal.id}</span>
                      <span className="material-symbols-outlined text-cyan-400 text-sm">shield</span>
                   </div>
                   
                   <h3 className="text-sm font-header font-bold text-on-background mb-1 group-hover:text-cyan-400 transition-colors uppercase tracking-tight">
                      {deal.title}
                   </h3>
                   <p className="text-lg font-black font-header mb-4">{deal.amount}</p>

                   <div className="space-y-1 mb-6">
                      <div className="flex justify-between text-[9px] font-mono uppercase tracking-widest">
                        <span className="text-white/30">AI_Probability</span>
                        <span className="text-cyan-400">{deal.probability}%</span>
                      </div>
                      <div className="w-full h-1 bg-white/5 overflow-hidden">
                        <div 
                          className="h-full bg-cyan-400 shadow-cyan-pulse transition-all duration-1000" 
                          style={{ width: `${deal.probability}%` }}
                        ></div>
                      </div>
                   </div>

                   <div className="flex items-center justify-between pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center">
                          <span className="material-symbols-outlined text-[12px] text-white/40">person</span>
                        </div>
                        <span className="text-[10px] font-mono text-white/60 uppercase">{deal.contact}</span>
                      </div>
                      <div className="flex gap-2">
                        <button className="text-white/20 hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-sm">mail</span></button>
                        <button className="text-white/20 hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-sm">call</span></button>
                      </div>
                   </div>
                </div>
              ))}

              {column.deals.length === 0 && (
                <div className="h-full border-2 border-dashed border-white/5 flex flex-col items-center justify-center opacity-20 hover:opacity-40 transition-all group">
                   <span className="material-symbols-outlined text-4xl mb-2 group-hover:animate-pulse">layers</span>
                   <span className="text-[10px] font-mono uppercase tracking-[0.2em]">Drop_Zone</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
