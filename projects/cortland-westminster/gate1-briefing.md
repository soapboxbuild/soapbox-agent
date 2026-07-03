# Gate 1 Briefing — Cortland Westminster Decarbonization Engagement

Status: P1 (evidence sweep) and P2 (baseline reconciliation) complete. Phase set to `GATE1`.
Nothing below has been auto-resolved — every conflict is presented as a numbered decision for you.

---

## (a) Verified Baseline

| Field | Value | Source |
|---|---|---|
| Electricity | 3,000,668 kWh/yr / $487,426/yr | AEI Energy & Water Audit 475250-EA1 (Nov 2023) |
| Gas | 24,154 GJ/yr / $371,948/yr | AEI Energy & Water Audit 475250-EA1 (Nov 2023) |
| GFA | 724,081 ft² | Agreement within rounding: Overture footprint-weighted helper dataset (724,081 ft²) vs audit (724,079 ft²) — both recorded, 724,081 used |
| Floors | 3 | Prior extraction / kickoff |
| Year built | 2003 | AEI audit + PCA agree |
| Buildings | 17 | Audette property group (property_uid 7d56c04e-ff1b-49bd-a918-14c36363a7cc) |
| Equipment — split AHUs, gas heat | avg install 2009 | AEI audit equipment survey |
| Equipment — gas DHW | avg install 2014 | AEI audit + helper-data agree; **confirmed** finding `31e99e2b-71f7-4f1f-b112-dcdeb7aede32` |
| Equipment — washers/dryers | avg install 2018 | AEI audit equipment survey |
| Units | **CONFLICTED — see conflict #1** | — |
| Owner/tenant gas split | **CONFLICTED — see conflict #2 (pre-existing finding)** | — |
| Emissions (tCO2e) | **NOT AVAILABLE** | Audette building-model emissions could not be pulled this phase (see "What could not be verified" below); no LLM-computed substitute produced |

---

## (b) Conflicts — numbered decisions

### 1. Unit count
- Candidates:
  - **504** — helper/platform dataset (Cortland Batch 1 helper data)
  - **504** — AEI audit 475250-EA1 summary table (one instance)
  - **530** — AEI audit 475250-EA1 property-info block, p.1 (per prior extraction)
- Suggested: **504**, from the helper/platform dataset.
- Rule: audit-reported 12-mo figures normally rank above estimates, but the audit contradicts itself (504 in its own summary table vs 530 in its property-info block). With the audit split against itself, the independently-sourced helper dataset (504) is used as the tiebreak *suggestion only* — this is materially important since unit count feeds measure-cost/unit economics (e.g., the NEST thermostat measure is priced per unit).
- Verifier finding: `14aedb80-ecc8-41c1-bd74-bb03bc3c8c05` (severity: high, verdict: conflict)
- **Your call needed.**

### 2. Owner/tenant gas split (pre-existing finding — not duplicated)
- Candidates:
  - Owner-paid $371,948/yr (100% of billed gas) — AEI audit cost-split analysis
  - Unconfirmed actual split — helper-data flags Medium confidence (EST), metering configuration unconfirmed
- Suggested: use the audit figure provisionally, pending metering confirmation — no measured/ESPM actuals exist to outrank it.
- Rule: measured utility/ESPM actuals > audit-reported 12-mo > estimate. No measured actuals exist, so audit stands provisionally, but confidence is explicitly Medium/EST.
- Verifier finding: `bbc6908d-125b-4a36-a262-d8652d8c19bb` (this is the **pre-existing open HIGH finding** surfaced by `verifier__list_findings` — referenced here, not duplicated).
- **Your call needed.** This also gates several measure economics already in the retrofit register (e.g., EBCx measure `bd73ea95-3d05-48bf-9e0e-31e436aacb81` explicitly says its savings are provisional until this is resolved).

### 3. Baseline year vs. Reg 28 statutory baseline (methodology gap — flagging as its own question)
- Candidates:
  - 2023 — the only audit data we have (AEI 475250-EA1, a Nov 2023 12-month period)
  - 2021 — the year CO Reg 28 (HB21-1286) actually requires as the baseline for the -7% (2026) / -20% (2030) milestones
- Suggested: **none.** The reconciliation hierarchy has no rule for substituting a different year's data for a missing statutory baseline year — this is a scope/methodology decision, not a value pick.
- Verifier finding: `784f5591-8e4b-4bde-b977-a06826bc08a7` (severity: high, verdict: conflict)
- **This blocks Reg 28 target-trajectory math in Gate 1(c) below** — see "Pending adjudication" section.

---

## (c) Target trajectory — PENDING, cannot be computed yet

`kickoff.target.type` = `bps-fine-avoidance` (Colorado Reg 28 / HB21-1286). Per the skill, this requires
jurisdiction milestone table + fine-exposure via engines/Audette `run_compliance_analysis`, computed
against **the 2021 baseline year**.

This is blocked, not approximated, for two independent reasons:

1. **No 2021 baseline data exists in this engagement.** Only Nov-2023 audit data was sourced. Conflict #3
   above is the open question: do we (a) obtain real 2021 utility bills/ESPM actuals, or (b) knowingly use
   the 2023 audit as a disclosed proxy baseline (with the compliance math and report explicitly flagging
   that substitution)? This decision is yours — no target math has been run pending it.
2. **`run_compliance_analysis` requires a `building_model_uid`**, and building-level Audette model details
   could not be pulled this phase (see below) — even a disclosed-proxy run cannot execute yet without that.

No CRREM/BPS numbers are reported here — none were computed, consistent with "never LLM arithmetic, block
rather than approximate."

---

## What could not be verified / done this phase

- **Audette building-model details / equipment survey / emissions were not pulled.** The property
  (`Cortland Westminster`, `property_uid 7d56c04e-ff1b-49bd-a918-14c36363a7cc`, 17 buildings) was resolved
  via `list_properties` (account-scoped, not the disallowed bare `list_buildings`). But both
  `get_equipment_survey` and `get_building_model_details` require a `building_model_uid` — confirmed by a
  live call that errored with "Missing required argument: building_model_uid" when a `property_uid` was
  passed instead. There is no property-scoped building-lookup tool exposed by this Audette MCP surface
  short of the disallowed bare `list_buildings` (which would return every building across the whole
  account, not just this property). Per the runbook, this was skipped with this note rather than making
  that call. **Consequence:** no Audette-modeled emissions/EUI candidate values exist yet, and the
  emissions field in the baseline is empty rather than estimated.
- **ESPM actuals are deferred.** Hindsight REST for ESPM is not available to this agent. ESPM property id
  `17984313` sits at the top of the reconciliation hierarchy (measured actuals) and was not pulled. This
  means the electricity/gas figures recorded as "agreed" above are audit-confirmed only, not
  measured-actual-confirmed — if/when ESPM data becomes available, it could reopen these as new conflicts
  per the Gate-1-reopen rule.
- **Reg 28 baseline year gap** (2023 audit vs. 2021 statutory) is unresolved — see conflict #3.

## Retrofit register captured (for later phases, informational only at Gate 1)

5 measure records in the register from `retrofit__get_measure_state`: a NEST thermostat measure (defensive,
$51,000 cost), an EBCx measure (recommended, $45,000 cost, explicitly provisional pending the owner/tenant
gas-split resolution), and 3 probe/test records (`probe-score-3/4/5`) that appear to be test fixtures rather
than real candidates — flagging for your awareness, not acted on.

---

**Awaiting your adjudication on conflicts 1–3 and your decision on the Reg-28 baseline-year methodology
before P3 (measure plan) proceeds.**
