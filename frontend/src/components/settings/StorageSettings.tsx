// NOTICE: This file is protected under RCF-PL
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  HardDrive,
  Database,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  ShieldCheck,
  Zap,
  Globe2,
  Layers,
} from "lucide-react";

/* ── Types mirror the backend contract (GET/PUT /settings) ──────────── */
type StorageBackend = "local" | "mongodb";


interface SystemSettings {
  id: number | null; // null → no persisted row yet, defaults are shown
  user_id: number;
  media_storage_backend: StorageBackend;
  created_at: string;
  updated_at: string;
}


interface BackendOption {
  id: StorageBackend;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  tagline: string;
  description: string;
  bullets: { icon: React.ComponentType<{ size?: number; className?: string }>; text: string }[];
  recommendedFor: string;
}

const BACKENDS: BackendOption[] = [
  {
    id: "local",
    icon: HardDrive,
    title: "Local filesystem",
    tagline: "Simple · fast · zero-config",
    description:
      "Media is written straight to the server's disk. The lightest path — perfect for development, single-node deployments and indie projects.",
    bullets: [
      { icon: Zap, text: "Lowest latency, no network hop" },
      { icon: HardDrive, text: "Files live on the server volume" },
    ],
    recommendedFor: "Dev & indie",
  },
  {
    id: "mongodb",
    icon: Database,
    title: "MongoDB GridFS",
    tagline: "Distributed · durable · compliant",
    description:
      "Media is chunked into GridFS with per-user isolation and replicated across your Atlas cluster. The production-grade choice for scale and compliance.",
    bullets: [
      { icon: ShieldCheck, text: "Per-user isolation & audit-ready" },
      { icon: Layers, text: "Replicated across Atlas nodes" },
      { icon: Globe2, text: "Survives node loss — horizontally scalable" },
    ],
    recommendedFor: "Production",
  },
];

/* ── Loading skeleton ───────────────────────────────────────────────── */

function CardSkeleton() {
  return (
    <div
      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
      aria-hidden="true"
    >
      <div className="flex items-start gap-3">
        <div className="storage-shimmer h-9 w-9 rounded-lg" />
        <div className="flex-1 space-y-2">
          <div className="storage-shimmer h-3.5 w-32 rounded" />
          <div className="storage-shimmer h-2.5 w-24 rounded" />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <div className="storage-shimmer h-2.5 w-full rounded" />
        <div className="storage-shimmer h-2.5 w-4/5 rounded" />
      </div>
    </div>
  );
}


export function StorageSettings() {
  const [selected, setSelected] = useState<StorageBackend | null>(null);
  const [persisted, setPersisted] = useState<StorageBackend | null>(null);
  const [hasRow, setHasRow] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [savingTo, setSavingTo] = useState<StorageBackend | null>(null);

  // Refs to each radio button so we can drive roving-tabindex keyboard nav.
  const cardRefs = useRef<Record<StorageBackend, HTMLButtonElement | null>>({
    local: null,
    mongodb: null,
  });

  // Bumping this counter re-runs the load effect (used by the Retry button).
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;

    api
      .get<SystemSettings>("/settings")
      .then((data) => {
        if (cancelled) return;
        setSelected(data.media_storage_backend);
        setPersisted(data.media_storage_backend);
        setHasRow(data.id !== null);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Failed to load storage settings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // Retry handler for the error state — re-arms the load effect.
  const retry = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    setReloadKey((k) => k + 1);
  }, []);

  const handleSelect = useCallback(
    async (next: StorageBackend) => {
      // No-op if it's already the saved value or a save is in flight.
      if (next === persisted || savingTo) return;

      const previous = selected;
      // Optimistic: reflect the choice instantly.
      setSelected(next);
      setSavingTo(next);

      try {
        const data = await api.put<SystemSettings>("/settings", {
          media_storage_backend: next,
        });
        setSelected(data.media_storage_backend);
        setPersisted(data.media_storage_backend);
        setHasRow(data.id !== null);
        toast.success(
          next === "mongodb"
            ? "Storage backend set to MongoDB GridFS"
            : "Storage backend set to Local filesystem",
        );
      } catch (err) {
        // Roll back the optimistic change.
        setSelected(previous);
        toast.error(
          err instanceof Error ? err.message : "Could not update storage backend",
        );
      } finally {
        setSavingTo(null);
      }
    },
    [persisted, savingTo, selected],
  );

  // Roving keyboard navigation for the radio group.

  const onKeyDown = (e: React.KeyboardEvent, current: StorageBackend) => {
    const order = BACKENDS.map((b) => b.id);
    const idx = order.indexOf(current);
    let nextIdx: number | null = null;

    if (e.key === "ArrowDown" || e.key === "ArrowRight") nextIdx = (idx + 1) % order.length;
    else if (e.key === "ArrowUp" || e.key === "ArrowLeft")
      nextIdx = (idx - 1 + order.length) % order.length;

    if (nextIdx !== null) {
      e.preventDefault();
      const target = order[nextIdx];
      cardRefs.current[target]?.focus();
      handleSelect(target);
    }
  };

  /* ── Render: error state ──────────────────────────────────────────── */
  if (loadError) {
    return (
      <div className="space-y-5">
        <Header />
        <div
          role="alert"
          className="rounded-xl border border-[var(--color-danger)]/30 bg-[var(--color-danger-soft)] p-5 flex items-start gap-3"
        >
          <AlertTriangle size={16} className="text-[var(--color-danger)] mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--color-fg)]">
              Couldn&apos;t load storage settings
            </p>
            <p className="text-xs text-[var(--color-fg-muted)] mt-1 break-words">{loadError}</p>
          </div>
          <Button variant="outline" size="sm" onClick={retry} className="shrink-0">
            <RotateCw size={13} /> Retry
          </Button>
        </div>
      </div>
    );
  }

  /* ── Render: loading skeleton ─────────────────────────────────────── */
  if (loading) {
    return (
      <div className="space-y-5">
        <Header />
        <div className="grid gap-4 sm:grid-cols-2">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  /* ── Render: ready ────────────────────────────────────────────────── */
  return (
    <div className="space-y-5">
      <Header />

      {!hasRow && (
        <p
          className="text-xs text-[var(--color-fg-subtle)] -mt-2"
          style={{ animation: "mpIn 250ms cubic-bezier(0.16,1,0.3,1) both" }}
        >
          Using the default backend — your choice will be saved the moment you pick one.
        </p>
      )}

      <div
        role="radiogroup"
        aria-label="Media storage backend"
        className="grid gap-4 sm:grid-cols-2"
      >
        {BACKENDS.map((opt, i) => {
          const Icon = opt.icon;
          const isSelected = selected === opt.id;
          const isPersisted = persisted === opt.id;
          const isSaving = savingTo === opt.id;

          return (
            <button
              key={opt.id}
              ref={(el) => {
                cardRefs.current[opt.id] = el;
              }}
              type="button"
              role="radio"
              aria-checked={isSelected}
              // Roving tabindex: only the selected card is in the tab order.
              tabIndex={isSelected ? 0 : -1}
              disabled={!!savingTo && !isSaving}
              onClick={() => handleSelect(opt.id)}
              onKeyDown={(e) => onKeyDown(e, opt.id)}
              className={`storage-card group/card relative flex flex-col rounded-xl border p-5 text-left outline-none transition-[border-color,background-color,box-shadow,transform] ${isSelected
                  ? "border-[var(--color-accent)]/60 bg-[var(--color-surface-2)] shadow-[0_0_0_3px_var(--color-accent-soft)]"
                  : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-2)]"
                } focus-visible:ring-3 focus-visible:ring-[var(--color-accent)]/40 disabled:opacity-50 disabled:pointer-events-none`}
              style={{
                animationDelay: `${i * 45}ms`,
              }}
            >
              {/* Top row: icon + title + radio dot */}
              <div className="flex items-start gap-3">
                <div
                  className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg transition-colors ${isSelected
                      ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)]"
                      : "bg-[var(--color-surface-2)] text-[var(--color-fg-muted)] group-hover/card:text-[var(--color-fg)]"
                    }`}
                >
                  <Icon size={17} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-[var(--color-fg)] truncate">
                      {opt.title}
                    </h3>
                    <span className="text-[10px] font-medium uppercase tracking-wide px-1.5 py-px rounded bg-[var(--color-surface-2)] border border-[var(--color-border)] text-[var(--color-fg-subtle)] shrink-0">
                      {opt.recommendedFor}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--color-fg-subtle)] mt-0.5">{opt.tagline}</p>
                </div>

                {/* Radio indicator */}
                <span
                  aria-hidden="true"
                  className={`mt-1 grid h-[18px] w-[18px] shrink-0 place-items-center rounded-full border transition-all duration-200 ${isSelected
                      ? "border-[var(--color-accent)] bg-[var(--color-accent)]"
                      : "border-[var(--color-border-strong)] bg-transparent"
                    }`}
                >
                  <span
                    className={`block rounded-full bg-[var(--color-bg)] transition-all duration-200 ${isSelected ? "h-1.5 w-1.5" : "h-0 w-0"
                      }`}
                  />
                </span>
              </div>

              {/* Description */}
              <p className="text-xs leading-relaxed text-[var(--color-fg-muted)] mt-3">
                {opt.description}
              </p>

              {/* Trade-off bullets */}
              <ul className="mt-3.5 space-y-1.5">
                {opt.bullets.map((b) => {
                  const BIcon = b.icon;
                  return (
                    <li
                      key={b.text}
                      className="flex items-center gap-2 text-[11px] text-[var(--color-fg-subtle)]"
                    >
                      <BIcon
                        size={12}
                        className={
                          isSelected
                            ? "text-[var(--color-accent)] shrink-0"
                            : "text-[var(--color-fg-subtle)] shrink-0"
                        }
                      />
                      <span>{b.text}</span>
                    </li>
                  );
                })}
              </ul>

              {/* Footer status line */}
              <div className="mt-4 pt-3 border-t border-[var(--color-border)] flex items-center gap-1.5 min-h-[18px]">
                {isSaving ? (
                  <>
                    <RotateCw size={12} className="text-[var(--color-accent)] storage-spin" />
                    <span className="text-[11px] font-medium text-[var(--color-accent)]">
                      Saving…
                    </span>
                  </>
                ) : isPersisted ? (
                  <>
                    <CheckCircle2 size={12} className="text-[var(--color-success)]" />
                    <span className="text-[11px] font-medium text-[var(--color-success)]">
                      Active backend
                    </span>
                  </>
                ) : (
                  <span className="text-[11px] text-[var(--color-fg-subtle)]">
                    Click to switch
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ── Shared header ──────────────────────────────────────────────────── */

function Header() {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 p-2 rounded-lg bg-[var(--color-surface-2)] text-[var(--color-fg-muted)]">
        <HardDrive size={16} />
      </div>
      <div>
        <h2 className="text-sm font-semibold text-[var(--color-fg)]">Storage Backend</h2>
        <p className="text-xs text-[var(--color-fg-muted)] mt-0.5">
          Where uploaded media (images, files, attachments) is stored. Applies to new uploads.
        </p>
      </div>
    </div>
  );
}
