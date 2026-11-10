import { AnimatePresence, motion } from "framer-motion";
import { Check, CircleAlert, Info, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { DURATION, EASE_OUT } from "../../lib/motion";

type ToastTone = "info" | "success" | "error";
interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}
interface ToastApi {
  push: (toast: Omit<ToastItem, "id">) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
const SHOW_FOR_MS = 6000;
const ICON = { info: Info, success: Check, error: CircleAlert } as const;

/** Wrap the app once; call useToast().push(...) from anywhere to show a small message. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((all) => all.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = nextId.current++;
      setToasts((all) => [...all.slice(-2), { ...toast, id }]);
      window.setTimeout(() => dismiss(id), SHOW_FOR_MS);
    },
    [dismiss],
  );
  const api = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-(--toast-bottom) z-toast flex flex-col items-center gap-2 px-4">
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon = ICON[toast.tone];
            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ duration: DURATION.base, ease: EASE_OUT }}
                className="pointer-events-auto flex w-full max-w-96 items-start gap-3 rounded-card border border-line-on-navy bg-navy-800 p-3 text-cream shadow-2"
              >
                <Icon className="mt-1 size-4 shrink-0" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="text-14 font-medium">{toast.title}</p>
                  {toast.description && <p className="text-13 text-muted-on-navy">{toast.description}</p>}
                </div>
                <button type="button" aria-label="Dismiss message" onClick={() => dismiss(toast.id)} className="rounded-control p-1 text-muted-on-navy hover:text-cream">
                  <X className="size-4" aria-hidden="true" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) throw new Error("useToast must be used inside <ToastProvider>");
  return api;
}
