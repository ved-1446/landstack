import { useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef } from "react";
import { buildFlowFieldDocument } from "./flowFieldDocument";

const STILL_AFTER_MS = 1800; // reduced motion: let the trails paint for a moment, then freeze on one frame

/**
 * The animated login background (ThreeUI "Flow Field"). It runs in a sandboxed iframe with no network
 * access and is loaded only on the login screen. It pauses when the tab is hidden, and shows a still frame
 * when the visitor prefers reduced motion.
 */
export default function FlowField() {
  const frame = useRef<HTMLIFrameElement>(null);
  const reduceMotion = useReducedMotion();
  const html = useMemo(() => buildFlowFieldDocument({ particleCount: window.innerWidth < 768 ? 1200 : 2500 }), []);

  const setSpeed = (value: number) => frame.current?.contentWindow?.postMessage({ type: "landstack-flow-speed", value }, "*");

  useEffect(() => {
    const onVisibility = () => setSpeed(document.hidden || reduceMotion ? 0 : 1);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [reduceMotion]);

  function onLoad() {
    if (!reduceMotion) return;
    window.setTimeout(() => setSpeed(0), STILL_AFTER_MS);
  }

  return (
    <iframe
      ref={frame}
      title="Animated background"
      aria-hidden="true"
      tabIndex={-1}
      srcDoc={html}
      sandbox="allow-scripts"
      onLoad={onLoad}
      data-testid="flow-field"
      className="absolute inset-0 size-full border-0"
    />
  );
}
