// NOTICE: This file is protected under RCF-PL
"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { API_URL } from "@/lib/api";

interface ImportResult {
  created: number;
  skipped: number;
  total_rows: number;
}

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

// Default column mapping — user can override after preview
const DEFAULT_MAPPING = {
  name_col: "name",
  email_col: "email",
  phone_col: "phone",
  company_col: "company",
  tags_col: "tags",
  notes_col: "notes",
};

export function ImportExcelModal({ onClose, onSuccess }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState(DEFAULT_MAPPING);
  const [step, setStep] = useState<"select" | "map" | "importing" | "done">("select");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (f: File) => {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError("Only .xlsx and .xls files are supported");
      return;
    }
    setFile(f);
    setError(null);
    setStep("map");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleImport = async () => {
    if (!file) return;
    setStep("importing");
    setError(null);

    try {
      const token = localStorage.getItem("access_token");
      const fd = new FormData();
      fd.append("file", file);

      // Build query string from mapping
      const params = new URLSearchParams(mapping as Record<string, string>);
      const res = await fetch(`${API_URL}/crm/contacts/import?${params}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }

      const data: ImportResult = await res.json();
      setResult(data);
      setStep("done");
      onSuccess();
    } catch (e: any) {
      setError(e.message || "Import failed");
      setStep("map");
    }
  };

  return (
    <div
      id="import-excel-modal-overlay"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        id="import-excel-modal"
        className="relative w-full max-w-lg rounded-2xl border shadow-2xl p-6"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xl">📥</span>
            <h2 className="text-base font-semibold">Import Contacts from Excel</h2>
          </div>
          <button
            id="import-modal-close"
            onClick={onClose}
            className="text-[var(--color-fg-muted)] hover:text-[var(--color-fg)] transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {/* Step: select file */}
        {step === "select" && (
          <div
            id="import-drop-zone"
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileRef.current?.click()}
            className="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-all"
            style={{
              borderColor: dragOver ? "var(--color-accent)" : "var(--color-border)",
              background: dragOver ? "var(--color-surface-2)" : "transparent",
            }}
          >
            <span className="text-4xl">📊</span>
            <p className="text-sm font-medium">Drop your .xlsx file here</p>
            <p className="text-xs text-[var(--color-fg-muted)]">or click to browse</p>
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
          </div>
        )}

        {/* Step: map columns */}
        {step === "map" && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
              <span>📄</span>
              <span className="font-medium truncate">{file?.name}</span>
              <button
                onClick={() => { setFile(null); setStep("select"); }}
                className="ml-auto text-xs text-[var(--color-fg-muted)] hover:text-[var(--color-danger)]"
              >
                Change
              </button>
            </div>

            <p className="text-xs text-[var(--color-fg-muted)]">
              Map your spreadsheet column names to CRM fields. Leave as-is if your headers match.
            </p>

            <div className="grid grid-cols-2 gap-2">
              {Object.entries(mapping).map(([key, val]) => {
                const label = key.replace("_col", "").replace(/^\w/, (c) => c.toUpperCase());
                const required = key === "name_col";
                return (
                  <div key={key}>
                    <label className="text-[11px] text-[var(--color-fg-muted)] mb-1 block">
                      {label} {required && <span className="text-[var(--color-danger)]">*</span>}
                    </label>
                    <input
                      id={`col-map-${key}`}
                      value={val}
                      onChange={(e) => setMapping({ ...mapping, [key]: e.target.value })}
                      className="w-full rounded-md border px-2 py-1.5 text-xs"
                      style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
                      placeholder={`Column name in Excel`}
                    />
                  </div>
                );
              })}
            </div>

            {error && (
              <p id="import-error" className="text-xs text-[var(--color-danger)] rounded-lg border px-3 py-2"
                style={{ borderColor: "var(--color-danger)", background: "var(--color-danger-soft)" }}>
                ⚠ {error}
              </p>
            )}

            <div className="flex gap-2 pt-1">
              <Button id="import-cancel-btn" variant="outline" className="flex-1" onClick={onClose}>
                Cancel
              </Button>
              <Button id="import-submit-btn" className="flex-1" onClick={handleImport}>
                Import Contacts
              </Button>
            </div>
          </div>
        )}

        {/* Step: importing */}
        {step === "importing" && (
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: "var(--color-accent)", borderTopColor: "transparent" }} />
            <p className="text-sm text-[var(--color-fg-muted)]">Importing contacts…</p>
          </div>
        )}

        {/* Step: done */}
        {step === "done" && result && (
          <div className="space-y-4">
            <div className="flex flex-col items-center gap-2 py-4">
              <span className="text-4xl">✅</span>
              <p className="text-base font-semibold">Import complete!</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Created", value: result.created, color: "var(--color-accent)" },
                { label: "Skipped", value: result.skipped, color: "var(--color-fg-muted)" },
                { label: "Total rows", value: result.total_rows, color: "var(--color-fg)" },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex flex-col items-center gap-1 rounded-xl border p-3"
                  style={{ borderColor: "var(--color-border)", background: "var(--color-surface-2)" }}>
                  <span className="text-2xl font-bold" style={{ color }}>{value}</span>
                  <span className="text-[11px] text-[var(--color-fg-muted)]">{label}</span>
                </div>
              ))}
            </div>
            <Button id="import-done-btn" className="w-full" onClick={onClose}>
              Done
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
