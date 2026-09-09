import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-m)] font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ai focus-visible:ring-offset-1 focus-visible:ring-offset-surface disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        // The prototype's `.btn-primary`: solid dark ink, light text — used for
        // New scrutiny, the sign-off button and the composer send button.
        //
        // The colour is set with an arbitrary property rather than `text-canvas`
        // because tailwind-merge treats `text-canvas` and the size variant's
        // `text-[14px]` as the same `text-*` utility and drops the colour, which
        // left the label invisible on the dark button.
        primary: "bg-ink [color:var(--bg)] hover:brightness-125",
        secondary:
          "border border-line bg-surface text-ink hover:bg-surface-3",
        ghost: "text-ink-2 hover:bg-surface-3 hover:text-ink",
        danger: "bg-fail-soft text-fail hover:brightness-95",
      },
      size: {
        sm: "h-8 px-2.5 text-[13px] [&_svg]:size-4",
        md: "h-9 px-3 text-[14px] [&_svg]:size-4",
        icon: "size-9 [&_svg]:size-4",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return (
    <Component
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { buttonVariants };
