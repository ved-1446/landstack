import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { ToastProvider } from "../components/ui";
import { AppRoutes } from "../routes";
import { api, AUDIT_ROWS, INSIGHTS, resetApi, SYSTEM } from "../test/fixtures";
import type { Role } from "../types";
import { sinceFor } from "./admin/AuditLog";

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
const lastAuditCall = () => api.getAuditLog.mock.calls.at(-1)?.[0] as Record<string, unknown>;

beforeEach(() => {
  resetApi();
  window.scrollTo(0, 0);
});
afterEach(cleanup);

describe("only an admin may open the Control Room pages", () => {
  it.each(["/app/audit", "/app/users", "/app/system", "/app/insights", "/app/desk"])("%s: an officer and a citizen see the 'not for your role' page, and no admin data is requested", async (path) => {
    for (const role of ["officer", "citizen"] as const) {
      cleanup();
      renderAt(path, role);
      expect(await screen.findByText(/this page is not for your role/i)).toBeTruthy();
    }
    for (const fn of ["getAuditLog", "getAdminUsers", "getAdminSystem", "getAdminInsights"]) expect(api[fn]).not.toHaveBeenCalled();
  });

  it("an admin can open every one of them", async () => {
    for (const [path, title] of [["/app/audit", /who looked at/i], ["/app/users", /people and/i], ["/app/system", /system/i], ["/app/insights", /model\s+insights/i], ["/app/dashboard", /running/i]] as const) {
      cleanup();
      renderAt(path, "admin");
      expect(await h1(title)).toBeTruthy();
    }
  });
});

describe("the admin Overview is about the system and the people, not the plot queue", () => {
  it("shows health tiles in words, people by role, activity counts and the latest activity", async () => {
    api.getAuditLog.mockImplementation(async (q: { limit?: number }) => ({ rows: AUDIT_ROWS.slice(0, q.limit ?? 20), total: q.limit === 1 ? 12 : 45 }));
    renderAt("/app/dashboard", "admin");
    await h1(/running/i);
    expect(await screen.findAllByText("Running")).toHaveLength(3);                          // API, database, PostGIS: an icon and a word
    expect(screen.getByText("Switched off")).toBeTruthy();                                   // the AI explainer
    await waitFor(() => expect(screen.getByText("CITIZENS").closest("div")?.parentElement?.textContent).toContain("2"));
    const latest = await screen.findByRole("list", { name: "Latest activity" });
    expect(within(latest).getAllByRole("listitem")).toHaveLength(8);
    expect(screen.getByText("LAST 24 HOURS")).toBeTruthy();
    expect(screen.queryByText("Priority queue")).toBeNull();                                 // that is the officer's page
  });

  it("the officer dashboard stays reachable for an admin from the Work desk", async () => {
    renderAt("/app/desk", "admin");
    expect(await h1(/attention/i)).toBeTruthy();
    expect(await screen.findByRole("list", { name: "Priority queue" })).toBeTruthy();
  });
});

describe("audit log", () => {
  it("is a timeline with the person, role, time, plain-words action and the plot", async () => {
    renderAt("/app/audit", "admin");
    const list = await screen.findByRole("list", { name: "Audit timeline" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(20);
    expect(rows[0].textContent).toContain("officer");
    expect(rows[0].textContent).toContain("Viewed a passport");
    expect(rows[0].textContent).toMatch(/MH\d{12}/);
    expect(rows[3].textContent).toContain("Asked the Land Guide a question");
    expect(rows[1].textContent).toContain("Tried to open a plot that is not yours");
    expect(rows[1].textContent).not.toMatch(/MH\d{12}/);
    expect(screen.getByText(/45 entries\. Page 1 of 3/)).toBeTruthy();
  });

  it("starts on the last 7 days and every filter goes to the server", async () => {
    renderAt("/app/audit", "admin");
    await screen.findByRole("list", { name: "Audit timeline" });
    expect(lastAuditCall()).toMatchObject({ limit: 20, offset: 0 });
    expect(typeof lastAuditCall().since).toBe("string");
    fireEvent.change(screen.getByLabelText("Person"), { target: { value: "citizen2" } });
    await waitFor(() => expect(lastAuditCall()).toMatchObject({ username: "citizen2" }));
    fireEvent.change(screen.getByLabelText("Kind of action"), { target: { value: "download_passport_pdf" } });
    await waitFor(() => expect(lastAuditCall()).toMatchObject({ username: "citizen2", action: "download_passport_pdf" }));
    fireEvent.click(screen.getByRole("button", { name: /all time/i }));
    await waitFor(() => expect(lastAuditCall().since).toBeUndefined());
    fireEvent.click(screen.getByRole("button", { name: /last 24 hours/i }));
    await waitFor(() => expect(typeof lastAuditCall().since).toBe("string"));
  });

  it("the time presets are 24 hours, 7 days, 30 days and all time", () => {
    const now = Date.parse("2026-11-11T12:00:00Z");
    expect(sinceFor("24h", now)).toBe("2026-11-10T12:00:00.000Z");
    expect(sinceFor("7d", now)).toBe("2026-11-04T12:00:00.000Z");
    expect(sinceFor("30d", now)).toBe("2026-10-12T12:00:00.000Z");
    expect(sinceFor("all", now)).toBeUndefined();
  });

  it("pages: Older and Newer move by 20 rows, the ends are disabled, and a filter returns to page 1", async () => {
    renderAt("/app/audit", "admin");
    await screen.findByRole("list", { name: "Audit timeline" });
    expect((screen.getByRole("button", { name: /newer/i }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /older/i }));
    await waitFor(() => expect(lastAuditCall()).toMatchObject({ offset: 20 }));
    fireEvent.click(await screen.findByRole("button", { name: /older/i }));
    await waitFor(() => expect(lastAuditCall()).toMatchObject({ offset: 40 }));
    await waitFor(() => expect((screen.getByRole("button", { name: /older/i }) as HTMLButtonElement).disabled).toBe(true));
    fireEvent.change(screen.getByLabelText("Person"), { target: { value: "officer" } });
    await waitFor(() => expect(lastAuditCall()).toMatchObject({ username: "officer", offset: 0 }));
  });

  it("has an empty state and an error state in plain words", async () => {
    api.getAuditLog.mockResolvedValue({ rows: [], total: 0 });
    renderAt("/app/audit", "admin");
    expect(await screen.findByText("Nothing matches")).toBeTruthy();
    cleanup();
    api.getAuditLog.mockReset().mockRejectedValueOnce(new Error("The server answered with an error (HTTP 500).")).mockResolvedValue({ rows: AUDIT_ROWS, total: 20 });
    renderAt("/app/audit", "admin");
    expect(await screen.findByText("Could not load the audit log")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByRole("list", { name: "Audit timeline" })).toBeTruthy();
  });
});

describe("users", () => {
  it("lists every account with its role, linked plots and last activity, and never a password", async () => {
    renderAt("/app/users", "admin");
    const list = await screen.findByRole("list", { name: "Users" });
    const rows = within(list).getAllByRole("listitem").map((r) => r.textContent ?? "");
    expect(rows).toHaveLength(4);
    expect(rows[2]).toContain("citizen1");
    expect(rows[2]).toContain("3 plots linked");
    expect(rows[2]).toContain("never active");
    expect(rows[2]).toContain("CITIZEN");
    expect(rows[1]).toContain("41 actions in 30 days");
    expect(document.body.textContent).not.toMatch(/\$argon2|Demo#2026/i);
  });

  it("has an empty state", async () => {
    api.getAdminUsers.mockResolvedValue([]);
    renderAt("/app/users", "admin");
    expect(await screen.findByText("No users")).toBeTruthy();
  });
});

describe("system", () => {
  it("shows each part as an icon and a word, the model, the counts and the versions", async () => {
    renderAt("/app/system", "admin");
    await h1(/system/i);
    expect(await screen.findAllByText("Running")).toHaveLength(3);
    expect(screen.getByText("Switched off")).toBeTruthy();
    expect(screen.getByText(/never calls it/i)).toBeTruthy();
    expect(screen.getByText("Isolation Forest (a statistical hint, not a conflict)")).toBeTruthy();
    expect(screen.getByText(/5,000 generated plots/)).toBeTruthy();
    expect(screen.getByText("fastapi").nextSibling?.textContent).toBe("0.162.2");
    expect(screen.getByText("API 0.13.3")).toBeTruthy();
  });

  it("says plainly when no model is loaded, and can be checked again", async () => {
    api.getAdminSystem.mockResolvedValue({ ...SYSTEM, ai_explainer: { state: "ok", detail: "Switched on." }, model: { ...SYSTEM.model, loaded: false } });
    renderAt("/app/system", "admin");
    expect(await screen.findByText(/No \(the passport simply shows no unusual note\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /check again/i }));
    await waitFor(() => expect(api.getAdminSystem).toHaveBeenCalledTimes(2));
  });
});

describe("insights", () => {
  it("is clearly labelled as explanation only and lists the 12 signals in plain words", async () => {
    renderAt("/app/insights", "admin");
    await h1(/model\s+insights/i);
    const note = await screen.findByRole("note", { name: /what this page is/i });
    expect(note.textContent).toContain("Explanation only.");
    expect(note.textContent).toContain("never changes a score");
    const bars = within(screen.getByRole("heading", { name: "What it pays attention to" }).parentElement as HTMLElement).getAllByRole("listitem");
    expect(bars).toHaveLength(12);
    expect(bars[0].textContent).toContain("How many other plots it overlaps or touches (30%)");
    expect(bars.every((b) => !/_/.test(b.textContent ?? ""))).toBe(true);              // words, not column names
    expect(INSIGHTS.features.reduce((s, f) => s + f.share, 0)).toBeCloseTo(1, 2);
  });

  it("explains that no model is installed, and how to train one", async () => {
    api.getAdminInsights.mockResolvedValue({ ...INSIGHTS, available: false, features: [], flagged: 0 });
    renderAt("/app/insights", "admin");
    expect(await screen.findByText("No model is installed")).toBeTruthy();
    expect(screen.getByText("python -m ml.train_unusual")).toBeTruthy();
    expect(screen.getByRole("note", { name: /what this page is/i })).toBeTruthy();       // the label is still there
  });
});
