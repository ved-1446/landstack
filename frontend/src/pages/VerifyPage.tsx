import { CircleCheck, FileQuestion, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router";
import { ApiError, verifyDocument } from "../api";
import { Button, GlassCard, PageHeader } from "../components/ui";
import type { Verification } from "../types";

export type Outcome = { kind: "matches" | "changed"; result: Verification } | { kind: "not_found" } | { kind: "error"; message: string };

const when = (iso: string) => new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

/** The verify form and its result. Used by the public /verify page and by the citizen's Verify tab. */
export function VerifyPanel({ initialId = "", onFound }: { initialId?: string; onFound?: (outcome: Outcome) => void }) {
  const [id, setId] = useState(initialId);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const abort = useRef<AbortController | null>(null);

  async function check(value: string) {
    const clean = value.trim();
    if (!clean) return;
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    try {
      const result = await verifyDocument(clean, controller.signal);
      const found: Outcome = { kind: result.valid ? "matches" : "changed", result };
      setOutcome(found);
      onFound?.(found);
    } catch (err) {
      if (controller.signal.aborted) return;
      if (err instanceof ApiError && (err.status === 404 || err.status === 422)) setOutcome({ kind: "not_found" });
      else setOutcome({ kind: "error", message: err instanceof Error ? err.message : "Something went wrong." });
    }
    setBusy(false);
  }

  useEffect(() => {
    if (initialId) void check(initialId);
    return () => abort.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    void check(id);
  }

  return (
    <>
      <GlassCard className="mt-8">
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1">
            <label htmlFor="doc-id" className="mb-2 block text-13 text-muted-on-navy">
              Document id
            </label>
            <input
              id="doc-id"
              value={id}
              onChange={(e) => setId(e.target.value)}
              placeholder="7KQ2-M9XD-4TPA"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={40}
              className="h-11 w-full rounded-control border border-glass-border bg-navy-950 px-3 font-mono text-14 text-cream placeholder:text-faint-on-navy"
            />
          </div>
          <Button type="submit" loading={busy} disabled={!id.trim()}>
            Verify
          </Button>
        </form>

        <div aria-live="polite" className="mt-6">
          {outcome?.kind === "matches" && (
            <Result icon={CircleCheck} word="MATCHES" toneClass="text-risk-green-tint">
              The records are still what was printed. Plot <span className="font-mono">{outcome.result.ulpin}</span>, issued {when(outcome.result.issued_at)}.
            </Result>
          )}
          {outcome?.kind === "changed" && (
            <Result icon={TriangleAlert} word="HAS CHANGED" toneClass="text-risk-amber-tint">
              The records for plot <span className="font-mono">{outcome.result.ulpin}</span> are different from when this paper was printed ({when(outcome.result.issued_at)}).
              Ask the issuing office for a new passport. The paper is not wrong or fake; the records moved on.
            </Result>
          )}
          {outcome?.kind === "not_found" && (
            <Result icon={FileQuestion} word="NOT FOUND" toneClass="text-cream">
              No passport has that document id. Check the id for typing mistakes. A passport from a different copy of LandStack will not be found here.
            </Result>
          )}
          {outcome?.kind === "error" && (
            <Result icon={TriangleAlert} word="COULD NOT CHECK" toneClass="text-cream">
              {outcome.message}
            </Result>
          )}
        </div>
      </GlassCard>
      <p className="mt-4 text-13 text-muted-on-navy">
        We show only whether it matches, the plot id and the date. No names, no evidence and no score.
      </p>
    </>
  );
}

/** /verify: type the document id printed on a land passport and see whether the records still match. Public, no login. */
export default function VerifyPage() {
  const [params] = useSearchParams();
  return (
    <div className="mx-auto max-w-3xl px-(--edge) py-12">
      <PageHeader
        eyebrow="VERIFY A PASSPORT"
        title="Is this paper still"
        emphasis="true?"
        subtitle="Type the document id printed at the bottom of a land passport (or scan its QR code). We say whether the records still match what was printed. No login needed."
      />
      <VerifyPanel initialId={params.get("id") ?? ""} />
    </div>
  );
}

function Result({ icon: Icon, word, toneClass, children }: { icon: typeof CircleCheck; word: string; toneClass: string; children: React.ReactNode }) {
  return (
    <div className="route-in rounded-card border border-glass-border bg-glass-fill p-4">
      <p className={`flex items-center gap-2 font-serif text-34 ${toneClass}`}>
        <Icon className="size-8" aria-hidden="true" />
        {word}
      </p>
      <p className="mt-2 text-14 text-muted-on-navy">{children}</p>
    </div>
  );
}
