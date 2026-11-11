import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router";
import { cn } from "../../lib/cn";

export interface NavLinkItem {
  to: string;
  label: string;
  /** match the path exactly (for "Home") */
  end?: boolean;
  /** a plain link that is never shown as the active tab (for example a link to a section of the home page) */
  plain?: boolean;
}

interface GlassNavProps {
  /** where the logo goes */
  home: string;
  links: NavLinkItem[];
  /** the right-hand side: a sign-in button, or the role badge and account menu */
  right?: ReactNode;
  label?: string;
}

/**
 * The top navigation: a floating translucent pill that blurs more once the page has scrolled.
 * The active tab is a coral pill with navy text. Under 768px the tabs sit on a second, sideways-scrolling row inside the pill.
 */
export function GlassNav({ home, links, right, label = "Main" }: GlassNavProps) {
  const [scrolled, setScrolled] = useState(false);
  const tabs = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  // on a phone the tabs scroll sideways: keep the active tab in view after every page change
  useEffect(() => {
    tabs.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [pathname]);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className="fixed inset-x-0 top-0 z-nav px-(--edge) pt-3">
      <div
        data-scrolled={scrolled}
        className={cn(
          "mx-auto flex max-w-(--content-width) flex-wrap items-center justify-between gap-x-4 gap-y-2 rounded-pill border border-glass-border px-4 py-2 transition-[background-color,backdrop-filter] duration-200 ease-out",
          scrolled ? "bg-glass backdrop-blur-xl" : "bg-glass-fill backdrop-blur-md",
        )}
      >
        <Link to={home} className="flex items-center gap-2 rounded-pill px-2 font-serif text-26 text-cream">
          LandStack
        </Link>
        <nav ref={tabs} aria-label={label} className="order-3 -mx-2 flex w-full gap-1 overflow-x-auto px-2 lg:order-none lg:mx-0 lg:w-auto lg:overflow-visible lg:px-0">
          {links.map((link) => link.plain ? (
            <Link key={link.to + link.label} to={link.to} className="shrink-0 whitespace-nowrap rounded-pill px-4 py-2 text-14 font-medium text-muted-on-navy transition-colors duration-150 ease-out hover:bg-glass-fill-strong hover:text-cream">
              {link.label}
            </Link>
          ) : (
            <NavLink
              key={link.to + link.label}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                cn(
                  "shrink-0 whitespace-nowrap rounded-pill px-4 py-2 text-14 font-medium transition-colors duration-150 ease-out",
                  isActive ? "bg-coral text-navy-950" : "text-muted-on-navy hover:bg-glass-fill-strong hover:text-cream",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">{right}</div>
      </div>
    </header>
  );
}
