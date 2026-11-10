import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  /** which surface it sits on */
  on?: "navy" | "cream";
  className?: string;
}

/** What to show when there is nothing to show (no plots, not found, an error). Always says what happened. */
export function EmptyState({ icon: Icon, title, description, action, on = "navy", className }: EmptyStateProps) {
  const cream = on === "cream";
  return (
    <div className={cn("flex flex-col items-center gap-3 px-4 py-8 text-center", className)}>
      <span className={cn("flex size-12 items-center justify-center rounded-pill", cream ? "bg-ink text-cream" : "bg-navy-800 text-cream")}>
        <Icon className="size-6" aria-hidden="true" />
      </span>
      <h3 className={cn("font-serif text-26", cream ? "text-ink" : "text-cream")}>{title}</h3>
      {description && <p className={cn("max-w-72 text-13", cream ? "text-muted-on-cream" : "text-muted-on-navy")}>{description}</p>}
      {action}
    </div>
  );
}
