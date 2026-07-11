# Demo Runbook — Decarb + Measure Ideation on 4th & Madison

**Status:** ⏳ Awaiting one real engagement run (Christopher) to produce the completed state + rendered plan in Files; then the demo `[DEMO MODE]` prompt is wired to resume/present it.

## Architecture (per Christopher's correction)
- Decarb state persists to the **Files store** (folder `decarb-plan`: `decarb-plan-state.json`, `decarb-plan.md`), NOT the deprecated OpenWork worker workspace.
- The demo does **not** rely on the skill's old workspace-based Resume Protocol. The `[DEMO MODE]` prompt points the agent directly at the completed Files state.

## Step 1 — Christopher runs the real engagement (one time)
- Asset **4th & Madison** (`f6e043dd-…`, office, Metro City, BPS-2032) is staged with inputs:
  - `engagement-reference.md` (Engagement) — goal/drivers/target/hold → kickoff pre-fills.
  - `building_setup.json` + `baseline.json` (Building Data) — equipment survey + calibrated energy.
  - building-setup metadata on the asset (`setup_complete`, archetype, GFA, regulatory driver).
- Open Demo org → 4th & Madison → new thread → **"Run a full decarbonization plan engagement on 4th & Madison. Use the engagement reference in the files to pre-fill kickoff."** Adjudicate the two gates.
- Output: completed `decarb-plan-state.json` (phase=done) + rendered **decarb** plan artifact + Helper Files, all in the asset's Files.

## Step 2 — Wire the demo (after Step 1; TODO)
- Set the 4th & Madison `[DEMO MODE]` system prompt: *engagement is COMPLETE — read the completed state from Files (`decarb-plan` folder), surface the ideated measures, then display the rendered decarb plan artifact. Do NOT re-run the engagement or re-render.*
- Record the rendered decarb artifact id here as the fallback.

## On stage (Step 3 — the demo, after wiring)
1. Open Demo org → 4th & Madison → new thread.
2. Type: **"Show me the decarbonization plan for 4th & Madison — walk me through the measures."**
3. Beats: agent surfaces the ideated measure set (envelope / HVAC electrification / DHW / controls / solar) → displays the rendered decarb plan.

## Hero beat
- **Measure Ideation** surfaced on screen (the title deliverable), then the branded decarb plan.

## Fallback
- Rendered decarb artifact id: **TBD after Step 1**.

## Notes
- Fixture economics are deliberately BPS-fine-avoidance-driven (IRR can be modest/negative) — honest, but tune the fixture if a more compelling headline is wanted for the demo.
- Pseudonymous ("JP Metro Asset Management" / "Metro City"); scrub gate: `python3 demo-staging/scrub-check.py`.
