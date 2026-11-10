import { useSyncExternalStore } from "react";

/** True while the CSS media query matches (updates live). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (notify) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", notify);
      return () => list.removeEventListener("change", notify);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Phones: under 768px, where the rail becomes a bottom bar and panels become bottom sheets. */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 767px)");
}
