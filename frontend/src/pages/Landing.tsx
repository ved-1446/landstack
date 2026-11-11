import { ArrowRight } from "lucide-react";
import { lazy, Suspense, useEffect, type CSSProperties } from "react";
import { Link, useLocation } from "react-router";
import { getPublicStats } from "../api";
import { ContourLines, StripeGlow } from "../components/Backdrop";
import { GlassCard, RoleBadge, StatCard } from "../components/ui";
import { ROLE_IDENTITY } from "../components/ui/RoleBadge";
import { useFetch } from "../hooks";
import type { Role } from "../types";
import { ROLES, STEPS } from "./content";
import { StepArt } from "./Illustrations";
import { CheckCard } from "./landing/CheckCard";
import { Proof } from "./landing/Proof";

// The live Flow Field runs ONLY here (the hero) and on the login page. It is loaded on demand, pauses when the tab is hidden
// and shows a still frame when the visitor prefers reduced motion (see FlowField.tsx).
const FlowField = lazy(() => import("../features/login/FlowField"));

const rise = (n: number) => ({ ["--i" as string]: n }) as CSSProperties;
const cta = "inline-flex h-12 items-center gap-2 rounded-control px-5 text-14 font-medium transition-colors duration-150";

/** The public home page. Every number is from GET /public/stats or is labelled "Sample data". */
export default function Landing() {
  const stats = useFetch((signal) => getPublicStats(signal), []);
  const { hash } = useLocation();

  // "Check a plot" in the nav goes to /#check: scroll to the card (no separate page)
  useEffect(() => {
    if (hash === "#check") document.getElementById("check")?.scrollIntoView({ block: "center" });
  }, [hash]);

  return (
    <div>
      {/* ---------- hero: the live Flow Field, the headline and the public check card ---------- */}
      <section aria-labelledby="hero-title" className="relative -mt-(--nav-height) overflow-hidden pt-(--nav-height)">
        <Suspense fallback={null}>
          <FlowField />
        </Suspense>
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-linear-to-b from-navy-950/40 via-transparent to-navy-950" />
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-linear-to-r from-navy-950/60 via-navy-950/20 to-transparent max-lg:hidden" />
        <div className="relative mx-auto grid max-w-(--content-width) gap-10 px-(--edge) pb-20 pt-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:pt-24">
          <div>
            <p className="rise font-mono text-12 tracking-widest text-muted-on-navy" style={rise(0)}>
              LAND RECORDS, MADE CLEAR
            </p>
            <h1 id="hero-title" className="rise mt-3 font-serif text-58 text-cream" style={rise(1)}>
              Every plot.
              <br />
              One passport.
              <br />
              <em className="text-coral">No surprises.</em>
            </h1>
            <p className="rise mt-6 max-w-xl text-16 text-muted-on-navy" style={rise(2)}>
              LandStack puts every plot on a map, checks its papers against its shape, and gives it a risk score from fixed rules, with a printable
              passport anyone can verify.
            </p>
            <div className="rise mt-8 flex flex-wrap gap-3" style={rise(3)}>
              <Link to="/login" className={`${cta} bg-coral text-navy-950 hover:bg-coral-hover`}>
                Sign in
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link to="/#check" className={`${cta} glass-card text-cream hover:bg-glass-fill-strong`}>
                Check a plot
              </Link>
            </div>
          </div>
          <div className="rise" style={rise(4)}>
            <CheckCard />
          </div>
        </div>
      </section>

      {/* ---------- proof: three preview cards ---------- */}
      <section aria-labelledby="proof-title" className="relative mx-auto max-w-(--content-width) px-(--edge) py-16">
        <StripeGlow />
        <div className="relative">
          <p className="font-mono text-12 tracking-widest text-muted-on-navy">SEE WHAT YOU GET</p>
          <h2 id="proof-title" className="mt-2 max-w-2xl font-serif text-34 text-cream md:text-58">
            A score, the proof, and <em className="text-coral">no guessing</em>
          </h2>
          <div className="mt-10">
            <Proof stats={stats.data} failed={Boolean(stats.error)} />
          </div>
          <div className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Plots in the demo" value={stats.data?.total_plots ?? "…"} hint="live count" style={rise(0)} />
            <StatCard label="Checks" value={9} hint="fixed rules" style={rise(1)} />
            <StatCard label="Score range" value="0 to 100" hint="set by code only" style={rise(2)} />
            <StatCard label="Languages" value={3} hint="English, हिन्दी, मराठी" style={rise(3)} />
          </div>
          {stats.error && <p className="mt-4 text-13 text-muted-on-navy">The live numbers could not be loaded ({stats.error}).</p>}
        </div>
      </section>

      {/* ---------- how it works, with contour lines ---------- */}
      <section aria-labelledby="how-title" className="relative overflow-hidden py-16">
        <ContourLines className="opacity-30" />
        <div className="relative mx-auto max-w-(--content-width) px-(--edge)">
          <p className="font-mono text-12 tracking-widest text-muted-on-navy">HOW IT WORKS</p>
          <h2 id="how-title" className="mt-2 font-serif text-34 text-cream md:text-58">
            Four steps, <em className="text-coral">nothing hidden</em>
          </h2>
          <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, i) => (
              <li key={step.key}>
                <GlassCard lift className="h-full">
                  <StepArt step={step.key} />
                  <p className="mt-4 font-mono text-12 tracking-widest text-muted-on-navy">STEP {i + 1}</p>
                  <h3 className="mt-1 font-serif text-26 text-cream">{step.title}</h3>
                  <p className="mt-2 text-14 text-muted-on-navy">{step.short}</p>
                </GlassCard>
              </li>
            ))}
          </ol>
          <Link to="/how-it-works" className="mt-8 inline-flex items-center gap-2 text-14 text-cream underline underline-offset-4">
            Read it step by step
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* ---------- after you sign in: three roles ---------- */}
      <section aria-labelledby="roles-title" className="relative mx-auto max-w-(--content-width) px-(--edge) py-16">
        <div aria-hidden="true" className="pattern-dots pointer-events-none absolute inset-0" />
        <div className="relative">
          <p className="font-mono text-12 tracking-widest text-muted-on-navy">AFTER YOU SIGN IN</p>
          <h2 id="roles-title" className="mt-2 font-serif text-34 text-cream md:text-58">
            One app, <em className="text-coral">three views</em>
          </h2>
          <ul className="mt-10 grid gap-4 md:grid-cols-3">
            {ROLES.map((role) => {
              const Icon = ROLE_IDENTITY[role.key as Role].icon;
              return (
                <li key={role.key}>
                  <GlassCard lift className="flex h-full flex-col">
                    <Icon className="size-8 text-coral" aria-hidden="true" />
                    <p className="mt-4 font-mono text-12 tracking-widest text-muted-on-navy">{role.area}</p>
                    <h3 className="mt-1 font-serif text-34 text-cream">{role.title}</h3>
                    <p className="mt-2 flex-1 text-14 text-muted-on-navy">{role.text}</p>
                    <RoleBadge role={role.key as Role} className="mt-4 self-start" />
                  </GlassCard>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* ---------- final call to action ---------- */}
      <section aria-labelledby="cta-title" className="mx-auto max-w-(--content-width) px-(--edge) py-16">
        <GlassCard strong className="text-center">
          <h2 id="cta-title" className="font-serif text-34 text-cream md:text-58">
            Ready to look at the <em className="text-coral">map</em>?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-16 text-muted-on-navy">Sign in with a demo account and open a red plot to see its passport.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to="/login" className={`${cta} bg-coral text-navy-950 hover:bg-coral-hover`}>
              Sign in
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
            <Link to="/verify" className={`${cta} glass-card text-cream hover:bg-glass-fill-strong`}>
              Verify a passport
            </Link>
          </div>
        </GlassCard>
      </section>
    </div>
  );
}
