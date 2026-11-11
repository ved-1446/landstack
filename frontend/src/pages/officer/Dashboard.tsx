import { ArrowRight, ListChecks } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { Async } from "../../components/Async";
import { MiniMap } from "../../components/MiniMap";
import { BandChip, BarList, Chip, DataList, GlassCard, PageHeader, StatCard } from "../../components/ui";
import { useAppData } from "../../lib/appData";
import { useAuth } from "../../auth";
import { prettyType } from "../../constants";
import type { ConflictType, Summary } from "../../types";

const QUEUE_SIZE = 10;

function problemBars(summary: Summary, simulated: ReadonlySet<string>) {
  return (Object.entries(summary.findings_per_type) as [ConflictType, number][])
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([type, value]) => ({ label: simulated.has(type) ? `${prettyType(type)} (simulated)` : prettyType(type), value, barClass: simulated.has(type) ? "bg-sim" : "bg-cream" }));
}

/** The officer's dashboard: the numbers, the problems by type, the priority queue and a map preview. Admin sees the same page as "Overview" until 13c. */
export default function Dashboard() {
  const { session } = useAuth();
  const { plots, summary, conflicts, types } = useAppData();
  const navigate = useNavigate();
  const simulated = new Set((types.data ?? []).filter((t) => t.simulated).map((t) => t.type));
  const eyebrow = session?.role === "admin" ? "CONTROL ROOM" : "OFFICER WORK DESK";

  return (
    <section>
      <PageHeader eyebrow={eyebrow} title="What needs your" emphasis="attention" subtitle="Counts for every plot, the kinds of problems found, and the ten riskiest plots." />

      <div className="mt-8">
        <Async state={summary} what="the counts" skeleton={<div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">{Array.from({ length: 6 }, (_, i) => <div key={i} className="h-28 animate-pulse rounded-glass bg-glass-fill motion-reduce:animate-none" />)}</div>}>
          {(s) => {
            if (!s) return null;
            const open = Object.values(s.findings_per_type).reduce((sum, n) => sum + n, 0);
            return (
              <>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
                  <StatCard label="Total plots" value={s.total_plots} />
                  <StatCard label="Red" value={s.plots_per_band.red} hint="high risk" />
                  <StatCard label="Amber" value={s.plots_per_band.amber} hint="watch" />
                  <StatCard label="Green" value={s.plots_per_band.green} hint="low risk" />
                  <StatCard label="Open conflicts" value={open} hint="findings in total" />
                  <StatCard label="Construction flags" value={s.findings_per_type.unrecorded_construction} hint="simulated" />
                </div>
                <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
                  <GlassCard>
                    <h2 className="font-serif text-26 text-cream">Problems by type</h2>
                    <p className="mt-1 text-13 text-muted-on-navy">How many findings each of the 9 checks made.</p>
                    <BarList className="mt-4" items={problemBars(s, simulated)} />
                  </GlassCard>
                  <GlassCard className="flex flex-col">
                    <h2 className="font-serif text-26 text-cream">Map preview</h2>
                    <Async state={plots} what="the map preview" skeleton={<div className="aspect-square animate-pulse rounded-card bg-glass-fill motion-reduce:animate-none" />}>
                      {(data) => (
                        <>
                          <MiniMap features={data.features} className="mt-4 aspect-square w-full" />
                          <p className="mt-3 text-13 text-muted-on-navy">
                            {s.plots_per_band.green} green, {s.plots_per_band.amber} amber, {s.plots_per_band.red} red.
                          </p>
                        </>
                      )}
                    </Async>
                    <Link to="/app/map" className="mt-auto inline-flex items-center gap-2 pt-4 text-14 text-cream underline underline-offset-4">
                      Open the map
                      <ArrowRight className="size-4" aria-hidden="true" />
                    </Link>
                  </GlassCard>
                </div>
              </>
            );
          }}
        </Async>
      </div>

      <GlassCard className="mt-6">
        <h2 className="font-serif text-26 text-cream">Priority queue</h2>
        <p className="mt-1 text-13 text-muted-on-navy">The {QUEUE_SIZE} plots with the highest score. Open one to see the proof.</p>
        <div className="mt-4">
          <Async
            state={conflicts}
            what="the priority queue"
            isEmpty={(rows) => !rows || rows.length === 0}
            empty={{ icon: ListChecks, title: "No problems found", description: "None of the plots has a finding, so there is nothing to look at first." }}
          >
            {(rows) => (
              <DataList
                label="Priority queue"
                rows={(rows ?? []).slice(0, QUEUE_SIZE).map((row) => ({
                  key: row.ulpin,
                  onClick: () => navigate(`/app/plots/${row.ulpin}`),
                  primary: (
                    <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      <span className="font-mono">{row.ulpin}</span>
                      <span className="text-muted-on-navy">{row.village}</span>
                    </span>
                  ),
                  secondary: (
                    <span className="flex flex-wrap gap-1">
                      {row.findings.map((f) => (
                        <Chip key={f.type} tone={f.simulated ? "sim" : "neutral"}>
                          {prettyType(f.type)} +{f.points}
                          {f.simulated ? " (simulated)" : ""}
                        </Chip>
                      ))}
                    </span>
                  ),
                  trailing: (
                    <span className="flex items-center gap-3">
                      <BandChip band={row.band} />
                      <span className="w-8 text-right font-serif text-26 text-cream">{row.score}</span>
                    </span>
                  ),
                }))}
              />
            )}
          </Async>
        </div>
      </GlassCard>
    </section>
  );
}
