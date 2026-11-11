import { Suspense } from "react";
import { Link, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth";
import { StaticLayer } from "../components/Backdrop";
import { RouteLoading } from "../components/RouteLoading";
import { GlassNav } from "../components/ui";
import { HOME, VISITOR_LINKS } from "../lib/nav";

/** The frame of the public pages (home, how it works, about, verify): the glass nav on top and a footer with the honesty note. */
export default function PublicShell() {
  const { session } = useAuth();
  const { pathname } = useLocation();
  return (
    <StaticLayer identity="visitor">
      <GlassNav
        home="/"
        links={VISITOR_LINKS}
        label="Public pages"
        right={
          <Link
            to={session ? HOME[session.role] : "/login"}
            className="rounded-pill bg-coral px-4 py-2 text-14 font-medium text-navy-950 transition-colors duration-150 hover:bg-coral-hover active:bg-coral-pressed"
          >
            {session ? "Open the app" : "Sign in"}
          </Link>
        }
      />
      <div className="relative pt-(--nav-height)">
        <div key={pathname} className="route-in">
          <Suspense fallback={<RouteLoading />}>
            <Outlet />
          </Suspense>
        </div>
        <footer className="relative mx-auto mt-16 max-w-(--content-width) px-(--edge) pb-10 text-13 text-muted-on-navy">
          <p>
            LandStack is a demo. All plots, names and records are made up; construction changes are simulated; the machine-learning
            part learned from made-up data. It is not an official or legal service.
          </p>
          <p className="mt-2">Origin: the SIH 2026 land-records problem statement.</p>
        </footer>
      </div>
    </StaticLayer>
  );
}
