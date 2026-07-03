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
version: 1.0.0
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
4. **Never fail silently.** Outages halt the phase with the standing reconnect message.

**State ledger:** `projects/<asset-key>/decarb-plan.json`, conforming to
`skills/decarb-plan/state-schema.json`. Human-readable companion:
`projects/<asset-key>/decarb-plan.md`, registered in Files. Update BOTH at every phase
boundary. `<asset-key>` follows the project-kickoff convention: lowercase the asset name,
replace spaces with hyphens.

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

1. Invoke the **project-kickoff** skill with project type **`decarb-plan`**
   (`cat skills/project-kickoff/project-types/decarb-plan.md` for the question set).
   Kickoff checks existing asset data before asking and saves
   `projects/<asset-key>/decarb-plan-kickoff.md`.
2. Map the kickoff outputs into `state.kickoff` **field-by-field**:

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
   | `turn_schedule` | `kickoff.turn_schedule` |
   | `disruption_tolerance` | `kickoff.disruption_tolerance` |
   | `existing_docs` | `kickoff.existing_docs` (also seeds `documents` in P1) |
   | `documents_expected` | `kickoff.documents_expected` |
   | `cap_rate` `{value, source}` | `kickoff.cap_rate` — source string **verbatim, never paraphrased** |
   | `stakeholders` | `kickoff.stakeholders` |
   | `review_cadence` | `kickoff.review_cadence` |
   | `deadline` | `kickoff.deadline` |
   | `primary_contact` | `kickoff.primary_contact` |

3. Create the state file with `asset` (`{id, name, portfolio_id}` — `id` is the **Soapbox
   asset id**), the mapped `kickoff` block, and `phase: "P0"`. Create the companion
   `decarb-plan.md` and register it in Files.
4. Set `phase: "P1"` and save.

---

## P1 — Evidence Sweep

Gather every source; record everything in state as you go.

1. **Asset documents:** enumerate with `list_files` / `search_files`, read each relevant
   document (audits, PCAs, utility data) with `read_file` / `search_documents`. Record each
   in `state.documents` as `{name, type: audit|pca|utility|other, storage_path, read}` and
   mark `read: true` once ingested.
2. **Retrofit register + findings ledger:** `retrofit__get_measure_state` for the asset's
   existing measure register; load open `verifier__` findings via
   `verifier__verification_status` and `verifier__get_verification_checklist` so known
   data-quality issues carry into reconciliation.
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

Set `phase: "P2"` and save.

---

## P2 — Baseline Reconciliation

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
  of the field to targets/economics) and store the returned `finding_id` on the row.

**NO auto-resolution.** Every conflict waits for Gate 1.

Set `phase: "GATE1"` and save.

---

## GATE 1 — Baseline, Conflicts, Targets (user)

Present exactly three blocks, then **stop and wait for the user**:

**(a) Verified baseline** — every agreed field with value, unit, source.

**(b) Conflicts** — every row of `state.conflicts` as a **numbered decision**: candidates
with sources, the suggested resolution, and the hierarchy rule that produced the suggestion.
The user decides each one; the suggestion is never applied without their word.

**(c) Target trajectory** — computed from `kickoff.target.type`, engine math only:

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
2. Call `verifier__resolve_finding` for each adjudicated conflict's `finding_id`.
3. Promote adjudicated values into `state.baseline` with the adjudicated source.
4. On target confirmation, set `state.targets.confirmed_at`.

Set `phase: "P3"` and save.

---

## P3 — Measure Plan

1. `retrofit__propose_candidates` with the **real, adjudicated asset attributes** from
   `state.baseline` (never pre-Gate-1 values).
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
   - Record returned measure ids in `state.measures.register_ids`.
5. `retrofit__screen_measures` to produce the roster labels.
6. **Roadmap phasing:** read `retrofit__get_retrofit_playbook('staging')` and phase measures
   against `kickoff.capital_events` and equipment end-of-life (from the equipment survey +
   adjudicated install years). Write `state.measures.roadmap_phases`.
7. **Target-gap statement:** does the recommended set reach the confirmed target
   (`state.targets`)? If not, which defensive additions close the gap and at what cost —
   engine math only. Write `state.measures.gap_statement`.

Set `phase: "GATE2"` and save.

---

## GATE 2 — Roster, Roadmap, Gap (user)

Present, then **stop and wait for the user**:

1. **Roster** — every measure under all four screening labels
   (recommended / defensive / screened-out / deferred), each with its reason, including the
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
2. **Survey corrections:** for every adjudicated equipment conflict, `submit_equipment_survey`
   with the corrected values. Record each submission in
   `state.audette.survey_corrections_submitted`.
3. **RENDER GATE (HARD):** call `verifier__verification_status` for the asset and write the
   result to `state.report.verification_status`. The deployed tool returns
   `{pass: boolean, open_high: number, open_total: number}` — store that shape verbatim.
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

1. **Assemble the report data JSON** per `templates/decarb/example-data.json` — the
   **authoritative example payload** (created by Task 3; its field names are exactly what the
   template consumes). Save it and record the path in `state.report.data_json_path`.
   Section mapping:

   | Template section | Source in state |
   |---|---|
   | Baseline Performance | `state.baseline` (values + sources) |
   | Decarbonization Feasibility | `state.targets` (trajectory, milestones, fine exposure) |
   | Recommended Measures | measure register via `state.measures.register_ids` |
   | CRREM-Aligned Measures | measure register, CRREM-flagged entries |
   | Exit-value scenarios | engine outputs (capitalized at `kickoff.cap_rate`, source cited) |
   | Data Quality & Adjudications appendix | `state.conflicts` (incl. adjudications) + verifier findings |
   | Methodology & Sources | `state.citations` |

2. **Render via template-mcp** (same entry point as the rsra skill, NOT the `report-renderer`
   subagent, which is built around a different schema/layout/sections contract that
   `templates/decarb` does not have). Unlike rsra's template, `templates/decarb/layout-agent.html`
   has no `<script id="report-data">` block and no client-side rendering JS — it is
   **agent-filled**, so the agent (not the tool) must do the substitution:
   - Call `get_report_template('decarb')` to fetch `layout-agent.html`. (Tool names verified against the live service 2026-07-03: get_report_template / fill_report — if these error, list the template server's tools and adapt rather than failing silently.)
   - Replace every `[[TOKEN]]` scalar placeholder with the assembled data, and expand every
     repeated-row placeholder (`[[SCENARIO_1_ROWS]]`, `[[ROADMAP_ROWS]]`,
     `[[ADJUDICATION_ROWS]]`, `[[CITATION_ROWS]]`, etc.) into literal `<tr>`/card HTML — one
     block per data row, matching the commented example directly below each placeholder in
     the template. Field names exactly as `templates/decarb/example-data.json` documents.
   - Pass the fully-filled HTML through `fill_report({report_type: 'decarb', data: <filled-html>})` to produce the artifact, then hand off
     to `report-review` for the interactive loop, same as rsra.
   - Record `state.report.render_iterations` starting at 0.

3. **Loop `report-review`:** present the artifact, apply user revisions (re-fill the template
   with updated data and re-call `fill_report`; increment `state.report.render_iterations`),
   and on approval export **PDF and/or PPTX** — this loop is unchanged from the
   subagent-dispatch flow.
4. **Register the deliverable in Files** and write all export paths to
   `state.report.exports`.
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
