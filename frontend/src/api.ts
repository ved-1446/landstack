// The ONLY file that talks to the backend. Everything else calls these functions.
import type {
  ConflictTypeInfo,
  ConstructionCollection,
  Explanation,
  GuideAnswer,
  LoginResponse,
  Passport,
  PlotCollection,
  PlotFilters,
  Session,
  Summary,
  Verification,
} from "./types";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  /** the HTTP status (401, 404, 429...) or undefined when the server could not be reached */
  status?: number;
  /** seconds to wait, from a 429's Retry-After header */
  retryAfter?: number;
  constructor(message: string, status?: number, retryAfter?: number) {
    super(message);
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

// ---- the login session ----
//
// The token is kept in sessionStorage. Trade-off: JavaScript on the page can read it, so a
// cross-site-scripting bug could steal it (an httpOnly cookie cannot be read by scripts, but then
// the server must also defend against cross-site request forgery). sessionStorage at least goes
// away when the tab closes and is not shared between tabs. Tokens last 60 minutes.
const SESSION_KEY = "landstack.session";

export function getSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null; // storage blocked or the value is damaged: act as logged out
  }
}

function saveSession(session: Session) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    // storage blocked: the session then lasts only until the page is reloaded
  }
}

export function logout(): void {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // nothing to clear
  }
}

// App registers one function here; it is called when the server says "401: log in again".
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

/** Turn the contract's error bodies (401 / 403 / 404 / 422 / 429 / 503 / 500) into one readable sentence. */
function messageFromBody(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    // 422: FastAPI's list of problems
    const first = detail[0] as { loc?: unknown[]; msg?: string };
    const where = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : "";
    return `Invalid request${where ? ` (${where})` : ""}: ${first.msg ?? "bad value"}`;
  }
  return `The server answered with an error (HTTP ${status}).`;
}

interface Options {
  params?: Record<string, string | undefined>;
  signal?: AbortSignal;
  body?: unknown; // sent as JSON with POST
  authenticated?: boolean; // default true: send the token, and treat 401 as "session over"
}

/** Sends the request and returns the response if it worked. Everything that went wrong becomes an ApiError. */
async function send(path: string, options: Options = {}): Promise<Response> {
  const { params = {}, signal, body, authenticated = true } = options;
  const url = new URL(BASE_URL + path);
  for (const [key, value] of Object.entries(params)) {
    if (value) url.searchParams.set(key, value);
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = authenticated ? getSession()?.token : undefined;
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: body !== undefined ? "POST" : "GET",
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw err; // the caller cancelled on purpose; not an error to show
    throw new ApiError(`Cannot reach the API at ${BASE_URL}. Is the backend running?`);
  }

  if (response.status === 401 && authenticated) {
    logout();
    onUnauthorized?.();
    throw new ApiError("Your session has ended. Please log in again.", 401);
  }
  if (response.status === 429) {
    const header = response.headers.get("Retry-After");
    const wait = header ? Number(header) : undefined;
    throw new ApiError(
      wait ? `Too many requests. Please wait ${wait} seconds and try again.` : "Too many requests. Please wait a moment and try again.",
      429,
      wait,
    );
  }
  if (!response.ok) {
    let json: unknown = null;
    try {
      json = await response.json();
    } catch {
      // not JSON; the generic message below is used
    }
    throw new ApiError(messageFromBody(response.status, json), response.status);
  }
  return response;
}

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const response = await send(path, options);
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError("The server sent a reply that is not valid JSON.");
  }
}

export async function login(username: string, password: string): Promise<Session> {
  const result = await request<LoginResponse>("/auth/login", {
    body: { username, password },
    authenticated: false, // a wrong password is a 401 too, but it is not "session over"
  });
  const session: Session = { token: result.access_token, username: result.user.username, role: result.user.role };
  saveSession(session);
  return session;
}

export function getPlots(filters: PlotFilters = {}, signal?: AbortSignal) {
  return request<PlotCollection>("/plots", { params: { ...filters }, signal });
}

export function getPassport(ulpin: string, signal?: AbortSignal) {
  return request<Passport>(`/plots/${encodeURIComponent(ulpin)}`, { signal });
}

export function getSummary(signal?: AbortSignal) {
  return request<Summary>("/summary", { signal });
}

export function getConflictTypes(signal?: AbortSignal) {
  return request<ConflictTypeInfo[]>("/conflict-types", { signal });
}

/** Plain-words explanation of a plot's existing findings (Phase 11). The AI only rewrites them; it never changes any. */
export function explainPassport(ulpin: string, signal?: AbortSignal) {
  return request<Explanation>(`/plots/${encodeURIComponent(ulpin)}/explain`, { body: {}, signal });
}

/** Ask the Land Guide a general question. Only the question is sent: no plot, no personal data. */
export function askGuide(question: string, signal?: AbortSignal) {
  return request<GuideAnswer>("/guide/ask", { body: { question }, signal });
}

/** SIMULATED new-building outlines for the map (citizens get only their own plots). */
export function getConstructionAlerts(signal?: AbortSignal) {
  return request<ConstructionCollection>("/construction-alerts", { signal });
}

/** The printable passport as a PDF file (the login token is sent, so the same role rules apply). */
export async function downloadPassportPdf(ulpin: string, signal?: AbortSignal): Promise<Blob> {
  const response = await send(`/plots/${encodeURIComponent(ulpin)}/passport.pdf`, { signal });
  return response.blob();
}

/** Does a printed passport still match the records? Public endpoint: no login needed. */
export function verifyDocument(docId: string, signal?: AbortSignal) {
  return request<Verification>(`/verify/${encodeURIComponent(docId.trim())}`, { signal, authenticated: false });
}
