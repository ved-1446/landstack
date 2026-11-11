/** "1,849 m²" (or "Not available" for an invalid outline). */
export function sqm(value: number | null | undefined): string {
  return value === null || value === undefined ? "Not available" : `${Math.round(value).toLocaleString("en-IN")} m²`;
}

/** "12 Nov 2026, 5:30 pm" */
export function when(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
}

/** What each audit action means, in plain words (the API sends the raw action names). */
export const ACTION_WORDS: Record<string, string> = {
  view_passport: "Viewed a passport",
  view_passport_denied: "Tried to open a plot that is not yours",
  view_passport_not_found: "Looked for a plot that was not found",
  download_passport_pdf: "Downloaded a PDF passport",
  download_passport_pdf_denied: "Tried to download a PDF for a plot that is not yours",
  download_passport_pdf_not_found: "Tried to download a PDF for a plot that was not found",
  explain_passport: "Asked for a plain-words explanation",
  explain_passport_denied: "Tried to get an explanation for a plot that is not yours",
  explain_passport_not_found: "Tried to get an explanation for a plot that was not found",
  guide_ask: "Asked the Land Guide a question",
};

export function actionWords(action: string): string {
  return ACTION_WORDS[action] ?? action.replace(/_/g, " ");
}

/** True for a 14-character plot id. */
export const isUlpin = (text: string) => /^[A-Z0-9]{14}$/.test(text);

/** Pull a document id out of what was pasted or scanned: the id itself, or the QR code's web address ending in /verify/<id>. */
export function documentIdFrom(text: string): string | null {
  const clean = text.trim();
  const fromUrl = /\/verify\/([A-Za-z0-9-]{4,40})(?:[/?#].*)?$/.exec(clean);
  const candidate = fromUrl ? fromUrl[1] : clean;
  return /^[A-Za-z0-9-]{4,40}$/.test(candidate) ? candidate : null;
}
