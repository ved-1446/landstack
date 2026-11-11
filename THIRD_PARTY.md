# Third-party material

LandStack's own code is under the MIT licence (see `LICENSE`). It uses the material below. Nothing here is sold or relicensed.
This file is a good-faith summary made on 11 November 2026 from the package metadata installed in the tested environment, not legal advice.
Transitive packages (the ones our packages depend on) keep their own licences: `frontend/package-lock.json` lists them for the web app.

## Code copied into this repository

### Flow Field (login background): MIT
`frontend/src/features/login/flow-field/flow-field.source.html` is the **Flow Field** shader page from **ThreeUI** (the Community
catalogue), kept byte for byte. The upstream file is `src/shaders/neuform-isolated/sources/flow-field.html` in the public repository
<https://github.com/MengTo/threeui>, whose licence is MIT. We check at run time (in `flowFieldDocument.ts`) that nothing else is
loaded, and strip an analytics tag that the upstream file contains. We do not use ThreeUI's remote thumbnails or its separate Pro catalogue.

What MIT allows here: use, copy, modify, merge, publish, distribute, sublicense and sell, **as long as this notice stays with
the code**. The ThreeUI website also has a Terms of Use page. It could not be read when this was checked (it needs JavaScript),
so it is **unverified**; the MIT licence of the repository file is what we rely on.

```
MIT License

Copyright (c) 2026 Meng To

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Fonts: SIL Open Font License 1.1
The OFL allows use, bundling and modification. The fonts may not be sold on their own, and the reserved font names stay with their authors.

| Font | Where | Copyright holder |
|---|---|---|
| Noto Sans Devanagari | web app (`@fontsource/noto-sans-devanagari`, self-hosted) and the PDF (`backend/app/fonts/`, two static files cut from the upstream variable font; the licence text is `backend/app/fonts/OFL.txt`) | The Noto Project Authors |
| Geist and Geist Mono | web app (`@fontsource/geist`, `@fontsource/geist-mono`, self-hosted) | The Geist Project Authors |
| Instrument Serif | web app (`@fontsource/instrument-serif`, self-hosted) | The Instrument Serif Project Authors |

The PDF's Latin text uses ReportLab's built-in Helvetica and Courier.

## Map data and tiles (used from the internet at run time, not stored in this repository)
| Service | What for | Notes |
|---|---|---|
| OpenStreetMap contributors | map data inside the CARTO basemaps | ODbL. The attribution "© OpenStreetMap contributors © CARTO" is shown on the map. |
| CARTO (Positron and Dark Matter basemaps) | Light and Dark basemaps | Used through a keyless style address that works today but may stop; CARTO has said a free key is needed. Set `VITE_CARTO_KEY` to use one. CARTO's own terms apply (check them before any commercial use). |
| Esri World Imagery | Satellite basemap | Attribution ("Powered by Esri, Maxar, Earthstar Geographics, and the GIS User Community") is shown on the map. Esri's terms apply; for anything beyond a demo use an Esri API key (`VITE_ESRI_KEY`). |

## Land Guide sources
The Land Guide answers from public pages of **Vikaspedia** (C-DAC Hyderabad, Ministry of Electronics and Information Technology,
Government of India) and from `chatbot/glossary.md`, which was written for LandStack. Vikaspedia's terms allow reproduction with clear credit
to the source and exclude third-party material; every answer links its page. The pages used are listed in `chatbot/sources.json`.
The downloaded pages and the chunks made from them stay on the user's machine (git-ignored) because they are other people's text.

## Python packages (`backend/requirements.txt`, exact versions)
| Package | Version | Licence |
|---|---|---|
| argon2-cffi | 25.1.0 | MIT |
| beautifulsoup4 | 4.15.0 | MIT |
| fastapi | 0.162.2 | MIT |
| fonttools | 4.68.0 | MIT |
| httpx | 0.28.1 | BSD-3-Clause |
| pandas | 3.1.1 | BSD-3-Clause |
| psycopg and psycopg-binary | 3.3.8 | LGPL-3.0 (see note) |
| PyJWT | 2.15.1 | MIT |
| pypdf | 7.0.0 | BSD-3-Clause |
| pytest | 9.2.0 | MIT |
| qrcode | 8.2 | BSD |
| rank_bm25 | 0.2.2 | Apache-2.0 |
| reportlab | 5.1.0 | BSD |
| scikit-learn | 1.9.1 | BSD-3-Clause |
| shap | 0.54.1 | MIT |
| shapely | 2.2.0 | BSD-3-Clause |
| slowapi | 0.1.10 | MIT |
| uharfbuzz | 0.57.0 | Apache-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |

The notebook tools in `ml/requirements.txt` (matplotlib, nbformat, nbconvert, ipykernel) are only for exploring the ML and are not needed to run the app.

**Note on psycopg (LGPL-3.0):** LandStack installs it from PyPI as a separate library and does not modify or copy it, which the LGPL allows.
If you ship LandStack inside one bundled program, read the LGPL first.

## Web app packages (`frontend/package.json`, resolved by `package-lock.json`)
| Package | Version | Licence |
|---|---|---|
| react, react-dom | 19.3.1 | MIT |
| maplibre-gl | 6.17.0 | BSD-3-Clause |
| framer-motion | 14.12.0 | MIT |
| react-router | 8.5.1 | MIT |
| lucide-react | 1.71.0 | ISC |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx, tailwind-merge | 2.1.1, 3.7.0 | MIT |
| tailwindcss, @tailwindcss/vite | 4.3.5 | MIT |
| vite, @vitejs/plugin-react | 8.3.7, 6.3.0 | MIT |
| typescript | 7.0.2 | Apache-2.0 |
| vitest, jsdom, @testing-library/react, @testing-library/dom (tests only, never shipped) | 5.1.0, 31.0.0, 16.3.3, 10.4.2 | MIT |
| @types/react, @types/react-dom | 19.3.0 | MIT |
| the four `@fontsource/*` font packages | 5.3.0 | OFL-1.1 |

The lock file holds 199 packages (153 of them are build and test tools that are not shipped to the browser): 132 MIT, 26 Apache-2.0, 12 ISC, 12 MPL-2.0 (build tools only), 5 BSD-3-Clause, 4 OFL-1.1, 4 BSD-2-Clause, 2 0BSD, and one each dual MIT or Apache-2.0 and BlueOak-1.0.0. There is no non-open-source licence in the list.

**GSAP was removed in Phase 13a.** The score gauge now sweeps with a CSS animation and counts up with a small hook, so the "Standard No Charge" licence question no longer applies.

## Development aid, not part of the app
`.agents/skills/design-taste-frontend/` (and `skills-lock.json`) is an AI-coding-agent "skill" (from `Leonxlnx/taste-skill` on GitHub)
that was used as a design reference while building the web app. It is **not** used at run time or in the build, it contains no licence file,
and its licence was **not checked**. It is the owner's decision whether it should stay in the repository.
