"use client";

import React, { MouseEvent } from "react";
import {
  MessageSquare,
  Plus,
  Trash2,
  Bot,
  Globe,
  X,
  Search,
  PanelLeftClose,
} from "lucide-react";

export interface Agent {
  id: number;
  name: string;
  role: string;
}

export interface Session {
  id: number;
  title: string;
  agent_id: number;
  created_at: string;
}

interface ChatSidebarProps {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  sessions: Session[];
  agents: Agent[];
  sessionQuery: string;
  activeSession: Session | null;
  selectedAgentId: string;
  isGeneralChat: boolean;
  onSetSidebarOpen: (open: boolean) => void;
  onToggleCollapse: () => void;
  onSetSessionQuery: (query: string) => void;
  onNewChat: () => void;
  onOpenGeneralChat: () => void;
  onOpenSession: (session: Session) => void;
  onDeleteSession: (id: number, e: MouseEvent) => void;
  onSelectAgent: (agentId: string) => void;
}

export function ChatSidebar({
  sidebarOpen,
  sidebarCollapsed,
  sessions,
  agents,
  sessionQuery,
  activeSession,
  selectedAgentId,
  isGeneralChat,
  onSetSidebarOpen,
  onToggleCollapse,
  onSetSessionQuery,
  onNewChat,
  onOpenGeneralChat,
  onOpenSession,
  onDeleteSession,
  onSelectAgent,
}: ChatSidebarProps) {
  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(sessionQuery.toLowerCase())
  );

  return (
    <>
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => onSetSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:relative inset-y-0 left-0 z-40 bg-muted/30 border-r border-border/50 flex flex-col transition-all duration-300 ease-in-out shrink-0 ${
          sidebarCollapsed
            ? "w-0 opacity-0 border-r-0 overflow-hidden pointer-events-none"
            : "w-72 opacity-100"
        } ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <div className="p-4 border-b border-border/50 flex items-center justify-between gap-2">
          <button
            onClick={onNewChat}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-medium text-xs shadow-sm hover:opacity-90 transition-all cursor-pointer"
          >
            <Plus size={14} />
            <span>New Chat</span>
          </button>
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-2 text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-xl transition-colors shrink-0"
            title="Hide history sidebar"
          >
            <PanelLeftClose size={16} />
          </button>
          <button
            onClick={() => onSetSidebarOpen(false)}
            className="lg:hidden p-2 text-muted-foreground hover:text-foreground rounded-lg ml-1"
          >
            <X size={16} />
          </button>
        </div>

        {/* Unified General Chat item */}
        <div className="px-3 pt-3">
          <button
            onClick={onOpenGeneralChat}
            className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left ${
              isGeneralChat && !activeSession
                ? "bg-primary/10 text-primary border border-primary/20 shadow-xs"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            <Globe size={15} className="shrink-0 text-primary" />
            <span className="truncate flex-1 font-semibold">General Chat</span>
          </button>
        </div>

        {/* Agent selection drop */}
        <div className="p-3 border-b border-border/50">
          <label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-1.5 block px-1">
            Agent Mode
          </label>
          <div className="relative">
            <select
              value={selectedAgentId}
              onChange={(e) => onSelectAgent(e.target.value)}
              className="w-full appearance-none bg-background border border-border/80 rounded-xl px-3 py-2 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all pr-8 cursor-pointer"
            >
              <option value="unified">🧠 Unified System Agent</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  🤖 {agent.name} ({agent.role})
                </option>
              ))}
            </select>
            <Bot size={14} className="absolute right-3 top-2.5 text-muted-foreground pointer-events-none" />
          </div>
        </div>

        {/* Filter search input */}
        <div className="px-3 pt-3">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              value={sessionQuery}
              onChange={(e) => onSetSessionQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full bg-background/80 border border-border/60 rounded-xl pl-8 pr-3 py-1.5 text-xs placeholder:text-muted-foreground/60 focus:outline-none focus:border-primary/40 transition-all"
            />
          </div>
        </div>

        {/* Sessions history list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider mb-2 px-1">
            Recent Chats
          </p>
          {filteredSessions.length === 0 ? (
            <p className="text-xs text-muted-foreground/60 text-center py-6">
              No conversations found
            </p>
          ) : (
            filteredSessions.map((session) => (
              <div
                key={session.id}
                onClick={() => onOpenSession(session)}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
                  activeSession?.id === session.id
                    ? "bg-muted text-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <MessageSquare size={13} className="shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                  <span className="truncate">{session.title}</span>
                </div>
                <button
                  onClick={(e) => onDeleteSession(session.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-muted-foreground hover:text-red-500 rounded transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>
    </>
  );
}
