# LandStack design system

The look of `frontend/` (rebuilt in Phase 13a). Everything below lives in `frontend/src/styles/tokens.css` and is mapped into the Tailwind theme in `frontend/src/styles/index.css`. **Components never contain hex codes or arbitrary pixel values**; `npm run check:design` fails the build if they do (hex codes are allowed in `tokens.css` only).

## Palette: 60 / 30 / 10 (taken from the login Flow Field)

| Share | Token | Value | Use |
|---|---|---|---|
| 60% | `navy-950` ("ink") | #08101F | page background |
| 60% | `navy-900` ("navy") | #0B1530 | panels, the passport drawer shell |
| 60% | `navy-800` ("navy-2") | #16275A | raised surfaces |
| 60% | `forest-line` | #2F7A66 | flow lines and patterns only (contour lines). Never text |
| 30% | glass | fill white 7% (10% strong), 1px border white 16%, `backdrop-filter` blur 18px (24px once the page is scrolled), radius 22px | glass cards, the nav pill, secondary buttons |
| 30% | `cream` | #F3ECDD | cream cards and primary text on dark |
| 30% | `muted-on-navy` / `faint-on-navy` | #A9B3C7 / #97A2BA | secondary text on dark |
| 30% | `ink` / `muted-on-cream` / `faint-on-cream` | #0B1530 / #4B5670 / #566178 | text on cream |
| 10% | `coral` / hover / pressed | #FF6B4E / #FF8468 / #E8553A | buttons, the active nav pill, the ONE italic emphasis word in a headline, key highlights, focus rings. **Text on coral is navy-950.** |
| risk | `risk-green` / `risk-amber` / `risk-red` | #2F9E6E / #D9970F / #D23B41 | **only** risk: plot fills, chip borders, gauge arcs |
| risk text on dark | `risk-*-tint` | #5FD3A0 / #F2BC4B / #FF8F93 | the lighter shades for risk TEXT on dark |
| risk on cream | `risk-*-ink` | #17653C / #7A4B00 / #A31E32 | chip text and arcs on cream (green text 6.1:1, amber 6.3:1, red 6.4:1) |
| simulated | `sim` / `sim-ink` | #B9A7FF / #4D3AA8 | **only** for simulated data: lavender, always with a dashed outline or chip and the word SIMULATED |
| role glow | `glow-citizen` / `glow-officer` / `glow-admin` / `glow-visitor` | coral 20% / forest 34% / indigo (#5B6CFF) 26% / coral 22% | soft background glows only, never text or borders |

Coral is **never** used for risk. Risk is never colour-only: every band comes with an icon plus words (`BandChip`: "LOW RISK · GREEN", "WATCH · AMBER", "HIGH RISK · RED"). Lavender never marks risk.

### Contrast rules (all text 4.5:1 or better)
Measured for every token pair in 13a-1 (the lowest is now `faint-on-navy` on navy-2, 5.6:1; `risk-green-ink` on cream was darkened from 4.53:1 to 6.1:1; cream on ink 16.2:1; muted-on-navy on ink 9.0:1 and on navy-2 6.8:1; navy-950 on coral 6.8:1; the three risk tints on ink 8.7 to 10.9:1; `sim` on ink 9.1:1; `sim-ink` on cream 7.2:1). **Rendered pages (13a-2):** a script hides each text, samples the pixels behind it from a screenshot and compares them with the real text colour; the worst of the public pages is 4.69:1 (login) and none is under 4.5:1. Contour lines sit at 30% opacity so they never cut the contrast of text over them.
- Text on a coral button is **navy-950**. Cream on coral fails, so it is never used. Coral is not used as text on cream.
- Risk text on dark uses the `tint` shades; on cream the `ink` shades. Chips on dark keep cream text with a coloured border and an icon.

## Type (self-hosted with @fontsource, no CDN)
- **Instrument Serif** for display: regular, with **one italic coral word** per headline (`PageHeader`).
- **Geist** for UI text. **Geist Mono** for ULPINs, numbers and the small uppercase eyebrow labels (11 to 12 px, letter-spacing `.08em`, `tracking-widest`).
- The Devanagari fallback (Noto Sans Devanagari, Hindi and Marathi) stays in all three stacks.
- Sizes only: 11, 12, 13, 14, 16, 20, 26, 34, 58 px (`text-11` ... `text-58`).

## Space, shape, depth
- Spacing is the 4px scale. No arbitrary values such as `mt-[13px]`.
- Radius: 8 `rounded-control`, 12 `rounded-card`, 16 `rounded-panel`, 20 `rounded-drawer`, **22 `rounded-glass`** (glass and cream cards), `rounded-pill` (nav, chips, badges).
- Shadows: `shadow-1`, `shadow-2`, `shadow-3`. Z-layers by name: `z-map`, `z-panel`, `z-rail`, `z-drawer`, `z-modal`, `z-toast`, `z-nav`.

## Backgrounds and patterns
- **Live Flow Field only on the landing hero and the login page.** It runs in a sandboxed iframe, pauses when the tab is hidden and shows a still frame under `prefers-reduced-motion`.
- **Every other page** uses `StaticLayer` (`components/Backdrop.tsx`): a gradient, a dot grid and a soft glow in the role's tint (`static-layer--citizen|officer|admin|visitor`). No WebGL.
- Three patterns, a different one per section so pages do not look the same: **dot grid** (`.pattern-dots`), **topographic contour lines** (`ContourLines`, SVG, `forest-line`) and a **soft vertical stripe glow** (`StripeGlow`, `.pattern-stripes`).

## Motion
All of it is CSS or `framer-motion`, and all of it respects `prefers-reduced-motion` (a global CSS rule shortens animations to 0.01 ms; `MotionConfig reducedMotion="user"` for framer-motion; the count-up hook shows the end number at once).
- Staggered rise on load (`.rise`: 24px, 0.8 s, 0.12 s steps through `--i`).
- Slow float on preview cards (`.float-slow`), hover lift on cards (`.lift`), route transition (`.route-in`: fade plus a 16px, 200 ms slide).
- Count-up on stat numbers and the gauge number (`lib/useCountUp.ts`, about 900 ms). The gauge arc sweeps with `.gauge-sweep`.
- **GSAP is gone** (removed from dependencies and THIRD_PARTY.md in 13a).

## Shared components (`src/components/ui`, one implementation each)
`GlassNav` (pill, translucent, blurs more when scrolled; coral active tab; on phones the tabs wrap to a sideways-scrolling second row), `PageHeader` (eyebrow + serif title with italic coral word + subtitle), `GlassCard`, `CreamCard`, `StatCard` (counts up), `BandChip` (icon + words), `RoleBadge`, `ScoreGauge` (cream or dark surface), `BarList`, `Donut` (legend always writes the numbers), `DataList` (rows, not a table), `EmptyState`, `Skeleton`, `Toast`, `Button` (primary coral, secondary glass, ghost, paper for cream sheets). Also: `Chip`, `Switch`, `Segmented`, `SearchPill`, `Drawer`, `Popover`, `EvidenceCard`. `cn()` (clsx + tailwind-merge) and `cva` variants throughout. Icons: lucide-react only.

## Role identity (same components, different identity)

| Role | Area name (eyebrow) | Background glow | Surfaces | Nav tabs | Signature |
|---|---|---|---|---|---|
| Visitor | (public pages) | coral glow; live Flow Field on the home hero and login | glass cards | Home, Check a plot, Verify a passport, How it works, About, Sign in | the "Check a plot" card and three preview cards |
| Citizen | **MY LAND** | warm coral | cream cards dominate, big plain-words text | Home, My plots, Activity, Land Guide | plain-words story card + "what to do next" list |
| Officer | **OFFICER WORK DESK** | teal (forest) | dense glass cards | Dashboard, Plots, Map, Conflicts, Construction, Land Guide | priority queue + charts + map preview card |
| Admin | **CONTROL ROOM** | indigo | dense glass cards; a **second tab strip** | Overview, Audit log, Users, System, Insights, plus the officer pages under a "Work desk" strip | audit timeline + system health tiles |

13a built the shell, the tabs per role and the visitor pages; the role pages (dashboards, plots, conflicts and so on) are placeholders until 13b (citizen, officer) and 13c (admin). A role can open only its own pages; anything else sends it to its home page. The map is open to every role (a citizen sees only their own plots on it).

## Routes and the app shell
`/` home, `/login`, `/how-it-works`, `/about`, `/verify` (public); `/app/*` (protected). After sign-in: officer and admin go to `/app/dashboard`, a citizen to `/app/plots`. `AppShell` = glass nav at the top, role badge, account menu (sign out). There is **no side rail and no floating Land Guide button**; the Land Guide is one tab, `/app/guide`, a full-page version of the same panel. `/app/map` shows the map as a **framed card** (`.map-frame`, `contain: layout paint`) under the page header; its search box, tool buttons, dock and popovers sit inside the card. The passport drawer overlays the page.

## The Land Guide and "Explain in plain words" (Phase 11)
The Land Guide is a page (or a `Popover` where one is used) with a pinned input. Every state is written in words with an icon, never colour alone: "AI answer, from the sources", "Not in my sources", "AI is off", "AI is busy", "AI could not answer", "Could not ask". The AI label and a "can be wrong, not legal advice" note are always visible. "Explain in plain words" is a `paper` button in the cream sheet; its result card carries the label the API sends and says the score, band and findings are unchanged.

## Hindi and Marathi, and Devanagari text (Phase 11b)
- **Font:** Noto Sans Devanagari (SIL OFL 1.1), self-hosted, Devanagari subset only, weights 400, 500, 600, loaded only when a Devanagari letter is on the page.
- **Line height:** `:lang(hi), :lang(mr) { line-height: 1.6 }`. Hindi and Marathi text carries a `lang` attribute.
- **Language selector:** `LanguageSelector` (EN / हिन्दी / मराठी), one choice per browser tab, never auto-detected, shared by the Land Guide and Explain.
- **Strings:** every fixed Hindi and Marathi sentence is in `chatbot/strings.json`. **Not yet reviewed by a native speaker.**
- **PDF:** Devanagari is shaped with HarfBuzz and drawn as vector outlines (`backend/app/devanagari.py`).

## Accessibility
Real buttons and links; labels on icon-only buttons; visible coral focus rings; Escape closes the drawer, popovers and the account menu; the gauge is an image with a text alternative ("Risk score 75 out of 100, red band"); toasts live in an `aria-live` region; the nav is a `<nav>` with a label; pages have one `h1`.

## Public pages (13a-2)
Landing (hero with the live Flow Field, the public check card, three tilted preview cards, stat tiles, four steps with contour lines, role cards, closing call to action), How it works, About, Verify and Login. Page text lives in `src/pages/content.ts`; the step illustrations are original inline SVGs in `src/pages/Illustrations.tsx`. Every live number is from `/public/stats`; invented examples carry a visible "Sample data" label.

## Role pages (13b)
Same components, a different identity per role (see the table above).
- **Citizen, "MY LAND"** (warm coral glow, cream cards dominate, big plain-words text). Tabs: Home, My plots, Verify, Activity, Land Guide. *Home*: a "short story" cream card written by code from the real counts (never by an AI), two stat cards and a "What to do next" list (open the worst red plot first, download a PDF, verify a printed passport, ask the Land Guide); no greeting. *My plots*: one cream card per plot (id, village, area, `BandChip` on cream, score). *Verify*: paste a document id, the web address in a QR code, or a plot id (a plot id opens that passport page); a camera QR scan button appears only in browsers that support `BarcodeDetector`. *Activity*: my own recent actions in plain words.
- **Officer, "OFFICER WORK DESK"** (teal glow, dense glass cards). Tabs: Dashboard, Plots, Map, Conflicts, Construction, Zones, Land Guide; "My activity" is in the account menu. *Dashboard*: six stat cards, "Problems by type" (`BarList`, the 9 checks; the simulated one in lavender with the word "simulated"), a map preview (`MiniMap`, always with the counts written next to it) and the top-10 priority queue with reason chips. *Plots*: a real table with search, a multi-band filter (any combination), a village filter, sortable columns (`aria-sort`) and pages of 15. *Conflicts*: type chips with counts. *Construction*: a dashed lavender "SIMULATED" banner. *Zones*: bars plus a list with a small outline per zone.
- **Admin** sees the officer pages (as "Overview" and the Work desk strip); its own pages are placeholders until 13c.
- **Shared passport page** (`/app/plots/:ulpin`): the same content as the map drawer (`PassportDrawer variant="page"`).
- **"Not for your role"** (`pages/NotForRole.tsx`): a page that belongs to another role shows this friendly page inside the normal shell, never a blank screen or a silent redirect. The server checks the data again.
- **Every data page has the three states in plain words** through one component, `components/Async.tsx`: loading (grey blocks announced to screen readers), an error with a "Try again" button, and an empty state that says why it is empty.
- **Data**: `lib/appData.tsx` fetches the plots, the summary, the conflicts and the rule texts once when the signed-in area opens and shares them, so moving between pages does not run the scoring again. Citizens never request the staff-only lists.
- **Map card**: the passport drawer now docks INSIDE the framed map card (a side panel on a wide screen, a bottom sheet sized from the card on a phone).
- **Code splitting**: every page is a lazy chunk; vendor libraries are split (`react`, `router`, `motion`); the map library loads only on `/app/map`. See HANDOFF for the sizes.
- Coral is used only for primary buttons, the active tab and emphasis words, never for risk; bars that show problems use cream, simulated ones lavender.

## Control Room (13c, admin only)
CONTROL ROOM in indigo, the same components. *Overview* is about the system and the people (not the plot queue, which is the officer's, reachable for an admin as "Dashboard" in the Work desk strip): four `StatusTile`s (an icon and a word: Running, Switched off, Not loaded; never colour alone), people by role, activity in the last 24 hours and 7 days, the model status and the latest activity as a timeline. *Audit log*: a timeline (an icon, who, role, when, what in plain words, the plot) with filters for person, kind of action and time (presets: last 24 hours, 7 days, 30 days, all time) and pages of 20 with "Newer" and "Older". *Users*: rows with the role badge, linked plots, last activity and actions in 30 days; no password or hash. *System*: the status tiles, the model, counts and versions, and a "Check again" button. *Insights*: a note that says "Explanation only" on every state of the page, the 12 signals the model looks at in plain words with their share, and why flagged plots look unusual; scoring stays code-only. Lavender is not used there (it is only for simulated data).

## Polish (13c)
- A "Skip to content" link is the first focusable thing on every page; after a page change the keyboard focus moves to the new page (`<main id="main" tabindex="-1">`).
- Below 1024 px the nav tabs wrap onto a second row inside the pill (`--nav-height` 112px), so the nav never overlaps the page at 768 px.
- The map card is sized so that it fits inside the visible screen on a phone and a tablet (`--map-card-height`), so the bottom sheet's half position is never cut off.
- Filter drop-downs are full width on a phone, so no page scrolls sideways.

## Responsive
- 1440 and wider: nav pill on top (max width 1200), content centred, map card under the header, passport drawer 430px on the right.
- Under 768px: the nav tabs wrap to a second row inside the pill, popovers and the passport drawer become bottom sheets, page gutters are 16px.

## Tests
`npm test` (vitest + Testing Library + jsdom) checks the route guards (a visitor cannot open `/app/*`, a role cannot open another role's pages), the tabs of each role, and the singular "Showing 1 plot". They use no network and no real API.

## Basemaps and attribution
Light = CARTO Positron, Dark (default) = CARTO Dark Matter, Satellite = Esri World Imagery. The keyless endpoints are used unless `VITE_CARTO_KEY` / `VITE_ESRI_KEY` are set. Attribution is always visible on the map. If a basemap fails to load, a toast says so and the map falls back to Dark. See `docs/HANDOFF.md` for the terms risk.
