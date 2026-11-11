import { GlassCard, PageHeader } from "../components/ui";

/** Short first versions of the two information pages; 13a-2 writes the full text for a 10-year-old. */
export function HowItWorks() {
  return (
    <div className="mx-auto max-w-3xl px-(--edge) py-12">
      <PageHeader eyebrow="HOW IT WORKS" title="Four steps, no" emphasis="magic" subtitle="The full explanation is written in the next step." />
      <GlassCard className="mt-8">
        <ol className="list-decimal space-y-2 pl-5 text-14 text-muted-on-navy">
          <li>Every plot has a map outline and records (owner, area, registration, tax).</li>
          <li>Nine fixed checks compare them and look for conflicts.</li>
          <li>Each conflict adds points. Only code sets the score, never an AI.</li>
          <li>The plot gets a band (green, amber or red) and a printable passport you can verify.</li>
        </ol>
      </GlassCard>
    </div>
  );
}

export function About() {
  return (
    <div className="mx-auto max-w-3xl px-(--edge) py-12">
      <PageHeader eyebrow="ABOUT" title="What LandStack" emphasis="is" subtitle="The full page is written in the next step." />
      <GlassCard className="mt-8">
        <p className="text-14 text-muted-on-navy">
          LandStack is a demo of land records on a map, with fake data near Pune. It began with the SIH 2026 land-records problem statement.
        </p>
      </GlassCard>
    </div>
  );
}
