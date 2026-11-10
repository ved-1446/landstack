import { cn } from "../../lib/cn";

interface SkeletonProps {
  className?: string;
  /** which surface it sits on (so it stays visible on cream and on navy) */
  on?: "navy" | "cream";
}

/** A grey placeholder block shown while data loads (it pulses; reduced motion keeps it still). */
export function Skeleton({ className, on = "navy" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-control motion-reduce:animate-none", on === "navy" ? "bg-navy-800" : "bg-line-on-cream", className)}
    />
  );
}
