"use client";

export default function CommsPage() {
  return (
    <div className="flex h-[calc(100vh-64px)] w-[calc(100vw-256px)] -m-gutter overflow-hidden relative z-10 font-sans">
      {/* Pane 1: Routing Nodes */}
      <section className="w-64 bg-surface-plate/80 backdrop-blur-md border-r border-white/10 flex flex-col relative z-20">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <span className="font-mono text-[10px] text-white/50 tracking-widest uppercase">Routing_Nodes</span>
          <button className="text-white/40 hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-[16px]">add</span></button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-6">
          <div>
            <h3 className="text-[10px] font-header font-bold text-cyan-400/60 mb-2 px-2 uppercase tracking-widest">Live Streams</h3>
            <ul className="space-y-1">
              <li>
                <a className="flex items-center gap-3 px-2 py-1.5 bg-cyan-400/5 border-l-2 border-cyan-400 text-on-background hover:bg-cyan-400/10 transition-colors group" href="#">
                  <span className="material-symbols-outlined text-[18px] text-cyan-400">send</span>
                  <span className="font-mono text-xs flex-1">Telegram_Net</span>
                  <span className="text-[10px] bg-cyan-400/20 text-cyan-400 px-1 rounded-sm">12</span>
                </a>
              </li>
              <li>
                <a className="flex items-center gap-3 px-2 py-1.5 text-white/60 hover:text-on-background hover:bg-white/5 transition-colors group border-l-2 border-transparent" href="#">
                  <span className="material-symbols-outlined text-[18px]">chat</span>
                  <span className="font-mono text-xs flex-1">WhatsApp_Bus</span>
                </a>
              </li>
              <li>
                <a className="flex items-center gap-3 px-2 py-1.5 text-white/60 hover:text-on-background hover:bg-white/5 transition-colors group border-l-2 border-transparent" href="#">
                  <span className="material-symbols-outlined text-[18px]">sms</span>
                  <span className="font-mono text-xs flex-1">SMS_Gateway</span>
                  <span className="text-[10px] bg-white/10 px-1 rounded-sm">3</span>
                </a>
              </li>
            </ul>
          </div>
          <div>
            <h3 className="text-[10px] font-header font-bold text-cyan-400/60 mb-2 px-2 uppercase tracking-widest">Smart Queues</h3>
            <ul className="space-y-1">
              {['High_Priority', 'AI_Assigned', 'Pending_RCF'].map((item, i) => (
                <li key={item}>
                  <a className="flex items-center gap-3 px-2 py-1.5 text-white/60 hover:text-on-background hover:bg-white/5 transition-colors group border-l-2 border-transparent" href="#">
                    <span className="material-symbols-outlined text-[18px]">{['verified', 'robot_2', 'rule'][i]}</span>
                    <span className="font-mono text-xs uppercase">{item}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="p-3 border-t border-white/10 bg-black/40">
          <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 uppercase tracking-widest">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-cyan-pulse"></div>
            <span>HUB_ONLINE // ALL_SYS_GO</span>
          </div>
        </div>
      </section>

      {/* Pane 2: Message List */}
      <section className="w-[320px] bg-surface-lowest/90 backdrop-blur-md border-r border-white/10 flex flex-col relative z-10">
        <div className="p-4 border-b border-white/10 flex flex-col gap-3">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-header font-bold text-on-background uppercase tracking-widest">Inbox</h2>
            <button className="text-white/40 hover:text-cyan-400"><span className="material-symbols-outlined">filter_list</span></button>
          </div>
          <div className="relative">
            <input className="w-full bg-surface-plate border border-white/10 focus:border-cyan-400 focus:ring-0 text-white font-mono text-xs px-3 py-1.5 outline-none transition-all placeholder:text-white/20 rounded-sm" placeholder="Filter node traffic..." type="text"/>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto flex flex-col">
          <div className="p-3 border-b border-white/5 bg-cyan-400/5 cursor-pointer relative group">
            <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-cyan-400 shadow-cyan-pulse"></div>
            <div className="flex justify-between items-start mb-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px] text-cyan-400">send</span>
                <span className="font-mono text-xs text-cyan-400 font-bold uppercase">@Elara_Vance</span>
              </div>
              <span className="text-[10px] font-mono text-white/40">JUST NOW</span>
            </div>
            <p className="text-xs text-white/80 line-clamp-2 leading-relaxed">
              Initiating sequence for the new protocol. The cryptographic handshake is verified on my end.
            </p>
            <div className="mt-2">
              <span className="px-1.5 py-0.5 bg-cyan-400/10 border border-cyan-400/30 text-[9px] font-mono text-cyan-400 flex items-center gap-1 w-fit uppercase">
                <span className="material-symbols-outlined text-[10px]">verified_user</span> RCF: VAL
              </span>
            </div>
          </div>
          {/* Mock items */}
          <div className="p-3 border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors group opacity-60 hover:opacity-100">
            <div className="flex justify-between items-start mb-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px] text-white/40">chat</span>
                <span className="font-mono text-xs text-white/80 uppercase">Client_X49</span>
              </div>
              <span className="text-[10px] font-mono text-white/40">10:42 AM</span>
            </div>
            <p className="text-xs text-white/50 line-clamp-2 leading-relaxed italic">
              Can we get an update on the deployment schedule?
            </p>
          </div>
        </div>
      </section>

      {/* Pane 3: Active Conversation */}
      <section className="flex-1 flex flex-col bg-black/20 backdrop-blur-sm relative overflow-hidden">
        <header className="h-[72px] border-b border-white/10 bg-surface-plate/80 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full border border-cyan-400/30 overflow-hidden bg-black flex items-center justify-center">
               <span className="material-symbols-outlined text-cyan-400/40 text-2xl">person</span>
            </div>
            <div>
              <h2 className="font-mono text-sm font-bold text-on-background flex items-center gap-2 uppercase">
                @Elara_Vance
                <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full shadow-cyan-pulse"></span>
              </h2>
              <div className="flex items-center gap-2 text-[10px] font-mono text-white/40 mt-0.5">
                <span className="material-symbols-outlined text-[12px]">vpn_key</span>
                <span>Sess_ID: 0x8F9...A1B2</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-header font-bold text-white/50 uppercase tracking-widest">Connection Integrity</span>
              <span className="text-cyan-400 font-mono text-xs flex items-center gap-1 uppercase">
                <span className="material-symbols-outlined text-[14px]">shield_locked</span> Level 4 Sovereign
              </span>
            </div>
            <button className="w-8 h-8 flex items-center justify-center rounded border border-white/10 text-white/40 hover:text-cyan-400 transition-all ml-4">
              <span className="material-symbols-outlined text-[18px]">more_vert</span>
            </button>
          </div>
        </header>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col">
          <div className="flex flex-col items-start max-w-[80%] animate-in slide-in-from-left duration-300">
            <div className="flex items-center gap-1 mb-1 bg-surface-plate border border-cyan-400/20 px-2 py-0.5 rounded-t-sm w-fit border-b-0">
              <span className="material-symbols-outlined text-[10px] text-cyan-400">verified_user</span>
              <span className="font-mono text-[9px] text-cyan-400/80 uppercase">RCF Validated // Hash: 9a4f...</span>
            </div>
            <div className="bg-surface-plate border border-white/10 p-4 rounded-b-md rounded-tr-md shadow-lg relative text-sm text-white/90 leading-relaxed">
              <p>Initiating sequence for the new protocol. The cryptographic handshake is verified on my end. Awaiting confirmation before I push the payload to the primary node.</p>
              <span className="absolute right-2 bottom-1 text-[9px] font-mono text-white/30 uppercase">08:42:15Z</span>
            </div>
          </div>

          <div className="flex flex-col items-end max-w-[80%] self-end animate-in slide-in-from-right duration-300">
            <div className="bg-cyan-400/10 border border-cyan-400/30 p-4 rounded-b-md rounded-tl-md shadow-cyan-glow relative text-sm text-cyan-50 leading-relaxed">
              <p>Copy that. Handshake recognized. I am spinning up the secondary verification agent now. Hold for green light.</p>
              <span className="absolute left-2 bottom-1 text-[9px] font-mono text-cyan-400/50 flex items-center gap-1">
                <span className="material-symbols-outlined text-[10px]">done_all</span> 08:45:02Z
              </span>
            </div>
          </div>
        </div>

        {/* Composer Area */}
        <div className="p-6 bg-surface-plate/90 border-t border-white/10 backdrop-blur-xl shrink-0 flex flex-col gap-3">
          <div className="flex items-start gap-2 p-3 bg-white/[0.02] border border-white/5 rounded-sm relative group hover:border-cyan-400/30 transition-all">
            <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-cyan-400/50"></div>
            <span className="material-symbols-outlined text-[14px] text-cyan-400 mt-0.5">auto_awesome</span>
            <div className="flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] font-header font-bold text-cyan-400 uppercase tracking-widest">Agent Response Draft</span>
                <div className="flex gap-2">
                  <button className="text-[10px] font-mono text-white/40 hover:text-white transition-colors">Discard</button>
                  <button className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors">Insert</button>
                </div>
              </div>
              <p className="text-xs font-medium text-white/60 italic leading-relaxed">
                "Perimeter check complete. Secondary agent is active and monitoring. Proceed with Sovereign Protocol execution."
              </p>
            </div>
          </div>

          <div className="relative flex items-end gap-3">
            <div className="flex-1 bg-surface-lowest border-b border-white/20 focus-within:border-cyan-400 focus-within:shadow-[inset_0_-2px_0_rgba(0,255,255,0.5)] transition-all rounded-t-sm flex flex-col">
              <textarea className="w-full bg-transparent border-none focus:ring-0 text-white font-sans text-sm p-3 resize-none placeholder:text-white/20 outline-none" placeholder="Transmit message (End-to-End Encrypted)..." rows={2}></textarea>
              <div className="px-3 py-2 flex items-center justify-between border-t border-white/5">
                <div className="flex items-center gap-3 text-white/40">
                  <button className="hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-[18px]">attach_file</span></button>
                  <button className="hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-[18px]">terminal</span></button>
                  <button className="hover:text-cyan-400 transition-colors"><span className="material-symbols-outlined text-[18px]">lock</span></button>
                </div>
                <span className="font-mono text-[10px] text-white/30 uppercase">Ctrl+Enter to Send</span>
              </div>
            </div>
            <button className="bg-cyan-400 text-black w-12 h-12 flex items-center justify-center rounded-sm hover:bg-cyan-300 active:scale-95 transition-all shrink-0 shadow-cyan-pulse">
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
