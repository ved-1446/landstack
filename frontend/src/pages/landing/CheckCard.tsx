import { Search } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, getPublicPlot } from "../../api";
import { SamplePlotChips } from "../../components/SamplePlotChips";
import { BandChip, Button, GlassCard } from "../../components/ui";
import type { PublicPlot } from "../../types";

type Outcome = { kind: "found"; plot: PublicPlot } | { kind: "none" } | { kind: "error"; message: string };

/**
 * The public "Check a plot" card. It asks GET /public/plot/{ulpin}, which returns ONLY the id, the village and the band, and shows
 * exactly those three things (the band as an icon plus words). No login, no AI. Any wrong id gets the same "No plot found" message.
 */
export function CheckCard({
  eyebrow = "CHECK A PLOT",
  title = (
    <>
      Is this plot <em className="text-coral-text">safe</em> to trust?
    </>
  ),
  intro = "Type a plot id (14 letters and digits). You get the village and the risk band. Nothing else is shown to the public.",
  initialUlpin = "",
}: {
  eyebrow?: string;
  title?: ReactNode;
  intro?: ReactNode;
  initialUlpin?: string;
} = {}) {
  const [value, setValue] = useState(initialUlpin);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const abort = useRef<AbortController | null>(null);

  async function run(raw: string) {
    const clean = raw.trim().toUpperCase();
    if (!clean) return;
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    try {
      setOutcome({ kind: "found", plot: await getPublicPlot(clean, controller.signal) });
    } catch (err) {
      if (controller.signal.aborted) return;
      if (err instanceof ApiError && err.status === 404) setOutcome({ kind: "none" });
      else setOutcome({ kind: "error", message: err instanceof Error ? err.message : "Something went wrong. Please try again." });
    }
    setBusy(false);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void run(value);
  }

  function pick(ulpin: string) {
    setValue(ulpin);
    void run(ulpin);
  }

  useEffect(() => {
    if (initialUlpin) void run(initialUlpin);
    return () => abort.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <GlassCard strong id="check" className="scroll-mt-32" aria-labelledby="check-title">
      <p className="font-mono text-12 tracking-widest text-muted-on-navy">{eyebrow}</p>
      <h2 id="check-title" className="mt-2 font-serif text-34 text-cream">
        {title}
      </h2>
      <p className="mt-2 text-14 text-muted-on-navy">{intro}</p>
      <form onSubmit={submit} className="mt-4 flex flex-wrap gap-3">
        <div className="min-w-0 flex-1">
          <label htmlFor="check-ulpin" className="sr-only">
            Plot id (ULPIN)
          </label>
          <input
            id="check-ulpin"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="MH000100000006"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            maxLength={14}
            className="h-11 w-full rounded-control border border-glass-border bg-navy-950 px-3 font-mono text-14 text-cream placeholder:text-faint-on-navy"
          />
        </div>
        <Button type="submit" loading={busy} disabled={!value.trim()}>
          <Search className="size-4" aria-hidden="true" />
          Check
        </Button>
      </form>
      <SamplePlotChips onPick={pick} />
      <div aria-live="polite" className="mt-4 min-h-6">
        {outcome?.kind === "found" && (
          <dl className="route-in flex flex-wrap items-center gap-x-6 gap-y-2 rounded-card border border-glass-border bg-glass-fill p-4">
            <div>
              <dt className="font-mono text-11 tracking-widest text-muted-on-navy">PLOT</dt>
              <dd className="font-mono text-16 text-cream">{outcome.plot.ulpin}</dd>
            </div>
            <div>
              <dt className="font-mono text-11 tracking-widest text-muted-on-navy">VILLAGE</dt>
              <dd className="text-16 text-cream">{outcome.plot.village}</dd>
            </div>
            <div>
              <dt className="mb-1 font-mono text-11 tracking-widest text-muted-on-navy">RISK BAND</dt>
              <dd>
                <BandChip band={outcome.plot.band} />
              </dd>
            </div>
          </dl>
        )}
        {outcome?.kind === "none" && <p className="route-in text-14 text-cream">No plot found with that id. Check it for typing mistakes.</p>}
        {outcome?.kind === "error" && <p className="route-in text-14 text-cream">{outcome.message}</p>}
      </div>
      <p className="text-12 text-muted-on-navy">Demo data: every plot here is made up.</p>
    </GlassCard>
  );
}
