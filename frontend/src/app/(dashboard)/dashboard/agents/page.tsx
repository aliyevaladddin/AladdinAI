"use client";

const agents = [
  {
    id: "AGT-001",
    name: "Sentinel-Alpha",
    role: "CUSTOMER_ROUTING",
    engine: "MiniCPM3",
    latency: "42ms",
    status: "ACTIVE",
    channels: ["Telegram", "SMS"],
  },
  {
    id: "AGT-002",
    name: "Nexus-Beta",
    role: "DATA_EXTRACTION",
    engine: "BentoML",
    latency: "120ms",
    status: "STANDBY",
    channels: ["WhatsApp"],
  },
];

export default function AgentsPage() {
  return (
    <div className="flex gap-gutter h-full animate-in slide-in-from-right duration-500">
      {/* Left Section: Agent Cards */}
      <div className="flex-1 space-y-stack-lg">
        <div className="flex justify-between items-end border-b border-white/5 pb-4">
          <div>
            <h1 className="text-3xl font-black font-header tracking-widest text-on-background">ACTIVE AGENTS</h1>
            <p className="text-xs text-white/40 mt-2 max-w-md leading-relaxed">
              Monitor and configure deployed autonomous entities. Adjust LLM providers, routing protocols, and active communication channels in real-time.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-gutter">
          {agents.map((agent) => (
            <div key={agent.id} className={`glass-panel p-6 relative group transition-all hover:border-cyan-400/50 ${agent.status === 'ACTIVE' ? 'border-cyan-400/30' : ''}`}>
              <div className="flex justify-between items-start mb-6">
                <span className="text-[10px] font-mono text-white/40 tracking-widest uppercase">ID: {agent.id}</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 border ${agent.status === 'ACTIVE' ? 'text-cyan-400 border-cyan-400/30 bg-cyan-400/10' : 'text-white/40 border-white/10'} tracking-widest uppercase`}>
                  SYS.OP.{agent.status}
                </span>
              </div>

              <div className="space-y-1 mb-8">
                <h3 className="text-2xl font-black font-header tracking-widest flex items-center gap-2">
                  {agent.name}
                  {agent.status === 'ACTIVE' && <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-cyan-glow"></span>}
                </h3>
                <p className="text-[10px] font-mono text-white/40 tracking-widest">ROLE: {agent.role}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-4 mb-6">
                <div>
                  <p className="text-[9px] font-mono text-white/20 uppercase">Engine</p>
                  <p className="text-xs font-mono text-white/80">{agent.engine}</p>
                </div>
                <div>
                  <p className="text-[9px] font-mono text-white/20 uppercase">Latency</p>
                  <p className="text-xs font-mono text-cyan-400">{agent.latency}</p>
                </div>
              </div>

              <div className="flex gap-2">
                {agent.channels.map(channel => (
                  <span key={channel} className="text-[9px] font-mono text-white/40 border border-white/10 px-1.5 py-0.5 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[10px]">arrow_right</span> {channel}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Section: Configuration Panel */}
      <div className="w-80 glass-panel p-6 flex flex-col h-fit shrink-0">
        <div className="flex justify-between items-center mb-8 border-b border-white/5 pb-4">
          <span className="text-sm font-black font-header tracking-widest uppercase">Configuration</span>
          <button className="text-white/40 hover:text-cyan-400"><span className="material-symbols-outlined">close</span></button>
        </div>

        <div className="space-y-6">
          <div className="space-y-2">
            <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest">LLM Provider</label>
            <select className="w-full bg-surface-container border border-white/10 text-white font-mono text-xs px-3 py-2 outline-none focus:border-cyan-400 transition-all">
              <option>MiniCPM3 (High Speed)</option>
              <option>BentoML Local</option>
              <option>OpenAI GPT-4o</option>
            </select>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest">System Prompt</label>
              <span className="text-[9px] font-mono text-cyan-400/60 lowercase">{'{variables}'} supported</span>
            </div>
            <textarea 
              className="w-full h-32 bg-surface-container border border-white/10 text-white font-mono text-xs p-3 outline-none focus:border-cyan-400 transition-all resize-none placeholder:text-white/10"
              placeholder="Enter system instructions..."
            ></textarea>
          </div>

          <div className="space-y-3">
            <label className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Active Channels</label>
            <div className="space-y-2">
              {['Telegram', 'WhatsApp', 'SMS Gateway'].map(channel => (
                <label key={channel} className="flex items-center justify-between group cursor-pointer">
                  <span className="text-xs font-mono text-white/60 group-hover:text-white flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm">
                      {channel === 'Telegram' ? 'send' : channel === 'WhatsApp' ? 'chat' : 'sms'}
                    </span>
                    {channel}
                  </span>
                  <input type="checkbox" defaultChecked={channel !== 'WhatsApp'} className="appearance-none w-3 h-3 border border-white/20 checked:bg-cyan-400 checked:border-transparent transition-all"/>
                </label>
              ))}
            </div>
          </div>

          <button className="w-full border border-cyan-400 text-cyan-400 font-header text-[12px] font-bold py-3 mt-4 hover:bg-cyan-400 hover:text-black transition-all tracking-widest uppercase">
            COMMIT CHANGES
          </button>
        </div>
      </div>
    </div>
  );
}
