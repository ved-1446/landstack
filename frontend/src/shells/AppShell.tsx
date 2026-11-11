import { NavLink, Outlet, useLocation } from "react-router";
import { useAuth } from "../auth";
import { StaticLayer } from "../components/Backdrop";
import { GlassNav, RoleBadge } from "../components/ui";
import { LanguageProvider } from "../features/guide/language";
import { cn } from "../lib/cn";
import { HOME, navFor } from "../lib/nav";
import { AccountMenu } from "./AccountMenu";

/**
 * The frame of everything after sign-in: the glass nav on top with this role's tabs, the role badge and the account menu.
 * An admin also gets a second tab strip ("Work desk") with the officer pages. There is no side rail and no floating button.
 */
export default function AppShell() {
  const { session } = useAuth();
  const { pathname } = useLocation();
  if (!session) return null; // the route guard has already sent a visitor to /login
  const nav = navFor(session.role);

  return (
    <LanguageProvider>
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
            <Outlet />
          </main>
        </div>
      </StaticLayer>
    </LanguageProvider>
  );
}
