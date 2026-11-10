// Builds the Flow Field background document.
//
// `flow-field/flow-field.source.html` is the AUTHORED source from ThreeUI (https://threeui.com/source-code/flow-field.json),
// kept byte for byte. Here it is patched, in the same way ThreeUI's own wrapper patches it, with explicit
// replacements. Each one is checked: if the source ever changes and a patch no longer matches, this
// throws instead of quietly showing a frozen background.
//
//   1. the wrapper's own flow-field patches: strip the Cloudflare beacon script, set the particle count, and
//      multiply motion by window.__SF_CONTROLS.speed (the source freezes when that control is unset);
//   2. ONLY colour constants are changed: background -> navy-950, particle palette -> cream, coral, mist;
//   3. the "Flow Field" caption is hidden with an injected style (not an edit to the authored markup).
//
// Colours are read from the design tokens at run time, so they always match tokens.css.
import source from "./flow-field/flow-field.source.html?raw";
import { hexToRgb, readPalette } from "../../lib/tokens";

function patch(doc: string, from: string | RegExp, to: string): string {
  const found = typeof from === "string" ? doc.includes(from) : from.test(doc);
  if (!found) throw new Error(`Flow Field patch did not match: ${String(from).slice(0, 60)}`);
  return doc.replace(from, to);
}

/** The speed control the authored code multiplies by. 1 = normal; 0 = still. Changed by postMessage. */
const CONTROL_SCRIPT = `<script>
window.__SF_CONTROLS = { speed: 1 };
window.addEventListener("message", function (e) {
  if (e.data && e.data.type === "landstack-flow-speed") window.__SF_CONTROLS.speed = e.data.value;
});
</script>
<style>.label { display: none !important; }</style>`;

export function buildFlowFieldDocument({ particleCount }: { particleCount: number }): string {
  const palette = readPalette();
  const navy = hexToRgb(palette.navy950);
  const particleColours = [palette.cream, palette.coral, palette.mist].map(hexToRgb);
  const speed = "((window.__SF_CONTROLS&&window.__SF_CONTROLS.speed)||0)";

  let doc = source;
  // 1. the wrapper's flow-field patches
  doc = patch(doc, /<script defer src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js[^>]*><\/script>/, "");
  doc = patch(doc, "const PARTICLE_COUNT = 2500;", `const PARTICLE_COUNT = ${particleCount};`);
  doc = patch(doc, "time += 0.0008;", `time += 0.0008 * ${speed};`);
  doc = patch(doc, "let vx = Math.cos(angle) * p.speed * SPEED;", `let vx = Math.cos(angle) * p.speed * SPEED * ${speed};`);
  doc = patch(doc, "let vy = Math.sin(angle) * p.speed * SPEED;", `let vy = Math.sin(angle) * p.speed * SPEED * ${speed};`);

  // 2. colour constants only
  doc = doc.replaceAll("#0a0a0a", palette.navy950); // design-check-ignore: the authored source's own colour, being replaced
  doc = patch(doc, "rgba(10, 10, 10, 0.03)", `rgba(${navy.join(", ")}, 0.03)`);
  doc = patch(
    doc,
    /const palette = \[[\s\S]*?\n {2}\];/,
    `const palette = [\n${particleColours.map(([r, g, b]) => `    { r: ${r}, g: ${g}, b: ${b} },`).join("\n")}\n  ];`,
  );

  // the control script and the hidden caption go first in <head>
  return patch(doc, "<head>", `<head>\n${CONTROL_SCRIPT}`);
}
