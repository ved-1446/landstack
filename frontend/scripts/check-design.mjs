// Design guard (no extra libraries): fails when components break the LandStack design rules.
// Run with: npm run check:design   (it also runs before every build)
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const SKIP_FILES = new Set(["src/styles/tokens.css"]); // the one place hex codes live

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

const rules = [
  { name: "hex colour (use a token)", test: /#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g, exts: [".ts", ".tsx", ".css"] },
  { name: "arbitrary pixel/rem value in a class (use the spacing scale)", test: /-\[[^\]\s]*\d(?:px|rem|em)[^\]\s]*\]/g, exts: [".ts", ".tsx"] },
  { name: "default Tailwind text size (use text-11 ... text-58)", test: /\btext-(?:xs|sm|base|lg|xl|[2-9]xl)\b/g, exts: [".ts", ".tsx"] },
  {
    name: "default Tailwind palette colour (use a token)",
    test: /\b(?:bg|text|border|ring|fill|stroke|from|to|via|outline|shadow)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)(?:-\d+)?\b/g,
    exts: [".ts", ".tsx"],
  },
  { name: "emoji", test: /\p{Extended_Pictographic}/gu, exts: [".ts", ".tsx", ".css", ".html"] },
  { name: "old product name in the UI", test: /LandStack/gi, exts: [".ts", ".tsx", ".css", ".html", ".webmanifest", ".svg"] },
];

const files = [...walk(join(ROOT, "src")), join(ROOT, "index.html"), ...walk(join(ROOT, "public"))];
let problems = 0;
for (const file of files) {
  const rel = relative(ROOT, file).replaceAll("\\", "/");
  if (SKIP_FILES.has(rel) || rel.endsWith(".source.html")) continue;
  const ext = rel.slice(rel.lastIndexOf("."));
  const text = readFileSync(file, "utf8");
  for (const rule of rules) {
    if (!rule.exts.includes(ext)) continue;
    if (rule.name.startsWith("hex") && (ext === ".svg" || ext === ".webmanifest" || ext === ".html")) continue; // public assets need literal colours
    text.split("\n").forEach((line, index) => {
      if (line.includes("design-check-ignore")) return; // an explicit, reviewed exception
      for (const match of line.matchAll(rule.test)) {
        if (rule.name === "emoji" && "\u00a9\u00ae\u2122".includes(match[0])) continue; // copyright and trademark signs are text
        problems += 1;
        console.error(`${rel}:${index + 1}  ${rule.name}: ${match[0]}`);
      }
    });
  }
}
if (problems) {
  console.error(`\ncheck:design found ${problems} problem(s).`);
  process.exit(1);
}
console.log("check:design: no problems (no hex codes, arbitrary px values, off-scale text, default palette, emoji or old name).");
