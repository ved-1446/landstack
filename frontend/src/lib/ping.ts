import { API_URL_MISSING, BASE_URL } from "./apiBase";
import { markAwake } from "./serverState";

/** Ask the API once whether it is up (the "Try again" button on the waking-up note). */
export async function pingServer(): Promise<boolean> {
  try {
    if (API_URL_MISSING) return false;
    const response = await fetch(BASE_URL + "/health");
    if (response.ok) {
      markAwake();
      return true;
    }
  } catch {
    // still not answering
  }
  return false;
}
