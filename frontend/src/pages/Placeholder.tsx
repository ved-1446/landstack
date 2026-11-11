import { Link } from "react-router";
import { GlassCard, PageHeader } from "../components/ui";
import { ROLE_IDENTITY } from "../components/ui/RoleBadge";
import { useAuth } from "../auth";

/** A page that is wired into the navigation but built in the next step (13b for citizens and officers, 13c for the admin). */
export default function Placeholder({ title, emphasis, showMapLink }: { title: string; emphasis: string; showMapLink?: boolean }) {
  const { session } = useAuth();
  if (!session) return null;
  return (
    <section>
      <PageHeader eyebrow={ROLE_IDENTITY[session.role].area} title={title} emphasis={emphasis} subtitle="This page is built in the next step. The navigation, sign-in and map already work." />
      <GlassCard className="mt-8 max-w-xl">
        <p className="text-16 text-cream">Built in the next step.</p>
        <p className="mt-2 text-14 text-muted-on-navy">
          You are signed in as <span className="font-mono">{session.username}</span>. The plots, passports, PDFs and the simulated construction layer are all on the map page.
        </p>
        {showMapLink && (
          <Link to="/app/map" className="mt-4 inline-flex h-11 items-center rounded-control bg-coral px-4 text-14 font-medium text-navy-950 hover:bg-coral-hover">
            Open the map
          </Link>
        )}
      </GlassCard>
    </section>
  );
}
