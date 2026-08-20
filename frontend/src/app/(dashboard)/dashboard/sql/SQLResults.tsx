"use client";

import { Database, Clock, X, BarChart3 } from "lucide-react";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface QueryResult {
  success: boolean;
  rows: any[];
  columns: string[];
  row_count: number;
  error?: string;
  message?: string;
  execution_time?: number;
}

interface SQLResultsProps {
  result: QueryResult;
  visualizationType: "table" | "bar" | "line" | "pie";
  onSetVisualizationType: (type: "table" | "bar" | "line" | "pie") => void;
}

export function SQLResults({ result, visualizationType, onSetVisualizationType }: SQLResultsProps) {
  return (
    <div className="flex-1 flex flex-col border rounded-xl overflow-hidden min-h-0" style={{ borderColor: "var(--color-border)" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>
            Results {result.success && `(${result.row_count} rows)`}
          </span>
          {result.execution_time && (
            <span className="flex items-center gap-1 text-xs px-2 py-1 rounded" style={{ background: "var(--color-surface)", color: "var(--color-fg-muted)" }}>
              <Clock size={10} />
              {result.execution_time.toFixed(0)}ms
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {result.success && result.rows.length > 0 && (
            <div className="flex items-center gap-1 p-1 rounded" style={{ background: "var(--color-surface)" }}>
              {(["table", "bar", "line", "pie"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => onSetVisualizationType(type)}
                  className={`p-1 rounded transition-colors ${visualizationType === type ? "bg-[var(--color-accent)] text-white" : "hover:bg-[var(--color-surface-2)]"}`}
                  title={`${type.charAt(0).toUpperCase() + type.slice(1)} view`}
                >
                  {type === "table" ? (
                    <Database size={12} />
                  ) : (
                    <BarChart3
                      size={12}
                      style={{
                        transform:
                          type === "line" ? "rotate(90deg)" :
                          type === "pie" ? "rotate(45deg)" : "none",
                      }}
                    />
                  )}
                </button>
              ))}
            </div>
          )}
          {result.success ? (
            <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-accent)", color: "#fff" }}>Success</span>
          ) : (
            <span className="text-xs px-2 py-1 rounded" style={{ background: "var(--color-danger)", color: "#fff" }}>Error</span>
          )}
        </div>
      </div>

      {/* Content */}
      {result.error ? (
        <div className="p-4 space-y-3">
          <div className="flex items-start gap-2 p-3 rounded-lg border" style={{ borderColor: "var(--color-danger)", background: "rgba(239, 68, 68, 0.05)" }}>
            <X size={16} className="text-red-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-red-500 mb-1">Query Error</div>
              <pre className="text-xs font-mono text-red-400 whitespace-pre-wrap break-words">{result.error}</pre>
            </div>
          </div>
        </div>
      ) : result.rows.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-8">
          <p className="text-sm italic" style={{ color: "var(--color-fg-muted)" }}>{result.message || "No rows returned"}</p>
        </div>
      ) : visualizationType === "table" ? (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0" style={{ background: "var(--color-surface-2)" }}>
              <tr className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <th className="px-4 py-2 text-left font-bold uppercase w-12" style={{ color: "var(--color-fg-muted)" }}>#</th>
                {result.columns.map((col) => (
                  <th key={col} className="px-4 py-2 text-left font-bold uppercase" style={{ color: "var(--color-fg-muted)" }}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--color-border)" }}>
              {result.rows.map((row, i) => (
                <tr key={i} className="hover:bg-[var(--color-surface-2)] transition-colors group">
                  <td className="px-4 py-2 text-right" style={{ color: "var(--color-fg-muted)" }}>{i + 1}</td>
                  {result.columns.map((col) => (
                    <td
                      key={col}
                      className="px-4 py-2 font-mono max-w-md truncate"
                      style={{ color: "var(--color-fg)" }}
                      title={typeof row[col] === "object" ? JSON.stringify(row[col]) : String(row[col] ?? "")}
                    >
                      {typeof row[col] === "object" ? JSON.stringify(row[col]) : String(row[col] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-4">
          {result.columns.length < 2 ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm" style={{ color: "var(--color-fg-muted)" }}>Visualization requires at least 2 columns. Switch to table view.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              {visualizationType === "bar" ? (
                <BarChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={result.columns[0]} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {result.columns.slice(1).map((col, i) => (
                    <Bar key={col} dataKey={col} fill={`hsl(${i * 60}, 70%, 50%)`} />
                  ))}
                </BarChart>
              ) : visualizationType === "line" ? (
                <LineChart data={result.rows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={result.columns[0]} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {result.columns.slice(1).map((col, i) => (
                    <Line key={col} type="monotone" dataKey={col} stroke={`hsl(${i * 60}, 70%, 50%)`} />
                  ))}
                </LineChart>
              ) : (
                <PieChart>
                  <Pie
                    data={result.rows}
                    dataKey={result.columns[1]}
                    nameKey={result.columns[0]}
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    label
                  >
                    {result.rows.map((_, i) => (
                      <Cell key={i} fill={`hsl(${(i * 360) / result.rows.length}, 70%, 50%)`} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              )}
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}
