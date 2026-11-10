import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "../../lib/cn";
import { useIsMobile } from "../../lib/media";
import { DURATION, EASE_OUT } from "../../lib/motion";
import { Button } from "./Button";

interface PopoverProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** pinned under the scrolling content (for example a chat input) */
  footer?: ReactNode;
  className?: string;
}

/**
 * A frosted panel that floats next to the rail. Under 768px it becomes a bottom sheet above the tab bar.
 * Escape closes it, and so does a click anywhere outside it (the rail buttons toggle it themselves).
 */
export function Popover({ open, onClose, title, children, footer, className }: PopoverProps) {
  const mobile = useIsMobile();
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onPointer = (event: PointerEvent) => {
      const target = event.target as Node;
      if (panel.current?.contains(target)) return;
      if (target instanceof Element && target.closest("[data-rail]")) return;
      onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={panel}
          role="dialog"
          aria-label={title}
          initial={mobile ? { y: 24, opacity: 0 } : { x: -8, opacity: 0 }}
          animate={{ x: 0, y: 0, opacity: 1 }}
          exit={mobile ? { y: 24, opacity: 0 } : { x: -8, opacity: 0 }}
          transition={{ duration: DURATION.base, ease: EASE_OUT }}
          className={cn(
            "glass fixed z-panel flex flex-col overflow-hidden shadow-2",
            mobile
              ? "inset-x-0 bottom-(--tabbar-height) max-h-(--sheet-max) rounded-t-drawer"
              : "left-(--popover-left) top-(--popover-top) max-h-[calc(100dvh-var(--popover-top)-var(--popover-bottom))] w-(--popover-width) rounded-panel",
            className,
          )}
        >
          <div className="flex shrink-0 items-center justify-between px-4 pt-3">
            <h2 className="font-serif text-26 text-cream">{title}</h2>
            <Button variant="ghost" size="icon" aria-label={`Close ${title}`} onClick={onClose}>
              <X className="size-5" aria-hidden="true" />
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4">{children}</div>
          {footer && <div className="shrink-0 border-t border-line-on-navy px-4 py-3">{footer}</div>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
