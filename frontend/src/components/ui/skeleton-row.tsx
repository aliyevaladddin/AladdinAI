"use client";

/**
 * Reusable skeleton row for loading states. Renders an animated placeholder
 * with configurable width and optional avatar circle.
 */
export function SkeletonRow({
  lines = 2,
  avatar = false,
  className = "",
}: {
  lines?: number;
  avatar?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex items-start gap-3 animate-pulse ${className}`}>
      {avatar && (
        <div className="w-8 h-8 rounded-full bg-border/30 shrink-0" />
      )}
      <div className="flex-1 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-3 bg-border/30 rounded"
            style={{ width: i === lines - 1 ? "60%" : "100%" }}
          />
        ))}
      </div>
    </div>
  );
}
