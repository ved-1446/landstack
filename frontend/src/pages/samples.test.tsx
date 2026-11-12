import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SAMPLE_PLOTS } from "../lib/samplePlots";

class FakeApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}
const getPublicPlot = vi.fn();
const explainPassport = vi.fn();
const askGuide = vi.fn();
const verifyDocument = vi.fn();

vi.mock("../api", () => ({
  ApiError: FakeApiError,
  getPublicPlot: (...args: unknown[]) => getPublicPlot(...args),
  explainPassport: (...args: unknown[]) => explainPassport(...args),
  askGuide: (...args: unknown[]) => askGuide(...args),
  verifyDocument: (...args: unknown[]) => verifyDocument(...args),
}));

const BAND_WORD = { green: /low risk · green/i, amber: /watch · amber/i, red: /high risk · red/i };

beforeEach(() => {
  getPublicPlot.mockImplementation(async (ulpin: string) => ({ ulpin, village: "Hinjewadi", band: SAMPLE_PLOTS.find((s) => s.ulpin === ulpin)?.band ?? "green" }));
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  delete document.documentElement.dataset.theme;
});

async function renderCard(props = {}) {
  const { CheckCard } = await import("./landing/CheckCard");
  return render(<MemoryRouter><CheckCard {...props} /></MemoryRouter>);
}

describe("sample plot data", () => {
  it("covers green, amber and red with 14-character ids", () => {
    expect(new Set(SAMPLE_PLOTS.map((s) => s.band))).toEqual(new Set(["green", "amber", "red"]));
    for (const s of SAMPLE_PLOTS) expect(s.ulpin).toMatch(/^[A-Z0-9]{14}$/);
  });
});

describe.each(["dark", "light"])("the example chips in the %s theme", (theme) => {
  beforeEach(() => {
    document.documentElement.dataset.theme = theme;
  });

  it("shows each id in mono type with its band as icon plus words", async () => {
    await renderCard();
    expect(screen.getByText(/not sure what to type\? try one of these/i)).toBeTruthy();
    const chips = within(screen.getByRole("list", { name: /not sure what to type/i })).getAllByRole("button");
    expect(chips).toHaveLength(SAMPLE_PLOTS.length);
    SAMPLE_PLOTS.forEach((sample, i) => {
      const id = within(chips[i]).getByText(sample.ulpin);
      expect(id.className).toContain("font-mono");
      expect(within(chips[i]).getByText(BAND_WORD[sample.band])).toBeTruthy();
      expect(chips[i].querySelector("svg")).toBeTruthy();
    });
  });

  it("fills the input and runs the public check, and nothing else (no AI call)", async () => {
    await renderCard();
    const [first] = SAMPLE_PLOTS;
    fireEvent.click(screen.getByRole("button", { name: new RegExp(first.ulpin) }));
    expect((screen.getByLabelText(/plot id/i) as HTMLInputElement).value).toBe(first.ulpin);
    await waitFor(() => expect(getPublicPlot).toHaveBeenCalledTimes(1));
    expect(getPublicPlot).toHaveBeenCalledWith(first.ulpin, expect.anything());
    expect(await screen.findByText("Hinjewadi")).toBeTruthy();
    expect(explainPassport).not.toHaveBeenCalled();
    expect(askGuide).not.toHaveBeenCalled();
  });
});

describe("the signed-in 'Check any plot' card", () => {
  it("explains where own plots appear and what other plots return", async () => {
    await renderCard({ eyebrow: "CHECK ANY PLOT", intro: "Your own plots appear under My plots. Any other plot returns only the public summary: its id, village and risk band." });
    expect(screen.getByText("CHECK ANY PLOT")).toBeTruthy();
    expect(screen.getByText(/under my plots/i)).toBeTruthy();
    expect(screen.getByText(/only the public summary/i)).toBeTruthy();
  });

  it("an unknown id still gets the generic 'No plot found'", async () => {
    getPublicPlot.mockRejectedValue(new FakeApiError("nope", 404));
    await renderCard();
    fireEvent.change(screen.getByLabelText(/plot id/i), { target: { value: "MH999999999999" } });
    fireEvent.click(screen.getByRole("button", { name: /^check$/i }));
    expect(await screen.findByText(/no plot found/i)).toBeTruthy();
  });
});

describe("the Verify page", () => {
  function Where() {
    const l = useLocation();
    return <p data-testid="where">{l.pathname + l.search + l.hash}</p>;
  }

  it("explains where a document id comes from, and a 'Try a plot id' chip goes to the home check", async () => {
    const { default: VerifyPage } = await import("./VerifyPage");
    render(
      <MemoryRouter initialEntries={["/verify"]}>
        <Routes>
          <Route path="/verify" element={<VerifyPage />} />
          <Route path="*" element={<Where />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText(/download a passport from my plots, then paste its document id here or scan its qr code/i)).toBeTruthy();
    expect(screen.getByText("Try a plot id")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: new RegExp(SAMPLE_PLOTS[2].ulpin) }));
    expect((await screen.findByTestId("where")).textContent).toBe(`/?plot=${SAMPLE_PLOTS[2].ulpin}#check`);
    expect(verifyDocument).not.toHaveBeenCalled();
  });

  it("the landing check runs a plot id given in the address", async () => {
    await renderCard({ initialUlpin: SAMPLE_PLOTS[0].ulpin });
    await waitFor(() => expect(getPublicPlot).toHaveBeenCalledWith(SAMPLE_PLOTS[0].ulpin, expect.anything()));
  });
});
