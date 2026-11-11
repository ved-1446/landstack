import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { Dock } from "./features/map/Dock";
import { allowedPaths, HOME, navFor, VISITOR_LINKS } from "./lib/nav";
import { AppRoutes } from "./routes";
import type { Role, Session } from "./types";

// The real API and the real map are never used here.
vi.mock("./api", () => ({
  getSession: () => null,
  logout: () => undefined,
  setUnauthorizedHandler: () => undefined,
  login: vi.fn(),
  getPublicPlot: vi.fn(),
  getPublicStats: () => Promise.resolve({ total_plots: 100, plots_per_band: { green: 58, amber: 29, red: 13 } }),
  askGuide: vi.fn(),
  ApiError: class ApiError extends Error {},
}));
vi.mock("./screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("./features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

const session = (role: Role): Session => ({ token: "t", username: role, role });

function renderAt(path: string, role: Role | null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initial={role ? session(role) : null}>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

const tabs = (name: string) => within(screen.getByRole("navigation", { name })).getAllByRole("link").map((a) => a.textContent);

beforeEach(() => window.scrollTo(0, 0));
afterEach(cleanup);

describe("a visitor", () => {
  it.each(["/app", "/app/map", "/app/plots", "/app/guide", "/app/dashboard", "/app/audit"])("cannot open %s: they land on the sign-in page", async (path) => {
    renderAt(path, null);
    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeTruthy();
    expect(screen.queryByTestId("map-screen")).toBeNull();
  });

  it("sees the public tabs and a Sign in button on the home page", async () => {
    renderAt("/", null);
    await screen.findByRole("heading", { level: 1 });
    expect(tabs("Public pages")).toEqual(VISITOR_LINKS.map((l) => l.label));
    expect(tabs("Public pages")).toEqual(["Home", "Check a plot", "Verify a passport", "How it works", "About"]);
    expect(screen.getAllByRole("link", { name: "Sign in" }).length).toBeGreaterThan(0);
  });

  it("can open the verify page without signing in", async () => {
    renderAt("/verify", null);
    expect(await screen.findByLabelText(/document id/i)).toBeTruthy();
  });
});

describe("each role gets its own tabs", () => {
  it("citizen: Home, My plots, Activity, Land Guide", async () => {
    renderAt("/app/plots", "citizen");
    await screen.findByRole("heading", { level: 1 });
    expect(tabs("citizen pages")).toEqual(["Home", "My plots", "Activity", "Land Guide"]);
  });

  it("officer: Dashboard, Plots, Map, Conflicts, Construction, Land Guide", async () => {
    renderAt("/app/dashboard", "officer");
    await screen.findByRole("heading", { level: 1 });
    expect(tabs("officer pages")).toEqual(["Dashboard", "Plots", "Map", "Conflicts", "Construction", "Land Guide"]);
  });

  it("admin: Overview, Audit log, Users, System, Insights, plus a Work desk strip with the officer pages", async () => {
    renderAt("/app/dashboard", "admin");
    await screen.findByRole("heading", { level: 1 });
    expect(tabs("admin pages")).toEqual(["Overview", "Audit log", "Users", "System", "Insights"]);
    expect(tabs("Work desk pages")).toEqual(["Plots", "Map", "Conflicts", "Construction", "Land Guide"]);
  });

  it("only an admin has a second tab strip", async () => {
    renderAt("/app/dashboard", "officer");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByRole("navigation", { name: "Work desk pages" })).toBeNull();
  });

  it("there is no side rail and no floating Land Guide button; the Guide is one nav tab", async () => {
    renderAt("/app/dashboard", "officer");
    await screen.findByRole("heading", { level: 1 });
    expect(document.querySelector("[data-rail]")).toBeNull();
    expect(screen.queryByRole("button", { name: /ask the land guide/i })).toBeNull();
    expect(screen.getAllByRole("link", { name: "Land Guide" })).toHaveLength(1);
  });
});

describe("route guards by role", () => {
  it("a citizen who types an admin URL is sent to their own home", async () => {
    renderAt("/app/audit", "citizen");
    expect(await screen.findByRole("heading", { level: 1, name: /my\s+plots/i })).toBeTruthy();
  });

  it("an officer cannot open the admin pages", async () => {
    for (const path of ["/app/audit", "/app/users", "/app/system", "/app/insights"]) {
      cleanup();
      renderAt(path, "officer");
      expect(await screen.findByRole("heading", { level: 1, name: /dashboard/i })).toBeTruthy();
    }
  });

  it("an admin can open the audit page", async () => {
    renderAt("/app/audit", "admin");
    expect(await screen.findByRole("heading", { level: 1, name: /audit/i })).toBeTruthy();
  });

  it("everyone can open the map, which is shown inside the shell", async () => {
    for (const role of ["citizen", "officer", "admin"] as const) {
      cleanup();
      renderAt("/app/map", role);
      expect(await screen.findByTestId("map-screen")).toBeTruthy();
      expect(screen.getByRole("navigation", { name: `${role} pages` })).toBeTruthy();
    }
  });

  it("/app sends each role to its home page", async () => {
    expect(HOME).toEqual({ citizen: "/app/plots", officer: "/app/dashboard", admin: "/app/dashboard" });
    renderAt("/app", "officer");
    expect(await screen.findByRole("heading", { level: 1, name: /dashboard/i })).toBeTruthy();
  });

  it("a signed-in person who opens /login is sent to their home page", async () => {
    renderAt("/login", "citizen");
    expect(await screen.findByRole("heading", { level: 1, name: /my\s+plots/i })).toBeTruthy();
  });
});

describe("navigation data", () => {
  it("no role may open a page that is not in its own tabs, except the map", () => {
    expect(allowedPaths("citizen")).not.toContain("/app/audit");
    expect(allowedPaths("citizen")).not.toContain("/app/dashboard");
    expect(allowedPaths("citizen")).toContain("/app/map");
    expect(allowedPaths("officer")).not.toContain("/app/users");
    expect(allowedPaths("admin")).toContain("/app/audit");
    expect(navFor("citizen").workDesk).toBeUndefined();
  });
});

describe("the plot counter", () => {
  const noop = () => undefined;
  const render1 = (shown: number) =>
    render(<Dock shown={shown} counts={{ green: 1, amber: 0, red: 0 }} active={new Set(["green", "amber", "red"])} onToggle={noop} loading={false} drawerOpen={false} />);

  it("says '1 plot' for one plot and 'N plots' otherwise", () => {
    render1(1);
    expect(screen.getByText("Showing 1 plot")).toBeTruthy();
    cleanup();
    render1(3);
    expect(screen.getByText("Showing 3 plots")).toBeTruthy();
    cleanup();
    render1(0);
    expect(screen.getByText("Showing 0 plots")).toBeTruthy();
  });
});
