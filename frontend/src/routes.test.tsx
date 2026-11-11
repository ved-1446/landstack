import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { ToastProvider } from "./components/ui";
import { Dock } from "./features/map/Dock";
import { allowedPaths, HOME, mayOpen, navFor, VISITOR_LINKS } from "./lib/nav";
import { AppRoutes } from "./routes";
import { api, resetApi } from "./test/fixtures";
import type { Role, Session } from "./types";

// The real API and the real map are never used here.
vi.mock("./api", async () => {
  const { api } = await import("./test/fixtures");
  return {
    ...api,
    getSession: () => null,
    logout: () => undefined,
    setUnauthorizedHandler: () => undefined,
    login: vi.fn(),
    askGuide: vi.fn(),
    downloadPassportPdf: vi.fn(),
    verifyDocument: vi.fn(),
    explainPassport: vi.fn(),
    ApiError: class ApiError extends Error {},
  };
});
vi.mock("./screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("./features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

const session = (role: Role): Session => ({ token: "t", username: role, role });

function renderAt(path: string, role: Role | null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initial={role ? session(role) : null}>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

const tabs = (name: string) => within(screen.getByRole("navigation", { name })).getAllByRole("link").map((a) => a.textContent);
const heading1 = (name: RegExp) => screen.findByRole("heading", { level: 1, name });
const NOT_FOR_ROLE = /this page is not for your role/i;

beforeEach(() => {
  resetApi();
  window.scrollTo(0, 0);
});
afterEach(cleanup);

describe("a visitor", () => {
  it.each(["/app", "/app/map", "/app/plots", "/app/guide", "/app/dashboard", "/app/audit", "/app/zones", "/app/plots/MH000100000001"])("cannot open %s: they land on the sign-in page", async (path) => {
    renderAt(path, null);
    expect(await heading1(/sign in/i)).toBeTruthy();
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
  it("citizen: Home, My plots, Verify, Activity, Land Guide", async () => {
    renderAt("/app/plots", "citizen");
    await heading1(/my\s+plots/i);
    expect(tabs("citizen pages")).toEqual(["Home", "My plots", "Verify", "Activity", "Land Guide"]);
  });

  it("officer: Dashboard, Plots, Map, Conflicts, Construction, Zones, Land Guide", async () => {
    renderAt("/app/dashboard", "officer");
    await heading1(/attention/i);
    expect(tabs("officer pages")).toEqual(["Dashboard", "Plots", "Map", "Conflicts", "Construction", "Zones", "Land Guide"]);
  });

  it("admin: Overview, Audit log, Users, System, Insights, plus a Work desk strip with the officer pages", async () => {
    renderAt("/app/dashboard", "admin");
    await heading1(/running/i);
    expect(tabs("admin pages")).toEqual(["Overview", "Audit log", "Users", "System", "Insights"]);
    expect(tabs("Work desk pages")).toEqual(["Dashboard", "Plots", "Map", "Conflicts", "Construction", "Zones", "Land Guide"]);
  });

  it("only an admin has a second tab strip", async () => {
    renderAt("/app/dashboard", "officer");
    await heading1(/attention/i);
    expect(screen.queryByRole("navigation", { name: "Work desk pages" })).toBeNull();
  });

  it("there is no side rail and no floating Land Guide button; the Guide is one nav tab", async () => {
    renderAt("/app/dashboard", "officer");
    await heading1(/attention/i);
    expect(document.querySelector("[data-rail]")).toBeNull();
    expect(screen.queryByRole("button", { name: /ask the land guide/i })).toBeNull();
    expect(screen.getAllByRole("link", { name: "Land Guide" })).toHaveLength(1);
  });
});

describe("role guards: a page for another role shows a friendly page, never a blank screen", () => {
  it.each(["/app/dashboard", "/app/conflicts", "/app/construction", "/app/zones", "/app/audit", "/app/users", "/app/system", "/app/insights"])("a citizen on %s", async (path) => {
    renderAt(path, "citizen");
    expect(await screen.findByText(NOT_FOR_ROLE)).toBeTruthy();
    expect(screen.getByRole("link", { name: /go to my home page/i }).getAttribute("href")).toBe("/app/plots");
    expect(tabs("citizen pages")).toHaveLength(5);                         // the shell and the tabs are still there
    expect(api.getConflicts).not.toHaveBeenCalledWith(expect.anything());   // and no officer data was asked for
  });

  it.each(["/app/home", "/app/verify", "/app/audit", "/app/users", "/app/system", "/app/insights"])("an officer on %s", async (path) => {
    renderAt(path, "officer");
    expect(await screen.findByText(NOT_FOR_ROLE)).toBeTruthy();
    expect(screen.getByRole("link", { name: /go to my home page/i }).getAttribute("href")).toBe("/app/dashboard");
  });

  it("an admin may open the admin pages and the officer pages, but not the citizen-only ones", async () => {
    renderAt("/app/audit", "admin");
    expect(await heading1(/who looked at/i)).toBeTruthy();
    cleanup();
    renderAt("/app/zones", "admin");
    expect(await heading1(/zones/i)).toBeTruthy();
    cleanup();
    renderAt("/app/home", "admin");
    expect(await screen.findByText(NOT_FOR_ROLE)).toBeTruthy();
  });

  it("citizens never request the staff-only lists", async () => {
    renderAt("/app/plots", "citizen");
    await heading1(/my\s+plots/i);
    expect(api.getSummary).not.toHaveBeenCalled();
    expect(api.getConflicts).not.toHaveBeenCalled();
  });

  it("everyone can open the map, which is shown inside the shell", async () => {
    for (const role of ["citizen", "officer", "admin"] as const) {
      cleanup();
      renderAt("/app/map", role);
      expect(await screen.findByTestId("map-screen")).toBeTruthy();
      expect(screen.getByRole("navigation", { name: `${role} pages` })).toBeTruthy();
    }
  });

  it("a plot passport page follows the plots list: both roles may open it", () => {
    expect(mayOpen("citizen", "/app/plots/MH000100000001")).toBe(true);
    expect(mayOpen("officer", "/app/plots/MH000100000001")).toBe(true);
    expect(mayOpen("citizen", "/app/zones/1")).toBe(false);
    expect(mayOpen("officer", "/app/activity")).toBe(true);        // from the account menu
  });

  it("/app sends each role to its home page", async () => {
    expect(HOME).toEqual({ citizen: "/app/plots", officer: "/app/dashboard", admin: "/app/dashboard" });
    renderAt("/app", "officer");
    expect(await heading1(/attention/i)).toBeTruthy();
  });

  it("a signed-in person who opens /login is sent to their home page", async () => {
    renderAt("/login", "citizen");
    expect(await heading1(/my\s+plots/i)).toBeTruthy();
  });
});

describe("navigation data", () => {
  it("no role may open a page that is not its own, except the map", () => {
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
