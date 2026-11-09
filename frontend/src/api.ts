// The ONLY file that talks to the backend. Everything else calls these functions.
import type {
  ConflictTypeInfo,
  Passport,
  PlotCollection,
  PlotFilters,
  Summary,
} from "./types";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {}

/** Turn the contract's error bodies (404 / 422 / 503 / 500) into one readable sentence. */
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

async function request<T>(
  path: string,
  params: Record<string, string | undefined> = {},
  signal?: AbortSignal,
): Promise<T> {
  const url = new URL(BASE_URL + path);
  for (const [key, value] of Object.entries(params)) {
    if (value) url.searchParams.set(key, value);
  }

  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch (err) {
    if (signal?.aborted) throw err; // the caller cancelled on purpose; not an error to show
    throw new ApiError(`Cannot reach the API at ${BASE_URL}. Is the backend running?`);
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // not JSON; handled below
  }
  if (!response.ok) throw new ApiError(messageFromBody(response.status, body));
  if (body === null) throw new ApiError("The server sent a reply that is not valid JSON.");
  return body as T;
}

export function getPlots(filters: PlotFilters = {}, signal?: AbortSignal) {
  return request<PlotCollection>("/plots", { ...filters }, signal);
}

export function getPassport(ulpin: string, signal?: AbortSignal) {
  return request<Passport>(`/plots/${encodeURIComponent(ulpin)}`, {}, signal);
}

export function getSummary(signal?: AbortSignal) {
  return request<Summary>("/summary", {}, signal);
}

export function getConflictTypes(signal?: AbortSignal) {
  return request<ConflictTypeInfo[]>("/conflict-types", {}, signal);
}
