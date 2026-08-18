// NOTICE: This file is protected under RCF-PL
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/* Shared empty-state card. Centralises the dashed-border CTA pattern that was
   previously re-implemented per page (agents list, traces panel, memory panel,
   dashboard …) with slightly different classes every time. */

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 rounded-2xl border border-dashed border-border/60 bg-surface-1 text-center",
        className,
      )}
    >
      {icon && (
        <div className="mb-4 text-muted-foreground/40">{icon}</div>
      )}
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground max-w-md mt-1.5 leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
