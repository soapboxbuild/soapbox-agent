# RSRA Visuals & Report Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 5 inline SVG visualizations to the RSRA skill, establish a shared Design System block across all three report skills, and delete the dead soapbox-report-skill Paged.js pipeline.

**Architecture:** All changes are edits to SKILL.md markdown files in `~/soapbox-agent/skills/`. No runtime code changes. Each skill gets a `## Design System` reference block inserted near the top (after the preamble, before Phase 1). The 5 RSRA visualizations are SVG templates inserted into the Phase 2 HTML template section of `rsra/SKILL.md` — Claude reads them and fills in the values at generation time. Dead code is deleted from `~/soapbox-report-skill/`.

**Tech Stack:** Markdown skill files · inline SVG (no libraries) · git

## Global Constraints

- All charts: inline SVG only — zero external charting libraries, zero CDN, zero `<canvas>`
- Font everywhere: `-apple-system,'Helvetica Neue',Arial,sans-serif` — zero exceptions
- Colors: navy `#12253A` · green `#4CAF82` · muted `#64748B` · page bg `#F8F9FB` · warn `#F59E0B` · danger `#EF4444`
- Hard prohibitions in all skills: Paged.js · Georgia · serif · web font `@import` · external CDN
- Two-phase artifact pattern: identical file path for Phase 1 skeleton and Phase 2 full report
- Numeric precision: 2 significant figures on all calculated values
- All external links: `target="_blank" rel="noopener noreferrer"`
- Repo for skill files: `~/soapbox-agent/` (commit here)
- Repo for dead code: `~/soapbox-report-skill/` (commit here separately)

---

## File Map

| File | Action |
|------|--------|
| `~/soapbox-agent/skills/rsra/SKILL.md` | Add `## Design System` block + 5 SVG visualization templates |
| `~/soapbox-agent/skills/portfolio-analysis/SKILL.md` | Add `## Design System` block, verify CSS matches standard |
| `~/soapbox-agent/skills/sustainability-passport/SKILL.md` | Add `## Design System` block, add explicit CSS to Phase 2 section |
| `~/soapbox-agent/scripts/build_xlsx.py` | Remove dead `--templates-dir` CLI arg and reference |
| `~/soapbox-report-skill/templates/` | Delete entire directory |
| `~/soapbox-report-skill/agents/` | Delete entire directory |
| `~/soapbox-report-skill/skills/soapbox-report/SKILL.md` | Replace with deprecation notice |
| `~/soapbox-report-skill/README.md` | Update to say deprecated |

---

## Task 1: Shared Design System Block

Add an identical `## Design System` section to all three skills, and add explicit CSS to sustainability-passport Phase 2 (it currently only references RSRA by prose description with no inline CSS block).

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`
- Modify: `~/soapbox-agent/skills/portfolio-analysis/SKILL.md`
- Modify: `~/soapbox-agent/skills/sustainability-passport/SKILL.md`

**Interfaces:**
- Produces: canonical `## Design System` block used by Tasks 2–6 as style reference

- [ ] **Step 1: Read the opening of each skill to find insertion point**

```bash
head -30 ~/soapbox-agent/skills/rsra/SKILL.md
head -30 ~/soapbox-agent/skills/portfolio-analysis/SKILL.md
head -30 ~/soapbox-agent/skills/sustainability-passport/SKILL.md
```

Find the line after the preamble/trigger section and before `## Phase 1` (or equivalent first phase). Insert the Design System block there.

- [ ] **Step 2: Insert Design System block into rsra/SKILL.md**

Find the line `## Phase 1: Document Triage` (line ~41) and insert the block immediately before it:

```markdown
## Design System

All RSRA HTML output must conform to these rules. Claude must apply them on every run — never drift.

**Colors**
- Navy: `#12253A` — headers, section titles, strong text
- Green: `#4CAF82` — eyebrows, accents, positive signals, chart fills
- Muted: `#64748B` — secondary text, axis labels
- Page bg: `#F8F9FB`
- Section bg: `#fff`
- Border: `#E2E8F0`
- Warn: `#F59E0B` · Danger: `#EF4444`

**Typography**
- Font stack everywhere: `-apple-system,'Helvetica Neue',Arial,sans-serif`
- Zero `Georgia`, zero `serif`, zero `@import`, zero web fonts
- Section label: 9px, weight 600, `letter-spacing:.15em`, `text-transform:uppercase`, color `#1F6B45`
- Section title: 18px, weight 700, color `#12253A`, `border-bottom:1.5px solid #12253A`, `padding-bottom:8px`

**Section chrome pattern**
```html
<div class="section">
  <div class="section-label">EYEBROW LABEL</div>
  <h2 class="section-title">Section Title</h2>
  <!-- content -->
</div>
```

**Charts — inline SVG only**
- Zero external charting libraries (no Chart.js, D3, Plotly, etc.)
- Zero `<canvas>` elements
- Zero CDN `<script>` tags
- All SVG coordinates computed at generation time from the data being reported
- If data is unavailable for a chart, omit the chart entirely — no placeholder SVG

**Hard prohibitions**
- `Paged.js` — never reference or import
- `Georgia` or any serif font
- Any `@import url(...)` for fonts
- Any `<link rel="stylesheet">` or `<script src="...">` pointing to an external host
- External `<img src="https://...">` — all images must be inline SVG or data URIs

**Artifact output rules**
- Two-phase artifact: Phase 1 = loading skeleton, Phase 2 = full report
- Both phases use the **identical** file path — one artifact, updated in place
- Never save the Phase 1 skeleton to asset documents — only the completed Phase 2 report
- Numeric precision: 2 significant figures (`$1.4M` not `$1,427,000`; `42 kgCO₂e` not `41.7`)
- Mark all benchmark-derived estimates inline with `(est.)`

```

- [ ] **Step 3: Insert identical Design System block into portfolio-analysis/SKILL.md**

Find the line `## Step 0: Resolve Run Configuration` (line ~32) and insert the block immediately before it. Use the exact same markdown as Step 2.

- [ ] **Step 4: Insert identical Design System block into sustainability-passport/SKILL.md**

Find the line `## Step 1: Data Inventory & Gap Assessment` (line ~32) and insert the block immediately before it. Use the exact same markdown as Step 2.

- [ ] **Step 5: Add explicit CSS block to sustainability-passport Phase 2**

The sustainability-passport Phase 2 section (around line 535 after insertion) currently says *"Use the same consulting aesthetic as the RSRA loading skeleton: navy `#12253A` header..."* with no inline CSS. Add the full CSS block immediately after that prose sentence:

```markdown
The Phase 2 full passport uses this CSS (identical to RSRA):

```css
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;background:#F8F9FB;color:#1A1A2E}
.report{max-width:860px;margin:0 auto;padding:40px 0 80px}
.doc-header{background:#12253A;color:#fff;padding:32px 40px 0}
.doc-header-eyebrow{font-size:8px;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#4CAF82;margin-bottom:8px}
.doc-header-property-name{font-size:28px;font-weight:700;margin:8px 0 4px;line-height:1.2}
.doc-header-address{font-size:13px;font-weight:300;color:rgba(255,255,255,.65);margin-bottom:24px}
.doc-header-meta-strip{background:#1A3550;padding:8px 40px;display:flex;justify-content:space-between;font-size:11px;color:rgba(255,255,255,.5)}
.meta-bar{display:flex;gap:32px;padding:14px 40px;background:#F1F4F8;border-top:1px solid #CBD5E1}
.meta-item{display:flex;flex-direction:column;gap:2px}
.meta-label{font-size:9px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B}
.section{padding:32px 40px;background:#fff;margin-bottom:2px}
.section-label{font-size:9px;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#1F6B45;margin-bottom:4px}
.section-title{font-size:18px;font-weight:700;color:#12253A;border-bottom:1.5px solid #12253A;padding-bottom:8px;margin-bottom:16px}
.profile-dl{display:grid;gap:0}
.profile-row{display:grid;grid-template-columns:160px 1fr;gap:16px;padding:10px 0;border-bottom:1px solid #F1F4F8}
.profile-dt{font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.04em;padding-top:2px}
.profile-dd{font-size:13px;line-height:1.6;color:#334155}
table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
th{background:#F1F4F8;text-align:left;padding:8px 12px;font-weight:600;border:1px solid #E2E8F0;font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:#475569}
td{padding:8px 12px;border:1px solid #E2E8F0;vertical-align:top}
tr:nth-child(even) td{background:#FAFBFC}
.risk-high{color:#991B1B;font-weight:600}
.risk-moderate{color:#92400E;font-weight:600}
.risk-low{color:#065F46;font-weight:600}
```
```

- [ ] **Step 6: Verify no CSS drift in portfolio-analysis**

Check that portfolio-analysis uses the same color values. The skill uses `.port-name` and `.kpi-bar` (different class names for portfolio-specific elements) — that is acceptable. Verify that `#12253A`, `#4CAF82`, `#F8F9FB` appear and no `Georgia`/`serif` is present:

```bash
grep -n "Georgia\|serif\|Paged\|CDN\|external" ~/soapbox-agent/skills/portfolio-analysis/SKILL.md | grep -v "zero\|no \|prohibit\|never"
```

Expected: no results. If any appear, remove them.

- [ ] **Step 7: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md skills/portfolio-analysis/SKILL.md skills/sustainability-passport/SKILL.md
git commit -m "feat(skills): add shared Design System block to all report skills

Codifies canonical colors, typography, SVG-only chart rule, and hard
prohibitions in a ## Design System section at the top of each skill.
Also adds explicit CSS block to sustainability-passport Phase 2 which
previously only referenced the RSRA aesthetic by prose description.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: RSRA — BPD Peer Histogram (Energy & Emissions)

Add an SVG histogram template to the RSRA skill. The existing `#emissions-benchmark-chart` div in the Phase 2 HTML is already present but `display:none`. This task adds the template Claude uses to populate it.

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`

**Interfaces:**
- Consumes: BPD MCP `get_statistics()` response from Phase 2C (already documented in skill)
- Produces: populated `#emissions-benchmark-chart` div with inline SVG histogram

- [ ] **Step 1: Read the Phase 2C BPD section and the Phase 2 HTML template section**

```bash
grep -n "BPD\|2C\|benchmark-chart\|emissions-benchmark" ~/soapbox-agent/skills/rsra/SKILL.md
```

Find: (a) where Phase 2C BPD instructions end, (b) where the `#emissions-benchmark-chart` div is in the HTML template.

- [ ] **Step 2: Add histogram data instruction to Phase 2C**

After the existing BPD `get_statistics()` call instruction, add:

```markdown
**Histogram data for chart:** From the `get_statistics()` response, extract:
- `buckets`: array of `{eui_min, eui_max, count}` objects (kBtu/sqft/yr)
- `median_eui`: peer median (kBtu/sqft/yr)
- `target_2030_eui`: CRREM 2030 target for this asset type and climate zone

If `get_statistics()` returns no bucket data, set `bpd_chart_available = false` and skip the histogram. Do NOT estimate or fabricate bucket values.
```

- [ ] **Step 3: Add histogram SVG template to the Phase 2 HTML section**

Find the comment `<!-- Benchmark chart — hidden until JS populates it -->` in the HTML template (inside the emissions section). Replace the entire `#emissions-benchmark-chart` div with this template, which Claude fills in at generation time:

```markdown
**Histogram SVG template** (insert inside `.emissions-card` when `bpd_chart_available = true`):

Replace the hidden `<div id="emissions-benchmark-chart" style="display:none">` with:

```html
<div style="margin-top:20px">
  <div style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B;margin-bottom:8px">
    Peer EUI Distribution — [ASSET CLASS] ([CLIMATE ZONE]) · [N] buildings
  </div>
  <svg viewBox="0 0 560 160" width="100%" style="display:block;overflow:visible" aria-label="EUI distribution histogram">
    <!-- Y-axis label -->
    <text x="8" y="80" font-size="9" fill="#94A3B8" text-anchor="middle" transform="rotate(-90,8,80)"># Buildings</text>
    <!-- Bars: one <rect> per bucket. Claude computes x, width, height from bucket data.
         Chart area: x=28 to x=548 (width=520), y=10 to y=130 (height=120).
         Bar x = 28 + (bucket_index / total_buckets) * 520
         Bar width = 520 / total_buckets - 1
         Bar height = (count / max_count) * 120
         Bar y = 130 - bar_height -->
    [BARS — one <rect> per bucket, fill="#CBD5E1", rx="1"]

    <!-- X-axis line -->
    <line x1="28" y1="130" x2="548" y2="130" stroke="#E2E8F0" stroke-width="1"/>

    <!-- X-axis labels: min, midpoint, max EUI values -->
    <text x="28" y="145" font-size="9" fill="#94A3B8" text-anchor="middle">[MIN]</text>
    <text x="288" y="145" font-size="9" fill="#94A3B8" text-anchor="middle">[MID] kBtu/SF/yr</text>
    <text x="548" y="145" font-size="9" fill="#94A3B8" text-anchor="middle">[MAX]</text>

    <!-- Median line: x = 28 + ((median_eui - min_eui) / (max_eui - min_eui)) * 520 -->
    <line x1="[MEDIAN_X]" y1="10" x2="[MEDIAN_X]" y2="130"
          stroke="#12253A" stroke-width="1.5" stroke-dasharray="4,3"/>
    <text x="[MEDIAN_X]" y="8" font-size="9" fill="#12253A" text-anchor="middle" font-weight="600">
      Median [MEDIAN_VAL]
    </text>

    <!-- 2030 target line: x = 28 + ((target_eui - min_eui) / (max_eui - min_eui)) * 520 -->
    <line x1="[TARGET_X]" y1="10" x2="[TARGET_X]" y2="130"
          stroke="#4CAF82" stroke-width="1.5"/>
    <text x="[TARGET_X]" y="8" font-size="9" fill="#1F6B45" text-anchor="middle" font-weight="600">
      2030 target [TARGET_VAL]
    </text>
  </svg>
  <div style="font-size:11px;color:#94A3B8;margin-top:4px">
    Source: Lawrence Berkeley National Lab Building Performance Database · [YEAR] release
  </div>
</div>
```

**Circular benchmarking rule:** Never place an asset-specific marker on this chart if the asset EUI is a CBECS estimate. The chart shows the peer landscape only.
```

- [ ] **Step 4: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md
git commit -m "feat(rsra): add BPD peer histogram to Energy & Emissions section

Populates the existing #emissions-benchmark-chart div with an inline SVG
histogram. Claude fills bucket bars, median line, and 2030 CRREM target
line from BPD get_statistics() data. Enforces circular benchmarking rule.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: RSRA — Climate Hazard Radar Chart

Add a radar/spider chart above the existing hazard table. Six spokes, three rings (Low / Moderate / High).

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`

**Interfaces:**
- Consumes: hazard risk levels already written by Claude into `#physical-risk-table`
- Produces: SVG radar chart inserted before the table in the Physical Climate Risk section

- [ ] **Step 1: Find the Physical Climate Risk section in the Phase 2 HTML template**

```bash
grep -n "physical-risk\|Climate Hazard\|PHYSICAL\|hazard" ~/soapbox-agent/skills/rsra/SKILL.md | head -15
```

- [ ] **Step 2: Add radar chart template to the skill**

In the SKILL.md, find the `<!-- 4. PHYSICAL CLIMATE RISK -->` section comment and add the radar chart template instruction immediately after the `<h2>` line and before the `<table>` instruction:

```markdown
**Radar chart** (insert before the hazard table):

Map each hazard to a value: Low=1, Moderate=2, High=3.

With N hazards evenly spaced, spoke angle for hazard i: `θ_i = (2π/N)*i - π/2` (start from top).
Point coordinates at value v: `x = cx + (v/3)*r*cos(θ_i)`, `y = cy + (v/3)*r*sin(θ_i)`
Use: cx=140, cy=140, r=110 (outer ring radius for High).

```html
<svg viewBox="0 0 420 280" width="100%" style="display:block;margin-bottom:16px" aria-label="Climate hazard radar chart">

  <!-- Ring labels -->
  <text x="144" y="138" font-size="8" fill="#94A3B8">Low</text>
  <text x="144" y="102" font-size="8" fill="#94A3B8">Moderate</text>
  <text x="144" y="32" font-size="8" fill="#94A3B8">High</text>

  <!-- Low ring (r=36.7): polygon connecting all Low points -->
  <polygon points="[LOW_RING_POINTS]"
    fill="none" stroke="#E2E8F0" stroke-width="1"/>
  <!-- Moderate ring (r=73.3) -->
  <polygon points="[MED_RING_POINTS]"
    fill="none" stroke="#E2E8F0" stroke-width="1"/>
  <!-- High ring (r=110) -->
  <polygon points="[HIGH_RING_POINTS]"
    fill="none" stroke="#E2E8F0" stroke-width="1"/>

  <!-- Spokes: one line per hazard from center to High ring -->
  [SPOKES — one <line x1="140" y1="140" x2="[spoke_x]" y2="[spoke_y]" stroke="#F1F4F8" stroke-width="1"/> per hazard]

  <!-- Data polygon: connect all hazard data points -->
  <polygon points="[DATA_POINTS]"
    fill="#4CAF82" fill-opacity="0.35" stroke="#4CAF82" stroke-width="2"/>

  <!-- Data point dots -->
  [DATA_DOTS — one <circle cx="[x]" cy="[y]" r="4" fill="#12253A"/> per hazard]

  <!-- Hazard labels at spoke tips (High ring + 18px offset) -->
  [LABELS — one <text> per hazard, font-size="10", fill="#475569", text-anchor computed from angle]

</svg>
```

**Computing ring polygon points** (example for 6 hazards):
- Angles (6 spokes, start top): -90°, -30°, 30°, 90°, 150°, 210° → in radians
- Low ring point i: `x=140+36.7*cos(θ_i)`, `y=140+36.7*sin(θ_i)`
- Moderate ring point i: `x=140+73.3*cos(θ_i)`, `y=140+73.3*sin(θ_i)`
- High ring point i: `x=140+110*cos(θ_i)`, `y=140+110*sin(θ_i)`
- Data point i at value v: `x=140+(v/3*110)*cos(θ_i)`, `y=140+(v/3*110)*sin(θ_i)`

Label offset: position label at `x=140+128*cos(θ_i)`, `y=140+128*sin(θ_i)`, then adjust `text-anchor` based on angle quadrant (middle if top/bottom, start if right, end if left).

Adjust N spokes to match the actual number of hazards written in the table.
```

- [ ] **Step 3: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md
git commit -m "feat(rsra): add radar chart to Climate Hazard Exposure section

Six-spoke SVG radar with Low/Moderate/High concentric rings. Claude maps
each hazard row to a numeric value and computes polygon coordinates at
generation time. Sits above the existing detail table.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: RSRA — GHG Scoping Donut Chart

Add a Scope 1/2/3 donut chart alongside the existing GHG table.

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`

**Interfaces:**
- Consumes: Scope 1, 2, 3 tCO₂e values already written into `#ghg-table`
- Produces: SVG donut chart inserted before the table in the GHG Scoping section

- [ ] **Step 1: Add donut chart template to RSRA skill**

Find the `<!-- 5. GHG SCOPING -->` section comment in the HTML template instructions. Add the donut template after the `<h2>` and before the table:

```markdown
**GHG donut chart** (insert before the GHG table; float right):

SVG donut math for a slice from `startAngle` to `endAngle` (radians, 0=top, clockwise):
```
x1 = cx + r*sin(startAngle),  y1 = cy - r*cos(startAngle)
x2 = cx + r*sin(endAngle),    y2 = cy - r*cos(endAngle)
large_arc = (endAngle - startAngle > π) ? 1 : 0
outer arc: M x1,y1 A r,r,0,large_arc,1,x2,y2
inner arc (reverse): L ix2,iy2 A ir,ir,0,large_arc,0,ix1,iy1 Z
(inner r = r - ring_width; ix/iy use inner r)
```

Use: cx=90, cy=90, r=70, ring_width=28 (inner r=42).
Total = Scope1 + Scope2 + Scope3. Each slice angle = (value/total) * 2π.
Scope 1 starts at 0 (top). Scope 2 follows. Scope 3 follows.

```html
<div style="display:flex;gap:24px;align-items:flex-start;margin-bottom:16px">
  <svg viewBox="0 0 180 180" width="180" height="180" flex-shrink="0" aria-label="GHG scope breakdown donut">

    <!-- Scope 3 slice (draw first — largest, muted grey) -->
    <path d="[SCOPE3_ARC_PATH]"
      fill="#CBD5E1" stroke="#fff" stroke-width="2"/>

    <!-- Scope 2 slice (owner-paid electricity, green) -->
    <path d="[SCOPE2_ARC_PATH]"
      fill="#4CAF82" stroke="#fff" stroke-width="2"/>

    <!-- Scope 1 slice (combustion, navy — often zero → omit if 0) -->
    [IF SCOPE1 > 0:]
    <path d="[SCOPE1_ARC_PATH]"
      fill="#12253A" stroke="#fff" stroke-width="2"/>

    <!-- Center label -->
    <text x="90" y="85" text-anchor="middle" font-size="18" font-weight="700" fill="#12253A">[OWNER_TOTAL]</text>
    <text x="90" y="100" text-anchor="middle" font-size="9" fill="#64748B">tCO₂e/yr</text>
    <text x="90" y="113" text-anchor="middle" font-size="8" fill="#94A3B8">owner boundary</text>

  </svg>

  <!-- Legend -->
  <div style="font-size:12px;line-height:2">
    <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#12253A;margin-right:6px;vertical-align:middle"></span>Scope 1 — [S1] tCO₂e</div>
    <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#4CAF82;margin-right:6px;vertical-align:middle"></span>Scope 2 — [S2] tCO₂e (owner boundary)</div>
    <div><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#CBD5E1;border:1px dashed #94A3B8;margin-right:6px;vertical-align:middle"></span>Scope 3 — [S3] tCO₂e <em style="color:#94A3B8">(excluded — tenant)</em></div>
  </div>
</div>
```

If Scope 1 = 0: omit the Scope 1 slice path. The donut is only Scope 2 (green arc) + Scope 3 (grey arc).
```

- [ ] **Step 2: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md
git commit -m "feat(rsra): add Scope 1/2/3 donut chart to GHG Scoping section

Owner-boundary donut (Scope 1 navy + Scope 2 green + Scope 3 muted grey
with dashed boundary). Claude computes arc paths from tCO2e values at
generation time. Scope 1 slice omitted when zero.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: RSRA — Livability Status Dots

Add colored RAG dots to the Livability & Reputation section. Minimal change — just a dot prepended to each value.

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`

**Interfaces:**
- Consumes: Walk/Bike/Transit score values and Google rating narrative already written into `#qol-dl`
- Produces: dot prepended to each `<dd>` in the QoL section

- [ ] **Step 1: Add status dot instructions to the RSRA skill**

Find the `<!-- 7. QUALITY OF LIFE -->` section comment in the HTML template instructions. After the section title instruction, add:

```markdown
**Status dots** — prepend a colored dot `<span>` to each `<dd>` value:

```html
<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:[COLOR];margin-right:6px;vertical-align:middle;flex-shrink:0"></span>
```

Color mapping (apply to the score or narrative Claude writes):
- `#4CAF82` (green): Walk/Bike/Transit score ≥ 70 · Google rating "strong" / 4.0+ stars
- `#F59E0B` (yellow): score 40–69 · Google rating "moderate" / 3.0–3.9 stars  
- `#EF4444` (red): score < 40 · flagged concern / negative reviews
- `#94A3B8` (grey): no data · not scored · "N/A" · "not applicable"

Apply one dot per `profile-row`. The Walk Score of 20 = red. Bike Score 40 = yellow boundary — use yellow. Transit "not scored" = grey. Google "strong reviews" = green.
```

- [ ] **Step 2: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md
git commit -m "feat(rsra): add RAG status dots to Livability & Reputation section

8px colored circle prepended to each dd value. Green/yellow/red/grey
mapping based on score thresholds and narrative sentiment.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: RSRA — UN SDG Tiles

Add official UN SDG colored tiles to the SDG Alignment section. All 17 tiles defined as inline SVG in the skill; Claude picks the relevant ones per report.

**Files:**
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md`

**Interfaces:**
- Consumes: SDG numbers already written into `#sdg-table`
- Produces: 40×40 SVG tile replacing the plain text SDG name in the first column

- [ ] **Step 1: Add the SDG tile data block and rendering instructions to the skill**

Find the `<!-- 10. UN SDG ALIGNMENT -->` section comment. Add this block immediately after in the SKILL.md (before the table HTML):

```markdown
**UN SDG tiles** — replace the plain text first column with a colored tile + name:

For each SDG row, use this tile SVG (40×40px, official UN color, white text):

```html
<!-- SDG [N] tile — replace [BG] with official color, [N] with number, [SHORT] with abbreviation -->
<svg viewBox="0 0 40 40" width="40" height="40" style="flex-shrink:0;border-radius:3px" aria-label="SDG [N]">
  <rect width="40" height="40" fill="[BG]"/>
  <text x="20" y="15" text-anchor="middle" font-size="8" fill="rgba(255,255,255,0.85)" font-weight="600" font-family="-apple-system,Helvetica,Arial,sans-serif">SDG</text>
  <text x="20" y="26" text-anchor="middle" font-size="14" fill="#fff" font-weight="700" font-family="-apple-system,Helvetica,Arial,sans-serif">[N]</text>
  <text x="20" y="37" text-anchor="middle" font-size="6" fill="rgba(255,255,255,0.85)" font-family="-apple-system,Helvetica,Arial,sans-serif">[SHORT]</text>
</svg>
```

**Official SDG colors and short titles** (all 17):
| SDG | BG color | Short title |
|-----|----------|-------------|
| 1 | `#E5243B` | NO POVERTY |
| 2 | `#DDA63A` | ZERO HUNGER |
| 3 | `#4C9F38` | GOOD HEALTH |
| 4 | `#C5192D` | QUALITY EDU |
| 5 | `#FF3A21` | GENDER EQ. |
| 6 | `#26BDE2` | CLEAN WATER |
| 7 | `#FCC30B` | CLEAN ENERGY |
| 8 | `#A21942` | DECENT WORK |
| 9 | `#FD6925` | INDUSTRY |
| 10 | `#DD1367` | REDUCED INEQ |
| 11 | `#FD9D24` | SUST. CITIES |
| 12 | `#BF8B2E` | RESP. CONSUMP |
| 13 | `#3F7E44` | CLIMATE ACT. |
| 14 | `#0A97D9` | LIFE BELOW |
| 15 | `#56C02B` | LIFE ON LAND |
| 16 | `#00689D` | PEACE JUST. |
| 17 | `#19486A` | PARTNERSHIPS |

**Row structure** — replace the plain text SDG table with flex rows:

```html
<div style="display:flex;flex-direction:column;gap:8px">
  <div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid #F1F4F8">
    [SDG TILE SVG]
    <div>
      <div style="font-size:12px;font-weight:600;color:#12253A;margin-bottom:2px">SDG [N] — [FULL TITLE]</div>
      <div style="font-size:13px;color:#334155;line-height:1.5">[ALIGNMENT NARRATIVE]</div>
    </div>
  </div>
  [REPEAT FOR EACH SDG]
</div>
```
```

- [ ] **Step 2: Commit**

```bash
cd ~/soapbox-agent
git add skills/rsra/SKILL.md
git commit -m "feat(rsra): add official UN SDG tiles to SDG Alignment section

All 17 SDG tiles defined as inline 40x40 SVG with official UN colors.
Claude picks relevant SDGs per report and renders flex rows with tile +
full title + alignment narrative.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Dead Code Removal

Delete the old Paged.js pipeline repo contents and fix the dead `build_xlsx.py` reference.

**Files:**
- Delete: `~/soapbox-report-skill/templates/` (entire directory)
- Delete: `~/soapbox-report-skill/agents/` (entire directory)
- Replace: `~/soapbox-report-skill/skills/soapbox-report/SKILL.md`
- Update: `~/soapbox-report-skill/README.md`
- Modify: `~/soapbox-agent/scripts/build_xlsx.py`

**Interfaces:**
- No produced interfaces — this is cleanup only

- [ ] **Step 1: Read build_xlsx.py to understand the --templates-dir usage**

```bash
grep -n "templates.dir\|templates_dir\|soapbox-report" ~/soapbox-agent/scripts/build_xlsx.py
```

- [ ] **Step 2: Remove the --templates-dir argument from build_xlsx.py**

Read the relevant lines, then edit to remove:
- The `argparse` argument definition for `--templates-dir`
- Any usage of `args.templates_dir` in the script body
- The help text referencing `soapbox-report-skill`

The script generates Excel companions from RSRA data — it doesn't actually need template files. Keep all other functionality intact.

- [ ] **Step 3: Commit build_xlsx.py fix**

```bash
cd ~/soapbox-agent
git add scripts/build_xlsx.py
git commit -m "fix(scripts): remove dead --templates-dir arg from build_xlsx.py

The soapbox-report-skill templates directory is being deleted. build_xlsx.py
never needed it for the actual Excel generation logic.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 4: Delete templates and agents directories from soapbox-report-skill**

```bash
cd ~/soapbox-report-skill
git rm -r templates/ agents/
```

- [ ] **Step 5: Replace soapbox-report SKILL.md with deprecation notice**

```bash
cat > ~/soapbox-report-skill/skills/soapbox-report/SKILL.md << 'EOF'
---
name: soapbox-report
---

# ⚠️ Deprecated

This skill and the Paged.js pipeline it referenced have been superseded by the monolithic HTML report skills in `soapbox-agent`.

**Use these instead:**

| Report type | Skill location |
|-------------|---------------|
| Acquisition risk assessment | `soapbox-agent/skills/rsra/SKILL.md` |
| Portfolio decarbonization analysis | `soapbox-agent/skills/portfolio-analysis/SKILL.md` |
| Sustainability passport (disposition) | `soapbox-agent/skills/sustainability-passport/SKILL.md` |

All live reports use self-contained monolithic HTML — no Paged.js, no external CDN, no pipeline.
EOF
```

- [ ] **Step 6: Update README.md**

```bash
head -3 ~/soapbox-report-skill/README.md
```

Add a deprecation banner at the top of the README:

```markdown
> **⚠️ DEPRECATED** — This repo's Paged.js pipeline and templates are no longer used.
> Live report skills are in [`soapbox-agent/skills/`](../soapbox-agent/skills/).
> This repo is kept for git history only.
```

- [ ] **Step 7: Commit soapbox-report-skill cleanup**

```bash
cd ~/soapbox-report-skill
git add -A
git commit -m "chore: delete Paged.js templates and agents; deprecate soapbox-report skill

The pipeline-based Paged.js approach is fully superseded by monolithic HTML
skills in soapbox-agent. templates/ and agents/ deleted. SKILL.md replaced
with a deprecation notice pointing to live skill locations. README updated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Verification

After all tasks complete, verify the RSRA skill by spot-checking that the five visualization templates are present and follow the Design System rules:

```bash
grep -n "emissions-benchmark-chart\|radar\|donut\|status dot\|SDG tile\|## Design System" \
  ~/soapbox-agent/skills/rsra/SKILL.md
```

Expected: all 6 terms appear. Then verify no dead references remain:

```bash
grep -rn "soapbox-report-skill/templates\|Paged.js\|pagedjs" \
  ~/soapbox-agent/skills/ ~/soapbox-agent/scripts/ 2>/dev/null
```

Expected: no results.
