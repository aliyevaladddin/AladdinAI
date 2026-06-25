// NOTICE: This file is protected under RCF-PL
"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { X, Plus, Trash2, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { CustomProviderDraft } from "./types";


interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (draft: CustomProviderDraft) => Promise<void> | void;
}

const EMPTY: CustomProviderDraft = {
  name: "",
  image: "",
  internal_port: 8080,
  external_port: 8080,
  url_template: "http://{host}:{port}/?vm={vm_id}&token={token}",
  healthcheck: "/",
  env: [],
};

const PLACEHOLDER_REGEX = /\{(vm_id|host|port|token)\}/g;

/**
 * Highlights {vm_id}, {host}, {port}, {token} placeholders inside a string.
 * Returns a React fragment of mixed text + colored chips.
 */

function HighlightedTemplate({ value }: { value: string }) {
  const parts: Array<{ kind: "text" | "token"; text: string }> = [];
  let lastIndex = 0;
  for (const m of value.matchAll(PLACEHOLDER_REGEX)) {
    if (m.index! > lastIndex) {
      parts.push({ kind: "text", text: value.slice(lastIndex, m.index) });
    }
    parts.push({ kind: "token", text: m[0] });
    lastIndex = m.index! + m[0].length;
  }
  if (lastIndex < value.length) {
    parts.push({ kind: "text", text: value.slice(lastIndex) });
  }
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.5, wordBreak: "break-all" }}>
      {parts.map((p, i) =>
        p.kind === "token" ? (
          <span
            key={i}
            style={{
              background: "var(--amber-soft)",
              color: "var(--amber)",
              padding: "1px 5px",
              borderRadius: 4,
              border: "1px solid var(--amber-line)",
              fontWeight: 600,
              fontSize: 11.5,
              margin: "0 1px",
            }}
          >
            {p.text}
          </span>
        ) : (
          <span key={i} style={{ color: "var(--fg-2)" }}>{p.text}</span>
        ),
      )}
    </span>
  );
}


export function CustomProviderModal({ open, onClose, onSubmit }: Props) {
  const titleId = useId();
  const [draft, setDraft] = useState<CustomProviderDraft>(EMPTY);
  const [submitting, setSubmitting] = useState(false);

  // Reset when reopened.
  useEffect(() => {
    if (open) setDraft(EMPTY);
  }, [open]);

  // Auto-suggest external = internal until user touches it.
  const [externalTouched, setExternalTouched] = useState(false);
  useEffect(() => {
    if (!externalTouched) {
      setDraft((d) => ({ ...d, external_port: d.internal_port }));
    }
  }, [draft.internal_port, externalTouched]);

  // ESC to close.
  useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const previewUrl = useMemo(() => {
    return draft.url_template
      .replace(/\{host\}/g, "localhost")
      .replace(/\{port\}/g, String(draft.external_port || "8080"))
      .replace(/\{vm_id\}/g, "vm-demo-01")
      .replace(/\{token\}/g, "tk_•••••");
  }, [draft.url_template, draft.external_port]);

  const isValid =
    draft.name.trim().length > 0 &&
    draft.image.trim().length > 0 &&
    draft.internal_port > 0 &&
    draft.external_port > 0 &&
    draft.url_template.trim().length > 0;

  if (!open) return null;


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    setSubmitting(true);
    try {
      await onSubmit(draft);
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-[200] flex items-center justify-center motion-safe:animate-[modalFadeIn_200ms_cubic-bezier(0.16,1,0.3,1)]"
      style={{ background: "color-mix(in oklab, var(--bg-0) 70%, transparent)", backdropFilter: "blur(6px)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="relative w-full max-w-[920px] mx-4 motion-safe:animate-[modalSlideIn_240ms_cubic-bezier(0.16,1,0.3,1)]"
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--line-strong)",
          borderRadius: "var(--r-lg)",
          boxShadow: "0 32px 80px -16px rgba(0,0,0,0.55), 0 0 0 1px var(--line) inset",
          maxHeight: "calc(100vh - 64px)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: "var(--line)" }}
        >
          <div className="flex items-center gap-2.5">
            <Terminal size={16} style={{ color: "var(--violet)" }} />
            <h2 id={titleId} className="text-[15px] font-semibold tracking-tight" style={{ color: "var(--fg)" }}>
              New custom terminal provider
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="size-7 inline-flex items-center justify-center rounded-md transition-colors focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{ color: "var(--fg-3)", outlineColor: "var(--violet)" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "var(--bg-3)"; e.currentTarget.style.color = "var(--fg)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "var(--fg-3)"; }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Body: 2-column form + preview */}
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-[1fr_320px] gap-0 flex-1 min-h-0 overflow-hidden">
          {/* Left — form */}
          <div className="px-5 py-5 overflow-y-auto space-y-4">
            <Field label="Name" hint="Shown in the providers list">
              <input
                className="input"
                placeholder="e.g. Internal SSH gateway"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                required
                autoFocus
              />
            </Field>

            <Field label="Docker image" hint="Tag included; pulled at install">
              <input
                className="input"
                placeholder="registry/your-org/terminal:tag"
                value={draft.image}
                onChange={(e) => setDraft({ ...draft, image: e.target.value })}
                style={{ fontFamily: "var(--font-mono)" }}
                required
              />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Internal port" hint="Port the container listens on">
                <input
                  type="number"
                  className="input"
                  min={1}
                  max={65535}
                  value={draft.internal_port}
                  onChange={(e) => setDraft({ ...draft, internal_port: Number(e.target.value) })}
                  required
                />
              </Field>
              <Field
                label="External port"
                hint={externalTouched ? "Host-side port" : "Auto-suggested — mirrors internal"}
              >
                <input
                  type="number"
                  className="input"
                  min={1}
                  max={65535}
                  value={draft.external_port}
                  onChange={(e) => {
                    setExternalTouched(true);
                    setDraft({ ...draft, external_port: Number(e.target.value) });
                  }}
                  required
                />
              </Field>
            </div>

            <Field label="URL template" hint="Available tokens: {vm_id} {host} {port} {token}">
              <textarea
                className="input"
                rows={2}
                value={draft.url_template}
                onChange={(e) => setDraft({ ...draft, url_template: e.target.value })}
                style={{ fontFamily: "var(--font-mono)", resize: "vertical" }}
                required
              />
            </Field>

            <Field label="Healthcheck path" hint="GET returning 200 once the container is ready">
              <input
                className="input"
                placeholder="/"
                value={draft.healthcheck}
                onChange={(e) => setDraft({ ...draft, healthcheck: e.target.value })}
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </Field>

            {/* Env vars */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-[11.5px] font-medium uppercase tracking-wider" style={{ color: "var(--fg-3)" }}>
                  Environment variables
                </label>
                <button
                  type="button"
                  onClick={() => setDraft({ ...draft, env: [...draft.env, { key: "", value: "" }] })}
                  className="inline-flex items-center gap-1 text-[11.5px] font-medium"
                  style={{ color: "var(--violet)" }}
                >
                  <Plus size={11} strokeWidth={2.5} /> Add variable
                </button>
              </div>
              {draft.env.length === 0 && (
                <p className="text-[11.5px]" style={{ color: "var(--fg-4)" }}>
                  No environment variables. Click "Add variable" to define one.
                </p>
              )}
              <div className="space-y-1.5">
                {draft.env.map((kv, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_28px] gap-1.5">
                    <input
                      className="input"
                      placeholder="KEY"
                      value={kv.key}
                      onChange={(e) => {
                        const next = [...draft.env];
                        next[i] = { ...kv, key: e.target.value };
                        setDraft({ ...draft, env: next });
                      }}
                      style={{ fontFamily: "var(--font-mono)" }}
                    />
                    <input
                      className="input"
                      placeholder="value"
                      value={kv.value}
                      onChange={(e) => {
                        const next = [...draft.env];
                        next[i] = { ...kv, value: e.target.value };
                        setDraft({ ...draft, env: next });
                      }}
                      style={{ fontFamily: "var(--font-mono)" }}
                    />
                    <button
                      type="button"
                      onClick={() => setDraft({ ...draft, env: draft.env.filter((_, j) => j !== i) })}
                      aria-label="Remove variable"
                      className="size-7 inline-flex items-center justify-center rounded-md transition-colors"
                      style={{ color: "var(--fg-3)" }}
                      onMouseEnter={(e) => { e.currentTarget.style.color = "var(--err)"; e.currentTarget.style.background = "var(--err-soft)"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.color = "var(--fg-3)"; e.currentTarget.style.background = "transparent"; }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right — preview */}
          <aside
            className="hidden md:flex md:flex-col gap-3 px-5 py-5 border-l overflow-y-auto"
            style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
          >
            <div className="space-y-1">
              <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--fg-3)" }}>
                Live preview
              </h3>
              <p className="text-[11.5px] leading-snug" style={{ color: "var(--fg-3)" }}>
                Resolved URL for a sample VM, with placeholders substituted.
              </p>
            </div>

            <div
              className="rounded-md p-3 space-y-2"
              style={{
                background: "var(--bg-0)",
                border: "1px solid var(--line)",
              }}
            >
              <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--fg-4)" }}>
                Template
              </div>
              <HighlightedTemplate value={draft.url_template} />
            </div>

            <div
              className="rounded-md p-3 space-y-2"
              style={{
                background: "var(--violet-soft)",
                border: "1px solid var(--violet-line)",
              }}
            >
              <div className="text-[10px] uppercase tracking-wider" style={{ color: "var(--violet)" }}>
                Resolved
              </div>
              <span
                className="block break-all"
                style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fg)" }}
              >
                {previewUrl}
              </span>
            </div>

            <div className="space-y-1 pt-1">
              <h4 className="text-[10px] uppercase tracking-wider" style={{ color: "var(--fg-4)" }}>
                Tokens
              </h4>
              <ul className="space-y-1 text-[11.5px]" style={{ color: "var(--fg-3)" }}>
                <li><code style={{ color: "var(--amber)" }}>{"{vm_id}"}</code> — target VM identifier</li>
                <li><code style={{ color: "var(--amber)" }}>{"{host}"}</code> — provider container host</li>
                <li><code style={{ color: "var(--amber)" }}>{"{port}"}</code> — external port (mapped)</li>
                <li><code style={{ color: "var(--amber)" }}>{"{token}"}</code> — short-lived session token</li>
              </ul>
            </div>
          </aside>

          {/* Footer */}
          <div
            className="md:col-span-2 px-5 py-3.5 border-t flex items-center justify-end gap-2"
            style={{ borderColor: "var(--line)", background: "var(--bg-1)" }}
          >
            <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={!isValid || submitting}>
              {submitting ? "Installing…" : "Install provider"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}


function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11.5px] font-medium uppercase tracking-wider block" style={{ color: "var(--fg-3)" }}>
        {label}
      </label>
      {children}
      {hint && (
        <p className="text-[11px] leading-tight" style={{ color: "var(--fg-4)" }}>
          {hint}
        </p>
      )}
    </div>
  );
}
