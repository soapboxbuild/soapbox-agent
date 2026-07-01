# RSRA Visual Enhancements & Cross-Report Consistency

**Date:** 2026-07-01  
**Scope:** `~/soapbox-agent/skills/` (3 files) + `~/soapbox-report-skill/` cleanup  
**Status:** Approved

---

## Problem

1. The RSRA report is text-only — five sections have data that communicates better visually.
2. The three live report skills (RSRA, Portfolio Analysis, Sustainability Passport) each maintain their own CSS and typography rules with no shared reference, creating drift risk.
3. `~/soapbox-report-skill/` contains dead Paged.js templates and pipeline agents that are no longer used and contradict the current monolithic HTML approach.

---

## Architecture

All reports are **monolithic, self-contained HTML artifacts** generated directly by Claude from a skill. Key rules, consistent across all three skills:

- Font: `-apple-system, 'Helvetica Neue', Arial, sans-serif` — zero exceptions
- Colors: navy `#12253A` · green `#4CAF82` · muted `#64748B` · page bg `#F8F9FB`
- Section chrome: `.section-label` (9px uppercase green) → `.section-title` (18px bold navy, bottom border)
- Charts: **inline SVG only** — no external libraries, no CDN, no Canvas
- Hard prohibitions: Paged.js · Georgia · any serif · web font `@import` · external CDN references

Each skill gets a `## Design System` section codifying these rules so Claude can't drift on subsequent runs.

---

## Part 1: RSRA Visual Enhancements

Five new inline SVG visualizations added to `~/soapbox-agent/skills/rsra/SKILL.md`.

### 1A — Energy & Emissions Profile: BPD Peer Histogram

**Location:** Section 3, inside the existing `#emissions-benchmark-chart` div (already present, currently `display:none`).

**What it shows:** EUI distribution of BPD peer buildings (same asset class + climate zone). Not the asset's own EUI.

**Overlays:**
- Dashed navy vertical line: peer median, labeled
- Solid green vertical line: 2030 CRREM target for that asset type, labeled

**Data source:** BPD MCP `get_statistics()` called during Phase 2C. If BPD returns no data, div stays hidden — no fallback fabrication.

**Circular benchmarking rule enforced:** If the asset's only EUI is a CBECS estimate, no asset marker is placed on the chart. The chart shows the peer landscape, not a claim about this asset.

**SVG approach:** Histogram bars as `<rect>` elements. X-axis: EUI range (kBtu/sqft/yr). Y-axis: building count. Two `<line>` overlays with `<text>` labels. All coordinates computed by Claude from the BPD bucket data.

### 1B — Climate Hazard Exposure: Radar Chart

**Location:** Section 4, inserted above the existing hazard table (table stays for detail).

**Spokes:** One per hazard row Claude writes. Typically: Extreme Heat · Flood · Wind/Hail · Wildfire · Water Stress · Grid Reliability (or local equivalents).

**Rings:** Three concentric hexagons labeled Low / Moderate / High.

**Polygon:** Filled with `#4CAF82` at 40% opacity. Stroke `#12253A`. Each hazard maps to 1 (Low), 2 (Moderate), or 3 (High) based on the risk level Claude assigned.

**SVG approach:** Pure geometry — regular polygon ring coordinates computed from center + radius. Spoke labels positioned at spoke tips with small offset. No JS required; all computed at generation time.

### 1C — GHG Scoping: Owner Boundary Donut

**Location:** Section 5, floated right alongside the existing Scope 1/2/3 table.

**Slices:**
- Scope 1: navy `#12253A` (typically zero — shown as a thin arc or omitted if 0)
- Scope 2: green `#4CAF82` (owner-paid electricity)
- Scope 3: muted grey `#CBD5E1` with dashed stroke — labeled "excluded from owner boundary"

**Center label:** Owner boundary total in tCO₂e.

**SVG approach:** Donut via `<path>` arc commands. Claude computes arc angles from the tCO₂e values in the GHG table it just wrote.

### 1D — Livability & Reputation: Status Dots

**Location:** Section 7, prepended to each `<dd>` value in `#qol-dl`.

**Dot colors:**
- Green `#4CAF82`: score ≥ 70, or explicit "strong" / "very walkable" narrative
- Yellow `#F59E0B`: score 40–69, or "moderate" / "bikeable" narrative  
- Red `#EF4444`: score < 40, or flagged concern
- Grey `#94A3B8`: no data / not scored / not applicable

**Implementation:** A `<span>` with `display:inline-block; width:8px; height:8px; border-radius:50%; background:[color]; margin-right:6px; vertical-align:middle` inserted before the text value. Claude assigns color based on the score or narrative it wrote.

### 1E — UN SDG Alignment: Official Colored Tiles

**Location:** Section 10, replacing the plain text SDG column in the `#sdg-table`.

**What's shown:** Each SDG gets its official colored square tile — the recognized UN icon colors and SDG number, rendered as a compact SVG badge (40×40px) embedded inline.

**Implementation:** The SKILL.md includes a data block of `<svg>` tiles for all 17 SDGs, each with the official background color, white SDG number, and abbreviated title. Claude picks only the relevant SDGs and inserts the corresponding tiles. No external image URLs.

**Official SDG colors (subset most common in real estate):**
- SDG 6 (Clean Water): `#26BDE2`
- SDG 7 (Clean Energy): `#FCC30B`
- SDG 9 (Infrastructure): `#FD6925`
- SDG 11 (Sustainable Cities): `#FD9D24`
- SDG 12 (Responsible Consumption): `#BF8B2E`
- SDG 13 (Climate Action): `#3F7E44`
- SDG 15 (Life on Land): `#56C02B`
- SDG 17 (Partnerships): `#19486A`

Full set of 17 included in skill for completeness.

---

## Part 2: Cross-Report Design System Consistency

### Files in scope

| File | Current state | Change |
|------|--------------|--------|
| `skills/rsra/SKILL.md` | Modern HTML, explicit Paged.js prohibition | Add `## Design System` block + 5 visualizations |
| `skills/portfolio-analysis/SKILL.md` | Modern HTML, already has inline SVG charts | Add `## Design System` block, audit CSS for drift |
| `skills/sustainability-passport/SKILL.md` | Modern HTML, no charts yet | Add `## Design System` block, audit CSS for drift |

### What the `## Design System` block contains

Each skill gets an identical block:
1. Color palette with hex values
2. Typography rule (font stack, zero serif)
3. Section chrome pattern (label → title)
4. Chart rule (inline SVG only, how to handle no-data)
5. Hard prohibitions list
6. File output rules (two-phase artifact, identical file path, save_file after Phase 2 only)

This block is the single source of truth for style. If a future skill needs to generate a report, it references this pattern.

---

## Part 3: Dead Code Removal

### `~/soapbox-report-skill/` — old pipeline system

**Delete:**
```
~/soapbox-report-skill/templates/      (all Paged.js layout.html files)
~/soapbox-report-skill/agents/         (old pipeline workflow agents)
```

**Replace content of:**
```
~/soapbox-report-skill/skills/soapbox-report/SKILL.md
```
with a single deprecation notice pointing to the live skills in `~/soapbox-agent/skills/`.

**Keep:**
```
~/soapbox-report-skill/plugin.json     (registry tombstone — don't break plugin lookup)
~/soapbox-report-skill/README.md       (update to say deprecated)
```

### `~/rapid-sustainability-risk-skill/`

This is a separate plugin repo. Its `skills/rapid-sustainability-risk/SKILL.md` does not reference Paged.js (confirmed). No changes needed unless a future audit finds drift; out of scope for this work.

---

## What is NOT in scope

- GRESB submission report, BPS compliance, CRREM assessment, decarb roadmap — these Paged.js templates are being deleted, not migrated. If these report types are needed in future, they will be built as new monolithic HTML skills following the design system.
- PPTX/PDF export routes in `platform-web` — unaffected.
- Any database schema changes.

---

## Files changed summary

```
~/soapbox-agent/skills/rsra/SKILL.md                    MODIFIED (visuals + design system block)
~/soapbox-agent/skills/portfolio-analysis/SKILL.md      MODIFIED (design system block + audit)
~/soapbox-agent/skills/sustainability-passport/SKILL.md MODIFIED (design system block + audit)
~/soapbox-agent/scripts/build_xlsx.py                   MODIFIED (remove --templates-dir reference)
~/soapbox-report-skill/templates/                       DELETED
~/soapbox-report-skill/agents/                          DELETED
~/soapbox-report-skill/skills/soapbox-report/SKILL.md   REPLACED with deprecation notice
~/soapbox-report-skill/README.md                        UPDATED
```
