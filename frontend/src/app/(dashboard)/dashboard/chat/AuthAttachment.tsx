"use client";

import React, { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { VoicePlayer } from "./VoicePlayer";

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

  const isImg = kind === "image" || (mime && mime.startsWith("image/")) || filename.match(/\.(jpeg|jpg|gif|png|webp)$/i);
  const isAudio = kind === "audio" || (mime && mime.startsWith("audio/")) || filename.match(/\.(webm|ogg|wav|mp3|m4a)$/i);

  if (compact) {
    if (isImg) {
      // eslint-disable-next-line @next/next/no-img-element
      return <img src={src} alt={filename} className="w-16 h-16 rounded-xl object-cover border border-border shadow-sm" />;
    }
    return (
      <div className="flex items-center gap-2 px-2.5 py-1.5 bg-muted/80 border border-border rounded-xl text-xs max-w-[180px]">
        <span className="shrink-0 text-primary">📄</span>
        <span className="truncate text-xs">{filename}</span>
      </div>
    );
  }

  if (isImg) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={filename} className="max-w-xs max-h-80 rounded-xl border border-border shadow-sm" />;
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
