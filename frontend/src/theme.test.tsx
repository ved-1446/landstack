import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { Drawer, ThemeToggle, ToastProvider } from "./components/ui";
import { initTheme, THEME_KEY } from "./lib/theme";
import { AppRoutes } from "./routes";
import { resetApi } from "./test/fixtures";
import type { Role } from "./types";

vi.mock("./api", async () => {
  const { api } = await import("./test/fixtures");
  return { ...api, getSession: () => null, logout: () => undefined, setUnauthorizedHandler: () => undefined, login: vi.fn(), askGuide: vi.fn(), ApiError: class ApiError extends Error {} };
});
vi.mock("./screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("./features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

function systemPrefers(scheme: "light" | "dark") {
  window.matchMedia = ((query: string) => ({
    matches: query.includes("light") ? scheme === "light" : scheme === "dark",
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

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

beforeEach(() => {
  resetApi();
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
  systemPrefers("dark");
});
afterEach(cleanup);

describe("theme", () => {
  it("starts from the system preference when nothing is saved", () => {
    systemPrefers("light");
    expect(initTheme()).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    systemPrefers("dark");
    expect(initTheme()).toBe("dark");
  });

  it("a saved choice wins over the system preference", () => {
    systemPrefers("light");
    window.localStorage.setItem(THEME_KEY, "dark");
    expect(initTheme()).toBe("dark");
  });

  it("the sun/moon button has a label, switches the theme, and the choice is remembered", () => {
    initTheme();
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("light");
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_KEY)).toBe("dark");
  });

  it("still switches when the browser blocks storage", () => {
    initTheme();
    const broken = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement.dataset.theme).toBe("light");
    broken.mockRestore();
  });

  it.each([
    ["citizen", "/app/plots"],
    ["officer", "/app/dashboard"],
    ["admin", "/app/dashboard"],
  ] as const)("the %s nav and the public nav both have the toggle", async (role, path) => {
    initTheme();
    renderAt(path, role);
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeTruthy();
    cleanup();
    renderAt("/how-it-works", null);
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeTruthy();
  });

  it("switching the theme while the passport drawer is open does not close it", () => {
    initTheme();
    render(
      <>
        <ThemeToggle />
        <Drawer open onClose={() => undefined} label="Land passport" viewingAs="officer">
          <p>passport body</p>
        </Drawer>
      </>,
    );
    expect(screen.getByText("passport body")).toBeTruthy();
    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));
    });
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(screen.getByText("passport body")).toBeTruthy();
    expect(document.documentElement.dataset.drawer).toBe("open");
  });
});
