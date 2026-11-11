import type { CSSProperties } from "react";
import { BandChip, CreamCard, Donut, GlassCard, ScoreGauge } from "../../components/ui";
import type { PublicStats } from "../../types";

const tilt = (deg: number, i: number) => ({ ["--tilt" as string]: `${deg}deg`, ["--i" as string]: i, transform: `rotate(${deg}deg)` }) as CSSProperties;

// A made-up example, labelled "Sample data": three findings that add up to 65, which is the red band (60 and up).
const SAMPLE = [
  { name: "Boundary overlap", points: 40 },
  { name: "Tax overdue", points: 15 },
  { name: "Missing record", points: 10 },
];

function SampleTag() {
  return <span className="rounded-pill border border-line-on-cream px-2 py-0.5 font-mono text-11 tracking-wider text-muted-on-cream">SAMPLE DATA</span>;
}

/** Three slightly tilted preview cards (they float slowly). Only the middle one is real: it uses the counts from /public/stats. */
export function Proof({ stats, failed }: { stats: PublicStats | null; failed: boolean }) {
  const b = stats?.plots_per_band;
  return (
    <div className="grid gap-6 md:grid-cols-3 md:items-center">
      <CreamCard className="float-slow" style={tilt(-2, 0)}>
        <div className="flex items-center justify-between">
          <p className="font-mono text-11 tracking-widest text-muted-on-cream">A LAND PASSPORT</p>
          <SampleTag />
        </div>
        <ul className="mt-3 space-y-1 text-14 text-ink">
          {SAMPLE.map((f) => (
            <li key={f.name} className="flex justify-between">
              <span>{f.name}</span>
              <span className="font-mono">+{f.points}</span>
            </li>
          ))}
          <li className="flex justify-between border-t border-line-on-cream pt-1 font-medium">
            <span>Score</span>
            <span className="font-mono">40 + 15 + 10 = 65</span>
          </li>
        </ul>
        <ScoreGauge score={65} band="red" className="mt-4" />
        <div className="mt-2 flex justify-center">
          <BandChip band="red" surface="cream" />
        </div>
      </CreamCard>

      <GlassCard strong className="float-slow" style={tilt(1.5, 1)}>
        <p className="font-mono text-11 tracking-widest text-muted-on-navy">PLOTS BY RISK BAND</p>
        {b ? (
          <Donut
            className="mt-4"
            centre={String(stats.total_plots)}
            slices={[
              { label: "Green, low risk", value: b.green, strokeClass: "stroke-risk-green", dotClass: "text-risk-green" },
              { label: "Amber, watch", value: b.amber, strokeClass: "stroke-risk-amber", dotClass: "text-risk-amber" },
              { label: "Red, high risk", value: b.red, strokeClass: "stroke-risk-red", dotClass: "text-risk-red" },
            ]}
          />
        ) : (
          <p className="mt-4 text-14 text-muted-on-navy">{failed ? "The live counts could not be loaded. Is the API running?" : "Loading the live counts…"}</p>
        )}
        <p className="mt-4 text-12 text-muted-on-navy">Live counts from the demo data.</p>
      </GlassCard>

      <GlassCard className="float-slow" style={tilt(-1.5, 2)}>
        <p className="font-mono text-11 tracking-widest text-muted-on-navy">NEEDS A CLOSER LOOK</p>
        <p className="mt-3 font-serif text-58 text-cream">{b ? b.amber + b.red : "…"}</p>
        <p className="text-14 text-muted-on-navy">of {stats ? stats.total_plots : "…"} plots are in the amber or red band: worth a closer look.</p>
        <p className="mt-4 text-13 text-cream">{b ? `${b.red} of them are in the red band.` : ""}</p>
      </GlassCard>
    </div>
  );
}
