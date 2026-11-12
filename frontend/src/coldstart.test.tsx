import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, getPublicStats } from "./api";
import { ServerWakingBanner } from "./components/ServerWakingBanner";
import { resetServerState, wakeTuning } from "./lib/serverState";

const STATS = { total_plots: 100, plots_per_band: { green: 58, amber: 29, red: 13 }, findings_per_type: {}, checks: 9 };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const fetchMock = vi.fn();
const WAKING = /the demo server is waking up/i;

beforeEach(() => {
  vi.useFakeTimers();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  Object.assign(wakeTuning, { slowAfterMs: 5000, retryEveryMs: 4000, maxTries: 30 });
  resetServerState();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("a sleeping demo server", () => {
  it("shows the waking-up note while it cannot connect, retries by itself, and goes away when the server answers", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed")).mockRejectedValueOnce(new TypeError("fetch failed")).mockResolvedValue(json(STATS));
    render(<ServerWakingBanner />);
    expect(screen.queryByText(WAKING)).toBeNull();

    const result = getPublicStats();
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    expect(screen.getByText(WAKING)).toBeTruthy();
    expect(screen.getByRole("status").textContent).toMatch(/about a minute/i);

    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });   // second try fails too
    expect(screen.getByText(WAKING)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });   // third try works
    await expect(result).resolves.toMatchObject({ total_plots: 100 });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(screen.queryByText(WAKING)).toBeNull();
  });

  it("treats a 503 from the host as 'still starting', not as an error", async () => {
    fetchMock.mockResolvedValueOnce(json({ detail: "starting" }, 503)).mockResolvedValue(json(STATS));
    render(<ServerWakingBanner />);
    const result = getPublicStats();
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    expect(screen.getByText(WAKING)).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    await expect(result).resolves.toMatchObject({ total_plots: 100 });
    expect(screen.queryByText(WAKING)).toBeNull();
  });

  it("shows the note when the first answer is only slow, and removes it when the answer arrives", async () => {
    let answer: (r: Response) => void = () => undefined;
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => (answer = resolve)));
    render(<ServerWakingBanner />);
    const result = getPublicStats();
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(screen.queryByText(WAKING)).toBeNull();                          // 4 s is normal
    await act(async () => { await vi.advanceTimersByTimeAsync(1500); });
    expect(screen.getByText(WAKING)).toBeTruthy();                           // past 5 s
    await act(async () => { answer(json(STATS)); });
    await expect(result).resolves.toMatchObject({ total_plots: 100 });
    expect(screen.queryByText(WAKING)).toBeNull();
  });

  it("does not wait or show the note for a real error such as 404 or 401", async () => {
    fetchMock.mockResolvedValue(json({ detail: "No such plot" }, 404));
    render(<ServerWakingBanner />);
    await expect(getPublicStats()).rejects.toMatchObject({ status: 404 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(WAKING)).toBeNull();
  });

  it("once the server has answered, a later failure is reported at once (no waiting, no note)", async () => {
    fetchMock.mockResolvedValueOnce(json(STATS)).mockRejectedValue(new TypeError("fetch failed"));
    render(<ServerWakingBanner />);
    await getPublicStats();
    await expect(getPublicStats()).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(WAKING)).toBeNull();
  });

  it("gives up after the tries run out, says so, and 'Try again' checks /health", async () => {
    wakeTuning.maxTries = 3;
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    render(<ServerWakingBanner />);
    const result = getPublicStats().catch((e: unknown) => e);
    await act(async () => { await vi.advanceTimersByTimeAsync(9000); });
    expect(await result).toBeInstanceOf(ApiError);
    expect(screen.getByText(/still not answering/i)).toBeTruthy();

    const reload = vi.fn();
    vi.stubGlobal("location", { ...window.location, reload });
    fetchMock.mockReset().mockResolvedValue(json({ status: "ok" }));
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: /try again/i })); await vi.advanceTimersByTimeAsync(10); });
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/health$/);
    expect(reload).toHaveBeenCalled();
    expect(screen.queryByText(/still not answering/i)).toBeNull();
  });

  it("a call the page cancels is not retried and shows nothing", async () => {
    const controller = new AbortController();
    fetchMock.mockImplementation(() => Promise.reject(new DOMException("Aborted", "AbortError")));
    render(<ServerWakingBanner />);
    controller.abort();
    await expect(getPublicStats(controller.signal)).rejects.toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(WAKING)).toBeNull();
  });
});
