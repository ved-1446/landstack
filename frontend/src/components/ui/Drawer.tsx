import { animate, motion, useDragControls, useMotionValue, type PanInfo } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../../lib/cn";
import { useIsMobile } from "../../lib/media";
import { DURATION, EASE_OUT } from "../../lib/motion";
import { Button } from "./Button";

type Snap = "peek" | "half" | "full";
const SHEET_HEIGHT = 0.92; // the sheet is 92% of the screen tall; it slides up and down inside that
const SHEET_HALF = 0.55; // how much of the screen shows at "half"
const PEEK_PX = 132; // how much shows at "peek": just the header

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  label: string;
  viewingAs: string;
  children: ReactNode;
}

/**
 * The right-hand passport drawer (solid navy shell, 430px, 20px corners). Under 768px it is a bottom
 * sheet you can drag between peek, half and full.
 */
export function Drawer({ open, onClose, label, viewingAs, children }: DrawerProps) {
  const mobile = useIsMobile();
  const closeButton = useRef<HTMLButtonElement>(null);
  const returnFocusTo = useRef<HTMLElement | null>(null);
  const controls = useDragControls();
  const [snap, setSnap] = useState<Snap>("half");
  const [viewport, setViewport] = useState(() => window.innerHeight);

  const sheetHeight = viewport * SHEET_HEIGHT;
  const offsets: Record<Snap, number> = {
    full: 0,
    half: sheetHeight - viewport * SHEET_HALF,
    peek: sheetHeight - PEEK_PX,
  };
  const y = useMotionValue(sheetHeight);

  useEffect(() => {
    const onResize = () => setViewport(window.innerHeight);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // opening: remember where focus was, move it into the drawer; closing gives it back
  useEffect(() => {
    if (!open) return;
    returnFocusTo.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setSnap(mobile ? "half" : "full");
    closeButton.current?.focus({ preventScroll: true });
    return () => returnFocusTo.current?.focus({ preventScroll: true });
  }, [open, mobile]);

  // sheet position follows the snap point
  useEffect(() => {
    if (!mobile || !open) return;
    const controlsAnimation = animate(y, offsets[snap], { duration: DURATION.slow, ease: EASE_OUT });
    return () => controlsAnimation.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snap, mobile, open, viewport]);

  function onDragEnd(_: PointerEvent, info: PanInfo) {
    const target = y.get() + info.velocity.y * 0.15;
    if (target > offsets.peek + 80) {
      onClose();
      return;
    }
    const nearest = (Object.keys(offsets) as Snap[]).reduce((best, key) =>
      Math.abs(offsets[key] - target) < Math.abs(offsets[best] - target) ? key : best,
    );
    setSnap(nearest);
    animate(y, offsets[nearest], { duration: DURATION.slow, ease: EASE_OUT });
  }

  if (!open) return null;

  return (
    <motion.aside
      role="dialog"
      aria-label={label}
      className={cn(
        "fixed z-drawer flex flex-col overflow-hidden border border-line-on-navy bg-navy-900 text-cream shadow-3",
        mobile ? "inset-x-0 bottom-0 rounded-t-drawer" : "bottom-(--edge) right-(--edge) top-(--edge) w-(--drawer-width) rounded-drawer",
      )}
      style={mobile ? { height: sheetHeight, y } : undefined}
      initial={mobile ? { y: sheetHeight } : { x: 48, opacity: 0 }}
      animate={mobile ? undefined : { x: 0, opacity: 1 }}
      exit={mobile ? { y: sheetHeight } : { x: 48, opacity: 0 }}
      transition={{ duration: DURATION.slow, ease: EASE_OUT }}
      drag={mobile ? "y" : false}
      dragControls={controls}
      dragListener={false}
      dragConstraints={{ top: 0, bottom: offsets.peek }}
      dragElastic={0.08}
      onDragEnd={onDragEnd}
    >
      {mobile && (
        <div onPointerDown={(e) => controls.start(e)} className="flex shrink-0 cursor-grab touch-none justify-center pt-2" aria-hidden="true">
          <span className="h-1 w-8 rounded-pill bg-faint-on-navy" />
        </div>
      )}
      <div className="flex shrink-0 items-center justify-between gap-2 px-4 py-3" onPointerDown={mobile ? (e) => controls.start(e) : undefined}>
        <p className="font-mono text-11 tracking-wider text-muted-on-navy">VIEWING AS: {viewingAs.toUpperCase()}</p>
        <Button ref={closeButton} variant="ghost" size="icon" aria-label="Close passport" onClick={onClose}>
          <X className="size-5" aria-hidden="true" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4" style={mobile ? { marginBottom: offsets[snap] } : undefined}>
        {children}
      </div>
    </motion.aside>
  );
}
