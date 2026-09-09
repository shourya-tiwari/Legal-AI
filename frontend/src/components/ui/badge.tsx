import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium transition-colors whitespace-nowrap [&_svg]:size-3",
  {
    variants: {
      variant: {
        default: "border-border bg-muted text-muted-foreground",
        primary: "border-transparent bg-primary-muted text-primary",
        outline: "border-border-strong text-foreground",
        success:
          "border-transparent bg-success/15 text-success dark:text-success",
        warning:
          "border-transparent bg-warning/20 text-warning-foreground dark:text-warning",
        danger:
          "border-transparent bg-danger/15 text-danger dark:text-danger",
        info: "border-transparent bg-info/15 text-info dark:text-info",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.ComponentProps<"span">,
    VariantProps<typeof badgeVariants> {
  asChild?: boolean;
}

export function Badge({ className, variant, asChild, ...props }: BadgeProps) {
  const Comp = asChild ? Slot : "span";
  return (
    <Comp className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { badgeVariants };
