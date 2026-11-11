import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { ErrorState } from "./ErrorState";
import { EmptyState, Skeleton } from "./ui";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

interface AsyncProps<T> {
  state: AsyncState<T>;
  /** what this page is loading, in words ("your plots"), for the loading and error texts */
  what: string;
  /** true when there is nothing to show */
  isEmpty?: (data: T) => boolean;
  empty?: { icon: LucideIcon; title: string; description: string; action?: ReactNode };
  /** a loading placeholder; the default is three grey blocks */
  skeleton?: ReactNode;
  children: (data: T) => ReactNode;
}

/**
 * Every data page uses this, so every page has the three states in plain words:
 * loading (grey blocks, announced to screen readers), an error with a "Try again" button, and an empty state that says why it is empty.
 */
export function Async<T>({ state, what, isEmpty, empty, skeleton, children }: AsyncProps<T>) {
  if (state.error && !state.data) return <ErrorState title={`Could not load ${what}`} message={state.error} onRetry={state.retry} />;
  if (state.loading && !state.data) {
    return (
      <div role="status" aria-label={`Loading ${what}`} className="space-y-3">
        {skeleton ?? (
          <>
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </>
        )}
        <span className="sr-only">Loading {what}…</span>
      </div>
    );
  }
  if (state.data === null) return null;
  if (isEmpty?.(state.data) && empty) {
    return <EmptyState icon={empty.icon} title={empty.title} description={empty.description} action={empty.action} />;
  }
  return <>{children(state.data)}</>;
}
