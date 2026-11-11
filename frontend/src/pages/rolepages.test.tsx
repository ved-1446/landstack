import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { ToastProvider } from "../components/ui";
import { AppRoutes } from "../routes";
import { api, CONFLICTS, PLOTS, resetApi } from "../test/fixtures";
import type { Role } from "../types";
import * as realApi from "../api";

vi.mock("../api", async () => {
  const { api } = await import("../test/fixtures");
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
vi.mock("../screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("../features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

function renderAt(path: string, role: Role) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initial={{ token: "t", username: role, role }}>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}
const h1 = (name: RegExp) => screen.findByRole("heading", { level: 1, name });

beforeEach(() => {
  resetApi();
  window.scrollTo(0, 0);
});
afterEach(cleanup);

describe("citizen pages", () => {
  it("home: a plain-words summary with real counts, a what-to-do-next list and a Land Guide link", async () => {
    renderAt("/app/home", "citizen");
    await h1(/your land/i);
    expect(await screen.findByText(/You have 6 plots here\. 2 are in the red band \(high risk\) and 2 are in the amber band/)).toBeTruthy();
    expect(screen.getByText("What to do next")).toBeTruthy();
    expect(screen.getByRole("link", { name: /open plot MH000100000006 first/i })).toBeTruthy();   // the highest-scoring red plot comes first
    expect(screen.getByRole("link", { name: /ask the land guide/i }).getAttribute("href")).toBe("/app/guide");
    expect(document.body.textContent).not.toMatch(/hello|welcome back/i);        // "greeting-free"
  });

  it("my plots: one card per plot with id, village, area, band in words and score", async () => {
    renderAt("/app/plots", "citizen");
    await h1(/my\s+plots/i);
    const list = await screen.findByRole("list");
    const cards = within(list).getAllByRole("link");
    expect(cards).toHaveLength(6);
    expect(cards[5].getAttribute("href")).toBe("/app/plots/MH000100000006");
    expect(within(cards[5]).getByText("1,849 m² · residential")).toBeTruthy();
    expect(within(cards[5]).getByText(/high risk · red/i)).toBeTruthy();
    expect(within(cards[3]).getByText(/not available/i)).toBeTruthy();           // an invalid outline has no area
    expect(within(cards[0]).getByText(/low risk · green/i)).toBeTruthy();
  });

  it("has loading, empty and error states in plain words", async () => {
    api.getPlots.mockResolvedValue({ type: "FeatureCollection", features: [] });
    renderAt("/app/plots", "citizen");
    expect(await screen.findByText("No plots yet")).toBeTruthy();
    cleanup();

    api.getPlots.mockReset().mockRejectedValueOnce(new Error("Cannot reach the API. Is the backend running?")).mockResolvedValue(PLOTS);
    renderAt("/app/plots", "citizen");
    expect(await screen.findByText("Could not load your plots")).toBeTruthy();
    expect(screen.getByText(/cannot reach the api/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findAllByRole("link", { name: /MH0001000000/ })).toHaveLength(6);
    cleanup();

    api.getPlots.mockReset().mockReturnValue(new Promise(() => undefined));
    renderAt("/app/plots", "citizen");
    expect(await screen.findByRole("status", { name: /loading your plots/i })).toBeTruthy();
  });

  it("verify: a pasted QR address is turned into the document id; a plot id opens its passport page", async () => {
    vi.mocked(realApi.verifyDocument).mockResolvedValue({ valid: true, ulpin: "MH000100000001", issued_at: "2026-11-11T10:00:00Z", status: "matches" });
    renderAt("/app/verify", "citizen");
    await h1(/check a/i);
    fireEvent.change(screen.getByLabelText(/document id, qr address or plot id/i), { target: { value: "http://localhost:8000/verify/7KQ2-M9XD-4TPA" } });
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByText("MATCHES")).toBeTruthy();
    expect(realApi.verifyDocument).toHaveBeenCalledWith("7KQ2-M9XD-4TPA", expect.anything());
    fireEvent.change(screen.getByLabelText(/document id, qr address or plot id/i), { target: { value: "nonsense!!" } });
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByText(/does not look like a plot id/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/document id, qr address or plot id/i), { target: { value: "mh000100000001" } });
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(await screen.findByRole("link", { name: /back to my plots/i })).toBeTruthy();         // the passport page
    expect(api.getPassport).toHaveBeenCalledWith("MH000100000001", expect.anything());
  });

  it("activity: my own actions in plain words, newest first, and an empty state", async () => {
    renderAt("/app/activity", "citizen");
    expect(await screen.findByText("Nothing here yet")).toBeTruthy();
    cleanup();
    api.getMyActivity.mockResolvedValue([
      { id: 3, action: "download_passport_pdf", ulpin: "MH000100000001", looked_at: "2026-11-11T10:00:00Z" },
      { id: 2, action: "view_passport_denied", ulpin: null, looked_at: "2026-11-11T09:00:00Z" },
      { id: 1, action: "guide_ask", ulpin: null, looked_at: "2026-11-11T08:00:00Z" },
    ]);
    renderAt("/app/activity", "citizen");
    const list = await screen.findByRole("list", { name: /my recent activity/i });
    const rows = within(list).getAllByRole("listitem").map((r) => r.textContent ?? "");
    expect(rows[0]).toContain("Downloaded a PDF passport");
    expect(rows[0]).toContain("MH000100000001");
    expect(rows[1]).toContain("Tried to open a plot that is not yours");
    expect(rows[1]).not.toMatch(/MH\d{12}/);
    expect(rows[2]).toContain("Asked the Land Guide a question");
  });
});

describe("officer pages", () => {
  it("dashboard: stat cards with the real numbers, the 9 problem types and a priority queue of the top 10", async () => {
    renderAt("/app/dashboard", "officer");
    await h1(/attention/i);
    for (const [label, value] of [["TOTAL PLOTS", "100"], ["RED", "13"], ["AMBER", "29"], ["GREEN", "58"], ["OPEN CONFLICTS", "84"], ["CONSTRUCTION FLAGS", "10"]]) {
      await waitFor(() => {
        const card = screen.getByText(label).closest("div")?.parentElement as HTMLElement;
        expect(within(card).getByText(value)).toBeTruthy();
      }, { timeout: 4000 });
    }
    const bars = within(screen.getByRole("heading", { name: "Problems by type" }).parentElement as HTMLElement).getAllByRole("listitem");
    expect(bars).toHaveLength(9);
    expect(bars[0].textContent).toContain("Boundary overlap");                       // the biggest first
    expect(screen.getByText("Unrecorded construction (simulated)")).toBeTruthy();
    const queue = await screen.findByRole("list", { name: "Priority queue" });
    const rows = within(queue).getAllByRole("listitem");
    expect(rows).toHaveLength(10);                                                    // 12 plots have findings; only the top 10 are shown
    expect(rows[0].textContent).toContain(CONFLICTS[0].ulpin);
    expect(rows[0].textContent).toContain("Boundary overlap +40");
    expect(rows[0].textContent).toContain("Unrecorded construction +15 (simulated)");
    expect(rows[0].textContent).toMatch(/high risk · red/i);
    expect(within(rows[9]).getByText("55")).toBeTruthy();
    expect(screen.getByRole("img", { name: /map preview: 3 green|map preview: 2 green/i })).toBeTruthy();
  });

  it("dashboard: an error in one list does not blank the page, and each list can be retried", async () => {
    api.getSummary.mockReset().mockRejectedValueOnce(new Error("The server answered with an error (HTTP 500).")).mockResolvedValue((await import("../test/fixtures")).SUMMARY);
    renderAt("/app/dashboard", "officer");
    expect(await screen.findByText("Could not load the counts")).toBeTruthy();
    expect(await screen.findByRole("list", { name: "Priority queue" })).toBeTruthy();   // the other card still works
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(screen.queryByText("Could not load the counts")).toBeNull());
  });

  it("plots: a table with search, a multi-band filter, a village filter and sorting", async () => {
    renderAt("/app/plots", "officer");
    await h1(/all\s+plots/i);
    await screen.findByRole("table");
    const ids = () => within(screen.getByRole("table")).getAllByRole("row").slice(1).map((r) => within(r).getAllByRole("cell")[0].textContent);   // looked up each time: the table is replaced by a message when nothing matches
    expect(ids()).toEqual(["MH000100000006", "MH000100000003", "MH000100000005", "MH000100000002", "MH000100000001", "MH000100000004"]);
    // switch the green band off: any combination is allowed
    fireEvent.click(screen.getByRole("button", { name: /green band: shown/i }));
    expect(ids()).toHaveLength(4);
    fireEvent.click(screen.getByRole("button", { name: /amber band: shown/i }));
    expect(ids()).toEqual(["MH000100000006", "MH000100000003"]);
    fireEvent.click(screen.getByRole("button", { name: /green band: hidden/i }));
    expect(ids()).toEqual(["MH000100000006", "MH000100000003", "MH000100000001", "MH000100000004"]);
    fireEvent.click(screen.getByRole("button", { name: /red band: shown/i }));
    expect(ids()).toEqual(["MH000100000001", "MH000100000004"]);
    // nothing selected: a plain message, not a blank table
    fireEvent.click(screen.getByRole("button", { name: /green band: shown/i }));
    expect(screen.getByText(/no band is selected, so no plots are shown/i)).toBeTruthy();
    expect(screen.getByText("No plots match")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /clear the filters/i }));
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(7);
    // the village filter and the search box
    fireEvent.change(screen.getByLabelText("Village"), { target: { value: "Baner" } });
    expect(ids()).toEqual(["MH000100000006", "MH000100000005"]);
    fireEvent.change(screen.getByLabelText(/search by plot id or village/i), { target: { value: "0000005" } });
    expect(ids()).toEqual(["MH000100000005"]);
  });

  it("plots: clicking a column header sorts, and the header says which way", async () => {
    renderAt("/app/plots", "officer");
    const table = await screen.findByRole("table");
    const header = within(table).getByRole("columnheader", { name: /area/i });
    expect(header.getAttribute("aria-sort")).toBe("none");
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("descending");
    fireEvent.click(within(header).getByRole("button"));
    expect(header.getAttribute("aria-sort")).toBe("ascending");
    const first = within(within(table).getAllByRole("row")[1]).getAllByRole("cell")[0].textContent;
    expect(first).toBe("MH000100000005");                                            // the smallest area
  });

  it("conflicts: the type chips narrow the list", async () => {
    renderAt("/app/conflicts", "officer");
    await h1(/open\s+conflicts/i);
    const list = await screen.findByRole("list", { name: "Plots with conflicts" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(12);
    fireEvent.click(screen.getByRole("button", { name: /^Unrecorded construction\s*1$/ }));
    expect(within(screen.getByRole("list", { name: "Plots with conflicts" })).getAllByRole("listitem")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /^Tax overdue\s*0$/ }));
    expect(screen.getByText(/no plot has this kind of problem/i)).toBeTruthy();
  });

  it("construction: only plots with the simulated finding, clearly labelled SIMULATED", async () => {
    renderAt("/app/construction", "officer");
    await h1(/new\s+construction/i);
    expect(screen.getByText(/^SIMULATED: there is no real satellite data/)).toBeTruthy();
    const list = await screen.findByRole("list", { name: /simulated new building/i });
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
    cleanup();
    api.getConflicts.mockResolvedValue(CONFLICTS.filter((c) => c.findings.length === 1));
    renderAt("/app/construction", "officer");
    expect(await screen.findByText("No new construction flagged")).toBeTruthy();
  });

  it("zones: type, area and how many plots touch each zone", async () => {
    renderAt("/app/zones", "officer");
    await h1(/restricted\s+zones/i);
    expect(await screen.findByText(/50,000 m² · 7 plots touch it/)).toBeTruthy();
    cleanup();
    api.getZones.mockResolvedValue([]);
    renderAt("/app/zones", "officer");
    expect(await screen.findByText("No zones")).toBeTruthy();
  });

  it("activity (from the account menu): the officer's own log", async () => {
    renderAt("/app/activity", "officer");
    expect(await screen.findByText("Nothing here yet")).toBeTruthy();
    expect(api.getMyActivity).toHaveBeenCalledTimes(1);
  });

  it("the passport page asks the server for the plot, and a plot that is not found says so in words", async () => {
    api.getPassport.mockRejectedValue(new Error("No plot found"));
    renderAt("/app/plots/MH000100000006", "officer");
    expect(await screen.findByText("Plot not found")).toBeTruthy();
    expect(screen.getByRole("link", { name: /back to all plots/i })).toBeTruthy();
  });
});
