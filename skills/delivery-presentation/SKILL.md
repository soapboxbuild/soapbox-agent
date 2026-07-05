---
name: delivery-presentation
description: Build a client-facing HTML slide deck (Soapbox marketing brand, clickable slides + fullscreen) to present ANY deliverable — decarb plan, RSRA, portfolio analysis, retrofit plan, GRESB submission. v2 = the INITIAL PRESENTATION (open items expected, revisions collected); a 'final presentation' variant will follow. v2.0.0
---

# Delivery Presentation — Initial Presentation

Turn a deliverable into the deck for the FIRST client walkthrough. This is the **initial
presentation**: open items and pending decisions are expected, and the deck's job is to surface
them and **collect revisions** — not to declare the work finished. (A separate 'final
presentation' deck type will exist later for the post-revision close-out; do not improvise one.)

## The deck's purpose (drives every slide)
1. **Familiarize** the client with the asset.
2. **Talk through methodology** — and highlight assumptions and unknowns.
3. **Talk through what we found.**
4. **Evaluate options** — scenarios side by side, tradeoffs explicit.
5. **Collect additional feedback** — the deck ends by asking for it.

## When to use
- First delivery of any engagement deliverable; gate reviews / interim readouts.

## How it renders
Same client-render path as all named reports:

```
fill_report(artifact_id, template: 'delivery-presentation', data: { deck: {...}, slides: [...] })
```

**REVISIONS ARE DATA-ONLY — this is a hard rule.** To change a rendered deck, call
`fill_report(same artifact_id, template, updated_data)` with the new JSON payload and NOTHING
else. NEVER `save_file` a hand-built deck, and NEVER hand-edit the inlined template HTML or
reproduce its markup / chart / waterfall renderers — the template (fetched fresh from GitHub on
every `fill_report`) owns all layout and rendering. Hand-rebuilding is what mangles charts, drops
blocks like the value bridge, and reintroduces overflow; it also bypasses template fixes (a baked
artifact does NOT pick up template updates — only a re-`fill_report` does). You only ever touch the
data payload. Same discipline as the decarb render gate — see [[decarb-plan-workflow]].

Title and Agenda slides are AUTO-GENERATED — never author them. Fixed section order (the
template groups slides regardless of array order):

**Background → Methodology → Assumptions & Questions → Results → Revisions & Next Steps**

Contract: `templates/delivery-presentation/schema.json`; worked example: `example-data.json`.
Block types: `bullets`, `stats` (tiles; `accent: true` = dark-gradient money tile, max ONE per
slide), `table`, `bars`, `questions` (chips: open / resolved / adjudicated), `quote`, `two_col`,
`waterfall` (value-bridge SVG), `trajectory` (time-series carbon SVG — BAU vs planned vs CRREM 1.5°C
vs BPS target line).

## Slide plan (client-locked, learned from the Westminster pilot)
| Section | Slides |
|---|---|
| Background | Asset profile ONLY (stat tiles + key facts). NO "why now"/motivation slide. |
| Methodology | One slide: the process actually run, "expert-in-the-loop" voice (never "human-in-the-loop"). |
| Assumptions & Questions | Adjudicated assumptions (chips) + open unknowns (chips) — this drives the meeting discussion. |
| Results | 1) Measure/finding list (table) → 2) Stacking logic / why this order → 3) **Carbon trajectory** (`trajectory` block: BAU vs planned vs CRREM 1.5°C vs BPS/Reg-28 line — the emissions outcome over the hold) → 4) **Value bridge** (`waterfall`) → 5) **Incentives — the actual programs** (`table`: real program names, per-unit/per-ton rate, $ to this asset, status; e.g. Xcel ASHP rebate, DRCOG Power Ahead, §48E ITC) → 6) **The Decision, combined with results tradeoffs** (scenario stat tiles ≥2 plans side-by-side + what each choice trades away). NO capital-stack slide. Scope-boundary slide ("what this doesn't do") may follow. |
| Revisions & Next Steps | LAST slide = Action items: **no dates/urgency columns**; each item exists to clear an open question from the Assumptions slide; the final item is always **"Collect desired revisions to this plan and report."** |

## Layout rules (template enforces, but author to fit)
- Stat tiles lay out on a balanced grid (3-up for 5–6 tiles). Keep bullet blocks to **≤5 items** — the most important ones; the template auto-shrinks to fit but overflow-by-density is an authoring failure.
- No orange text on green surfaces (the accent money tile number is white). Orange stays on paper surfaces.

## Density & voice rules
- Limited verbosity, high impact: ≤6 bullets/slide, ≤12 words/bullet; split rather than cram.
- Visual where relevant: stats/waterfall/table over prose; one idea per slide.
- Fiscally sound: every number carries its basis inline ("5.35% exit cap", "vs 10% hurdle").
- Present ≥2 scenarios where applicable; make the tradeoff explicit on the Decision slide.
- Numbers not yet through verification are marked "Interim". Title/subtitle should say
  "Initial presentation" so no one mistakes it for the final.
- 6–12 content slides for a full delivery; 4–6 for a gate review.

## Sourcing discipline
Build slides FROM the verified engagement artifacts (state ledger, final report payload,
verifier findings) — never re-derive or fabricate numbers. Reuse the report's fill_report data
object as the source of truth and summarize down. Chart blocks (waterfall) must carry the SAME
numbers as the report's charts.
