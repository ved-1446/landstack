import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { ToastProvider } from "../components/ui";
import { AppRoutes } from "../routes";
import { resetApi } from "../test/fixtures";
import type { Role } from "../types";

vi.mock("../api", async () => {
  const { api } = await import("../test/fixtures");
  return { ...api, getSession: () => null, logout: () => undefined, setUnauthorizedHandler: () => undefined, login: vi.fn(), askGuide: vi.fn(), ApiError: class ApiError extends Error {} };
});
vi.mock("../screens/MapScreen", () => ({ default: () => <div data-testid="map-screen" /> }));
vi.mock("../features/login/FlowField", () => ({ default: () => <div data-testid="flow-field" /> }));

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
  window.scrollTo(0, 0);
});
afterEach(cleanup);

describe("keyboard users", () => {
  it("every shell starts with a 'Skip to content' link that points at the main area", async () => {
    for (const [path, role] of [["/how-it-works", null], ["/app/plots", "citizen"], ["/app/dashboard", "officer"], ["/app/dashboard", "admin"]] as const) {
      cleanup();
      renderAt(path, role);
      await screen.findByRole("heading", { level: 1 });
      const skip = screen.getByRole("link", { name: "Skip to content" });
      expect(skip.getAttribute("href")).toBe("#main");
      const main = document.getElementById("main");
      expect(main).toBeTruthy();
      expect(main?.getAttribute("tabindex")).toBe("-1");
      expect(document.querySelector("a, button, input")).toBe(skip);          // the very first thing Tab reaches
    }
  });

  it("the navigation landmarks have names", async () => {
    renderAt("/app/dashboard", "admin");
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByRole("navigation", { name: "admin pages" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Work desk pages" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /account: admin/i })).toBeTruthy();
  });
});
