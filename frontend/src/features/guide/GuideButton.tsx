import { MessageCircleQuestion } from "lucide-react";
import { cn } from "../../lib/cn";

interface GuideButtonProps {
  open: boolean;
  onToggle: () => void;
  /** the passport drawer is open: the button moves left of it (and above the dock) on wide screens and hides on phones (the sheet covers that spot).
   *  While the panel itself is open the button is also hidden on phones, because the panel is a bottom sheet over that spot. */
  drawerOpen: boolean;
}

/**
 * The floating "Ask the Land Guide" button. It opens the same panel as the Land Guide icon in the rail.
 * It is navy with a hairline border, not coral: coral is kept for primary actions. `data-rail` stops the panel's
 * click-outside handler from closing it first, so this button can also close the panel.
 */
export function GuideButton({ open, onToggle, drawerOpen }: GuideButtonProps) {
  return (
    <button
      type="button"
      data-rail
      aria-pressed={open}
      aria-label="Ask the Land Guide"
      title="Ask the Land Guide"
      onClick={onToggle}
      className={cn(
        "fixed bottom-(--fab-bottom) right-(--edge) z-panel flex h-11 items-center gap-2 rounded-pill border border-line-on-navy bg-navy-800 px-4 text-14 text-cream shadow-2 transition-colors duration-150 ease-out hover:bg-navy-900 max-md:w-11 max-md:justify-center max-md:px-0",
        open && "bg-navy-900 max-md:hidden",      // on a phone the open sheet would sit under it: the rail icon closes the panel there
        drawerOpen && "md:right-[calc(var(--drawer-width)+var(--edge)*2)] md:bottom-(--fab-bottom-drawer) max-md:hidden",
      )}
    >
      <MessageCircleQuestion className="size-5" aria-hidden="true" />
      <span className="max-md:sr-only">Ask the Land Guide</span>
      <span aria-hidden="true" className="rounded-pill border border-line-on-navy px-2 font-mono text-11 text-muted-on-navy max-md:hidden">
        AI
      </span>
    </button>
  );
}
