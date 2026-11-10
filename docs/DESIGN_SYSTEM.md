# LandStack design system

The look of `frontend/` (Phase 5). Everything below lives in `frontend/src/styles/tokens.css` and is mapped into the Tailwind theme in `frontend/src/styles/index.css`. **Components never contain hex codes or arbitrary pixel values**; `npm run check:design` fails the build if they do.

## Palette: navy about 60%, cream about 30%, coral about 10%

| Token | Value | Use |
|---|---|---|
| `navy-950` | #0A1429 | page, dark map |
| `navy-900` | #0F1E3D | panels, drawer shell |
| `navy-800` | #182C54 | raised surfaces |
| `cream` | #F6F0E4 | text on navy, the passport sheet |
| `muted-on-navy` | #B4BDD0 | secondary text on navy |
| `faint-on-navy` | #97A2BA | tertiary text on navy |
| `ink` | #0F1E3D | text on cream |
| `muted-on-cream` | #3E4A66 | secondary text on cream |
| `faint-on-cream` | #5B6781 | tertiary text on cream |
| `coral` / hover / pressed | #FF6F59 / #FF8A78 / #E85A44 | **only**: the search button, primary buttons, the selected-plot ring, focus rings, the active rail icon |
| `mist` | #8FA3C4 | the soft blue-grey particle colour on the login background |
| `risk-green` / `risk-amber` / `risk-red` | #3DBE7F / #E9B44C / #E5535F | **only** for risk (plot fills, chips' dots and borders) |
| `risk-*-ink` | #1E7A4C / #7A4B00 / #A31E32 | risk on cream (chip text, gauge arcs) |
| `gauge-red` | #D23A4A | the gauge arc on cream |
| `sim` / `sim-ink` | #5CC8FF / #0B5C86 | **only** for SIMULATED data (Phase 10, the construction alert): the new-building footprints and labels on the map, and the "Simulated" chips. `sim` on navy (about 10:1), `sim-ink` on cream (about 6:1) |
| `line-on-navy` / `line-on-cream` | cream 14% / navy 14% | hairlines |

Coral never marks risk. Risk colours are never used for anything but risk. `sim` never marks risk either: it is the colour of "this is simulated", always next to the word SIMULATED (a dashed outline on the map, a chip in the drawer), never colour alone.

### Contrast rules (checked with a script; all text 4.5:1 or better)
- Text on a coral button is **navy-950** (6.70:1). Cream on coral fails (2.41:1), so it is never used.
- Coral is never text on cream (2.41:1).
- Risk red on navy-800 is 3.75:1 and fails. Risk chips on navy therefore use **cream text** with a coloured dot and border; red text is never placed on navy-800.
- Risk is never colour-only: every risk colour comes with a word (LOW RISK, WATCH, HIGH RISK, GREEN BAND...), a dot or an icon.

## Type (self-hosted with @fontsource, no Google CDN)
- **Instrument Serif**: titles and the score number.
- **Geist**: all UI text.
- **Geist Mono**: ULPINs, numbers, small-caps labels.
- Sizes only: 11, 12, 13, 14, 16, 20, 26, 34, 58 px (`text-11` ... `text-58`).

## Space, shape, depth
- Spacing is the 4px scale: 4, 8, 12, 16, 24, 32, 48 (`1, 2, 3, 4, 6, 8, 12`). No arbitrary values such as `mt-[13px]`.
- Floating panels sit 24px from the screen edge on desktop and 16px on mobile (`--edge`).
- Radius: 8 `rounded-control` (inputs, chips), 12 `rounded-card`, 16 `rounded-panel` (floating panels), 20 `rounded-drawer`, `rounded-pill`.
- Shadows: three levels, `shadow-1`, `shadow-2`, `shadow-3`.
- Z-layers, by name: `z-map`, `z-panel`, `z-rail`, `z-drawer`, `z-modal`, `z-toast`.
- Glass (backdrop blur) only on panels floating over the map: the search pill, popovers and the dock. The drawer is solid navy. Nowhere else.

## Motion
- 150 to 300 ms, ease-out. framer-motion for UI transitions (login steps, drawer, cards, panels, toasts).
- GSAP only for the gauge arc fill and the score count-up (about 900 ms).
- `prefers-reduced-motion` is respected everywhere (framer-motion `MotionConfig reducedMotion="user"`, GSAP skipped, the Flow Field background shows a still frame).

## Components (`src/components/ui`, one file each)
Button, Chip, Card, Switch, Segmented, SearchPill, Gauge, EvidenceCard, Skeleton, Drawer, Toast, EmptyState, plus Popover (the frosted popover that becomes a bottom sheet on mobile). `cn()` (clsx + tailwind-merge) and `cva` variants throughout. Every data component has loading, empty and error states. Icons: lucide-react only (Copy = overlap, Users = owner mismatch, Receipt = tax, ShieldAlert = restricted zone, Ruler = area mismatch, Files = duplicate survey number, AlertTriangle = invalid boundary, FileX = missing record, Building2 = construction alert).

## The Land Guide and "Explain in plain words" (Phase 11)
No new tokens. The Land Guide is a `Popover` (wider via `--guide-width`, with a new optional `footer` slot that keeps the input pinned) opened by a rail icon and a floating button (navy with a hairline border: coral stays for primary actions; the button carries `data-rail` so the click-outside handler does not fight it, and it hides on phones while the sheet is open). Every state is written in words with an icon, never colour alone: "AI answer, from the sources", "Not in my sources", "AI is off", "AI is busy", "AI could not answer", "Could not ask". The AI label and a "can be wrong, not legal advice" note are always visible. "Explain in plain words" is a `paper` button in the cream sheet; its result card always carries the label the API sends ("AI-written summary of the findings above", or the honest "written by code" one) and says the score, band and findings are unchanged.

## Accessibility
Real buttons and inputs; labels on icon-only buttons; visible coral focus rings on everything focusable; keyboard friendly (Escape closes the drawer, popovers and dialogs); the gauge is an image with a text alternative ("Risk score 75 out of 100, red band") and the band is always written in words; toasts live in an `aria-live` region.

## Responsive
- 1440 and wider: icon rail on the left, floating search pill, dock at the bottom, drawer 430px on the right.
- 768 to 1439: the same, with narrower popovers.
- Under 768: the rail becomes a bottom tab bar, the search pill spans the width, popovers and the passport drawer become bottom sheets (the passport has peek / half / full snap points).

## Basemaps and attribution
Light = CARTO Positron, Dark (default) = CARTO Dark Matter, Satellite = Esri World Imagery. The keyless endpoints are used unless `VITE_CARTO_KEY` / `VITE_ESRI_KEY` are set. Attribution is always visible on the map and repeated in the Layers popover. If a basemap fails to load, a toast says so and the map falls back to Dark. See `docs/HANDOFF.md` for the terms risk.
