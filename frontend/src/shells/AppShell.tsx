import { Suspense } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth";
import { StaticLayer } from "../components/Backdrop";
import { RouteLoading } from "../components/RouteLoading";
import { GlassNav, RoleBadge } from "../components/ui";
import { LanguageProvider } from "../features/guide/language";
import { AppDataProvider } from "../lib/appData";
import { cn } from "../lib/cn";
import { HOME, mayOpen, navFor } from "../lib/nav";
import NotForRole from "../pages/NotForRole";
import { AccountMenu } from "./AccountMenu";

/**
 * The frame of everything after sign-in: the glass nav on top with this role's tabs, the role badge and the account menu.
 * An admin also gets a second tab strip ("Work desk") with the officer pages. There is no side rail and no floating button.
 * A page that belongs to another role shows a friendly "not for your role" page instead of its content (the server checks again).
 */
export default function AppShell() {
  const { session } = useAuth();
  const { pathname } = useLocation();
  if (!session) return null; // the route guard has already sent a visitor to /login
  const nav = navFor(session.role);
  const allowed = mayOpen(session.role, pathname) || pathname.replace(/\/+$/, "") === "/app";

  return (
    <LanguageProvider>
      <AppDataProvider role={session.role}>
        <StaticLayer identity={session.role}>
          <GlassNav
            home={HOME[session.role]}
            links={nav.links}
            label={`${session.role} pages`}
            right={
              <>
                <RoleBadge role={session.role} className="max-md:hidden" />
                <AccountMenu />
              </>
            }
          />
          <div className="relative mx-auto max-w-(--content-width) px-(--edge) pb-16 pt-(--nav-height)">
            {nav.workDesk && (
              <nav aria-label="Work desk pages" className="mb-6 flex items-center gap-2 overflow-x-auto pt-2">
                <span className="shrink-0 font-mono text-11 tracking-widest text-muted-on-navy">WORK DESK</span>
                {nav.workDesk.map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    className={({ isActive }) =>
                      cn(
                        "shrink-0 rounded-pill border px-3 py-1 text-13 transition-colors duration-150",
                        isActive ? "border-coral text-cream" : "border-glass-border text-muted-on-navy hover:text-cream",
                      )
                    }
                  >
                    {link.label}
                  </NavLink>
                ))}
              </nav>
            )}
            <main key={pathname} className="route-in pt-4">
              <Suspense fallback={<RouteLoading />}>{allowed ? <Outlet /> : <NotForRole />}</Suspense>
            </main>
          </div>
        </StaticLayer>
      </AppDataProvider>
    </LanguageProvider>
  );
}
