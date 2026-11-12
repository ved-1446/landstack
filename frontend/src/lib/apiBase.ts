// The API address comes ONLY from VITE_API_URL (set it in Vercel, or in frontend/.env). The localhost fallback exists for `npm run dev`
// only: a production build without it says so instead of quietly calling a server that is not there.
export const BASE_URL = (import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "")).replace(/\/$/, "");
export const API_URL_MISSING = BASE_URL === "";
