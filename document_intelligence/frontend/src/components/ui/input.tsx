import type * as React from "react";

import { cn } from "@/lib/utils";

export function Input({
  className,
  type = "text",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type={type}
      className={cn(
        "h-9 w-full rounded-[var(--radius-m)] border border-line bg-surface px-2.5 text-[14px] text-ink placeholder:text-ink-3 outline-none transition-colors focus-visible:border-ai focus-visible:ring-2 focus-visible:ring-ai/25 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
