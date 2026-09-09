import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * One badge for every verdict the system can reach, so a status always reads the
 * same colour wherever it appears. Kept as its own component rather than a
 * generic Badge because the palette IS the vocabulary.
 */
const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[12px] font-medium",
  {
    variants: {
      tone: {
        pass: "bg-pass-soft text-pass",
        warn: "bg-warn-soft text-warn",
        fail: "bg-fail-soft text-fail",
        info: "bg-info-soft text-info",
        pending: "bg-pending-soft text-pending",
        unavailable: "bg-pending-soft text-pending",
        neutral: "bg-surface-3 text-ink-2",
        ai: "bg-ai-soft text-ai-text",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusBadgeVariants> {}

export function StatusBadge({ className, tone, ...props }: StatusBadgeProps) {
  return <span className={cn(statusBadgeVariants({ tone }), className)} {...props} />;
}

export { statusBadgeVariants };
