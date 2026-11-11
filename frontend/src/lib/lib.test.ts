import { describe, expect, it } from "vitest";
import { PLOT_FEATURES } from "../test/fixtures";
import type { Band, PlotFeature } from "../types";
import { documentIdFrom, isUlpin, sqm } from "./format";
import { paginate, selectPlots, type PlotQuery } from "./plotFilters";

const base: PlotQuery = { text: "", bands: new Set<Band>(["green", "amber", "red"]), village: "", sort: { key: "score", dir: "desc" } };
const ids = (q: Partial<PlotQuery>) => selectPlots(PLOT_FEATURES, { ...base, ...q }).map((f) => f.properties.ulpin.slice(-2));

describe("the multi-band filter", () => {
  it("shows every plot when all three bands are on, highest score first", () => {
    expect(ids({})).toEqual(["06", "03", "05", "02", "01", "04"]);
  });

  it.each([
    [["green"], ["01", "04"]],
    [["amber"], ["05", "02"]],
    [["red"], ["06", "03"]],
    [["green", "amber"], ["05", "02", "01", "04"]],
    [["green", "red"], ["06", "03", "01", "04"]],
    [["amber", "red"], ["06", "03", "05", "02"]],
  ] as [Band[], string[]][])("any combination works: %j", (bands, expected) => {
    expect(ids({ bands: new Set(bands) })).toEqual(expected);
  });

  it("shows nothing when no band is on", () => {
    expect(ids({ bands: new Set() })).toEqual([]);
  });

  it("combines with the village filter and the search", () => {
    expect(ids({ bands: new Set<Band>(["red", "green"]), village: "Wagholi" })).toEqual(["03", "04"]);
    expect(ids({ text: "baner" })).toEqual(["06", "05"]);
    expect(ids({ text: "0000003" })).toEqual(["03"]);
    expect(ids({ text: "  HINJEWADI " })).toEqual(["02", "01"]);
  });
});

describe("sorting and pages", () => {
  it("sorts by area, with a missing area always last", () => {
    expect(ids({ sort: { key: "area_sqm", dir: "asc" } })).toEqual(["05", "02", "01", "03", "06", "04"]);
    expect(ids({ sort: { key: "area_sqm", dir: "desc" } })).toEqual(["06", "03", "01", "02", "05", "04"]);
  });

  it("sorts by village then plot id", () => {
    expect(ids({ sort: { key: "village", dir: "asc" } })).toEqual(["05", "06", "01", "02", "03", "04"]);
  });

  it("cuts a long list into pages and keeps the page number in range", () => {
    const many = Array.from({ length: 40 }, (_, i) => i) as unknown as PlotFeature[];
    expect(paginate(many, 1, 15)).toMatchObject({ pages: 3, page: 1 });
    expect(paginate(many, 3, 15).rows).toHaveLength(10);
    expect(paginate(many, 99, 15).page).toBe(3);
    expect(paginate(many, -4, 15).page).toBe(1);
    expect(paginate([], 1, 15)).toEqual({ rows: [], pages: 1, page: 1 });
  });
});

describe("format helpers", () => {
  it("writes areas and recognises plot ids and document ids", () => {
    expect(sqm(1849.4)).toBe("1,849 m²");
    expect(sqm(null)).toBe("Not available");
    expect(isUlpin("MH000100000006")).toBe(true);
    expect(isUlpin("mh000100000006")).toBe(false);
    expect(documentIdFrom("7KQ2-M9XD-4TPA")).toBe("7KQ2-M9XD-4TPA");
    expect(documentIdFrom("http://localhost:8000/verify/7KQ2-M9XD-4TPA")).toBe("7KQ2-M9XD-4TPA");
    expect(documentIdFrom("not a code!")).toBeNull();
  });
});
