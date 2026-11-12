import { useSyncExternalStore } from "react";

/**
 * Is the API awake? On a free host the server falls asleep when nobody uses it and takes up to about a minute to start again.
 * Until the first answer arrives, a slow call (or one that cannot connect, or that the host answers with 502/503/504 while it
 * starts) shows a friendly "waking up" note and is tried again by itself. After the first answer the server counts as awake for
 * the rest of the visit, so normal errors are shown at once, as before.
 */
export type ServerPhase = "ok" | "waking" | "down";

/** The timings, in one place (tests make them short). */
export const wakeTuning = {
  slowAfterMs: 5000, // a first call slower than this shows the note
  retryEveryMs: 4000, // wait between tries
  maxTries: 30, // about two minutes in all
};

let awake = false;
let phase: ServerPhase = "ok";
const listeners = new Set<() => void>();

function set(next: ServerPhase) {
  if (phase === next) return;
  phase = next;
  listeners.forEach((l) => l());
}

export const serverIsAwake = () => awake;
export const currentPhase = () => phase;

/** The server answered (any HTTP answer, even an error like 404 or 401, means it is up). */
export function markAwake() {
  awake = true;
  set("ok");
}
export function markWaking() {
  if (!awake) set("waking");
}
export function markDown() {
  if (!awake) set("down");
}
/** Back to the start, for tests and for the "Try again" button. */
export function resetServerState() {
  awake = false;
  set("ok");
}

/** Status codes a host sends while it is still starting the app. */
export const WAKING_STATUSES = new Set([502, 503, 504]);

export const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const id = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(id);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

export function useServerPhase(): ServerPhase {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    () => phase,
    () => "ok" as ServerPhase,
  );
}
