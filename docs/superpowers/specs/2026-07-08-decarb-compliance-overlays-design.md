# Decarb report: selectable compliance overlays (CRREM and/or BEPS)

**Date:** 2026-07-08
**Status:** Approved design — ready for implementation plan
**Approach:** A — unified `reference_pathways[]` (chosen over minimal-additive and interactive-toggle)

## Problem

The "Decarbonization Roadmap" the decarb report produces plots a single, hardcoded
reference curve on its Emissions Trajectory chart: the **CRREM 1.5°C** carbon
pathway. There is no way to plot a jurisdiction's actual Building Performance
Standard (BPS) instead of — or alongside — CRREM. When a user asks for "the BEPS
curve instead of CRREM," the agent has no structured knob, so it re-authors the
whole report as bespoke HTML and the report balloons in complexity on each pass.

Concrete trigger: asset `4th and Madison` (Seattle office). Its report shows the
CRREM curve (which makes it look like it strands in 2032), while the building is
actually **WSCBA-compliant** (EUI 33.5 vs 60.9) and **Seattle-BEPS exempt**
(all-electric). The user wants the report to be a structured template where CRREM
and/or the applicable BPS can be shown.

## Goal

Make the decarb report's trajectory chart(s) driven by a **structured, provenance-
gated list of reference pathways**, so any report can show CRREM and/or the BPS
standards that apply to the asset's jurisdiction (Seattle BEPS, WA Clean Buildings
Act / WSCBA, NYC LL97, Boston BERDO, …), each individually toggleable, without the
agent hand-authoring HTML.

## Non-goals

- No interactive carbon⇄energy metric toggle (rejected approach C). Two static
  charts only.
- No new BPS data source. Real target values come from the existing
  `bps-compliance` skill (LL97/BERDO/BEPS/WSCBA) and CRREM from the CRREM MCP.
- No change to how non-trajectory sections of the decarb report render.

## 1. Data model — `templates/decarb/schema.json` (`targets`)

Add `targets.reference_pathways`: an array of reference lines for the trajectory
charts. Each entry:

```jsonc
{
  "standard": "CRREM",              // "CRREM" | "Seattle BEPS" | "WSCBA" | "NYC LL97" | "Boston BERDO" | …
  "metric": "carbon",               // "carbon" (kgCO₂/m²/yr) | "eui" (kBtu/sf/yr or kWh/m²/yr)
  "unit": "kgCO2e/m2/yr",           // display unit; disambiguates the EUI sub-unit
  "label": "CRREM 1.5°C",           // legend + line label
  "points": [{ "year": 2026, "value": 25.51 }, …],  // the reference line
  "meta": { "source": "CRREM v2.05 MCP", "url": null, "version": "2.05", "notes": null },
  "color": "#B91C1C",               // optional; template assigns a default palette slot if omitted
  "dash": "5,4",                    // optional stroke-dasharray
  "show": true,                     // optional; default true. false = keep data, hide the line
  "strand_against": true            // optional; default true for CRREM only. Marks the pathway the
                                    // stranding marker is computed against.
}
```

Rules:
- **CRREM is just one entry** (`standard:"CRREM"`, `metric:"carbon"`).
- **Back-compat (must not break existing reports or the gate):** legacy
  `targets.crrem_pathway` / `targets.crrem_meta` / `targets.crrem_stranding_year`
  remain valid input. At render, if `reference_pathways` is absent/empty but a
  legacy `crrem_pathway` exists, normalize it into a single CRREM
  `reference_pathways` entry (`points` from `carbon_kgco2_m2yr`, `meta` from
  `crrem_meta`, `strand_against:true`, stranding year from
  `crrem_stranding_year`). If both are present, `reference_pathways` wins and the
  legacy fields are ignored.
- **Selection = presence.** "Show CRREM and/or BEPS" is expressed by which entries
  appear (and `show:false` to hide without deleting).
- Building trajectory: existing carbon `targets.trajectory` (BAU / planned /
  target) is **unchanged**. Add optional `targets.eui_trajectory[]`
  (`[{year, bau?, planned?, actual?}]`) to drive the EUI chart. If absent, the EUI
  chart plots the `baseline` EUI point (from `baseline.eui_kwh_m2`, converted to
  the target's unit) against the EUI target line.

## 2. Rendering — `templates/decarb/layout-agent.html`

Refactor the existing single-chart renderer into a small helper that draws a line
chart from (building series, reference pathways) for a given metric, then call it
up to twice:

- **Carbon "Emissions Trajectory" chart** (always): building carbon lines +
  every `reference_pathways` entry with `metric:"carbon"` (CRREM, Seattle BEPS,
  LL97, …). Each overlay gets its own color/dash and a legend toggle (reuse the
  existing `data-si` legend-toggle mechanism). Stranding marker computes against
  the entry flagged `strand_against` (fall back to CRREM; if none, no marker).
- **Energy "EUI Trajectory" chart** (only when ≥1 `metric:"eui"` entry exists):
  building EUI trajectory (or baseline point) vs the EUI target line(s), plus a
  compliance-deadline marker where the standard defines one.

Both charts share the existing SVG scaffolding (axes, grid, legend). No new chart
library.

## 3. Provenance gate — `soapbox-platform/apps/api/src/services/verification-gate.ts`

The gate currently validates `crrem_meta` to stop a fabricated/hand-drawn CRREM
curve from rendering. Generalize it:

- For every `targets.reference_pathways` entry, require `meta.source` to be
  present and non-empty. Reject the render if any overlay carries `points` but no
  `meta.source` (the "hand-drawn curve" failure mode) — same rule that protects
  CRREM today.
- Keep the existing legacy `crrem_meta` check working (a report using only the
  legacy fields still passes exactly as before).
- Gate message names the offending `standard` so the agent knows which overlay
  lacks provenance.

## 4. Data + skill wiring — `decarb-plan` / `crrem` skills + `bps-compliance`

- The decarb/crrem skill populates `reference_pathways` from **real** sources:
  CRREM via the CRREM MCP (as today); BPS standards via the `bps-compliance`
  skill for the asset's jurisdiction (it already knows LL97, BERDO, Seattle BEPS,
  WSCBA). Each emitted overlay carries `meta.source`.
- **Default selection (jurisdiction-auto-include):** the skill includes the
  standards that actually apply to the asset's jurisdiction — e.g. a Seattle asset
  gets Seattle BEPS (carbon) + WSCBA (EUI) — **plus** CRREM, each overridable by
  the user ("show only WSCBA", "drop CRREM"). A standard the asset is exempt from
  is still shown but annotated (label/footnote) as exempt/compliant, since that is
  itself the useful signal.
- Unit handling: carbon standards plot on the carbon chart; EUI standards
  (WSCBA) plot on the EUI chart. No **carbon⇄energy** conversion is performed — a
  standard is shown on the chart whose metric it natively uses. Within the EUI
  chart only, the building baseline is normalized to the standard's EUI sub-unit
  (e.g. `kWh/m²` → `kBtu/sf`) so the building line and target line share a scale.

## 5. Testing / verification

- **Template render tests:** fixture with (a) CRREM only → one carbon chart, no
  EUI chart; (b) CRREM + Seattle BEPS + WSCBA → carbon chart with two overlays +
  EUI chart with the WSCBA line; (c) `show:false` hides a line; (d) legacy
  `crrem_pathway` only → normalized CRREM entry renders identically to today.
- **Gate unit tests:** overlay with `points` but no `meta.source` → rejected
  (message names the standard); sourced overlay → passes; legacy `crrem_meta`
  path → still passes.
- **End-to-end:** re-render the `4th and Madison` decarb report with CRREM +
  Seattle BEPS on the carbon chart and WSCBA on the EUI chart; confirm on a
  Vercel preview before any prod promotion.

## Files touched

- `soapbox-agent/templates/decarb/schema.json` — `reference_pathways`,
  `eui_trajectory`; keep legacy fields.
- `soapbox-agent/templates/decarb/layout-agent.html` — chart helper + carbon/EUI
  charts + per-overlay legend toggles.
- `soapbox-agent/templates/decarb/example-data.json` — add multi-overlay example.
- `soapbox-platform/apps/api/src/services/verification-gate.ts` — generalize
  provenance check to all reference pathways.
- `soapbox-agent/skills/decarb-plan/SKILL.md` (and crrem skill) — emit
  `reference_pathways` from CRREM MCP + `bps-compliance`; jurisdiction-auto-include
  selection rules.
- Tests alongside the template renderer and the gate service.

## Open implementation questions (resolve during planning)

- Exact location/shape of the template render tests in the soapbox-agent
  template-mcp (confirm existing test harness).
- Whether `bps-compliance` exposes target trajectories as data callable by the
  skill, or the skill must transcribe target tables (affects `meta.source`).
- EUI unit normalization for the EUI chart (kBtu/sf vs kWh/m²) — pick one display
  unit and convert building baseline to match the standard.
