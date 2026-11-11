import { Sprout } from "lucide-react";
import { Link } from "react-router";
import { Async } from "../../components/Async";
import { BandChip, CreamCard, PageHeader } from "../../components/ui";
import { useAppData } from "../../lib/appData";
import { sqm } from "../../lib/format";

/** My plots: one cream card per plot with the id, village, area, band (icon and words) and score. A click opens its passport page. */
export default function CitizenPlots() {
  const { plots } = useAppData();
  return (
    <section>
      <PageHeader eyebrow="MY LAND" title="My" emphasis="plots" subtitle="Open a plot to see its checks, a plain-words explanation, and a PDF you can print." />
      <div className="mt-8">
        <Async
          state={plots}
          what="your plots"
          isEmpty={(d) => d.features.length === 0}
          empty={{ icon: Sprout, title: "No plots yet", description: "No plots are linked to your account in this demo." }}
        >
          {(data) => (
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.features.map((f, i) => {
                const p = f.properties;
                return (
                  <li key={p.ulpin} className="rise" style={{ ["--i" as string]: i }}>
                    <Link to={`/app/plots/${p.ulpin}`} className="block rounded-glass focus-visible:outline-offset-4">
                      <CreamCard lift className="h-full">
                        <p className="font-mono text-12 text-muted-on-cream">{p.ulpin}</p>
                        <p className="mt-1 font-serif text-34 text-ink">{p.village}</p>
                        <p className="mt-1 text-14 text-muted-on-cream">
                          {sqm(p.area_sqm)} · {p.land_use}
                        </p>
                        <div className="mt-4 flex items-center justify-between gap-2">
                          <BandChip band={p.band} surface="cream" />
                          <p className="font-serif text-34 text-ink">
                            {p.score}
                            <span className="ml-1 font-mono text-12 text-muted-on-cream">/ 100</span>
                          </p>
                        </div>
                      </CreamCard>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Async>
      </div>
    </section>
  );
}
