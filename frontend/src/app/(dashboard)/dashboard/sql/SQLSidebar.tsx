"use client";

import { Save, History, Table2, ChevronUp, ChevronDown, Pin, PinOff, Trash2 } from "lucide-react";

interface SavedQuery {
  id: string;
  name: string;
  query: string;
  created_at: number;
  pinned?: boolean;
}

interface TableSchema {
  table_name: string;
  columns: Array<{
    column_name: string;
    data_type: string;
    nullable: boolean;
    default: string | null;
  }>;
}

interface SQLSidebarProps {
  savedQueries: SavedQuery[];
  history: string[];
  schema: TableSchema[];
  showSaved: boolean;
  showHistory: boolean;
  showSchema: boolean;
  onToggleSaved: () => void;
  onToggleHistory: () => void;
  onToggleSchema: () => void;
  onSetQuery: (q: string) => void;
  onTogglePin: (id: string) => void;
  onDeleteSaved: (id: string) => void;
  onClearHistory: () => void;
}

const EXAMPLES = [
  { label: "All Agents", query: "SELECT id, name, status, created_at FROM agents ORDER BY created_at DESC LIMIT 10;" },
  { label: "Active Providers", query: "SELECT id, name, type, base_url FROM llm_providers WHERE is_active = true;" },
  { label: "Recent Messages", query: "SELECT am.id, am.content, a.name as agent_name, am.created_at\nFROM agent_messages am\nJOIN agents a ON am.agent_id = a.id\nORDER BY am.created_at DESC\nLIMIT 20;" },
  { label: "User Settings", query: "SELECT user_id, media_storage_backend, created_at FROM system_settings;" },
  { label: "Message Stats", query: "SELECT a.name, COUNT(am.id) as message_count\nFROM agents a\nLEFT JOIN agent_messages am ON a.id = am.agent_id\nGROUP BY a.id, a.name\nORDER BY message_count DESC;" },
];

function SavedQueryItem({
  sq,
  pinned,
  onSetQuery,
  onTogglePin,
  onDelete,
}: {
  sq: SavedQuery;
  pinned: boolean;
  onSetQuery: (q: string) => void;
  onTogglePin: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="group flex items-center gap-2 p-2 rounded-lg hover:bg-[var(--color-surface-2)] transition-colors">
      <button onClick={() => onSetQuery(sq.query)} className="flex-1 text-left min-w-0">
        <div className="text-xs font-medium truncate" style={{ color: "var(--color-fg)" }}>{sq.name}</div>
        <div className="text-xs font-mono truncate" style={{ color: "var(--color-fg-muted)" }}>{sq.query.split("\n")[0]}</div>
      </button>
      <button
        onClick={() => onTogglePin(sq.id)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-yellow-500/10 transition-all"
        title={pinned ? "Unpin" : "Pin"}
      >
        {pinned ? <PinOff size={12} className="text-yellow-500" /> : <Pin size={12} className="text-yellow-500" />}
      </button>
      <button
        onClick={() => onDelete(sq.id)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 transition-all"
        title="Delete"
      >
        <Trash2 size={12} className="text-red-500" />
      </button>
    </div>
  );
}

export function SQLSidebar({
  savedQueries,
  history,
  schema,
  showSaved,
  showHistory,
  showSchema,
  onToggleSaved,
  onToggleHistory,
  onToggleSchema,
  onSetQuery,
  onTogglePin,
  onDeleteSaved,
  onClearHistory,
}: SQLSidebarProps) {
  const pinned = savedQueries.filter((sq) => sq.pinned);
  const unpinned = savedQueries.filter((sq) => !sq.pinned);

  return (
    <div className="w-80 flex flex-col gap-4 shrink-0 overflow-y-auto">
      {/* Saved Queries */}
      <div className="border rounded-xl overflow-hidden flex flex-col" style={{ borderColor: "var(--color-border)" }}>
        <div className="px-4 py-2 border-b flex items-center justify-between" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
          <button onClick={onToggleSaved} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Save size={12} />
            <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>Saved Queries ({savedQueries.length})</span>
            {showSaved ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
        {showSaved && (
          <div className="p-2 space-y-1 max-h-96 overflow-y-auto">
            {savedQueries.length === 0 ? (
              <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>No saved queries yet</p>
            ) : (
              <>
                {pinned.length > 0 && (
                  <>
                    <div className="text-xs font-bold uppercase px-2 py-1" style={{ color: "var(--color-fg-muted)" }}>Pinned</div>
                    {pinned.map((sq) => (
                      <SavedQueryItem key={sq.id} sq={sq} pinned onSetQuery={onSetQuery} onTogglePin={onTogglePin} onDelete={onDeleteSaved} />
                    ))}
                  </>
                )}
                {unpinned.length > 0 && (
                  <>
                    {pinned.length > 0 && <div className="text-xs font-bold uppercase px-2 py-1 mt-2" style={{ color: "var(--color-fg-muted)" }}>Other</div>}
                    {unpinned.map((sq) => (
                      <SavedQueryItem key={sq.id} sq={sq} pinned={false} onSetQuery={onSetQuery} onTogglePin={onTogglePin} onDelete={onDeleteSaved} />
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Examples */}
      <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--color-border)" }}>
        <div className="px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
          <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>Examples</span>
        </div>
        <div className="p-2 space-y-1">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              onClick={() => onSetQuery(ex.query)}
              className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-[var(--color-surface-2)] transition-colors"
              style={{ color: "var(--color-fg-muted)" }}
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {/* History */}
      <div className="border rounded-xl overflow-hidden flex flex-col flex-1 min-h-0" style={{ borderColor: "var(--color-border)" }}>
        <div className="px-4 py-2 border-b flex items-center justify-between" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
          <button onClick={onToggleHistory} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <History size={12} />
            <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>History ({history.length})</span>
            {showHistory ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {history.length > 0 && (
            <button onClick={onClearHistory} className="p-1 rounded hover:bg-red-500/10 transition-colors" title="Clear history">
              <Trash2 size={12} className="text-red-500" />
            </button>
          )}
        </div>
        {showHistory && (
          <div className="p-2 space-y-1 overflow-y-auto flex-1">
            {history.length === 0 ? (
              <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>No history yet</p>
            ) : (
              history.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onSetQuery(q)}
                  className="w-full text-left px-3 py-1.5 rounded-lg text-xs font-mono truncate hover:bg-[var(--color-surface-2)] transition-colors"
                  style={{ color: "var(--color-fg-muted)" }}
                  title={q}
                >
                  {q.split("\n")[0]}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Schema Browser */}
      <div className="border rounded-xl overflow-hidden flex flex-col flex-1 min-h-0" style={{ borderColor: "var(--color-border)" }}>
        <div className="px-4 py-2 border-b flex items-center justify-between" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
          <button onClick={onToggleSchema} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Table2 size={12} />
            <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>Schema ({schema.length} tables)</span>
            {showSchema ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
        {showSchema && (
          <div className="p-2 space-y-1 overflow-y-auto flex-1">
            {schema.length === 0 ? (
              <p className="text-xs text-center py-4" style={{ color: "var(--color-fg-muted)" }}>Loading schema...</p>
            ) : (
              schema.map((table) => (
                <details key={table.table_name} className="group">
                  <summary className="cursor-pointer px-3 py-2 rounded-lg text-xs hover:bg-[var(--color-surface-2)] transition-colors list-none">
                    <span className="font-medium" style={{ color: "var(--color-fg)" }}>{table.table_name}</span>
                    <span className="ml-2" style={{ color: "var(--color-fg-muted)" }}>({table.columns.length} cols)</span>
                  </summary>
                  <div className="ml-4 mt-1 space-y-1">
                    {table.columns.map((col) => (
                      <div
                        key={col.column_name}
                        className="px-3 py-1 text-xs font-mono"
                        style={{ color: "var(--color-fg-muted)" }}
                        title={`${col.data_type}${col.nullable ? ", nullable" : ", not null"}${col.default ? `, default: ${col.default}` : ""}`}
                      >
                        <span style={{ color: "var(--color-fg)" }}>{col.column_name}</span>
                        <span className="ml-2 opacity-60">{col.data_type}</span>
                      </div>
                    ))}
                  </div>
                </details>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
