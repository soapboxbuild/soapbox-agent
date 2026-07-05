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

Title and Agenda slides are AUTO-GENERATED — never author them. Fixed section order (the
template groups slides regardless of array order):

**Background → Methodology → Assumptions & Questions → Results → Revisions & Next Steps**

Contract: `templates/delivery-presentation/schema.json`; worked example: `example-data.json`.
Block types: `bullets`, `stats` (tiles; `accent: true` = dark-gradient money tile, max ONE per
slide), `table`, `bars`, `questions` (chips: open / resolved / adjudicated), `quote`, `two_col`,
`waterfall` (value-bridge SVG), `trajectory` (time-series SVG — available, but see slide plan:
the initial deck does NOT include a carbon-trajectory slide by default).

## Slide plan (client-locked, learned from the Westminster pilot)
| Section | Slides |
|---|---|
| Background | Asset profile ONLY (stat tiles + key facts). NO "why now"/motivation slide. |
| Methodology | One slide: the process actually run, "expert-in-the-loop" voice (never "human-in-the-loop"). |
| Assumptions & Questions | Adjudicated assumptions (chips) + open unknowns (chips) — this drives the meeting discussion. |
| Results | 1) Measure/finding list (table) → 2) Stacking logic / why this order → 3) **Value bridge** (`waterfall` block) → 4) **The Decision, combined with results tradeoffs** (scenario stat tiles ≥2 plans side-by-side + what each choice trades away). NO capital-stack slide. NO carbon-trajectory slide. Scope-boundary slide ("what this doesn't do") may follow. |
| Revisions & Next Steps | LAST slide = Action items: **no dates/urgency columns**; each item exists to clear an open question from the Assumptions slide; the final item is always **"Collect desired revisions to this plan and report."** |

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
