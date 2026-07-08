# Decarb report: selectable compliance overlays (CRREM and/or BEPS)

**Date:** 2026-07-08
**Status:** Approved design (revised) — ready for implementation plan
**Approach:** B — extend the existing `targets` shape (revised down from A after
discovering the carbon BPS line already exists; see "Why B, not A").

## Problem

The decarb report's Emissions Trajectory chart shows the **CRREM 1.5°C** carbon
pathway, and users can't get their jurisdiction's actual Building Performance
Standard (BPS) shown instead of / alongside it. Asked to "use the BEPS curve
instead of CRREM," the agent re-authors the whole report as bespoke HTML and it
balloons in complexity.

Concrete trigger: asset `4th and Madison` (Seattle office). Report shows CRREM
(looks like it strands in 2032) while the building is actually **WSCBA-compliant**
(EUI 33.5 vs 60.9) and **Seattle-BEPS exempt** (all-electric).

## Why B, not A (what investigation changed)

The approved design was A (a new unified `reference_pathways[]`). Investigation of
the live code then showed:

- The chart **already** draws a BPS compliance line: `targets.trajectory[].bps_target`
  ("stepped navy dashed line"), with per-series **legend toggles already wired**
  (`data-si` mechanism in `drawTrajectory`). `validateFineConsistency` already
  reconciles fine claims against that `bps_target` geometry.
- In the trigger report, `bps_target` was simply **never populated** — a data/skill
  gap, not a template gap.
- CRREM's gate (`validateComplianceCurve`) re-verifies the curve against a real
  tool (`crrem get_pathway`). **BPS targets have no callable tool** — they live in
  `bps-compliance` reference tables. So a gate cannot re-verify BPS the way it does
  CRREM; BPS provenance can only be a **source citation**.
- WSCBA is an **EUI** standard and a **flat threshold the building beats**
  (33.5 < 60.9) — not a declining curve. It has no chart today.

So a new `reference_pathways[]` abstraction would re-implement a `bps_target` that
already exists — more complexity, not less. B extends the existing shape.

## Goal

Make the decarb report show, per the asset's jurisdiction, CRREM and/or the
applicable BPS standard(s): **carbon** standards (Seattle BEPS, BERDO, LL97) on the
existing trajectory chart via `bps_target`; **EUI** standards (WSCBA) in a new
compact **EUI compliance panel**. Each already-plotted line stays individually
toggleable. No new abstraction, no gate rewrite.

## Non-goals

- No `reference_pathways[]` abstraction (rejected — duplicates `bps_target`).
- No change to `validateComplianceCurve` (CRREM tool-gate) or
  `validateFineConsistency`. CRREM's real check stays; no fake BPS re-verify gate.
- No second full EUI *trajectory* chart — WSCBA is a flat threshold, shown as a
  compact panel (building value vs target + deadline), not a curve.
- No interactive carbon⇄energy toggle. No new BPS data source (values come from
  the `bps-compliance` skill tables + official-source verification).

## 1. Carbon chart — NO template code change

`targets.trajectory[].bps_target` (stepped navy dashed) and the CRREM pathway
already render, and both are legend-toggleable. "Show CRREM and/or BEPS" on the
carbon chart is therefore satisfied once `bps_target` is populated. Two small
additive schema fields for labeling/provenance (displayed, not gated):

- `targets.bps_label` (string, optional) — legend/footnote label for the
  `bps_target` line, e.g. `"Seattle BEPS (GHGI target)"`. Default `"BPS target"`.
- `targets.bps_source` (string, optional) — provenance citation for the BPS target
  values, e.g. `"Seattle OSE Director's Rule 2021-01, office GHGI targets"`.
  Rendered as a chart footnote next to the existing CRREM provenance line.

The layout change here is limited to **rendering `bps_label`/`bps_source`** where
the CRREM label/footnote already render (no new chart geometry).

## 2. EUI compliance panel — the one new render unit

New optional schema block:

```jsonc
"targets": {
  "eui_compliance": [                    // array → supports >1 EUI standard; omit/empty → panel hidden
    {
      "standard": "WA Clean Buildings Act (WSCBA)",
      "unit": "kBtu/sf/yr",              // display unit; building value normalized to this
      "building_eui": 33.5,
      "target_eui": 60.9,
      "compliance_year": 2027,           // deadline; optional
      "status": "compliant",             // "compliant" | "non-compliant" | "exempt"
      "source": "WAC 194-50-150, office EUIt"   // required when the entry is present
    }
  ]
}
```

Rendering (`layout-agent.html`): a compact panel, one row per entry, each showing
the standard name, a small horizontal bar with the building EUI marker against the
target threshold, the numeric `building_eui vs target_eui unit`, a status pill
(compliant/exempt/non-compliant), the compliance year, and the `source` as a
footnote. The panel section is hidden when `eui_compliance` is absent/empty (same
`display:none`-until-populated pattern the trajectory section uses). No axis, no
per-year series — it is a threshold panel, not a chart.

## 3. Gate — unchanged

`validateComplianceCurve` (CRREM tool re-verify) and `validateFineConsistency`
(fine-claim vs `bps_target` geometry) stay exactly as-is. `bps_label`/`bps_source`
and `eui_compliance` are display-only fields with no server verification (no tool
exists to re-verify BPS values). Provenance for BPS is the human-readable
`source`/`bps_source` citation, which the skill MUST fill from a real
`bps-compliance` reference or official source.

## 4. Skill wiring — where the values come from

`decarb-plan` (and the CRREM path) SKILL guidance:

- **Jurisdiction-auto-include:** determine the asset's jurisdiction, then include
  the standards that actually apply — e.g. a Seattle asset → Seattle BEPS (carbon →
  `bps_target` + `bps_label`/`bps_source`) **and** WSCBA (EUI → `eui_compliance`
  entry) — plus CRREM. User can override ("show only WSCBA", "drop CRREM").
- **Source of values:** the `bps-compliance` skill reference tables (BERDO/DC
  BEPS/WSCBA/LL97 target tables) + official-portal verification per the
  bps-compliance workflow. Every BPS value carries a `source`/`bps_source`
  citation. A standard the asset is exempt from is still shown, annotated
  `status:"exempt"` (that is itself the signal).
- Carbon BPS targets populate `targets.trajectory[].bps_target` per year (stepped);
  EUI standards populate `targets.eui_compliance`.

## 5. Testing / verification

- **Gate:** unchanged → no new gate tests. (Confirm existing gate tests still pass
  if the repo has them.)
- **EUI panel render:** `layout-agent.html` is client JS with no test harness, so
  verify by **actual render**: add an `eui_compliance` fixture to
  `templates/decarb/example-data.json`, render via `fill_report`/the platform
  render path, and confirm the panel appears (and is hidden when the field is
  absent). Preview before any prod promotion.
- **End-to-end:** re-render the `4th and Madison` decarb report — CRREM + Seattle
  BEPS `bps_target` on the carbon chart (Seattle BEPS annotated exempt) and WSCBA
  in the EUI panel (33.5 vs 60.9, compliant). Confirm on a Vercel preview.

## Files touched

- `soapbox-agent/templates/decarb/schema.json` — add `targets.bps_label`,
  `targets.bps_source`, `targets.eui_compliance[]`. (Keep everything else.)
- `soapbox-agent/templates/decarb/layout-agent.html` — render `bps_label`/
  `bps_source` where CRREM label/footnote render; add the EUI compliance panel
  section + its populate logic in `populateReport()`.
- `soapbox-agent/templates/decarb/example-data.json` — add a populated
  `bps_target` series + `eui_compliance` example.
- `soapbox-agent/skills/decarb-plan/SKILL.md` (+ CRREM path) — jurisdiction-auto-
  include selection; populate `bps_target`/`bps_label`/`bps_source` and
  `eui_compliance` from `bps-compliance`; keep CRREM as today.
- **Not touched:** `verification-gate.ts` (gate unchanged).

## Open implementation questions (resolve during planning)

- Exact insertion points in `populateReport()` / `drawTrajectory` for the
  `bps_label`/`bps_source` footnote and the new panel section (grounded:
  `drawTrajectory` lines ~941–1120, footnotes ~1074–1085, trajectory section
  markup ~1601–1604).
- EUI display-unit normalization when `building_eui` is provided in a different
  unit than `target_eui` (pick the target's unit; convert building value).
- Whether the CRREM path (RSRA-style single-asset) also needs the EUI panel or only
  the multi-phase decarb-plan workflow.
