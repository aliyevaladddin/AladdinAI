export interface PaletteCommand {
  id: string;
  category: "Navigation" | "AI & Agents" | "CRM & Sales" | "Developer & System" | "Fun & Utilities";
  label: string;
  description: string;
  shortcut?: string;
  iconName: string;
  actionType: "navigate" | "custom";
  path?: string;
  actionId?: string;
}

export const COMMANDS_REGISTRY: PaletteCommand[] = [
  // --- NAVIGATION ---
  {
    id: "nav-chat",
    category: "Navigation",
    label: "Open AI Assistant Chat",
    description: "Launch interactive streaming AI assistant & voice workspace",
    shortcut: "Alt+1",
    iconName: "MessageSquare",
    actionType: "navigate",
    path: "/dashboard/chat",
  },
  {
    id: "nav-agents",
    category: "Navigation",
    label: "Manage Autonomous Agents",
    description: "Deploy, configure, and inspect AI specialist agents",
    shortcut: "Alt+2",
    iconName: "Bot",
    actionType: "navigate",
    path: "/dashboard/agents",
  },
  {
    id: "nav-crm",
    category: "Navigation",
    label: "CRM & Leads Pipeline",
    description: "Track customer leads, deals pipeline, and automated outreach",
    shortcut: "Alt+3",
    iconName: "Users",
    actionType: "navigate",
    path: "/dashboard/crm",
  },
  {
    id: "nav-dashboard",
    category: "Navigation",
    label: "Analytics & System Overview",
    description: "View platform metrics, token usage, and active models status",
    shortcut: "Alt+4",
    iconName: "BarChart3",
    actionType: "navigate",
    path: "/dashboard",
  },
  {
    id: "nav-settings",
    category: "Navigation",
    label: "System Settings & Keys",
    description: "Manage LLM providers, API keys, storage, and preferences",
    shortcut: "Alt+5",
    iconName: "Settings",
    actionType: "navigate",
    path: "/dashboard/settings",
  },

  // --- AI & AGENTS ---
  {
    id: "ai-new-chat",
    category: "AI & Agents",
    label: "Start New Chat Session",
    description: "Clear active context and begin a fresh AI conversation",
    shortcut: "Alt+N",
    iconName: "PlusCircle",
    actionType: "navigate",
    path: "/dashboard/chat?new=true",
  },
  {
    id: "ai-create-agent",
    category: "AI & Agents",
    label: "Create Custom AI Agent",
    description: "Build a new autonomous specialist with custom system prompts",
    shortcut: "Alt+A",
    iconName: "UserPlus",
    actionType: "navigate",
    path: "/dashboard/agents?action=create",
  },
  {
    id: "ai-voice-toggle",
    category: "AI & Agents",
    label: "Toggle Voice Reply Mode",
    description: "Enable or disable audio voice replies in assistant messages",
    shortcut: "Alt+V",
    iconName: "Volume2",
    actionType: "custom",
    actionId: "toggle-voice",
  },

  // --- CRM & SALES ---
  {
    id: "crm-add-lead",
    category: "CRM & Sales",
    label: "Add New CRM Lead",
    description: "Create a prospective client lead card in the pipeline",
    shortcut: "Alt+L",
    iconName: "UserPlus",
    actionType: "navigate",
    path: "/dashboard/crm?action=add",
  },
  {
    id: "crm-export-leads",
    category: "CRM & Sales",
    label: "Export CRM Leads Data",
    description: "Download client leads report as CSV/Excel spreadsheet",
    shortcut: "Alt+E",
    iconName: "Download",
    actionType: "custom",
    actionId: "export-crm",
  },

  // --- DEVELOPER & SYSTEM ---
  {
    id: "dev-toggle-terminal",
    category: "Developer & System",
    label: "Toggle System Terminal Drawer",
    description: "Open or close the bottom Linux command terminal drawer",
    shortcut: "Alt+T",
    iconName: "Terminal",
    actionType: "custom",
    actionId: "toggle-terminal",
  },
  {
    id: "dev-copy-token",
    category: "Developer & System",
    label: "Copy JWT Access Token",
    description: "Copy current active session Bearer token to clipboard",
    shortcut: "Alt+K",
    iconName: "Key",
    actionType: "custom",
    actionId: "copy-token",
  },
  {
    id: "dev-clear-cache",
    category: "Developer & System",
    label: "Flush API In-Memory Cache",
    description: "Clear SWR API response cache and trigger fresh data fetch",
    shortcut: "Alt+R",
    iconName: "RefreshCw",
    actionType: "custom",
    actionId: "clear-cache",
  },

  // --- FUN & UTILITIES ---
  {
    id: "util-confetti",
    category: "Fun & Utilities",
    label: "Celebrate Achievement",
    description: "Launch a festive cascade of celebration confetti",
    shortcut: "Alt+C",
    iconName: "Sparkles",
    actionType: "custom",
    actionId: "trigger-confetti",
  },
  {
    id: "util-shortcuts-doc",
    category: "Fun & Utilities",
    label: "View All Keyboard Shortcuts",
    description: "Open complete documentation of key combinations and shortcuts",
    shortcut: "Alt+H",
    iconName: "HelpCircle",
    actionType: "navigate",
    path: "/dashboard/settings?tab=shortcuts",
  },
];
