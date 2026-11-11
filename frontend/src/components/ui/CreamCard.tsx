import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const creamCard = cva("rounded-glass border border-line-on-cream bg-paper text-ink shadow-2", {
  variants: {
    padding: { none: "", sm: "p-4", md: "p-6" },
    lift: { true: "lift", false: "" },
  },
  defaultVariants: { padding: "md", lift: false },
});

interface CreamCardProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof creamCard> {}

/** The cream card: primary text is ink, secondary text is muted-on-cream. Used for plain-words content and the passport sheet. */
export function CreamCard({ className, padding, lift, ...props }: CreamCardProps) {
  return <div className={cn(creamCard({ padding, lift }), className)} {...props} />;
}
