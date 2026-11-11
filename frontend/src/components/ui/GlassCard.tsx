import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const glassCard = cva("glass-card rounded-glass text-cream", {
  variants: {
    padding: { none: "", sm: "p-4", md: "p-6" },
    strong: { true: "glass-card-strong", false: "" },
    lift: { true: "lift", false: "" },
  },
  defaultVariants: { padding: "md", strong: false, lift: false },
});

interface GlassCardProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof glassCard> {}

/** The translucent card used on dark pages: a fine border, a blur, a 22px radius. */
export function GlassCard({ className, padding, strong, lift, ...props }: GlassCardProps) {
  return <div className={cn(glassCard({ padding, strong, lift }), className)} {...props} />;
}
