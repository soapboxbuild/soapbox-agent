---
name: helper-files
description: >
  The Soapbox working-file pattern shared by every deliverable-producing skill (Decarb Plan,
  Portfolio Analysis, Rehab Analysis, RSRA, …). Maintain exactly ONE growing, self-updating
  internal "helper" HTML per engagement — a utilitarian working companion (source-of-truth
  dashboard, open questions, adjudication log, per-phase/per-gate checklists) that absorbs all
  intermediate and gate material. It is NOT the deliverable: only the Report and the
  Delivery-Meeting Slides get the design-forward treatment, and only at their gate. Human gates
  are reviewed as checklist sections of the helper. Read this skill (by path) from any deliverable
  skill before creating or updating working artifacts.
  Triggers on: "helper file", "working file", "gate artifact", "scratchpad", "checklist",
  "source of truth doc", "where do I save this", "intermediate artifact", "working companion".
version: 1.0.0
---

# Helper Files — Soapbox working-file pattern

Every deliverable-producing skill classifies its outputs into **exactly two tiers, nothing in
between**:

| Tier | What | Treatment | Folder |
|---|---|---|---|
| **Working / checklist** | ONE growing "helper" HTML per engagement **+** the verifier `findings.md` ledger. Absorbs all intermediate **and gate** material. | **Utilitarian** — plain, terse, legible. Never "designed." | `Helper Files` |
| **Design-forward** | Exactly two client deliverables: the **Report** and the **Delivery-Meeting Slides**. | Polished, brand-quality. Rendered **only at their gate**. | `Reports` |

The verbose per-phase/per-gate HTML renders of the past do **not** exist here — they collapse into
checklist sections of the one helper file. **Human gates are reviewed as the relevant checklist
section of the helper**, never as a polished artifact.

## The helper file

### Identity (one growing file — never create a second)
- **Folder:** `Helper Files`
- **Filename:** `[ISO start date] - Helper Files - [Deliverable Type].html`
  - `[ISO start date]` = the engagement/analysis **start date**, captured **once** and **fixed
    forever** (NOT the save date — a changing date recreates clutter). Store it in state
    (`state.helper.start_date`, `state.helper.filename`) at engagement start and reuse verbatim
    on every later save.
  - `[Deliverable Type]` = `Decarb Plan` | `Portfolio Analysis` | `Rehab Analysis` | (skill's own).
  - Example: `2026-07-04 - Helper Files - Decarb Plan.html`
- **Save with `save_file`** using that exact `name` + `folder`. The runtime upserts by
  (asset, name, folder) — reusing the identical name **overwrites in place**, so there is always
  exactly one helper file. Never vary the name (no `p1-…`, no `-v2`, no asset suffix).

### It is a rendered VIEW of the state file (no drift)
- The engagement **state file (JSON) is the machine source of truth.** The helper is its
  human-readable projection.
- At **every phase checkpoint**, regenerate the WHOLE helper from current state and re-save it
  under the fixed name. "Grows and adapts" = re-render from state. **Never** hand-edit the helper
  so it diverges from state — if a value is in the helper, it came from state.

### Structure (fill the skeleton in `references/skeleton.html`)
Top to bottom (the skeleton ships all of this — you populate it):
1. **Header badge** — bold `INTERNAL WORKING FILE — NOT THE DELIVERABLE`; deliverable type, asset/
   portfolio, engagement start date, current phase, last-updated timestamp.
2. **Source-of-Truth panel** — every key input as a row: value · source · provenance tier
   (`measured > audit > modeled > estimate`) · 🔒 if adjudicated/locked.
3. **Open Questions / pending adjudications** — unresolved items + who owns each.
4. **Adjudication log** — decision · locked value · date (append-only).
5. **Per-phase / per-gate checklist sections** — one collapsible `<details>` per workflow phase,
   each a checklist with a status marker (`✓ done` / `○ in progress` / `⚠ blocked`) + the minimal
   working detail. **The phase list is supplied by the calling deliverable skill** (see contract).

Styling: single self-contained HTML file, inline CSS, no external assets, utilitarian and legible.
Deliberately **not** brand-polished — polish is reserved for the Report and Slides.

### Lifecycle
- **Create** at engagement start: capture fixed start date + filename into state; render the
  skeleton with the Source-of-Truth panel seeded from kickoff.
- **Update** at every phase checkpoint: regenerate from state, `save_file` under the fixed name.
- **Gate review**: point the user at the relevant checklist section of the helper — not a render.
- **Never gate on the helper** — gates read state; the helper is a working aid.

## Contract for a deliverable skill using this pattern
A deliverable skill (decarb-plan, portfolio-analysis, rehab-analysis, …) must:
1. At engagement start, set `state.helper.start_date` (fixed) and `state.helper.filename`.
2. Supply its **phase/gate checklist list** (the `<details>` sections) and the **Source-of-Truth
   field set** relevant to that deliverable.
3. Regenerate + `save_file` the helper (fixed name, folder `Helper Files`) at every checkpoint.
4. Keep the two design-forward deliverables (Report, Slides) separate, in `Reports`, gate-only.
5. Do **not** produce standalone verbose intermediate/gate HTML — put that material in the helper
   as checklist sections.

## Notes
- The verifier plugin's `findings.md` ledger also lives in `Helper Files` (working-tier material).
- This is doctrine + a skeleton, not a tool. No platform/runtime change is needed — `save_file`
  already provides upsert-by-name behavior.
