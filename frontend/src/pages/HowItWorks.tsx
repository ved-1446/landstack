import { Link } from "react-router";
import { ContourLines } from "../components/Backdrop";
import { BandChip, GlassCard, PageHeader } from "../components/ui";
import { BANDS, CHECKS, STEPS } from "./content";
import { StepArt } from "./Illustrations";

/** /how-it-works: the four steps, the nine checks, the three bands and what is simulated, in plain words. */
export default function HowItWorks() {
  return (
    <div className="mx-auto max-w-(--content-width) px-(--edge) py-12">
      <PageHeader
        eyebrow="HOW IT WORKS"
        title="Four steps, no"
        emphasis="magic"
        subtitle="LandStack looks at a plot the way a careful friend would: is the map right, do the papers agree, and what is the risk? Here is exactly how."
      />

      <ol className="mt-12 space-y-6">
        {STEPS.map((step, i) => (
          <li key={step.key}>
            <GlassCard className="grid items-center gap-6 md:grid-cols-[auto_1fr]">
              <StepArt step={step.key} className="h-32 w-44" />
              <div>
                <p className="font-mono text-12 tracking-widest text-muted-on-navy">STEP {i + 1}</p>
                <h2 className="mt-1 font-serif text-34 text-cream">{step.title}</h2>
                <p className="mt-2 text-16 text-muted-on-navy">{step.long}</p>
              </div>
            </GlassCard>
          </li>
        ))}
      </ol>

      <section aria-labelledby="checks-title" className="relative mt-20 overflow-hidden rounded-glass">
        <ContourLines className="opacity-30" />
        <div className="relative">
          <p className="font-mono text-12 tracking-widest text-muted-on-navy">THE NINE CHECKS</p>
          <h2 id="checks-title" className="mt-2 font-serif text-34 text-cream md:text-58">
            What gets <em className="text-coral">checked</em>
          </h2>
          <p className="mt-3 max-w-2xl text-16 text-muted-on-navy">Each check is a fixed question. If the answer is a problem, the plot gets that many points. The points never change from plot to plot.</p>
          <ul className="mt-8 grid gap-4 md:grid-cols-2">
            {CHECKS.map((check) => (
              <li key={check.name}>
                <GlassCard padding="sm" className="h-full">
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="text-16 font-medium text-cream">{check.name}</h3>
                    <span className="font-mono text-14 text-cream">+{check.points}</span>
                  </div>
                  <p className="mt-1 text-14 text-muted-on-navy">{check.plain}</p>
                  {check.simulated && (
                    <p className="mt-2 inline-block rounded-pill border border-dashed border-sim px-2 py-0.5 font-mono text-11 tracking-wider text-sim">SIMULATED</p>
                  )}
                </GlassCard>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="bands-title" className="mt-20">
        <p className="font-mono text-12 tracking-widest text-muted-on-navy">THE THREE BANDS</p>
        <h2 id="bands-title" className="mt-2 font-serif text-34 text-cream md:text-58">
          From the total, a <em className="text-coral">band</em>
        </h2>
        <p className="mt-3 max-w-2xl text-16 text-muted-on-navy">The points are added up, and the total never goes above 100. The total decides the band. The band is always written in words, never just a colour.</p>
        <ul className="mt-8 grid gap-4 md:grid-cols-3">
          {BANDS.map((band) => (
            <li key={band.key}>
              <GlassCard className="h-full">
                <BandChip band={band.key} />
                <p className="mt-4 font-serif text-34 text-cream">{band.range}</p>
                <p className="mt-2 text-14 text-muted-on-navy">{band.plain}</p>
              </GlassCard>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="rules-title" className="mt-20 grid gap-6 md:grid-cols-2">
        <GlassCard strong>
          <h2 id="rules-title" className="font-serif text-34 text-cream">
            Only code sets the <em className="text-coral">score</em>
          </h2>
          <p className="mt-3 text-14 text-muted-on-navy">
            The score is added up by ordinary code from the nine checks. An AI never changes it. When an AI is switched on, its only job is to
            explain the findings in plain words (and translate them), and that text is clearly labelled.
          </p>
        </GlassCard>
        <GlassCard strong>
          <h2 className="font-serif text-34 text-cream">
            What is <em className="text-sim">simulated</em>
          </h2>
          <p className="mt-3 text-14 text-muted-on-navy">
            All plots, names and records are made up. The new-building check compares two pretend surveys, not real satellite pictures, and its map outlines are
            marked SIMULATED. A small statistical model hints that a plot looks unusual; it learned from made-up data and adds no points.
          </p>
        </GlassCard>
      </section>

      <p className="mt-12 text-14 text-muted-on-navy">
        Want to see it?{" "}
        <Link to="/login" className="text-cream underline underline-offset-4">
          Sign in
        </Link>{" "}
        or{" "}
        <Link to="/verify" className="text-cream underline underline-offset-4">
          verify a printed passport
        </Link>
        .
      </p>
    </div>
  );
}
