import { MessageCircleQuestion } from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import { cn } from "../../lib/cn";
// the chat code is downloaded the first time the panel is opened, so every other page stays light
const GuidePanel = lazy(() => import("./GuidePanel").then((m) => ({ default: m.GuidePanel })));
import { useLanguage } from "./language";

/**
 * The Land Guide as a floating button fixed at the bottom-right of every signed-in page. It opens a compact chat panel above
 * the button. Escape or the close button closes it and the keyboard focus goes back to the button. The panel stays mounted while
 * it is closed, so the conversation is kept until the page is reloaded. The full page (/app/guide) still exists.
 * Mounted once, in the signed-in shell only: it never appears on the public pages or the login page.
 */
export function GuideLauncher() {
  const { t } = useLanguage();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [everOpened, setEverOpened] = useState(false); // once opened, the panel stays mounted so the conversation is kept
  const button = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  const close = useCallback(() => setOpen(false), []);

  // Escape closes the panel wherever the focus is
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // when the panel closes, the focus returns to the launcher; when it opens, the focus goes to the question box
  useEffect(() => {
    if (open) setEverOpened(true);
    if (open) document.getElementById("guide-input")?.focus();
    else if (wasOpen.current) button.current?.focus();
    wasOpen.current = open;
  }, [open]);

  // the full page has its own copy of the chat, so the button is not needed there
  if (pathname.replace(/\/+$/, "") === "/app/guide") return null;

  return (
    <div className={cn("guide-launcher fixed bottom-(--edge) right-(--edge) z-modal flex flex-col items-end gap-3")}>
      {everOpened && (
        <Suspense fallback={null}>
          <GuidePanel variant="popup" open={open} onClose={close} />
        </Suspense>
      )}
      <button
        ref={button}
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close the Land Guide" : "Ask the Land Guide"}
        className="flex h-12 items-center gap-2 rounded-pill bg-coral px-4 text-14 font-medium text-on-coral shadow-2 transition-colors duration-150 ease-out hover:bg-coral-hover active:bg-coral-pressed"
      >
        <MessageCircleQuestion className="size-5" aria-hidden="true" />
        <span className="max-sm:sr-only">{t("guide_title")}</span>
      </button>
    </div>
  );
}
