import { useSyncExternalStore } from "react";

export type Theme = "light" | "dark";

/** The saved choice. Same key as the inline script in index.html that sets the theme before the first paint. */
export const THEME_KEY = "landstack-theme";

function stored(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null; // private window, blocked storage: just follow the system
  }
}

function system(): Theme {
  try {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  } catch {
    return "dark";
  }
}

const listeners = new Set<() => void>();
let current: Theme | null = null;

function apply(theme: Theme) {
  current = theme;
  document.documentElement.dataset.theme = theme;
  const page = getComputedStyle(document.documentElement).getPropertyValue("--navy-950").trim();
  if (page) document.querySelector('meta[name="theme-color"]')?.setAttribute("content", page);
  document.querySelector('meta[name="color-scheme"]')?.setAttribute("content", theme);
  listeners.forEach((l) => l());
}

/** Read the theme once: the saved choice, else the system preference, else dark. Call before the first render. */
export function initTheme(): Theme {
  apply(stored() ?? system());
  try {
    // with no saved choice, follow the system when it changes
    window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      if (!stored()) apply(system());
    });
  } catch {
    /* no matchMedia: nothing to follow */
  }
  return current as Theme;
}

export function setTheme(theme: Theme) {
  try {
    window.localStorage.setItem(THEME_KEY, theme);
  } catch {
    /* the choice just lasts until the page is reloaded */
  }
  apply(theme);
}

function read(): Theme {
  if (current) return current;
  const fromDom = document.documentElement.dataset.theme;
  return fromDom === "light" || fromDom === "dark" ? fromDom : stored() ?? system();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => void listeners.delete(listener);
}

/** The current theme, and a function to switch it. */
export function useTheme(): { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void } {
  const theme = useSyncExternalStore(subscribe, read, () => "dark" as Theme);
  return { theme, setTheme, toggle: () => setTheme(theme === "light" ? "dark" : "light") };
}
