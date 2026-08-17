"use client";

import React, { useEffect, useState, useCallback } from "react";
import { API_URL } from "@/lib/api";
import { VoicePlayer } from "./VoicePlayer";
import { Download, Maximize2, X, ZoomIn } from "lucide-react";

/* ─────────────────────────────────────────────
   Lightbox – full-screen image viewer
───────────────────────────────────────────── */
function ImageLightbox({
  src,
  filename,
  onClose,
}: {
  src: string;
  filename: string;
  onClose: () => void;
}) {
  // Close on ESC
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = src;
    a.download = filename;
    a.click();
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center"
      style={{
        background: "rgba(0,0,0,0.85)",
        backdropFilter: "blur(8px)",
        animation: "fadeInLightbox 180ms ease-out both",
      }}
      onClick={onClose}
    >
      {/* Toolbar */}
      <div
        className="absolute top-4 right-4 flex items-center gap-2 z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleDownload}
          title="Скачать изображение"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-medium border border-white/20 transition-all backdrop-blur-sm shadow-lg active:scale-95"
        >
          <Download size={15} />
          <span>Скачать</span>
        </button>
        <button
          onClick={onClose}
          title="Закрыть (ESC)"
          className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white border border-white/20 transition-all backdrop-blur-sm shadow-lg active:scale-95"
        >
          <X size={17} />
        </button>
      </div>

      {/* Image */}
      <div
        className="relative max-w-[92vw] max-h-[90vh] flex items-center justify-center"
        onClick={(e) => e.stopPropagation()}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={filename}
          className="max-w-full max-h-[85vh] rounded-2xl shadow-2xl object-contain border border-white/10"
          style={{ animation: "scaleInLightbox 200ms cubic-bezier(.22,1,.36,1) both" }}
        />
      </div>

      {/* Filename */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-sm border border-white/10 text-white/70 text-xs font-mono truncate max-w-[60vw]">
        {filename}
      </div>

      <style>{`
        @keyframes fadeInLightbox {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes scaleInLightbox {
          from { opacity: 0; transform: scale(0.92); }
          to   { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Image card with hover panel
───────────────────────────────────────────── */
function ImageCard({
  src,
  filename,
  compact,
}: {
  src: string;
  filename: string;
  compact?: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const [lightbox, setLightbox] = useState(false);

  const handleDownload = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      const a = document.createElement("a");
      a.href = src;
      a.download = filename;
      a.click();
    },
    [src, filename]
  );

  const openLightbox = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setLightbox(true);
  }, []);

  if (compact) {
    return (
      <>
        <div
          className="relative group cursor-pointer"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onClick={openLightbox}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={filename}
            className="w-16 h-16 rounded-xl object-cover border border-border shadow-sm transition-all group-hover:brightness-75"
          />
          {/* Compact hover icon */}
          <div
            className="absolute inset-0 flex items-center justify-center rounded-xl transition-opacity"
            style={{ opacity: hovered ? 1 : 0 }}
          >
            <ZoomIn size={18} className="text-white drop-shadow" />
          </div>
        </div>

        {lightbox && (
          <ImageLightbox src={src} filename={filename} onClose={() => setLightbox(false)} />
        )}
      </>
    );
  }

  return (
    <>
      <div
        className="relative group cursor-pointer inline-block"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={filename}
          className="max-w-xs max-h-80 rounded-xl border border-border shadow-sm transition-all group-hover:brightness-90 block"
          onClick={openLightbox}
        />

        {/* Hover action panel */}
        <div
          className="absolute bottom-2 left-2 right-2 flex items-center gap-1.5 justify-end transition-all duration-200"
          style={{
            opacity: hovered ? 1 : 0,
            transform: hovered ? "translateY(0)" : "translateY(6px)",
            pointerEvents: hovered ? "auto" : "none",
          }}
        >
          <button
            onClick={openLightbox}
            title="Открыть полностью"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white text-[11px] font-medium backdrop-blur-sm border border-white/10 transition-all active:scale-95 shadow-md"
          >
            <Maximize2 size={12} />
            <span>Просмотр</span>
          </button>
          <button
            onClick={handleDownload}
            title="Скачать"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-black/60 hover:bg-black/80 text-white text-[11px] font-medium backdrop-blur-sm border border-white/10 transition-all active:scale-95 shadow-md"
          >
            <Download size={12} />
            <span>Скачать</span>
          </button>
        </div>
      </div>

      {lightbox && (
        <ImageLightbox src={src} filename={filename} onClose={() => setLightbox(false)} />
      )}
    </>
  );
}

/* ─────────────────────────────────────────────
   Main AuthAttachment export
───────────────────────────────────────────── */
export function AuthAttachment({
  filename,
  mime,
  kind,
  isUser,
  compact,
}: {
  filename: string;
  mime?: string;
  kind?: string;
  isUser?: boolean;
  compact?: boolean;
}) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    let revoke: string | null = null;
    let cancelled = false;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    fetch(`${API_URL}/chat/media/${filename}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => (r.ok ? r.blob() : null))
      .then((blob) => {
        if (!blob || cancelled) return;
        const url = URL.createObjectURL(blob);
        revoke = url;
        setSrc(url);
      })
      .catch(() => { });

    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [filename]);

  if (!src) {
    return compact ? (
      <div className="w-16 h-16 rounded-xl bg-muted/60 animate-pulse" />
    ) : (
      <div className="w-[280px] h-16 rounded-2xl bg-muted/60 animate-pulse" />
    );
  }

  const isImg =
    kind === "image" ||
    (mime && mime.startsWith("image/")) ||
    /\.(jpeg|jpg|gif|png|webp)$/i.test(filename);

  const isAudio =
    kind === "audio" ||
    (mime && mime.startsWith("audio/")) ||
    /\.(webm|ogg|wav|mp3|m4a)$/i.test(filename);

  if (isImg) {
    return <ImageCard src={src} filename={filename} compact={compact} />;
  }

  if (isAudio) {
    return <VoicePlayer src={src} isUser={isUser} />;
  }

  return (
    <a
      href={src}
      download={filename}
      className="flex items-center gap-2 px-3 py-2 bg-muted/80 hover:bg-muted border border-border rounded-lg text-xs font-medium text-foreground transition-colors max-w-sm"
    >
      <span className="shrink-0 text-primary">📄</span>
      <span className="truncate flex-1">{filename}</span>
      <span className="text-[10px] text-muted-foreground uppercase">{mime?.split("/")[1] || "DOC"}</span>
    </a>
  );
}
