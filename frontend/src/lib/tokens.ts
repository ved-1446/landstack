// Read design tokens (CSS variables) at run time, for the few places that need real colour values
// (MapLibre paint expressions, the Flow Field canvas). Components stay free of hex codes.

export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(full.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export interface Palette {
  navy950: string;
  navy900: string;
  cream: string;
  coral: string;
  mist: string;
  riskGreen: string;
  riskAmber: string;
  riskRed: string;
  sim: string;
}

export function readPalette(): Palette {
  return {
    navy950: cssVar("--navy-950"),
    navy900: cssVar("--navy-900"),
    cream: cssVar("--cream"),
    coral: cssVar("--coral"),
    mist: cssVar("--mist"),
    riskGreen: cssVar("--risk-green"),
    riskAmber: cssVar("--risk-amber"),
    riskRed: cssVar("--risk-red"),
    sim: cssVar("--sim"),
  };
}
