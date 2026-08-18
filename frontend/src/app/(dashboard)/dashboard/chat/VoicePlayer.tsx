"use client";

import React, { useRef, useState, useCallback } from "react";
import { Play, Pause } from "lucide-react";

export function VoicePlayer({ src, isUser }: { src: string; isUser?: boolean }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const toggle = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play();
    }
    setPlaying(!playing);
  }, [playing]);

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    setCurrentTime(audio.currentTime);
    setProgress((audio.currentTime / audio.duration) * 100);
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) setDuration(audioRef.current.duration);
  };

  const handleEnded = () => {
    setPlaying(false);
    setProgress(0);
    setCurrentTime(0);
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    audio.currentTime = ratio * audio.duration;
    setProgress(ratio * 100);
  };

  const fmt = (s: number) => {
    if (!isFinite(s) || s === 0) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  // Organic-looking waveform heights
  const bars = [3, 6, 10, 15, 20, 14, 18, 8, 22, 16, 10, 18, 12, 20, 7, 15, 22, 11, 17, 9, 14, 20, 6, 12, 18];

  return (
    <div
      className="flex items-center gap-3 px-3.5 py-3 rounded-2xl max-w-[280px] shadow-lg bg-card border border-primary/30 text-foreground transition-all hover:border-primary/50"
    >
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        className="hidden"
      />

      {/* Play / Pause button with glow */}
      <button
        onClick={toggle}
        className="relative w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-all duration-200 hover:scale-105 active:scale-95 bg-gradient-to-br from-primary to-primary/70 text-primary-foreground shadow-[0_0_12px_rgba(139,92,246,0.4)]"
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? (
          <Pause size={16} fill="white" className="shrink-0 text-white" />
        ) : (
          <Play size={16} fill="white" className="shrink-0 text-white translate-x-0.5" />
        )}
        {/* Ripple on play */}
        {playing && (
          <span className="absolute inset-0 rounded-full animate-ping opacity-30 bg-primary/60" />
        )}
      </button>

      {/* Waveform + seeker */}
      <div className="flex-1 min-w-0 space-y-1.5">
        {/* Animated waveform bars */}
        <div
          className="flex items-center gap-[2.5px] h-6 cursor-pointer"
          onClick={handleSeek}
        >
          {bars.map((h, i) => {
            const barProgress = (i / bars.length) * 100;
            const isPast = barProgress <= progress;
            const isNearCurrent = Math.abs(barProgress - progress) < 8 && playing;
            return (
              <div
                key={i}
                className={`rounded-full w-[2.5px] flex-shrink-0 transition-all duration-150 ${
                  isPast ? "bg-primary shadow-[0_0_6px_rgba(139,92,246,0.6)]" : "bg-muted/40"
                }`}
                style={{
                  height: `${h}px`,
                  transform: isNearCurrent ? "scaleY(1.3)" : "scaleY(1)",
                  animationDelay: `${i * 40}ms`,
                }}
              />
            );
          })}
        </div>

        {/* Time row */}
        <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground font-medium">
          <span>{fmt(currentTime)}</span>
          <span className="text-[9px] uppercase tracking-wide font-bold text-primary">Voice</span>
          <span>{fmt(duration || 0)}</span>
        </div>
      </div>
    </div>
  );
}
