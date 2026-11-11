import { Info, Telescope } from "lucide-react";
import { getAdminInsights } from "../../api";
import { Async } from "../../components/Async";
import { BarList, GlassCard, PageHeader, StatCard } from "../../components/ui";
import { useFetch } from "../../hooks";

/** Insights: what the unusual-plot model says overall, in plain words. EXPLANATION ONLY: scores are set by code. */
export default function Insights() {
  const state = useFetch((signal) => getAdminInsights(signal), []);
  return (
    <section>
      <PageHeader eyebrow="CONTROL ROOM" title="Model" emphasis="insights" subtitle="A small statistical model points out plots that look unusual. Here is what it pays attention to, in plain words." />
      <div className="mt-8">
        <Async state={state} what="the model insights">
          {(d) => (
            <>
              <GlassCard role="note" aria-label="What this page is" className="flex gap-3">
                <Info className="mt-1 size-5 shrink-0 text-muted-on-navy" aria-hidden="true" />
                <p className="text-14 text-cream">
                  <strong className="font-medium">Explanation only.</strong> {d.note.replace(/^Explanation only\.\s*/, "")}
                </p>
              </GlassCard>
              {!d.available ? (
                <GlassCard className="mt-6">
                  <div className="flex flex-col items-center gap-3 px-4 py-8 text-center">
                    <Telescope className="size-8 text-muted-on-navy" aria-hidden="true" />
                    <h2 className="font-serif text-26 text-cream">No model is installed</h2>
                    <p className="max-w-md text-13 text-muted-on-navy">
                      The API did not find a trained model, so passports show no unusual note and there is nothing to explain. Train one with{" "}
                      <span className="font-mono">python -m ml.make_dataset</span> and <span className="font-mono">python -m ml.train_unusual</span>, then restart the API.
                    </p>
                  </div>
                </GlassCard>
              ) : (
                <>
                  <div className="mt-6 grid gap-4 sm:grid-cols-3">
                    <StatCard label="Plots looked at" value={d.plots_checked} />
                    <StatCard label="Look unusual" value={d.flagged} hint={`the top ${100 - Math.round(d.flag_percentile ?? 95)}% of its training`} />
                    <StatCard label="Also amber or red" value={d.flagged_also_amber_or_red} hint="by the nine checks" />
                  </div>
                  <GlassCard className="mt-6">
                    <h2 className="font-serif text-26 text-cream">What it pays attention to</h2>
                    <p className="mt-1 text-13 text-muted-on-navy">
                      The share of the model&apos;s decisions each signal explains, averaged over every plot (worked out with {d.method === "shap" ? "SHAP" : "distance from the typical value"}). Learned from{" "}
                      {d.trained_on_plots?.toLocaleString("en-IN")} generated plots, so it mostly relearns how the demo data was made.
                    </p>
                    <BarList
                      className="mt-5"
                      items={d.features.map((f) => ({ label: `${f.label} (${Math.round(f.share * 100)}%)`, value: Math.round(f.share * 1000) / 10, barClass: "bg-cream" }))}
                    />
                  </GlassCard>
                  <GlassCard className="mt-6">
                    <h2 className="font-serif text-26 text-cream">Why the unusual plots look unusual</h2>
                    <p className="mt-1 text-13 text-muted-on-navy">For each plot it flags, the signal that pushed hardest. {d.flagged === 0 ? "No plot is flagged right now." : ""}</p>
                    <ul className="mt-4 space-y-2">
                      {d.features
                        .filter((f) => f.top_reason_for > 0)
                        .map((f) => (
                          <li key={f.name} className="flex justify-between gap-4 border-b border-glass-border pb-2 text-14">
                            <span className="text-cream">{f.label}</span>
                            <span className="font-mono text-muted-on-navy">
                              {f.top_reason_for} {f.top_reason_for === 1 ? "plot" : "plots"}
                            </span>
                          </li>
                        ))}
                    </ul>
                  </GlassCard>
                </>
              )}
            </>
          )}
        </Async>
      </div>
    </section>
  );
}
