/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** optional free CARTO basemap key (the keyless endpoints are used when unset) */
  readonly VITE_CARTO_KEY?: string;
  /** optional Esri API key for World Imagery (the keyless endpoint is used when unset) */
  readonly VITE_ESRI_KEY?: string;
  /** set to "false" to hide the demo-account row on the login screen. MUST be "false" in any real deployment. */
  readonly VITE_DEMO_ACCOUNTS?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
