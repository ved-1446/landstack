import { GlassCard, PageHeader } from "../components/ui";

const STACK = [
  ["The map", "MapLibre draws the plots. The map pictures come from CARTO and Esri, with data from OpenStreetMap."],
  ["The screens", "React and Tailwind make the pages you are looking at."],
  ["The brain", "A Python server (FastAPI) asks a spatial database (PostgreSQL with PostGIS) questions about shapes, like \"do these two plots overlap?\"."],
  ["The helpers", "A small statistical model hints at unusual plots, and an optional AI explains findings in plain words. Neither can change a score."],
];

const LIMITS = [
  "Everything is fake demo data near Pune. It is not an official or legal service and it never talks to a government system.",
  "New-building changes are simulated from two pretend surveys. There are no real satellite pictures.",
  "The machine-learning hint learned from made-up data, so it mostly relearns how the demo was made. Treat it as a nudge for a human to look.",
  "The Hindi and Marathi sentences have not been checked by a native speaker yet, and machine translation can make mistakes.",
  "Login tokens last an hour and cannot be cancelled early. There is no real-time update from any land office.",
];

const CREDITS = [
  "The Flow Field background is from ThreeUI, under the MIT licence.",
  "Fonts: Instrument Serif, Geist, Geist Mono and Noto Sans Devanagari, under the SIL Open Font Licence.",
  "Map pictures and data: CARTO, Esri and OpenStreetMap contributors.",
  "The Land Guide answers only from public pages from Vikaspedia (C-DAC, MeitY, Government of India), with a link in every answer.",
  "The full list is in THIRD_PARTY.md in the project.",
];

/** /about: what LandStack is, what it is not, how risk is scored, honest limits, credits. No personal names. */
export default function About() {
  return (
    <div className="mx-auto max-w-3xl px-(--edge) py-12">
      <PageHeader
        eyebrow="ABOUT"
        title="What LandStack"
        emphasis="is"
        subtitle="A demo that shows how land records could be checked on a map, so a buyer, an officer or an owner can see problems before they become disputes."
      />

      <div className="mt-10 space-y-6">
        <GlassCard>
          <h2 className="font-serif text-26 text-cream">What it is</h2>
          <p className="mt-2 text-14 text-muted-on-navy">
            LandStack puts land plots on a map and checks each plot&apos;s shape against its papers: the land record, the registration and the tax record. It gives every plot a risk score
            and a one-page passport that anyone can verify. It started from the SIH 2026 land-records problem statement.
          </p>
          <p className="mt-3 text-14 text-muted-on-navy">
            <span className="text-cream">Citizens</span> see only their own plots in plain words. <span className="text-cream">Officers</span> see every plot and its proof.{" "}
            <span className="text-cream">Admins</span> also see who looked at what.
          </p>
        </GlassCard>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">What it is not</h2>
          <p className="mt-2 text-14 text-muted-on-navy">
            It is not real government data and not a legal document. The plots and people are invented. Never use it to decide anything about real land.
          </p>
        </GlassCard>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">How the risk is scored</h2>
          <p className="mt-2 text-14 text-muted-on-navy">
            Nine fixed checks each add points when they find a problem. The total (never above 100) sets the band: green 0 to 24, amber 25 to 59, red 60 and up. Only code does this. An AI never changes
            a score; when one is on, it only explains the findings in plain words and says so.
          </p>
        </GlassCard>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">What it is built with</h2>
          <dl className="mt-3 space-y-3">
            {STACK.map(([name, text]) => (
              <div key={name}>
                <dt className="font-mono text-11 tracking-widest text-muted-on-navy">{name.toUpperCase()}</dt>
                <dd className="text-14 text-cream">{text}</dd>
              </div>
            ))}
          </dl>
        </GlassCard>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">Honest limits</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-14 text-muted-on-navy">
            {LIMITS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </GlassCard>

        <GlassCard>
          <h2 className="font-serif text-26 text-cream">Credits</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-14 text-muted-on-navy">
            {CREDITS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </GlassCard>
      </div>
    </div>
  );
}
