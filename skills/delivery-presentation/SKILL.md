---
name: delivery-presentation
description: Build a client-facing HTML slide deck (Soapbox marketing brand, clickable slides + fullscreen) to present ANY finished deliverable — decarb plan, RSRA, portfolio analysis, retrofit plan, GRESB submission. Fixed agenda; Agenda → Background → Methodology → Assumptions & Questions → Results → Revisions & Next Steps. v1.0.0
---

# Delivery Presentation

Turn a completed deliverable into the deck you present in the delivery meeting. The deck is a
summary FOR A CONVERSATION — the report artifact stays the reference document. Never duplicate the
whole report onto slides.

## When to use
- End-of-engagement delivery (decarb plan, RSRA, portfolio analysis, retrofit plan, GRESB…)
- Gate reviews / interim readouts (use the same structure; mark results "interim")
- Any time the client asks to "present" or "walk through" a deliverable

## How it renders
One call, same client-render path as all named reports:

```
fill_report(artifact_id, template: 'delivery-presentation', data: { deck: {...}, slides: [...] })
```

The platform fetches `templates/delivery-presentation/layout-agent.html` from soapbox-agent@main
and injects your JSON. Title and Agenda slides are AUTO-GENERATED — do not author them. The
template groups your slides into the fixed section order regardless of array order:

**Background → Methodology → Assumptions & Questions → Results → Revisions & Next Steps**

Authoritative payload contract: `templates/delivery-presentation/schema.json`; fully-worked
example: `templates/delivery-presentation/example-data.json`. Block types per slide: `bullets`,
`stats` (tiles; `accent: true` = the dark-gradient money tile — max ONE per slide), `table`,
`bars` (simple horizontal SVG bars), `questions` (chips: open / resolved / adjudicated), `quote`,
`two_col`.

## Mapping any deliverable into the sections
| Section | What goes there (source) |
|---|---|
| Background | Asset/portfolio, engagement driver + goal, hold/constraints (kickoff record + engagement state) |
| Methodology | The process actually run — model foundation, calibration, gates, tools; say "expert-in-the-loop" (never "human-in-the-loop") |
| Assumptions & Questions | Every material assumption WITH its basis, and adjudications as `questions` chips (open items stay visible — this slide drives the meeting discussion) |
| Results | The decision: money numbers as stat tiles (net value, IRR vs hurdle, ask), scenario comparison table (**present ≥2 scenarios where applicable**), key chart facts as `bars`/bullets. Distinguish BPS compliance (fines) from CRREM (stranding) when both apply |
| Revisions & Next Steps | What changed since the last readout, numbered next steps with owners/dates |

## Density & voice rules (client-locked)
- Limited verbosity, high impact: ≤6 bullets per slide, ≤12 words per bullet; split rather than cram.
- Visual where relevant: prefer `stats`/`bars`/`table` over prose; one idea per slide.
- Fiscally sound: every number carries its basis (sub-label or trailing parenthetical: "5.5% exit cap", "vs 12% hurdle").
- Decision-useful: the first Results slide answers fund / don't-fund before any detail.
- Numbers not yet through their verification gate are marked "Illustrative" or "Interim".
- 6–12 content slides total for a full delivery; 4–6 for a gate review.

## Sourcing discipline
Build slides FROM the verified engagement artifacts (state ledger, final report payload, verifier
findings) — never re-derive or fabricate numbers for slides. If the deliverable's report used
`fill_report`, reuse its data object as the source of truth and summarize down.
