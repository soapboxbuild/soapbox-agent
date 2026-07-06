---
name: decarb-plan
description: >
  Conduct a full client decarbonization engagement for a single asset — kickoff scoping,
  evidence sweep, human-adjudicated baseline reconciliation, target trajectory, Audette-modeled
  measure plan, two user gates, Audette write-back, verification-gated report render, and
  PDF/PPTX export. Durable phase state at projects/<asset-key>/decarb-plan.json lets any
  session resume mid-engagement. NOT the same as RSRA: RSRA is the SCREENING product (rapid
  pre-underwriting snapshot from an OM); decarb-plan is the full ENGAGEMENT product (multi-week
  client deliverable with gates and verified provenance) — do not trigger this skill for deal
  screening, and do not trigger RSRA for a full plan.
  Triggers on: "decarbonization report", "decarb plan", "decarbonization roadmap",
  "full decarb report", "net zero plan for [asset]", "BPS compliance plan".
version: 1.7.1
---

# Decarb-Plan Engagement

You are conducting a **full decarbonization engagement** for one asset. You orchestrate
existing capabilities only — project-kickoff (scoping), asset documents (evidence), Audette
(physics + write-back), the Retrofit Specialist plugin (`retrofit__*`, provenance-enforced
measure evaluation), the Verifier plugin (`verifier__*`, findings ledger + render gate),
org memory, the reference library, and the `decarb` report template.

**Non-negotiable ground rules — apply in every phase:**

1. **No LLM arithmetic.** Every number in the baseline, trajectory, economics, and report
   comes from an engine, Audette analysis, or a cited source. CRREM pathway points come from
   crrem tooling; BPS milestones and fine exposure come from engines/Audette compliance
   analysis (`run_compliance_analysis`); simple percent-reduction math may use the
   cashflow/DCF engines. You never compute a reported number yourself.
2. **The hierarchy is suggestion-only.** The reconciliation precedence — **measured
   utility/ESPM actuals > audit-reported 12-mo > Audette modeled > estimates** — produces the
   *suggested* resolution for each conflict. The human adjudicates ALL conflicts at Gate 1.
   Nothing is auto-resolved.
3. **The render gate is HARD and fails closed.** No report render without
   `verifier__verification_status` passing, or a documented override
   `{finding_id, override_reason, approved_by}` in state for every open high-severity finding.
4. **NEVER game or bypass the render gate.** The gate protects analytical integrity — satisfying
   it mechanically is a workflow failure, not "the correct path". Specifically:
   - **No self-certification.** Do NOT open a finding and confirm it yourself in the same turn to
     clear the gate ("record one and confirm it" is the exact anti-pattern). Baseline verification
     must be substantive and independent — a real `baseline_verified`-type record with provenance,
     not a placeholder you resolve to unblock a render.
   - **No `save_file` bypass.** If `fill_report` is gate-blocked, the answer is to *do the
     verification*, never to hand-render the report to static HTML and `save_file` it into
     `Reports/`. A report deliverable produced outside the gated `fill_report` path is UNVERIFIED
     and must not be presented as a rendered report. (This is how a broken, static, ungated
     roadmap ended up in Files on the Westminster pilot — [[decarb-plan-workflow]].)
   - **Headline-metric reconciliation.** Before any gate/render, every top-line % MUST equal the
     underlying tonnage/energy math: reduction % = (baseline − with-plan) / baseline on the SAME
     basis. A "−46% by 2034" next to "560 tCO₂e/yr saved" on a 2,811 t baseline (that's −20%, and
     the measure-reconciled figure is ~−33%) is a hard contradiction the gate must not pass. If a
     grid-inclusive vs measure-only figure differ, label each; never mix bases in one headline.
   - **CRREM provenance.** Pull the pathway from the `crrem` MCP `get_pathway` for the asset's
     actual region (US NA regional pathways are live — [[crrem-plugin]]). Put those points ONLY in
     `targets.crrem_pathway` (+ set `targets.crrem_meta` = country/property_type/region/scenario so
     the server can re-fetch and verify). There is NO inline per-year CRREM field — the legacy
     `trajectory[].crrem_target` was REMOVED and the render gate now BLOCKS any payload that uses it
     or ships a `crrem_pathway` that doesn't match `get_pathway` within tolerance. Never hand-type,
     interpolate, or eyeball CRREM values — if you can't reach the tool, STOP and say so rather than
     fabricating a curve. A directional/reference curve (e.g. LBNL/ULI Appendix G) may only appear if
     explicitly labeled "directional — pending asset-specific CRREM tool run"; never present a
     directional stranding year as a firm result.
     **On a RE-RENDER you MUST re-call get_pathway and repopulate targets.crrem_pathway — never
     rebuild the CRREM curve from saved state.** Stored state may predate the curve fix; the render
     gate now BLOCKS a decarb report whose crrem_meta is set but crrem_pathway is empty (it would
     otherwise silently drop the curve), so a from-state rebuild without a fresh fetch will fail.
5. **Pre-render sanity checks (the gate/verifier MUST reject these — they are self-evidently wrong):**
   - **Emissions trajectory must be non-increasing.** A with-plan (or BAU) carbon curve that *rises*
     over time is a sign/axis bug — decarb emissions decline. Reject and fix the payload.
   - **At-RUL / bundled-capital-event incremental cost is POSITIVE.** The like-for-like replacement
     that must happen anyway is the baseline; only the *upgrade spec above it* is incremental. A
     re-roof is the baseline — only the **added insulation** is incremental (positive). A negative
     incremental ("insulation saves money vs the mandatory re-roof") is the cost model backwards.
   - **Tenant vs landlord savings are SEPARATE explicit columns** in the cashflow — never merged.
     Only landlord/owner-share savings capitalize into the value-creation bridge; tenant-side
     savings do not accrue to the owner (see owner-share discipline in recipe 8 + analytics standards).
   - **Landlord-capture matches the end-use's payer.** Reject any measure whose owner-capture /
     Audette landlord-share equals the account default (commonly 15%) while its end-use is
     landlord-paid — central heating/DHW plant, elevators, garage ventilation, common lighting,
     amenity loads = **100% owner**. A common-area measure priced at the blended in-unit split
     understates owner IRR (the elevator-regen −6%→+12% flip). Record the correction as a
     `verifier__record_finding` (kind `data-quality`, verdict `conflict`) tying the measure to its
     true end-use capture from the 2C capture map.
   - **Measure equipment type matches the documented system.** Reject a measure whose equipment
     contradicts the PCA/as-built — e.g. an RTU/packaged-unit measure on a WSHP-loop building, or a
     DHW measure that assumes electric resistance when the PCA specifies gas boilers. Cross-check
     the Audette equipment survey against the PCA before screening; a mismatch is a
     `verifier__record_finding` conflict, not a silent screen-in.
   - **Plans are genuinely differentiated paths, not hold sensitivities.** Reject a two-plan report
     whose plans share identical capex, GHGI-reduction %, and ancillary revenue (that's one plan at
     two exit assumptions). Real plans differ on capex, carbon %, IRR, AND CRREM/stranding status
     (see recipe 8 "Plans"). The hold period maps to the path; it is not the differentiator.
   - **Both plan trajectories on the chart.** A two-path report must populate `targets.trajectory`
     with `planned_1` AND `planned_2` (+ `plan1_label`/`plan2_label`), not a single `planned` series.
   - **Soft ancillary/DR revenue is NOT capitalized as a perpetuity.** Reject `capitalized_ancillary_
     revenue = annual_DR ÷ exit_cap` on program-dependent PJM-DR/EV revenue; require risk-adjustment
     (haircut/PV over term) + a with/without-ancillary sensitivity. Flag any plan whose net value
     depends mostly on capitalized DR (fragile).
   - **Subscription measures judged on annual net, not capitalized-fee-vs-savings.** Capitalizing a
     cancellable subscription at the exit cap overstates the drag; require the annual net (savings +
     risk-adjusted DR − fee) and a one-time-RCx alternative for contrast (recipe 8).
   - **EV measures carry non-zero owner make-ready capex** (electrical/panel/trenching) — a $0-capex
     EV line under a host agreement is a red flag (host agreement zeroes hardware, not make-ready).
   - **Trajectory ↔ measure consistency (HARD — the verifier MUST check this).** Every measure with a
     material modeled energy/fuel reduction must show up as a corresponding bend in the plan curve it
     belongs to. A fuel-switch / electrification measure (e.g. gas WSHP boiler → air-source heat pump,
     gas DHW → HPWH) eliminates a large gas load and MUST visibly pull that plan's `planned_*` carbon
     line down in and after its install year. If a big electrification measure is in the measure list
     but the plan's trajectory doesn't reflect it (the curve is flat/unchanged through the install
     year), the trajectory and the measure model are inconsistent — that is a hard data error: record a
     `verifier__record_finding` (kind `data-quality`, verdict `conflict`) and fix the trajectory before
     render. Cross-check each plan's GHGI-reduction % against the sum of its measures' modeled
     reductions on the same basis; they must agree.
   - **No editorializing in report prose.** The deliverable states facts plainly — NO hype or
     rhetorical framing. Do not write lines like "two genuinely different strategies — same asset,
     different theses." The "genuinely differentiated plans" rule governs the MODELING (make the plans
     actually differ on capex/carbon/IRR/stranding), NOT the copy. recommendation, summary_points,
     section intros, and executive_summary must be plain and specific — name the plan, the number, the
     driver; skip the adjectives and the meta-commentary.
   - **Plan narrative goes in per-plan bullets, not a paragraph wall.** Populate
     `economics.plans[].summary_points[]` (3–5 short bullets each: what it deploys, headline
     IRR/value, the key trade-off/sensitivity) so each plan renders as a scannable list under its
     heading. Keep `executive_summary` to one short context line — do NOT cram both plans into a
     prose block there.
   - **Utility-rate escalation is applied** to the savings cashflow over the hold (e.g. ~3% elec /
     ~4% gas, or a cited regional forecast) and the assumption is stated — flat-nominal savings
     understate later years and the capitalized exit value.
   - **Regulatory/CRREM data comes from the tool, freshly.** Never carry a stale "tool unavailable"
     note from a prior session's saved state into a new report — re-attempt `crrem__get_pathway`
     (and record a finding if it genuinely errors); never ship "tool unavailable" prose as a result.
   - **Verify ALL math at report generation — do not trust LLM-computed figures.** Before render,
     recompute and reconcile every derived number in the payload: waterfall components sum to
     `net_value_creation`; each capitalization = annual ÷ exit cap; GHGI reduction % =
     (baseline − planned) / baseline; incremental = total − like-for-like; owner-share applied per
     the capture map; unit conversions correct (incl. the kWh→MWh/GWh scaling); every table total =
     Σ its line items; IRR consistent with the cashflow. Route the reconciliation through the
     verifier — any mismatch beyond rounding is a `verifier__record_finding` and **blocks the
     render** until resolved. The template's client-side sum check is a backstop, not the gate.
6. **Never fail silently.** Outages halt the phase with the standing reconnect message. And never
   fall back to hand-built report HTML when a tool/gate blocks — surface the blocker and stop.

**State ledger:** `projects/<asset-key>/decarb-plan.json`, conforming to
`skills/decarb-plan/state-schema.json`. Human-readable companion:
`projects/<asset-key>/decarb-plan.md`, registered in Files. Update BOTH at every phase
boundary. `<asset-key>` follows the project-kickoff convention: lowercase the asset name,
replace spaces with hyphens.

**Presentation standards** (apply to every number shown at a gate or in the report):

- **Energy intensity in kWh/m²; absolute energy scaled to magnitude.** Express intensity as
  kWh/m². For ABSOLUTE energy, scale the unit to keep the number readable: kWh, but switch to
  **MWh at ≥1,000 kWh and GWh at ≥1,000,000 kWh** (e.g. 5,929,000 kWh → **5.9 GWh** or **5,929 MWh**,
  never "5,929,000 kWh"). Convert gas from native units/GJ to the same energy basis. Areas in **m²**;
  carbon as **tCO₂e** and intensity as **kgCO₂e/m²**. No therms, kBtu, ft², or kBtu/ft² in output.
- **Max 2 significant figures displayed.** Round for display (e.g. 3.0 GWh, 130 kWh/m²,
  1,200 tCO₂e). Keep full precision in state/engine inputs; only the *displayed* figure is
  rounded.
- **Benchmarking: ENERGY STAR score first, then BPD.** Lead with the asset's ENERGY STAR
  score (1–100) where available. Where a peer comparison is needed, use the **Building
  Performance Database filtered by property type + climate zone** — **never national
  medians** and never an unfiltered peer set.

**Working files (helper) — read `skills/helper-files/SKILL.md`:** maintain exactly ONE growing
internal helper HTML for the engagement, saved via `save_file` to folder **`Helper Files`** as
**`[state.helper.start_date] - Helper Files - Decarb Plan.html`** (start date fixed at P0, stored
in `state.helper`). It is a rendered *view of state* — regenerate and re-save it at **every phase
checkpoint** (P2 foundation, P3 measures, P4 write-back). Fill the skeleton at
`skills/helper-files/references/skeleton.html`; the decarb **phase/gate checklist sections** are
P0 Kickoff · P1 Evidence · P2 Model Foundation (2A model · 2B baseline+calibration · 2C split ·
2D equipment) · GATE 1 · P3 Measures · GATE 2 · P4 Write-back+Verify · P5 Deliverables. **Do NOT produce standalone intermediate/gate HTML** (no `p1-baseline.html`,
no `building-model-verification.html`) — that material is checklist sections of the helper, and
**GATE 1 / GATE 2 are reviewed as the helper's checklist sections**, not as polished artifacts.
Only the **Report** and the **Delivery-Meeting Slides** are design-forward (`Reports/`, gate-only).

**Speed & efficiency (hard rules — learned from live engagements; violating these is what makes a
run slow):**

1. **Audette WRITES: batch ≤6 per turn, checkpoint state after each batch, NEVER fire a large
   parallel write burst.** The Audette OAuth token has no persisted refresh and dies mid-burst on
   ~10+ parallel calls — which kills the turn and loses any uncheckpointed progress, forcing a
   reconnect + resume. **Batch READS ≤6 per turn too (a large read burst stalls the session — see item 6); serialize/batch WRITES** (`create_building`,
   `edit_building_attributes`, `add_building_utility_data`, `submit_equipment_survey`,
   `create_custom_plan`). After each batch, write the done/pending building UIDs to state.
2. **Read the authoritative schema/reference BEFORE any structured write — never guess arg keys.**
   One `KeyError` retry-loop (e.g. the equipment-survey DHW keys) costs more than reading
   `references/audette-modeling-recipes.md` once. Blank numeric fields are `null`, never `0`.
3. **The state file is the ONE source of truth. Resume from the checkpoint; never recompute or
   re-enter values from memory.** Adjudicated values are **LOCKED** — tag them and never revert to
   a superseded number (the 15%→5% / 2031→2034 drift). Re-query IDs/UIDs from Audette; never
   hand-carry them across threads (clubhouse UIDs went stale this way).
4. **Validate the building model (count / GFA / UID set) in P2 step 2A BEFORE any upload or
   calibration.** Discovering a model error after uploads means redoing every upload.
   **Utility-data writes are CHECK-FIRST and idempotent.** Before `add_building_utility_data`, READ
   the building's existing utility data and compare — if the meters/periods are already present and
   match the source, SKIP the upload (or upload only the missing/changed periods). Never blind-upload
   data that may already be there — it double-counts consumption and corrupts the calibrated baseline.
   And if an upload call TIMES OUT or errors, do NOT blindly retry: **re-read the building first to
   see whether the write actually landed** — a timeout is frequently a false failure (the write
   succeeded server-side but the client gave up waiting), and a reflexive retry writes a duplicate.
   Only re-upload the periods that a re-read shows are genuinely missing.
5. **At each phase start, confirm the required tools/connectors are attached; STOP if missing**
   (don't fabricate — the ESPM tripwire). Checkpoint before every expensive/irreversible action so
   a dropped connection or deploy costs one batch, not the whole run.
6. **Parallelize independent READS, but cap each turn at ~6 calls** (documents, ESPM pulls,
   reference-library, memory recall, per-building plan/measure reads). One-at-a-time is too slow,
   but a large parallel burst (~10+ calls in a single turn — e.g. CRREM pathway + all 25 custom
   plans + state + template at once) stalls the managed-agent session's tool-result handshake and
   hangs the turn (this is what repeatedly stalled P5 at "fetch CRREM + plan data simultaneously").
   Fire ~6, wait, fire the next ~6.
7. **Kickoff in ONE consolidated pass.** When an engagement reference doc exists (it usually does —
   P0 step 1), pre-fill every kickoff answer from it + any needed research and present them **all at
   once for confirmation**; ask only the genuinely-open items. Do NOT walk 8 questions one-at-a-time
   across many turns (the first Westminster run burned ~30 min doing this).
8. **Resume cheaply. `switch_customer_account` ONCE per session, then cache it.** On resume, do the
   re-orientation in one or two small batches (≤6 calls each) — state file + account switch +
   required-tool presence check + the reconciled-model doc — then continue. Don't spend multiple turns re-loading
   context after every interruption (the original run re-oriented ~7 times).

---

## Resume Protocol (run this FIRST, always)

Before anything else:

```bash
cat projects/<asset-key>/decarb-plan.json 2>/dev/null
```

- **File exists:** validate it against `skills/decarb-plan/state-schema.json`
  (`phase` must be one of `P0|P1|P2|GATE1|P3|GATE2|P4|P5|done`). Resume at the recorded
  `phase`. **Never redo a completed phase** — every phase below is idempotent against the
  ledger: skip any step whose output is already recorded in state.
- **File missing:** this is a new engagement — start at P0.
- **Phase `done`:** tell the user the engagement is complete and where the exports are
  (`report.exports`); ask whether they want a revision cycle (re-enter P5) or a new engagement.
- **Post-Gate-1 baseline changes:** if resuming (or mid-flight) you discover new or changed
  baseline data after Gate 1 was passed, set `phase` back to `GATE1` and re-present **only
  the changed items** — not the full gate. Never silently update an adjudicated baseline.

---

## P0 — Kickoff

1. **FIRST, search the portfolio files for an engagement reference document.** Before asking
   the user anything, enumerate portfolio + asset files (`list_files` / `search_files`) and
   look for an **engagement reference** document (search terms: *"engagement reference",
   "engagement summary", "scope of work", "kickoff", "engagement letter"*). If one exists,
   read it and **pre-fill the kickoff answers from it** (goal, drivers, target, hold period,
   hurdle, cap rate, constraints, contacts, deadline), **citing the document** for each
   pre-filled field. Then ask the user **only what remains open** — do not re-ask questions
   the reference document already answers; surface the pre-filled values for confirmation.
2. Invoke the **project-kickoff** skill with project type **`decarb-plan`**
   (`cat skills/project-kickoff/project-types/decarb-plan.md` for the question set).
   Kickoff checks existing asset data before asking and saves
   `projects/<asset-key>/decarb-plan-kickoff.md`. Pass through the engagement-reference
   pre-fills so kickoff confirms rather than re-asks them.
3. Map the kickoff outputs into `state.kickoff` **field-by-field**:

   | Kickoff Store-as field | State ledger field |
   |---|---|
   | `goal` | `kickoff.goal` |
   | `drivers` | `kickoff.drivers` |
   | `primary_target` `{type, value, basis}` | `kickoff.target` `{type, value, basis}` |
   | `secondary_targets` | `kickoff.secondary_targets` |
   | `hold_period_years` | `kickoff.hold_period_years` |
   | `capital_events` | `kickoff.capital_events` |
   | `equipment_commitments` | `kickoff.equipment_commitments` |
   | `budget_ceiling` | `kickoff.budget_ceiling` |
   | `financing_appetite` | `kickoff.financing_appetite` |
   | `irr_hurdle` `{value, source}` | `kickoff.irr_hurdle` — source string **verbatim, never paraphrased** |
   | `turn_schedule` | `kickoff.turn_schedule` |
   | `disruption_tolerance` | `kickoff.disruption_tolerance` |
   | `existing_docs` | `kickoff.existing_docs` (also seeds `documents` in P1) |
   | `documents_expected` | `kickoff.documents_expected` |
   | `cap_rate` `{value, source}` | `kickoff.cap_rate` — source string **verbatim, never paraphrased** |
   | `utility_escalation` `{elec_pct, gas_pct, source}` | `kickoff.utility_escalation` — **pre-fill OUR DEFAULTS (3%/yr electricity, 4%/yr gas) and present for confirmation/override**; these feed the recipe-8 savings cashflow. If the user gives a figure or a doc cites one, use it (source verbatim); otherwise carry the defaults, labeled "Soapbox default". |
   | `stakeholders` | `kickoff.stakeholders` |
   | `review_cadence` | `kickoff.review_cadence` |
   | `deadline` | `kickoff.deadline` |
   | `primary_contact` | `kickoff.primary_contact` |

4. Create the state file with `asset` (`{id, name, portfolio_id}` — `id` is the **Soapbox
   asset id**), the mapped `kickoff` block, and `phase: "P0"`. Create the companion
   `decarb-plan.md` and register it in Files.
5. Set `phase: "P1"` and save.

---

## P1 — Evidence Sweep

Gather every source; record everything in state as you go.

1. **Asset documents:** enumerate with `list_files` / `search_files`, read each relevant
   document (audits, PCAs, utility data) with `read_file` / `search_documents`. Record each
   in `state.documents` as `{name, type: audit|pca|utility|other, storage_path, read}` and
   mark `read: true` once ingested.
2. **Retrofit register + findings ledger:** `retrofit__get_measure_state` for the asset's
   existing measure register; load existing open findings via `verifier__list_findings(asset_id)`
   — capture `finding_ids`; the gas-split style pre-existing findings must be adjudicated at
   Gate 1 alongside new conflicts, not duplicated — plus `verifier__verification_status` and
   `verifier__get_verification_checklist` so known data-quality issues carry into
   reconciliation.
3. **Audette pulls:** resolve the asset's Audette property, then its building model(s) —
   **one property may hold several buildings.** Pull `get_building_model_details`,
   `get_equipment_survey`, and `get_available_measures` for **every** building model on the
   property, plus any existing carbon-reduction/custom plan surfaced by the model details.
   Record the building uid(s) in `state.audette.building_uid`. When aggregating
   multi-building properties to the asset level: sum capex/savings/emissions; use
   **floor-area-weighted averages** for EUI and carbon intensity; never report one building
   as if it were the whole asset. (Never call bare `list_buildings` on a large account —
   resolve by property name.)
4. **ESPM actuals** where the asset is linked — these sit at the top of the reconciliation
   hierarchy.
5. **Memory:** `verifier__recall_expertise` for shared engagement lessons + org-bank memory
   recall for this asset/client.
6. **Research — jurisdiction rules and incentives:** `retrofit__search_reference_library`
   **FIRST**, web search second. **Every claim is cited with provenance `library|web`** in
   `state.citations` as `{claim, source, provenance, url}`. No uncited claims survive to the
   report.
7. **BPS coverage — verify at the jurisdiction's official source (DEFAULT).** Do not infer BPS
   applicability from size/type alone. Check the jurisdiction's covered-buildings registry for the
   asset's actual address — prefer a data export/open dataset where one exists (many run on the
   SEED Platform, e.g. Colorado's `co.beam-portal.org` "Covered Buildings List"), else navigate the
   specific portal/map with the **Web Browser MCP** (`browser_navigate` + `browser_snapshot`; plain
   web_fetch can't render these JS maps). Record whether the address is covered, its covered-building
   ID/baseline/targets if found, and tag `verified-at-source` vs `threshold-inferred` in
   `state.targets`. Full jurisdiction source registry + procedure live in the bps-analysis skill
   (Step 1.5).

Set `phase: "P2"` and save.

---

## P2 — Model Foundation (validate → calibrate → split → equipment; LOCK before Gate 1)

Establish and **LOCK all four foundation inputs before Gate 1 or any measure work.** Every rework
in prior engagements traced to a foundation input surfacing late or drifting (building set, split,
equipment, calibration). Gate 1 opens ONLY on a locked foundation. Record each with provenance in
`state`; any disagreement becomes a `verifier__record_finding` conflict for Gate 1 adjudication.

### 2A — Physical model validation (hard gate)

The Audette building count and per-building GFA are frequently auto-generated (footprint-matched
or total÷N) and WRONG. Before uploading utility/equipment data or calibrating, reconcile the model
against ground truth:

- Pull per-building footprints from the **ALTA / boundary survey** and **PCA** (search the asset's
  documents). These give real building count, per-building footprint/GFA, and structure type
  (residential vs clubhouse/amenity vs utility/mechanical).
- Confirm, and record each check as state: (a) building COUNT matches the survey; (b) each building's
  GFA matches its real footprint (not an even split); (c) the sum of building GFAs reconciles to the
  property total (flag any unexplained delta); (d) non-residential structures are identified and typed.
- If the model does NOT reconcile (wrong count, even-split GFAs, unreconciled total, mis-typed
  amenity buildings), **STOP**: record a `verifier__record_finding` (kind data-quality, asset_id,
  severity high) describing the discrepancy and surface it for adjudication. Do NOT upload utility
  data, calibrate, or generate measures against a model that fails validation — a 10–20% calibration
  "gap" is usually a building-model error, not an emission-factor difference.
- **Materialize the COMPLETE, correct building set here — before any per-building write.** If the
  model is short buildings (e.g. Audette has 17 but the survey shows 27), create ALL the missing
  buildings, assign the shared property_id, and lock the final UID set into state IN ONE validated
  step. Do not begin per-building edits/uploads on a partial set and discover the missing ones
  mid-stream (the first run churned 17→27 that way, forcing rework). Batch the `create_building`
  calls ≤6/turn per the Audette-write rule, checkpointing UIDs after each batch.
- Only once the model reconciles (or the owner adjudicates the correct structure) proceed. Then apply
  the [[utility-split-estimation]] allocation rule: carve out common/amenity loads first, allocate the
  remainder GFA-weighted (never even), and set landlord shares per building/end-use (tenant-metered
  fuel = 0% on residential buildings, 100% on amenity buildings).
- For Audette mechanics — building rebuilds, landlord shares, equipment survey patterns — read
  `references/audette-modeling-recipes.md`.

### 2B — Measured-energy baseline + calibration

**Calibrate to measured energy — don't ask whether it's authoritative.** If measured whole-building
energy exists (ESPM actuals, utility bills) and is sane, extract it, upload it to Audette, and
adjust calibration factors until the model matches — rather than asking the user to choose between
measured and modeled. A residual 10–20% gap after calibration is almost always a building-model
error (revisit 2A), not an emission-factor difference. Pull ESPM via the energy-star tools (verify
they're attached first — the tripwire); read the energy sub-skill for the exact tool sequence.

**Calibration is a HARD gate on the economics.** An uncalibrated model inflates BOTH projected
savings and costs, so no measure IRR is trustworthy until it is calibrated. If the model's
first-year energy is **> ~10% off** measured (ESPM/bills) after calibration, **do NOT run measure
economics (P3)** — record a `verifier__record_finding` (kind `data-quality`, verdict `conflict`,
severity by materiality) and return to 2A/2B to fix it. (In the Cortland Rosslyn engagement the
raw model was **+35%** over ESPM; uploading actuals + calibrating brought it to within ~4% and
materially changed every measure's economics.) Record the post-calibration gap in `state.baseline`
with its source.

Build the baseline table in `state.baseline`. Required fields (each stored as
`{value, unit, source}`):

- Electricity: kWh/yr + $/yr
- Gas: native units (therms/m³) **and** GJ, + $/yr
- Owner/tenant utility splits
- GFA, unit count, floors, year built
- Equipment inventory with install years
- Emissions tCO2e — with the emission-factor source named (factors via Audette/CRREM tooling)

For **each field**: gather ALL candidate values with their sources.

- **All sources agree** → record the value with its source in `state.baseline`.
- **Sources disagree** → do NOT pick one. Create a conflict row in `state.conflicts`:
  `{field, candidates: [{value, source}...], suggested: {value, source, rule}, finding_id}`
  where `suggested` is computed from the hierarchy (measured utility/ESPM actuals >
  audit-reported 12-mo > Audette modeled > estimates) and `rule` names which hierarchy rule
  fired. Then call `verifier__record_finding` (kind `data-quality`, severity by materiality
  of the field to targets/economics, verdict `conflict`, with `evidence[]` — the candidate
  values and their sources — and `sources[]`) and store the returned `finding_id` on the row.

**NO auto-resolution.** Every conflict waits for Gate 1.

### 2C — Utility split (per fuel, per building)

Establish the owner/tenant utility split **per fuel, per building** via the
**utility-split-estimation** skill (`cat skills/utility-split-estimation/SKILL.md`) — building form
+ jurisdiction RUBS rules + on-file docs + leasing evidence. Never default to 100%-owner or a round
number. Tenant-metered fuel = 0% owner on residential; amenity/clubhouse buildings are typically
100% owner on both fuels. The split is the **savings basis for every retrofit IRR**, so it is a
foundation input, not a P3 afterthought. Record it in `state.baseline`; an unconfirmed or presumed
split is a `verifier__record_finding` conflict adjudicated at Gate 1.

**Capture is PER END-USE, not one blended number per building.** A single residential building
has BOTH tenant-metered in-unit loads (in-unit electric HVAC/appliances ≈ the tenant %) AND
landlord-paid loads that are **100% owner regardless of the building's headline split**: the
central heating/DHW plant, elevators, garage ventilation, corridor/common-area lighting, and
amenity loads (spa, pool, common laundry). Build a **capture map** in `state.capture_map`
— every end-use a measure could touch → who pays → owner-capture % — and **never inherit Audette's
account-default landlord share (commonly 15%) onto a measure whose end-use is landlord-paid.** This
one gap sat behind four of the Cortland Rosslyn model errors: the central gas plant carried the 15%
default (belongs at 100%, which undervalued every gas measure) and elevator regen showed −6% IRR at
15% → **+12% at its true 100% common-area capture**. Where an end-use's payer is unconfirmed (in-unit
vs common laundry, spa heat source, garage metering), record a `verifier__record_finding` conflict
and resolve at Gate 1 — public listing sources (apartments.com, Zillow) are valid cited evidence.

### 2D — Equipment inventory (establish now — it drives P3 measure sequencing)

Gather the **real** equipment set + install years / remaining useful life (RUL) from the PCA / MEP
drawings / audit **now** — equipment type and RUL determine electrification timing (electrify at
end-of-life, DHW→HPWH at RUL), so the roadmap in P3 cannot be sequenced without it. Map each system
to its Audette representation per `references/audette-modeling-recipes.md` recipe 5 (e.g. hydronic
furnaces → native `hydronic_furnace`, not a fan-coil proxy). Record the inventory in `state`.
NOTE: the Audette `submit_equipment_survey` **write-back** happens in P4; here you establish the
inventory *knowledge* that feeds measure selection.

### Foundation lock

All four inputs — validated physical model (2A), calibrated measured baseline (2B), per-fuel/
per-building split (2C), equipment inventory (2D) — recorded in `state` with provenance, and every
disagreement captured as a verifier conflict. **Do not proceed to Gate 1 until the foundation is
locked.** Set `phase: "GATE1"` and save.

---

## GATE 1 — Foundation, Conflicts, Split/Exit, Targets (user)

Gate 1 opens **only on a locked Model Foundation (P2)**. Present these blocks, then **stop and wait
for the user**:

Present each adjudication/decision to the user via `ask_user_question` (one call per decision — options = the candidate values, recommended/suggested first, allow_other:true, context = the one-line why-it-matters), not as one markdown table wall. Fall back to one-decision-per-message lettered multiple-choice if the tool is unavailable.

**(a) Verified foundation** — the validated building model (count/GFA/types), calibrated baseline
(with the measured source + residual calibration gap), and every agreed field with value, unit, source.

**(b) Conflicts** — every row of `state.conflicts` as a **numbered decision**: candidates
with sources, the suggested resolution, and the hierarchy rule that produced the suggestion.
The user decides each one; the suggestion is never applied without their word.

**(c) Split & exit — the two economic-gating decisions.** Present the per-fuel/per-building
utility split (2C) and the exit assumptions (exit year + cap rate) for explicit confirmation.
These gate every IRR, so they must be adjudicated and **LOCKED here** — once locked, no later phase
re-enters a superseded value (past runs drifted 15%→5% / 2031→2034). Record the locked values with
`adjudicated_by: "user"` in `state.baseline` / `state.kickoff`.

**(d) Target trajectory** — computed from `kickoff.target.type`, engine math only:

| Target type | How the trajectory is computed |
|---|---|
| `crrem` | CRREM pathway points via crrem tooling → `state.targets.trajectory` |
| `bps-fine-avoidance` | Jurisdiction milestone table + fine-exposure via engines/Audette compliance analysis (`run_compliance_analysis`) → `state.targets.bps_milestones` + `state.targets.fine_exposure` |
| `percent` | Reduction-vs-baseline-year math via the cashflow/DCF engines |
| `net-zero-year` | Glide path to zero via engines/Audette analysis |

**Never LLM arithmetic** — if the engine for a target type is unavailable, the gate is
blocked (see Failure Handling), not approximated.

On the user's adjudications:

1. Write each decision into the conflict row's `adjudication`:
   `{value, source, adjudicated_by: "user", date}`.
2. Call `verifier__resolve_finding` for each adjudicated conflict's `finding_id`, with
   `resolution` `confirmed` or `dismissed` plus `note` (the adjudication rationale).
3. Promote adjudicated values into `state.baseline` with the adjudicated source.
4. On target confirmation, set `state.targets.confirmed_at`.

Set `phase: "P3"` and save.

---

## P3 — Measure Plan

1. `retrofit__propose_candidates` with the **real, adjudicated asset attributes** from
   `state.baseline` (never pre-Gate-1 values).
1a. **Completeness cross-check — screen DOWN from a full universe, not UP from the optimizer's
   output.** `retrofit__propose_candidates` and Audette's optimizer return a *starting* set, not the
   whole opportunity space. Before screening, reconcile the proposal against the standard candidate
   library for THIS building's systems — read `references/measure-universe.md` and confirm every
   applicable category was considered: envelope, HVAC plant + distribution, controls/retro-commissioning,
   DHW, lighting + lighting controls, plug/appliance, **common-area/amenity loads** (elevators, garage
   ventilation, spa/pool, common laundry), on-site generation/storage, EV, and procurement. Explicitly
   note each category as evaluated / screened-out-with-reason / not-applicable. A GRESB or
   portfolio deliverable that reaches the roster with only a handful of measures because the optimizer
   returned few is a red flag — the Cortland Rosslyn roster sat at 2 measures until challenged, then
   4+ real candidates surfaced (garage DCV, lighting controls, EV expansion, amenity HPHX).
2. Pull all source candidates the proposal references (register, Audette available measures,
   document-recommended measures).
3. For candidates needing modeled physics (savings/carbon), run Audette
   `run_measure_design_analysis`. Read `retrofit__get_retrofit_playbook('baseline-discipline')`
   and **mark all modeled savings as provisional** per that playbook — modeled numbers are not
   measured numbers and are labeled as such through to the report.
4. `retrofit__evaluate_measure` for **EVERY** candidate. Reminders:
   - `asset_id` = the **Soapbox asset id** (`state.asset.id`) — not the Audette uid.
   - `feasibility.score` is an **INTEGER 1–5**.
   - Every economic field must be engine- or source-provenanced; the tool refuses
     unprovenanced numbers — supply real sources, never fabricate provenance.
   - Cap rate for exit math comes from `kickoff.cap_rate` **with its verbatim source string**.
   - **Savings basis = the LOCKED per-end-use capture (from the 2C capture map, Gate 1).** A
     measure's dollar savings accrue only to the party that pays **that end-use's** bill — so a
     common-area or central-plant measure (elevators, garage ventilation, corridor lighting,
     central heating/DHW) uses its **100% owner capture, NOT the building's blended in-unit split**,
     even in a tenant-metered residential building. Never inherit Audette's account-default share;
     set Audette's landlord-share for the measure to the end-use's locked capture or modeled owner
     savings are mis-priced. Do NOT re-derive or re-open the map here.
   - Record returned measure ids in `state.measures.register_ids`.
5. `retrofit__screen_measures` to produce the roster labels.
6. **Roadmap phasing — sequence by decarb logic + equipment RUL, not independent IRR.** Read
   `retrofit__get_retrofit_playbook('staging')`. Order measures as: load-reduction / controls &
   retro-commissioning FIRST, then electrification of heating/DHW **timed to each system's RUL**
   (from the 2D equipment inventory) and to `kickoff.capital_events`, then supply (solar/storage)
   aligned to roof life. Screen by IRR ≥ hurdle *within* that sequence — never let a high-IRR
   measure jump ahead of the load-reduction it depends on. Write `state.measures.roadmap_phases`.
7. **Target-gap statement:** does the recommended set reach the confirmed target
   (`state.targets`)? If not, which defensive additions close the gap and at what cost —
   engine math only. Write `state.measures.gap_statement`.

Set `phase: "GATE2"` and save.

---

## GATE 2 — Roster, Roadmap, Gap (user)

Present, then **stop and wait for the user**:

Present each adjudication/decision to the user via `ask_user_question` (one call per decision — options = the candidate values, recommended/suggested first, allow_other:true, context = the one-line why-it-matters), not as one markdown table wall. Fall back to one-decision-per-message lettered multiple-choice if the tool is unavailable.

1. **Roster** — every measure under all four screening labels
   (recommended / defensive / screened-out / needs-data), each with its reason, including the
   named failing test for screened-out measures.
2. **Phased roadmap** — per-phase capex, NOI delta, and exit impact. **Engine numbers only.**
3. **Target-gap statement** — `state.measures.gap_statement`, with defensive closures priced.

The user confirms or edits the selection. Apply every edit via
`retrofit__update_measure_state` (never by editing state alone — the register is the system
of record for measure status). On confirmation set `state.measures.gate2_confirmed_at`.

Set `phase: "P4"` and save.

---

## P4 — Write-Back + Verification

1. **Audette write-back:** `create_custom_plan` with the confirmed measure set — or
   `update_custom_plan_measures` if `state.audette.custom_plan_id` already exists. Record the
   plan id in `state.audette.custom_plan_id`.
2. **Equipment survey write-back:** submit the equipment inventory established in P2 (step 2D) —
   and any Gate-1-adjudicated corrections — to Audette via `submit_equipment_survey`. (The inventory
   *knowledge* was gathered in 2D to drive P3 sequencing; this is the deferred *write*.) Record each
   submission in `state.audette.survey_corrections_submitted`.
   **BEFORE the first submit, read `references/audette-modeling-recipes.md` recipe 5** — the
   `equipment_survey` arg schema is free-form but the backend inferrer REQUIRES all 10 equipment
   groups present (each with `<group>_exists`), DHW needs `_central_distribution` +
   `_average_installation_year` keys, enum values are lowercase_snake (`hydronic_furnace`,
   `gas_heater`, …), and blank sizes/years must be `null` not `0`. Do NOT guess keys — copy the
   recipe's payload template. Hydronic furnaces map to `central_plant_heater_type=hydronic_furnace`
   (native match), never the fan-coil proxy. Submit in batches of ≤6 buildings per turn (the Audette
   OAuth token dies on large parallel bursts) and verify each with `get_equipment_survey`.
3. **RENDER GATE (HARD):** call `verifier__verification_status` for the asset and write the
   result to `state.report.verification_status`. The deployed tool returns
   `{pass: boolean, open_high: number, open_total: number}` — store that shape verbatim.
   Enumerate open findings via `verifier__list_findings` before deciding overrides.
   - **Pass** → proceed to P5.
   - **Not pass** → resolve findings, or — only with explicit user approval — record a
     documented override `{finding_id, override_reason, approved_by}` in
     `state.report.overrides` for **each** open high-severity finding.
   - Neither → **no render. The gate fails CLOSED.** Do not dispatch the renderer, do not
     produce a partial report, do not summarize around it.

Set `phase: "P5"` and save.

---

## P5 — Report

Before dispatching any render, re-run `verifier__verification_status` and re-confirm the
gate (resume may have skipped P4's check).

1. **Assemble the report data object** per `templates/decarb/schema.json` — the authoritative
   schema the template consumes (its field names are exactly what the template's `populateReport()`
   JS reads). Include the **`economics`** object (per-plan `waterfall` 5 components + annual
   `cashflow` + `plans` + exit cap/year) built per **recipe 8** in `references/audette-modeling-recipes.md`.
   Record the object in `state.report.data`.

   The report is **dashboard-first**: the template renders a Decision Dashboard (compliance
   chip, hero KPI tiles, one-line recommendation, cumulative-cashflow J-curve sparkline)
   from `data.dashboard`, then a Scenario Comparison strip (renders whenever
   `economics.plans` has **2+ plans** — present at least 2 scenarios where applicable, e.g.
   near-term positive-IRR vs CRREM-aligned), then per-plan waterfalls + cashflows, roadmap,
   emissions trajectory, and appendices. **Populate `data.dashboard`** (every field nullable;
   values from the selected plan's engine outputs — never LLM-computed) and the per-plan
   comparison fields (`irr_incremental`, `ghgi_reduction_pct`, `compliant`). If `dashboard`
   is omitted the template falls back to the legacy executive-summary row.

   **CRREM pathway (`targets.crrem_pathway` + `targets.crrem_meta`):** source the REAL curve
   from the **crrem MCP server** — call `crrem get_pathway` with the asset's country, region,
   property type, and scenario (`get_climate_zone(zip)` returns a `crrem_region_hint`), and
   pass the points as `targets.crrem_pathway` (`[{year, carbon_kgco2_m2yr}]`) with
   `targets.crrem_meta {country, region, property_type, scenario}`. **Never fabricate,
   extrapolate, or hand-interpolate the curve.** The template draws it as a distinct dashed
   line alongside the stepped `bps_target` line — BPS drives fines, CRREM drives stranding —
   and annotates the stranding year. All trajectory series are kgCO₂e·m⁻²·yr⁻¹; convert
   per-ft² GHGI values before filling.

   **Baseline/BAU carbon curve:** use the **actual Audette-modeled baseline carbon curve**
   (`state.targets` trajectory from Audette engine outputs, including grid-factor drift)
   for `bau`/`planned` wherever available — never a fabricated flat line.

   Section→source mapping:

   | Data key | Source in state |
   |---|---|
   | property / baseline | `state.baseline` (validated model + calibrated baseline, values + sources) |
   | dashboard | selected plan in `state.economics` + `state.targets` (compliance status, net value, IRR vs hurdle, capital ask, GHGI change, downside avoided, CF-positive year) |
   | targets / trajectory | `state.targets` (Audette baseline/planned carbon curves, BPS milestones, fine exposure) |
   | targets.crrem_pathway / crrem_meta | crrem MCP server `get_pathway` (region via `get_climate_zone(zip)` hint) — real curve only |
   | measures / roadmap | measure register via `state.measures.register_ids` + `state.measures.roadmap_phases` |
   | economics (waterfall + cashflow + plans, incl. per-plan `ghgi_reduction_pct`/`compliant`) | `state.economics` (recipe 8 — owner-share, incremental-over-LfL, fines as PV, capitalized savings/ancillary) |
   | data_quality | a **client-facing** confidence summary (`summary` + `items[]` dots) derived from `state.conflicts` / verifier findings — see the EXTERNAL-DELIVERABLE rule below. Do **NOT** pass an `adjudications[]` array (the internal reconciliation ledger is not rendered and must not be sent). |
   | sources | `state.citations` (cite the CRREM pathway export run) |

   **⚠️ EXTERNAL DELIVERABLE — no internal-process language anywhere in the report data.**
   The report is sent to external parties (owners, lenders, buyers) who have **no context**
   for our internal workflow. Nothing you put in ANY field — exec summary, dashboard, plan
   `label`/`name`, `data_quality.summary`/`items[]`, methodology, findings — may reference our
   internal process. Banned terms/patterns: **"Gate 1/2" / "Gate-1"/"Gate-2" / "at Gate…" /
   "locked at gate"**, **"adjudicated" / "adjudication" / "adjudicated_by"**, **"verifier" /
   "verification gate" / "Confirmed finding &lt;id&gt;" / raw finding IDs**, **"P0–P5" / "phase N"
   / "workflow" / "roster"**. Rephrase in client terms: instead of *"Utility split: Locked at
   Gate 1 — audit confirms…"* write *"Utility split confirmed by the AEI energy audit
   (475250-EA1)."*; instead of a plan label *"Solar (No ITC) — full Gate-2 roster ✓ Selected"*
   write *"Solar (No ITC) — Recommended"*. Confidence and provenance are welcome; the internal
   machinery that produced them is not.

2. **Render via `fill_report` — the SAME path RSRA uses (default; do not hand-write HTML or draw
   charts).** Call `fill_report(template: 'decarb', data: <the object from step 1>, title: "<Asset> — Decarbonization Roadmap")`.
   The server injects the JSON into the template's `<script id="report-data">` block and the
   template's own JavaScript renders every section and every chart from it — the **decision
   dashboard + J-curve sparkline**, the **scenario comparison strip**, the **value-creation
   waterfall SVG** per plan, and the **emissions trajectory with the CRREM pathway curve**.
   You write NO report HTML and draw NO charts — your only job is to compute the data
   object. (This mirrors rsra exactly. The old `[[TOKEN]]` / `get_report_template` + agent-fill
   path is retired — `templates/decarb/layout-agent.html` is now a client-render template.) The
   render is verifier-gated server-side; if blocked, fix findings and retry. Record
   `state.report.render_iterations` starting at 0.

3. **Revision loop — DATA-ONLY.** On user revisions, recompute the data object and call
   `fill_report(same artifact_id, template, updated_data)` — and NOTHING else (increment
   `state.report.render_iterations`); on approval export **PDF and/or PPTX**. NEVER `save_file` a
   hand-built report and NEVER hand-edit or reproduce the template's inlined HTML / chart /
   waterfall renderers to "apply" a revision — the template owns all rendering and is re-fetched
   fresh on every `fill_report` (so a re-fill also picks up any template fixes; a baked artifact
   does not). Hand-rebuilding mangles charts, drops blocks, reintroduces overflow, and bypasses the
   gate. You only ever touch the data payload.

   **Small presentation-layer tweaks → `patch_report`, not a full re-render.** For a minor edit
   after the report exists — reword a sentence, adjust a `data_quality`/`methodology` note, fix a
   non-cascading value (address, year built, a citation), or hide a section (set its key to
   `null`) — call **`patch_report(artifact_id, patch)`** with ONLY the changed fields (a JSON
   Merge Patch). It loads the persisted data object, merges your delta, and re-renders in place —
   no recomputation of the whole data object, far cheaper, and it re-runs the same verifier gate.
   `patch_report` rejects analytical fields (`economics`, `targets`, `dashboard`, …): any change
   to a headline number — or renaming a plan / reordering sections — still goes through a full
   `fill_report(same artifact_id, updated_data)` so the figures re-derive from state and re-pass
   the gate.
4. **Register the deliverable in Files.** `fill_report` already persists the fully-rendered HTML
   report to `Reports/` for you (server-side) — do **NOT** `save_file` the report HTML yourself
   (you don't hold the rendered ~80KB string, so a manual save would only write a broken stub).
   Just write all export paths (PDF/PPTX) to `state.report.exports`.
5. **Retain lessons:** call `verifier__retain_shared_expertise` with the generalizable,
   client-anonymous lessons from this engagement (reconciliation patterns, playbook gaps,
   jurisdiction findings). It will refuse content that identifies the client or asset —
   **never rephrase, strip, or restructure content to work around a refusal.** A refusal
   means the lesson is not generalizable; drop it.

Set `phase: "done"`, update the companion `decarb-plan.md`, and save.

---

## Failure Handling

Named blockers, never silent: Audette/verifier/renderer outages halt the phase with the
standing reconnect message; the state file always reflects the last completed step. The
render gate fails CLOSED. Conflicting data discovered after Gate 1 reopens Gate 1 rather
than silently updating the baseline.

In practice:

- **Audette outage** mid-P1/P3/P4: stop the phase, tell the user the Audette integration
  needs reconnecting, save state at the last completed step. Do not substitute estimates for
  the modeled physics and continue.
- **Verifier outage** at P2/Gate 1/P4: stop — conflicts cannot be recorded/resolved and the
  render gate cannot be evaluated without it. Never proceed on the assumption it would pass.
- **Renderer outage** at P5: stop after saving `state.report.data_json_path` — the data JSON
  is durable; rendering resumes when the renderer is back.
- **Gate-1 reopen:** any post-Gate-1 change to baseline data sets `phase: "GATE1"` and
  re-presents only the changed items (see Resume Protocol). Adjudicated values are never
  overwritten without the user re-adjudicating.
