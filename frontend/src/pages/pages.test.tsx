import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

class FakeApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}
const getPublicPlot = vi.fn();
const getPublicStats = vi.fn();

vi.mock("../api", () => ({
  ApiError: FakeApiError,
  getPublicPlot: (...args: unknown[]) => getPublicPlot(...args),
  getPublicStats: (...args: unknown[]) => getPublicStats(...args),
  getSession: () => null,
  logout: () => undefined,
  setUnauthorizedHandler: () => undefined,
  login: vi.fn(),
}));
vi.mock("../features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

const STATS = { total_plots: 100, plots_per_band: { green: 58, amber: 29, red: 13 } };

beforeEach(() => {
  getPublicStats.mockResolvedValue(STATS);
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function renderCheckCard() {
  const { CheckCard } = await import("./landing/CheckCard");
  return render(<CheckCard />);
}

describe("the public check card", () => {
  it("shows exactly the plot id, the village and the band (icon plus words), nothing else", async () => {
    // even if the server sent more, only these three are ever shown
    getPublicPlot.mockResolvedValue({ ulpin: "MH000100000006", village: "Hinjewadi", band: "red", score: 100, owner: "SECRET" });
    await renderCheckCard();
    fireEvent.change(screen.getByLabelText(/plot id/i), { target: { value: "mh000100000006" } });
    fireEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(await screen.findByText("Hinjewadi")).toBeTruthy();
    expect(getPublicPlot).toHaveBeenCalledWith("MH000100000006", expect.anything());
    expect(screen.getByText("MH000100000006")).toBeTruthy();
    expect(screen.getByText(/high risk · red/i)).toBeTruthy();
    expect(document.body.textContent).not.toContain("SECRET");
    expect(document.body.textContent).not.toMatch(/score/i);
  });

  it("says 'No plot found' for any wrong id (the same words every time)", async () => {
    getPublicPlot.mockRejectedValue(new FakeApiError("No plot found", 404));
    await renderCheckCard();
    fireEvent.change(screen.getByLabelText(/plot id/i), { target: { value: "NOPE" } });
    fireEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(await screen.findByText(/no plot found/i)).toBeTruthy();
  });

  it("shows the server's wait message when the limit is reached", async () => {
    getPublicPlot.mockRejectedValue(new FakeApiError("Too many requests. Please wait 30 seconds and try again.", 429));
    await renderCheckCard();
    fireEvent.change(screen.getByLabelText(/plot id/i), { target: { value: "MH000100000006" } });
    fireEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(await screen.findByText(/wait 30 seconds/i)).toBeTruthy();
  });

  it("does not call the server for an empty box", async () => {
    await renderCheckCard();
    expect((screen.getByRole("button", { name: /check/i }) as HTMLButtonElement).disabled).toBe(true);
    expect(getPublicPlot).not.toHaveBeenCalled();
  });
});

describe("the landing page", () => {
  async function renderLanding() {
    const { default: Landing } = await import("./Landing");
    return render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
  }

  it("has the headline and takes every live number from /public/stats", async () => {
    await renderLanding();
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1.textContent).toMatch(/every plot\.\s*one passport\.\s*no surprises\./i);
    await waitFor(() => expect(screen.getAllByText("100").length).toBeGreaterThan(0));
    // the donut legend writes the real band counts
    expect(screen.getByText("Green, low risk").parentElement?.textContent).toContain("58");
    expect(screen.getByText("Amber, watch").parentElement?.textContent).toContain("29");
    expect(screen.getByText("Red, high risk").parentElement?.textContent).toContain("13");
    expect(getPublicStats).toHaveBeenCalledTimes(1);
  });

  it("labels the sample passport as sample data, with the sum 40 + 15 + 10 = 65 in the red band", async () => {
    await renderLanding();
    expect(screen.getByText("SAMPLE DATA")).toBeTruthy();
    expect(screen.getByText("40 + 15 + 10 = 65")).toBeTruthy();
    expect(screen.getByRole("img", { name: /risk score 65 out of 100, red band/i })).toBeTruthy();
  });

  it("shows a message instead of invented numbers when the API is down", async () => {
    getPublicStats.mockRejectedValue(new FakeApiError("Cannot reach the API"));
    await renderLanding();
    expect((await screen.findAllByText(/could not be loaded/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText("58")).toBeNull();
  });

  it("has the four steps, the three roles and no Land Guide or AI on the public page", async () => {
    await renderLanding();
    expect(screen.getAllByText(/^STEP \d$/)).toHaveLength(4);
    for (const role of ["Citizen", "Officer", "Admin"]) expect(screen.getAllByRole("heading", { name: role }).length).toBe(1);
    expect(screen.queryByText(/ask the land guide/i)).toBeNull();
  });
});

describe("the public information pages", () => {
  it("how it works lists all 9 checks with their points, the 3 bands and says only code sets the score", async () => {
    const { default: HowItWorks } = await import("./HowItWorks");
    render(<MemoryRouter><HowItWorks /></MemoryRouter>);
    const checks = within(screen.getByRole("region", { name: /what gets checked/i })).getAllByRole("listitem");
    expect(checks).toHaveLength(9);
    expect(checks.map((c) => /\+(\d+)/.exec(c.textContent ?? "")?.[1]).sort()).toEqual(["10", "15", "15", "15", "20", "25", "25", "30", "40"]);
    expect(screen.getByText(/only code sets the/i)).toBeTruthy();
    expect(screen.getByText("0 to 24")).toBeTruthy();
    expect(screen.getByText("60 and up")).toBeTruthy();
  });

  it("about names no person and says the data is fake", async () => {
    const { default: About } = await import("./About");
    render(<MemoryRouter><About /></MemoryRouter>);
    expect(screen.getByText(/not real government data/i)).toBeTruthy();
    expect(screen.getByText(/SIH 2026/)).toBeTruthy();
  });
});

describe("the login page demo cards", () => {
  async function renderLogin() {
    const { AuthProvider } = await import("../auth");
    const { default: LoginScreen } = await import("../screens/LoginScreen");
    return render(
      <MemoryRouter>
        <AuthProvider initial={null}>
          <LoginScreen />
        </AuthProvider>
      </MemoryRouter>,
    );
  }

  it("shows the three role cards only when VITE_DEMO_ACCOUNTS is true", async () => {
    vi.stubEnv("VITE_DEMO_ACCOUNTS", "true");
    vi.resetModules();
    await renderLogin();
    const section = screen.getByRole("region", { name: /demo accounts/i });
    expect(within(section).getAllByRole("button").map((b) => b.textContent)).toEqual([
      expect.stringContaining("Citizen"),
      expect.stringContaining("Officer"),
      expect.stringContaining("Admin"),
    ]);
  });

  it.each(["false", "", "TRUE", "1"])("shows no demo cards when VITE_DEMO_ACCOUNTS is %j", async (value) => {
    vi.stubEnv("VITE_DEMO_ACCOUNTS", value);
    vi.resetModules();
    await renderLogin();
    expect(screen.queryByRole("region", { name: /demo accounts/i })).toBeNull();
    expect(document.body.textContent).not.toMatch(/Demo#2026/);
    expect(screen.getByRole("link", { name: /back to home/i })).toBeTruthy();
  });
});
