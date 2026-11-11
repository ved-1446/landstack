import { Skeleton } from "./ui";

/** Shown while a page's code is being downloaded (every page is its own chunk). */
export function RouteLoading() {
  return (
    <div role="status" aria-label="Loading the page" className="mx-auto max-w-(--content-width) space-y-4 px-(--edge) py-12">
      <Skeleton className="h-12 w-2/3" />
      <Skeleton className="h-40" />
      <span className="sr-only">Loading the page…</span>
    </div>
  );
}
