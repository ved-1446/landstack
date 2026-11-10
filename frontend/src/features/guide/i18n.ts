// The fixed Hindi and Marathi sentences for the Land Guide panel and the Explain section.
// They all live in ONE file shared with the backend, chatbot/strings.json, so a native speaker can review them in one place.
// They have NOT been reviewed yet. Full-app translation is out of scope: the rest of the app stays English.
import raw from "../../../../chatbot/strings.json";
import type { Language } from "../../types";

export const LANGUAGES: Language[] = ["en", "hi", "mr"];
export type StringKey = keyof typeof raw.strings;

type Entry = Record<Language, string>;
const strings = raw.strings as unknown as Record<StringKey, Entry>;

/** The name of each language written in that language: English, हिन्दी, मराठी. */
export const LANGUAGE_NAMES = raw.languages as Record<Language, string>;

export function translate(key: StringKey, language: Language): string {
  const entry = strings[key];
  return entry[language] || entry.en;
}

export function isLanguage(value: unknown): value is Language {
  return value === "en" || value === "hi" || value === "mr";
}
