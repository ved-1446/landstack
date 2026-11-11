import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { ToastProvider } from "./components/ui";
import { AppRoutes } from "./routes";
import { resetApi } from "./test/fixtures";
import type { Role } from "./types";

const askGuide = vi.fn();
vi.mock("./api", async () => {
  const { api } = await import("./test/fixtures");
  return { ...api, getSession: () => null, logout: () => undefined, setUnauthorizedHandler: () => undefined, login: vi.fn(), askGuide: (...a: unknown[]) => askGuide(...a), ApiError: class ApiError extends Error {} };
});
vi.mock("./screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("./features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

const ANSWER = { status: "answered", answer: "A ULPIN is a unique land parcel number.", sources: [], disclaimer: "General information only.", language: "en", ai: false };

function renderAt(path: string, role: Role | null) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider initial={role ? { token: "t", username: role, role } : null}>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

const launcher = () => screen.getByRole("button", { name: /(ask|close) the land guide/i });

beforeEach(() => {
  resetApi();
  askGuide.mockReset().mockResolvedValue(ANSWER);
});
afterEach(cleanup);

describe("the Land Guide launcher", () => {
  it.each([
    ["citizen", "/app/plots"],
    ["officer", "/app/dashboard"],
    ["admin", "/app/dashboard"],
  ] as const)("is on every %s page, closed at first", async (role, path) => {
    renderAt(path, role);
    await screen.findByRole("heading", { level: 1 });
    expect(launcher().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("dialog", { name: /land guide/i })).toBeNull();
  });

  it("is NOT on the public pages or the login page", async () => {
    for (const path of ["/", "/how-it-works", "/about", "/verify", "/login"]) {
      cleanup();
      renderAt(path, null);
      await screen.findAllByRole("heading");
      expect(screen.queryByRole("button", { name: /land guide/i }), path).toBeNull();
    }
  });

  it("is not shown on the full Land Guide page (it has its own chat)", async () => {
    renderAt("/app/guide", "citizen");
    await screen.findByRole("heading", { level: 1 }, { timeout: 8000 });
    expect(screen.queryByRole("button", { name: /ask the land guide/i })).toBeNull();
  });

  it("opens a dialog, moves the focus into it, and closes with the close button; the focus returns to the launcher", async () => {
    renderAt("/app/plots", "citizen");
    await screen.findByRole("heading", { level: 1 });
    fireEvent.click(launcher());
    const dialog = await screen.findByRole("dialog", { name: /land guide/i });
    expect(launcher().getAttribute("aria-expanded")).toBe("true");
    await waitFor(() => expect(document.activeElement?.id).toBe("guide-input"));
    fireEvent.click(within(dialog).getByRole("button", { name: /close/i }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /land guide/i })).toBeNull());
    expect(document.activeElement).toBe(launcher());
  });

  it("closes with Escape and gives the focus back", async () => {
    renderAt("/app/dashboard", "officer");
    await screen.findByRole("heading", { level: 1 });
    fireEvent.click(launcher());
    await screen.findByRole("dialog", { name: /land guide/i });
    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /land guide/i })).toBeNull());
    expect(document.activeElement).toBe(launcher());
  });

  it("keeps the conversation when it is closed and opened again", async () => {
    renderAt("/app/plots", "citizen");
    await screen.findByRole("heading", { level: 1 });
    fireEvent.click(launcher());
    await screen.findByRole("dialog", { name: /land guide/i });
    fireEvent.change(document.getElementById("guide-input") as HTMLTextAreaElement, { target: { value: "What is a ULPIN?" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText(/unique land parcel number/i)).toBeTruthy();
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /land guide/i })).toBeNull());
    fireEvent.click(launcher());
    expect(await screen.findByText(/unique land parcel number/i)).toBeTruthy();
    expect(askGuide).toHaveBeenCalledTimes(1);
  });

  it("has an 'Open full page' link to /app/guide", async () => {
    renderAt("/app/plots", "citizen");
    await screen.findByRole("heading", { level: 1 });
    fireEvent.click(launcher());
    const link = await screen.findByRole("link", { name: /open full page/i });
    expect(link.getAttribute("href")).toBe("/app/guide");
    fireEvent.click(link);
    expect(await screen.findByRole("heading", { level: 1, name: /ask in plain/i })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /ask the land guide/i })).toBeNull();
  });
});
