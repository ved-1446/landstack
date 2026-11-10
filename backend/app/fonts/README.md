# Fonts for the printable passport (Phase 11b)

`NotoSansDevanagari-Regular.ttf` and `NotoSansDevanagari-Bold.ttf` are **Noto Sans Devanagari**,
Copyright 2022 The Noto Project Authors, licensed under the **SIL Open Font License 1.1** (`OFL.txt` in this folder).
The licence allows bundling, use and modification; the fonts are not sold on their own.

They are used only by `backend/app/devanagari.py`, to draw Hindi and Marathi text in the PDF (the PDF stays English otherwise).

## How these two files were made (so you can remake them)
The source is the upstream variable font from <https://github.com/google/fonts/tree/main/ofl/notosansdevanagari>
(`NotoSansDevanagari[wdth,wght].ttf`, about 640 KB). With `fontTools` (already a requirement):

1. cut two static instances: `fontTools.varLib.instancer.instantiateVariableFont(font, {"wght": 400 or 700, "wdth": 100})`;
2. subset each with `fontTools.subset` to the Devanagari block (U+0900 to U+097F), the joiners U+200C and U+200D, the dotted
   circle U+25CC, no-break space and a few punctuation marks, **keeping every layout feature** (`layout_features = ["*"]`):
   the shaper needs the GSUB and GPOS tables to build conjuncts and place vowel signs. Glyph names are kept (the tests read them).

Result: about 170 KB each. Plain ReportLab cannot shape Devanagari, so `devanagari.py` shapes with HarfBuzz (`uharfbuzz`) and
draws each glyph's outline as a vector path, filled with the non-zero rule.

The web app loads the same family from the self-hosted npm package `@fontsource/noto-sans-devanagari` (also OFL 1.1).
