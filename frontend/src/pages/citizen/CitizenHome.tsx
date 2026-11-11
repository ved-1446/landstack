import { ArrowRight, BadgeCheck, FileDown, MessageCircleQuestion, Search, Sprout } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Async } from "../../components/Async";
import { BandChip, CreamCard, PageHeader, StatCard } from "../../components/ui";
import { useAppData } from "../../lib/appData";
import type { PlotCollection } from "../../types";

interface Todo {
  key: string;
  icon: typeof Search;
  to: string;
  text: ReactNode;
}

function story(plots: PlotCollection): string {
  const all = plots.features.map((f) => f.properties);
  const red = all.filter((p) => p.band === "red").length;
  const amber = all.filter((p) => p.band === "amber").length;
  if (all.length === 0) return "No plots are linked to your account yet, so there is nothing to show.";
  const own = `You have ${all.length} ${all.length === 1 ? "plot" : "plots"} here.`;
  if (red + amber === 0) return `${own} All of them look fine: the checks found nothing to worry about.`;
  const parts = [red > 0 ? `${red} ${red === 1 ? "is" : "are"} in the red band (high risk)` : "", amber > 0 ? `${amber} ${amber === 1 ? "is" : "are"} in the amber band (worth watching)` : ""].filter(Boolean);
  return `${own} ${parts.join(" and ")}. That means the papers and the map do not agree somewhere. Open the plot to see exactly where.`;
}

/** Citizen home: a plain-words summary of my plots, and what to do next. */
export default function CitizenHome() {
  const { plots } = useAppData();
  return (
    <section>
      <PageHeader eyebrow="MY LAND" title="Your land," emphasis="in plain words" subtitle="A short summary of the plots linked to your account, and what you can do next." />
      <div className="mt-8">
        <Async
          state={plots}
          what="your plots"
          isEmpty={(d) => d.features.length === 0}
          empty={{ icon: Sprout, title: "No plots yet", description: "No plots are linked to your account in this demo, so there is nothing to show." }}
        >
          {(data) => {
            const props = data.features.map((f) => f.properties);
            const closer = props.filter((p) => p.band !== "green");
            const worst = [...props].sort((a, b) => b.score - a.score).filter((p) => p.band === "red").slice(0, 3);
            const todo: Todo[] = [
              ...worst.map((p) => ({
                key: p.ulpin,
                icon: Search,
                to: `/app/plots/${p.ulpin}`,
                text: (
                  <>
                    Open plot <span className="font-mono">{p.ulpin}</span> first: it is in the red band, with {p.score} points.
                  </>
                ),
              })),
              ...(closer.length > worst.length ? [{ key: "watch", icon: Search, to: "/app/plots", text: <>Look at the plots marked &quot;Watch&quot; in your list.</> }] : []),
              { key: "pdf", icon: FileDown, to: "/app/plots", text: <>Download a printable PDF passport of a plot from its page.</> },
              { key: "verify", icon: BadgeCheck, to: "/app/verify", text: <>Check that a printed passport is genuine.</> },
              { key: "guide", icon: MessageCircleQuestion, to: "/app/guide", text: <>Ask the Land Guide a general question about land records.</> },
            ];
            return (
              <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
                <div className="space-y-6">
                  <CreamCard>
                    <p className="font-mono text-12 tracking-widest text-muted-on-cream">THE SHORT STORY</p>
                    <p className="mt-3 font-serif text-34 text-ink">{story(data)}</p>
                  </CreamCard>
                  <div className="grid grid-cols-2 gap-4">
                    <StatCard label="My plots" value={props.length} />
                    <StatCard label="Need a closer look" value={closer.length} hint="amber or red band" />
                  </div>
                  <div className="flex flex-wrap gap-2" aria-label="My plots by band">
                    {(["green", "amber", "red"] as const).map((band) => (
                      <span key={band} className="inline-flex items-center gap-2 text-13 text-muted-on-navy">
                        <BandChip band={band} />
                        {props.filter((p) => p.band === band).length}
                      </span>
                    ))}
                  </div>
                </div>
                <CreamCard>
                  <h2 className="font-serif text-26 text-ink">What to do next</h2>
                  <ul className="mt-4 space-y-3">
                    {todo.map((item) => (
                      <li key={item.key}>
                        <Link to={item.to} className="flex items-start gap-3 rounded-control p-2 text-14 text-ink transition-colors hover:bg-line-on-cream">
                          <item.icon className="mt-0.5 size-5 shrink-0 text-muted-on-cream" aria-hidden="true" />
                          <span className="flex-1">{item.text}</span>
                          <ArrowRight className="mt-0.5 size-4 shrink-0 text-muted-on-cream" aria-hidden="true" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CreamCard>
              </div>
            );
          }}
        </Async>
      </div>
    </section>
  );
}
