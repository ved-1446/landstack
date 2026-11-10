import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { Segmented } from "../../components/ui";
import type { Language } from "../../types";
import { isLanguage, LANGUAGE_NAMES, LANGUAGES, translate, type StringKey } from "./i18n";

const STORAGE_KEY = "landstack.language";

interface LanguageValue {
  language: Language;
  setLanguage: (language: Language) => void;
  /** a fixed sentence in the chosen language (English if it is missing) */
  t: (key: StringKey) => string;
}

const LanguageContext = createContext<LanguageValue | null>(null);

function readSaved(): Language {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    return isLanguage(saved) ? saved : "en";
  } catch {
    return "en"; // storage blocked: English
  }
}

/**
 * The language the visitor PICKED for the Land Guide and the Explain section. It is never guessed or detected (Hindi and
 * Marathi share a script). One choice is shared by both, and remembered for this browser tab only.
 */
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setState] = useState<Language>(readSaved);
  const setLanguage = useCallback((next: Language) => {
    setState(next);
    try {
      sessionStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage blocked: the choice lasts until the page is reloaded
    }
  }, []);
  const value = useMemo<LanguageValue>(() => ({ language, setLanguage, t: (key) => translate(key, language) }), [language, setLanguage]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage(): LanguageValue {
  const value = useContext(LanguageContext);
  if (!value) throw new Error("useLanguage must be used inside <LanguageProvider>");
  return value;
}

/** EN / हिन्दी / मराठी. A radio group (arrow keys move between the three). */
export function LanguageSelector({ surface = "navy" }: { surface?: "navy" | "cream" }) {
  const { language, setLanguage, t } = useLanguage();
  return (
    <div>
      <p className={`mb-2 font-mono text-11 tracking-wider ${surface === "navy" ? "text-faint-on-navy" : "text-faint-on-cream"}`} lang={language}>
        {t("language").toUpperCase()}
      </p>
      <Segmented
        label={t("language")}
        surface={surface}
        value={language}
        onChange={setLanguage}
        options={LANGUAGES.map((l) => ({ value: l, label: LANGUAGE_NAMES[l], lang: l }))}
      />
    </div>
  );
}
