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
