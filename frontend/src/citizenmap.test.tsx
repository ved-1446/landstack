import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { ToastProvider } from "./components/ui";
import { AppRoutes } from "./routes";
import { api, PLOT_FEATURES, resetApi } from "./test/fixtures";
import type { PlotFeature } from "./types";

vi.mock("./api", async () => {
  const { api } = await import("./test/fixtures");
  return { ...api, getSession: () => null, logout: () => undefined, setUnauthorizedHandler: () => undefined, login: vi.fn(), askGuide: vi.fn(), ApiError: class ApiError extends Error {} };
});
// the real map (WebGL) is replaced by a list of what it was given to draw
vi.mock("./features/map/MapView", () => ({
  default: ({ features }: { features: PlotFeature[] }) => (
    <ul aria-label="Plots drawn on the map">
      {features.map((f) => (
        <li key={f.properties.ulpin}>{f.properties.ulpin}</li>
      ))}
    </ul>
  ),
}));
vi.mock("./features/login/FlowField", () => ({ default: () => <div /> }));

// the server only returns the citizen's own plots (backend test: test_citizen_map_only_own_plots); the page must draw exactly those
const OWN = PLOT_FEATURES.slice(0, 3);

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initial={{ token: "t", username: "citizen1", role: "citizen" }}>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  resetApi();
  api.getPlots.mockResolvedValue({ type: "FeatureCollection", features: OWN });
});
afterEach(cleanup);

describe("the citizen's map", () => {
  it("shows only the citizen's own plots, in a framed card, and asks for no staff data", async () => {
    renderAt("/app/map");
    expect(await screen.findByRole("heading", { level: 1, name: /plots on the\s+map/i }, { timeout: 8000 })).toBeTruthy();
    expect(screen.getByText("MY LAND")).toBeTruthy();
    const drawn = await screen.findByRole("list", { name: "Plots drawn on the map" });
    await waitFor(() => expect(drawn.querySelectorAll("li")).toHaveLength(3));
    expect([...drawn.querySelectorAll("li")].map((li) => li.textContent)).toEqual(OWN.map((f) => f.properties.ulpin));
    expect(screen.queryByText(PLOT_FEATURES[5].properties.ulpin)).toBeNull();
    expect(api.getSummary).not.toHaveBeenCalled(); // /summary is staff only
  });

  it("the band chips write the word and the count, never colour alone", async () => {
    renderAt("/app/map");
    const dock = await screen.findByRole("region", { name: "Risk bands" }, { timeout: 8000 });
    expect(dock.textContent).toMatch(/green/i);
    expect(dock.textContent).toMatch(/amber/i);
    expect(dock.textContent).toMatch(/red/i);
  });
});

describe("the citizen's Home map preview", () => {
  it("is a link to the Map tab with the counts written in its label", async () => {
    renderAt("/app/home");
    const link = await screen.findByRole("link", { name: /open the map of my plots/i }, { timeout: 8000 });
    expect(link.getAttribute("href")).toBe("/app/map");
    expect(screen.getByRole("img", { name: /map preview: 1 green, 1 amber and 1 red/i })).toBeTruthy();
  });
});
