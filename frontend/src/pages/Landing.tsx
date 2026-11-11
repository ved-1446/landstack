import { Link } from "react-router";
import { getPublicStats } from "../api";
import { PageHeader, StatCard } from "../components/ui";
import { useFetch } from "../hooks";
import type { CSSProperties } from "react";

const step = (n: number) => ({ ["--i" as string]: n + 3 }) as CSSProperties;

/** The home page. In 13a-1 this is a working first version (headline, buttons, real counts); 13a-2 builds the full landing page. */
export default function Landing() {
  const stats = useFetch((signal) => getPublicStats(signal), []);
  return (
    <div className="mx-auto max-w-(--content-width) px-(--edge) py-16">
      <PageHeader
        eyebrow="LAND RECORDS, MADE CLEAR"
        title="Every plot. One passport."
        emphasis="No surprises."
        subtitle="LandStack checks a plot's map outline against its land record, its registration and its tax record, and gives it a risk score from fixed rules."
        actions={
          <>
            <Link to="/login" className="inline-flex h-11 items-center rounded-control bg-coral px-4 text-14 font-medium text-navy-950 hover:bg-coral-hover">
              Sign in
            </Link>
            <Link to="/how-it-works" className="glass-card inline-flex h-11 items-center rounded-control px-4 text-14 text-cream hover:bg-glass-fill-strong">
              How it works
            </Link>
          </>
        }
      />
      <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Plots" value={stats.data?.total_plots ?? "…"} style={step(0)} />
        <StatCard label="Green" value={stats.data?.plots_per_band.green ?? "…"} hint="low risk" style={step(1)} />
        <StatCard label="Amber" value={stats.data?.plots_per_band.amber ?? "…"} hint="watch" style={step(2)} />
        <StatCard label="Red" value={stats.data?.plots_per_band.red ?? "…"} hint="high risk" style={step(3)} />
      </div>
    </div>
  );
}
