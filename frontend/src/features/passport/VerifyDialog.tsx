import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, verifyDocument } from "../../api";
import { Button, Chip } from "../../components/ui";
import { DURATION, EASE_OUT } from "../../lib/motion";
import type { Verification } from "../../types";

interface VerifyDialogProps {
  open: boolean;
  onClose: () => void;
}

type Outcome = { kind: "result"; value: Verification } | { kind: "message"; text: string } | null;

/**
 * Check a printed passport. The document id is printed on the paper (and is in its QR code); the server
 * answers only whether the records still match. It tells nothing else about the plot.
 */
export function VerifyDialog({ open, onClose }: VerifyDialogProps) {
  const [docId, setDocId] = useState("");
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setOutcome(null);
    input.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", onKey, true);
    return () => document.removeEventListener("keydown", onKey, true);
  }, [open, onClose]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!docId.trim()) {
      setOutcome({ kind: "message", text: "Type the document ID printed on the passport." });
      return;
    }
    setBusy(true);
    setOutcome(null);
    try {
      setOutcome({ kind: "result", value: await verifyDocument(docId) });
    } catch (err) {
      const text =
        err instanceof ApiError && err.status === 404
          ? "No document with that ID was found. Check the ID on the page and try again."
          : err instanceof ApiError && err.status === 422
            ? "That does not look like a document ID. It is printed on the passport, like 7KQ2-M9XD-4TPA."
            : err instanceof Error
              ? err.message
              : "Could not check the document.";
      setOutcome({ kind: "message", text });
    }
    setBusy(false);
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-modal flex items-center justify-center bg-navy-950/80 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: DURATION.base, ease: EASE_OUT }}
          onPointerDown={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby="verify-title"
            initial={{ y: 16 }}
            animate={{ y: 0 }}
            exit={{ y: 16 }}
            transition={{ duration: DURATION.base, ease: EASE_OUT }}
            className="w-full max-w-96 rounded-panel border border-line-on-navy bg-navy-900 p-6 shadow-3"
          >
            <div className="flex items-start justify-between gap-2">
              <h2 id="verify-title" className="font-serif text-26 text-cream">
                Verify a passport
              </h2>
              <Button variant="ghost" size="icon" aria-label="Close" onClick={onClose}>
                <X className="size-5" aria-hidden="true" />
              </Button>
            </div>
            <p className="mt-2 text-13 text-muted-on-navy">
              Type the document ID printed on the paper passport. This checks whether the records still match what was printed.
            </p>
            <form onSubmit={submit} className="mt-4 space-y-3">
              <label htmlFor="doc-id" className="block font-mono text-11 tracking-wider text-faint-on-navy">
                DOCUMENT ID
              </label>
              <input
                id="doc-id"
                ref={input}
                value={docId}
                onChange={(e) => setDocId(e.target.value.toUpperCase())}
                placeholder="7KQ2-M9XD-4TPA"
                autoComplete="off"
                spellCheck={false}
                className="h-11 w-full rounded-control border border-line-on-navy bg-navy-950 px-3 font-mono text-14 tracking-wider text-cream placeholder:text-faint-on-navy"
              />
              <Button type="submit" className="w-full" loading={busy}>
                Check
              </Button>
            </form>
            <div aria-live="polite" className="mt-4">
              {outcome?.kind === "message" && <p className="rounded-control bg-navy-800 px-3 py-2 text-13 text-cream">{outcome.text}</p>}
              {outcome?.kind === "result" && (
                <div className="space-y-2 rounded-card border border-line-on-navy bg-navy-800 p-3">
                  <Chip tone={outcome.value.valid ? "green" : "amber"}>{outcome.value.valid ? "RECORDS MATCH" : "RECORDS CHANGED"}</Chip>
                  <p className="text-13 text-cream">
                    {outcome.value.valid
                      ? "This passport still matches the records."
                      : "The records have changed since this passport was issued. Ask for a new one."}
                  </p>
                  <p className="font-mono text-12 text-muted-on-navy">
                    {outcome.value.ulpin} · issued {new Date(outcome.value.issued_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
