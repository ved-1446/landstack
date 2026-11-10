import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const card = cva("rounded-card border", {
  variants: {
    surface: {
      navy: "border-line-on-navy bg-navy-900 text-cream",
      raised: "border-line-on-navy bg-navy-800 text-cream",
      paper: "border-line-on-cream bg-cream text-ink",
    },
    padding: { none: "", sm: "p-3", md: "p-4" },
  },
  defaultVariants: { surface: "navy", padding: "md" },
});

interface CardProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof card> {}

export function Card({ className, surface, padding, ...props }: CardProps) {
  return <div className={cn(card({ surface, padding }), className)} {...props} />;
}
