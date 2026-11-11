import { cva, type VariantProps } from "class-variance-authority";
import { LoaderCircle } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const button = cva(
  "inline-flex shrink-0 select-none items-center justify-center gap-2 rounded-control font-medium transition-colors duration-150 ease-out disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      variant: {
        // coral: primary actions only. The label is navy-950 (6.7:1); cream on coral would fail.
        primary: "bg-coral text-navy-950 hover:bg-coral-hover active:bg-coral-pressed",
        // the glass button: translucent with a fine border
        secondary: "glass-card text-cream hover:bg-glass-fill-strong",
        ghost: "text-cream hover:bg-glass-fill",
        // for buttons sitting on the cream passport sheet
        paper: "border border-line-on-cream bg-transparent text-ink hover:bg-line-on-cream",
      },
      size: {
        sm: "h-8 px-3 text-13",
        md: "h-11 px-4 text-14",
        icon: "h-11 w-11 text-14",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof button> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, loading = false, disabled, children, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(button({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />}
      {children}
    </button>
  );
});
