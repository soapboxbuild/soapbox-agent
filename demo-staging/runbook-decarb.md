# Demo Runbook — Decarb + Measure Ideation on 4th & Madison

**Status:** ✅ Validated end-to-end on stage (~70s scripted replay). Fixture built from a verified engagement run.

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

## Step 2 — Build and commit the fixture (after Step 1)
- Use `build-fixture-from-run.mjs` to extract a verified engagement run into a `decarb.json` fixture.
- Commit the fixture to `soapbox-platform/apps/api/src/services/demo-fixtures/decarb.json`.
- Deploy the API to make the fixture available for stage.

## On stage (Step 3 — the demo, after wiring)
1. Open Demo org → 4th & Madison → new thread.
2. Type: **"Show me the decarbonization plan for 4th & Madison — walk me through the measures."**
3. Beats (~70s target, scripted replay):
   - Asset ingestion + Files access — live upstream steps.
   - Scripted replay phase (~70s) — deterministic narration of the completed decarb engagement, surfacing the ideated measure set (envelope / HVAC electrification / DHW / controls / solar).
   - **Note:** The analysis phase replays the recorded engagement run for stage reliability. The only live step is the final `fill_report(decarb)` re-render.
   - `fill_report(decarb)` → branded artifact renders in the right pane (live re-render).

## Hero beat
- **fill_report(decarb)** — the final live render step (displays the branded decarb plan for the current asset).

## Fallback
- Rendered decarb artifact id: **TBD after Step 1**.

## Notes
- Fixture economics are deliberately BPS-fine-avoidance-driven (IRR can be modest/negative) — honest, but tune the fixture if a more compelling headline is wanted for the demo.
- Pseudonymous ("JP Metro Asset Management" / "Metro City"); scrub gate: `python3 demo-staging/scrub-check.py`.
