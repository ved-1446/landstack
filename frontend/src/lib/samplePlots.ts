import type { Band } from "../types";

/**
 * Example plots for visitors who do not know any plot id. The seed is fixed, so these ids and bands are stable.
 * Checked against db/planted_truth.json and the live public endpoint (Phase 14b). The band is shown as a hint on the chip;
 * clicking a chip still asks the real public check, which is the source of truth.
 */
export const SAMPLE_PLOTS: { ulpin: string; band: Band }[] = [
  { ulpin: "MH000100000009", band: "green" },
  { ulpin: "MH000100000004", band: "amber" },
  { ulpin: "MH000100000001", band: "red" },
  { ulpin: "MH000100000006", band: "red" },
];
