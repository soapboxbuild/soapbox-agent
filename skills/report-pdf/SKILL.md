---
name: report-pdf
description: >-
  Export any Soapbox paged HTML report/deck template to a consulting-grade,
  print-paginated PDF. Use when the user asks to download / export / save a
  report or deck as PDF, wants a "PDF version", a print-ready or shareable
  file, or a leave-behind. Works across every template that renders from a
  <script id="report-data"> payload (rsra, decarb, portfolio-analysis,
  esg-profile/esg-fund-deck, crrem, retrofit, delivery-presentation, …).
  Produces US-Letter pages with a big cover header on page 1, a minimized
  running header on pages 2+, a footer with page numbers, and keep-together
  pagination so components never split or overflow.
---

# report-pdf — paged HTML → consulting-grade PDF

Turns a Soapbox report/deck template (client-JS-populated HTML) into a paginated
US-Letter PDF with proper print vocabulary: a **full-bleed cover header on page
1**, a **discreet running header on every subsequent page**, a **footer with
`Page N of M`**, and **keep-together rules so tables/charts/cards never split
across a page break or overflow the sheet**.

## When to use
- "Export / download / save this report as a PDF", "PDF version", "print-ready",
  "leave-behind", "send me the deck as a file".
- After any report render (`fill_report`) when the user wants the PDF, not the
  interactive artifact.

Do **not** use it to author a new template — that's `soapbox-report`. This skill
only paginates an existing template's rendered output.

## How to run

```bash
python3 scripts/export_pdf.py \
  --template <name> \
  --data <path/to/report-data.json> \
  --out <output.pdf> \
  [--title "Client — Report Title"] \
  [--mode auto|report|deck] \
  [--templates-dir <dir>] [--assets-dir <dir>] [--timeout 45000]
```

`--mode` (default `auto`): **report** = continuous doc via Paged.js (hero page 1,
running header 2+, footer, keep-together); **deck** = a flip slide deck exported
one slide per landscape page (full-res screenshots → `img2pdf`, needs
`pip install img2pdf`). `auto` detects a deck by its `#deck`/`.slide` structure.

- `--template` — the template folder name under `templates/` (e.g. `decarb`,
  `rsra`, `portfolio-analysis`, `esg-fund-deck`).
- `--data` — the same JSON object you passed to `fill_report` (the render
  payload). For a deck whose content is baked into the template, pass `{}`.
- `--title` — optional; sets the cover/running-header title.

Example (verified): `--template decarb --data templates/decarb/example-data.json`
→ a 10-page US-Letter PDF (~290 KB), hero cover, running header + `Page N of M`
footer from page 2, the value-creation waterfall and cashflow tables intact.

The script prints a JSON result: `{"ok": true, "out": …, "pages": N, "bytes": …}`.

## What it does (pipeline)
1. Injects the data into the template's `<script id="report-data">` block and
   serves it from a local HTTP server (templates load their own CDN-free assets).
2. Runs it in headless Chromium so the template's `populateReport()` fills the
   DOM; waits for the `window.__reportReady` sentinel (fallback: a populated node).
3. Applies a **print transform**: opens every `<details>`, un-toggles chart
   legend "off" states, derives the running header/footer from the report's own
   title/meta, and relocates multi-state `<select>` views into a print appendix.
4. Paginates with **Paged.js** consuming `assets/print.css` (US-Letter `@page`,
   `@page:first` full-bleed hero, running header via `position: running()`,
   `@bottom-*` footer + `counter(page)/counter(pages)`, `break-inside: avoid`
   on cards/charts/figures, repeated `thead` on long tables, `orphans/widows`).
5. `page.pdf(preferCSSPageSize, printBackground)` → the final PDF.

## Requirements
- Python `playwright` + Chromium: `python3 -m playwright install chromium`
  (the managed-agent worker image already ships this; on a bare box run it once).

## Header / footer / overflow — how the spec is met
- **Big header, page 1 only:** `@page:first` drops the top margin and hides the
  running header so the template's own cover/hero bleeds to the top edge.
- **Minimized header, page 2+:** the report title is emitted as a
  `position: running()` element shown in the `@top-left`/`@top-right` margin box.
- **Footer everywhere:** confidentiality/meta at `@bottom-left`, `Page N of M`
  at `@bottom-right`.
- **Never overflow / split:** `break-inside: avoid` on sections, KPI tiles,
  charts, figures, and metric rows; tables taller than a page split *with their
  header repeated*; headings use `break-after: avoid`.

## Notes & caveats
- **Keep-together vs. whitespace:** because charts/cards never split, a block
  that doesn't fit in the remaining space moves to the next page, which can
  leave whitespace above it (a section heading may sit a little above its chart).
  This is the correct trade-off for "never overflow" — the content is intact on
  the following page, never clipped.
- **Charts must be SVG/DOM at populate time.** SVG/HTML charts (the Soapbox
  templates' default) render fine. A `<canvas>` or a chart drawn on
  `IntersectionObserver`/scroll may be blank in print — force it to draw during
  `populateReport()` (don't lazy-render), or extend `--timeout` / the settle wait.
- **Missing glyphs:** icon-font glyphs the print fonts lack render as tofu (□).
  Prefer inline SVG icons in templates destined for PDF.
- **Fonts:** templates link the Google Fonts they use; the PDF renderer has
  network, so webfonts load (unlike the CSP-sandboxed in-app artifact viewer).
