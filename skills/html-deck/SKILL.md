---
name: html-deck
description: >
  Build presentation/pitch slides as adaptable, visual-first HTML pages in the
  user's portfolio aesthetic (dark, Fraunces/DM Mono/Bebas, CSS-variable themes),
  then export each to a zero-loss PNG sized for a perfect Google Slides paste-in,
  or host the deck live via the here-now skill. Use when the user wants slides, a
  deck, a pitch deck, a presentation, or HTML slides — or to turn a project into a
  screenshot-ready deck. Ships icon + brand-logo libraries, theme presets, big
  image-dominant layouts, and a pitch playbook with anti-fabrication guardrails.
license: MIT
---

# html-deck

## Scoped creative contract

This contract applies only to deck work: honor `deck-standard`, search the
local asset library and suitable stock before generating media, use image
generation for genuinely envisioned or unavailable art, inspect the rendered
slides, and hand off the useful deck formats together. It is intentionally not
an always-on workspace prompt.

Turns content into a deck of **fixed 16:9 HTML slides** → **lossless 2560×1440 PNGs** (insert into a 16:9 Google Slide, fills with zero crop) or a **live deck** (with playing video) hosted on here.now. Adapts the user's site style; it does **not** force one template.

Engine beside this file: `deck.css` (canvas + theme + zones + layouts), `assets/` (icons, logos, themes), `scripts/{new-deck,export,icon}.mjs`. Rendering uses headless Chrome via `puppeteer-core`. **Run `export.mjs`/`icon.mjs fetch` with the Bash sandbox disabled** (network for fonts/logos).

## Before building: content quality
**Read `PITCH.md` first.** It defines the slide order per deck type (investor / product / showcase) and the **anti-BS guardrails**: ground every claim in the source, never invent traction/market/team/metrics, drop standard slides that have no real data, and use descriptive placeholders instead of faking assets. Decks are read in ~2.5 min: one idea per slide, **show > tell, 10–15 slides max, images big.**

## Workflow
1. **Scaffold:** `node <skill>/scripts/new-deck.mjs <deckDir> "Title" [--theme midnight|ocean|amber|mono|light]` → deck.css, theme.css, `assets/` (icons+logos copied in), visual-first `slides/<id>/slide.html`+`media/`, `index.html` (live), deck.json, README.
2. **Extract → outline → build** per PITCH.md. Replace template headlines/numbers with real, sourced content; delete slides you can't ground.
3. **Media (fixed convention):** per-slide assets in `slides/<id>/media/`, referenced as `media/<file>` (+ `onerror="this.remove()"`). Shared assets referenced as `../../assets/icons/<n>.svg` / `../../assets/logos/<slug>.svg`.
4. **Export:** `node <skill>/scripts/export.mjs <deckDir>` (sandbox OFF) → `build/export/*.png`. Flags `--scale 2`, `--only 03`.
5. **To PowerPoint / Google Slides:** `py <skill>/scripts/to-pptx.py <deckDir>` → `build/<deck>.pptx` (one full-bleed 16:9 image per slide; pixel-perfect, text baked in). The `.pptx` imports into **Google Slides** via Drive → Open as Google Slides. (True Slides-API push would need the user's Google OAuth.)
6. **Host:** publish the deck folder via the **here-now** skill (default host) — `index.html` is the live deck.

## Layouts (visual-first; see deck.css)
- Big media: `.feature` (image ~65%), `.slide.image-hero` (full-bleed cover + overlay title), `.slide.tight` + `.capbar` (edge-to-edge single visual).
- **Architecture**: `.flow` of `.node` boxes (auto arrows between) + a `.substrate` bar for the data/store layer. Build the diagram in HTML from real components; one architecture page per deck.
- Structure: `.split`, `.cards.c2/3/4`, `.stats`+`.stat`, `.bullets` (CSS-diamond list), `.logo-row`(`.mono`), `.quote`.
- Type: `.eyebrow`, `.kicker`, `h1/h2.title` (use `<em>` for gradient accent), `.sub`, `.lead`, `.tagline`. Backgrounds: `bg-grid`, `bg-aurora`.

## Media zones — reserve space + say what goes there
```html
<figure class="zone r-16x9" data-label="media/screen.png"
        data-desc="The product in action — large clean screenshot of the main UI">
  <img src="media/screen.png" alt="" onerror="this.remove()">
</figure>
```
Ratios: `.zone.r-16x9 / .r-9x16 / .r-1x1 / .r-4x3 / .fill` (full-bleed). `data-desc` = the real asset to drop in (shows as a clear placeholder until the file exists). Video slides: `media/poster.png` (PNG still) + `media/clip.mp4` (plays live).

## Icons & logos
- **UI icons** (Lucide, ~65 bundled): `<img class="ic" src="../../assets/icons/zap.svg">` (white via filter; `.ic.ink` for dark-on-light; size via width/height or `.ic.lg/.xl`). Card icons: `<img class="card-ic" src="...">`. `.bullets` lists use a CSS diamond marker (no icon needed). **Never use CSS `mask` for icons** — external SVG masks are blocked under `file://` and vanish in PNG export; `<img>` is reliable in both export and hosting.
- **Brand/tech logos** (Simple Icons, ~27 bundled incl. openai/python/react/docker/huggingface): `<img class="logo" src="../../assets/logos/<slug>.svg">`; `.logo-row.mono` forces uniform white on dark. Fetch any brand on demand: `node scripts/icon.mjs fetch <slug> <deck>/assets/logos` (sandbox OFF). List bundled: `icon.mjs list ui|logos`.

## Themes
`--theme` presets in `assets/themes/`: `midnight` (purple/cyan, default), `ocean` (teal), `amber` (warm), `mono` (terminal green), `light` (corporate). Or edit `theme.css` vars per deck.
