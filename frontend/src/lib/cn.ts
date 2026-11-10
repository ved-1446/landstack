import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// tailwind-merge must know our own utility names, or it would treat `text-14` (a size) and `text-cream`
// (a colour) as the same kind of class and drop one of them.
const merge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["11", "12", "13", "14", "16", "20", "26", "34", "58"] }],
      rounded: [{ rounded: ["control", "card", "panel", "drawer", "pill"] }],
      shadow: [{ shadow: ["1", "2", "3"] }],
      z: [{ z: ["map", "panel", "rail", "drawer", "modal", "toast"] }],
    },
  },
});

/** Join class names, then let the last conflicting Tailwind class win. */
export function cn(...inputs: ClassValue[]): string {
  return merge(clsx(inputs));
}
