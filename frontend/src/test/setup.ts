// jsdom has no matchMedia; framer-motion and our media hooks ask for it. Say "no match" (desktop, motion allowed).
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
window.scrollTo = (() => undefined) as typeof window.scrollTo;

// Pages are lazy-loaded and the whole suite runs in parallel: give "findBy..." a longer patience than the 1 s default so a busy
// machine does not make a correct test fail.
import { configure } from "@testing-library/react";
configure({ asyncUtilTimeout: 5000 });
