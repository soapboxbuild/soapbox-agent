# Soapbox Costing — Plan 6: Rewire decarb-plan + quality-review to the costing layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Connect the shipped Soapbox Costing capability to the core decarb pipeline: extend the canonical `measure.cost` contract with the additive fields, have `decarb-plan` source measure CapEx from the costing skill/MCP (with the placeholder `cost-bases.md` demoted to fallback), and add a `quality-review` stale-cost WARN.

**Architecture:** All changes in `soapbox-agent` on branch `feat/costing-decarb-rewire`. Additive + surgical: the schema change is backward-compatible; the `decarb-plan` change INSERTS a costing-source step into measure screening without disturbing the existing Audette-engine economics/capture logic; the `quality-review` change appends one WARN bullet to the existing decarb gates.

**Tech Stack:** JSON Schema + `ajv` validator (`scripts/validate-measure-cost.mjs`), Markdown skills, `node scripts/lint-*.mjs`.

## Global Constraints

- **Additive / backward-compatible only.** Existing `measure.cost` objects (capex/opex_delta_yr/electrical_capacity/efficiency_alternative) MUST still validate. New fields are OPTIONAL in the schema.
- **Do not rewrite decarb-plan's economics.** The Audette engine + `compute_plan_economics` + landlord-capture logic stay. The costing skill is a CapEx *source* feeding `measure.cost.cost.capex` (+ breakdown/contingency/escalation) into screening — an additive step, clearly marked, with `cost-bases.md`/engine as the fallback when the MCP has no coverage.
- **Managed-agent bundles are frozen at install** — merging to `main` does NOT change running portfolios until re-sync. State this in the finishing step; do not claim production impact on merge.
- The costing skill/MCP is the one shipped in Plans 1–5 (`costing.mcp.soapbox.build`, `soapbox-costing` plugin). Reference it by name; do not duplicate its logic here.
- Preserve existing lint/validator green (`scripts/lint-skill-quality-review.mjs`, `scripts/lint-archetype-guidance.mjs`, `scripts/validate-measure-cost.mjs`).

---

### Task 1: Additive contract extension (schema + validator + fixture)

**Files:** Modify `skills/construction-costing/schema/measure-cost.schema.json`, `scripts/validate-measure-cost.mjs`, `skills/construction-costing/example-data.json`.

**Interfaces:** the `cost` object gains OPTIONAL `contingency_pct` (number 0–1), `cost_breakdown` (object `{material,labour,equipment}` numbers summing ~1.0), `escalation` (object `{base_year:int, index:string, index_vintage:string, escalated_to:int}`).

- [ ] **Step 1: Extend the validator's checks (failing test first)** — in `scripts/validate-measure-cost.mjs` add rule assertions: (a) the existing fixture still passes; (b) if `cost.escalation` is present, `escalated_to` must be an integer year and `index_vintage` a non-empty string; (c) if `cost_breakdown` present, its three shares sum to within 0.011 of 1.0. Add a NEW fixture case exercising the additive fields. Run → it should FAIL until the schema allows the new fields.
- [ ] **Step 2: Run** `node scripts/validate-measure-cost.mjs` → FAIL (ajv rejects unknown fields if `additionalProperties:false`, or the new fixture violates the not-yet-present rules).
- [ ] **Step 3: Extend the schema** — add the three optional properties to `cost.properties` with types/constraints; keep them OUT of `cost.required`; ensure `additionalProperties` on `cost` permits them (add to properties). Do NOT make them required.
- [ ] **Step 4: Update `example-data.json`** — add the additive fields to ONE existing measure (e.g. the ASHP fuel-switch) so the fixture exercises them; leave another measure without them (proving optionality).
- [ ] **Step 5: Run** → `measure-cost contract OK`. Confirm the pre-existing rules (fuel_switch requires electrical_capacity + efficiency_alternative; UNVERIFIED must be a range; measure_kind required; service_capacity_known=false⇒UNVERIFIED) still pass.
- [ ] **Step 6: Commit** `skills/construction-costing/schema/measure-cost.schema.json scripts/validate-measure-cost.mjs skills/construction-costing/example-data.json`, msg `feat(contract): additive contingency_pct + cost_breakdown + escalation on measure.cost`.

---

### Task 2: quality-review stale-cost WARN

**Files:** Modify `skills/quality-review/SKILL.md` (append one WARN bullet to the existing "### WARN" list in the "## Decarb measure-recommendation gates" section); Modify `scripts/lint-skill-quality-review.mjs` (add an assertion for the new content).

- [ ] **Step 1: Extend the lint (failing)** — add to `scripts/lint-skill-quality-review.mjs`'s `must` array: `'Stale cost'` and `'escalation'` (or the exact phrases you'll write). Run → FAIL (not yet in SKILL.md).
- [ ] **Step 2: Run** `node scripts/lint-skill-quality-review.mjs` → FAIL.
- [ ] **Step 3: Append the WARN bullet** to the WARN list: **Stale cost basis** — a CapEx figure lacking an `escalation` stamp (or with an `index_vintage` older than one year / `escalated_to` not the current year) is not current-dollar; surface it and request a re-escalation. Keep it consistent with the existing WARN bullets' style.
- [ ] **Step 4: Run** → `quality-review lint OK`.
- [ ] **Step 5: Commit** `skills/quality-review/SKILL.md scripts/lint-skill-quality-review.mjs`, msg `feat(verifier): stale-cost WARN (missing/old escalation stamp)`.

---

### Task 3: Rewire decarb-plan measure screening to source CapEx from the costing skill

**Files:** Modify `skills/decarb-plan/SKILL.md` (insert a costing-source step into the measure-screening section); Modify `skills/decarb-plan/references/measure-universe.md` (note the costing skill as the CapEx source, cost-bases fallback).

**Interfaces:** decarb-plan's screening step now: for each screened-in measure, obtain `measure.cost.cost.capex` (+ `cost_breakdown`, `contingency_pct`, `escalation`, `references`) from the **`costing` skill / Soapbox Costing MCP** (`get_measure_capex`, `estimate_service_upgrade` for fuel-switch electrical capacity, `get_der_economics`, `get_energy_prices`/`get_tariff` for opex); fall back to `cost-bases.md`/engine defaults only where the MCP has no coverage, flagging low confidence. The downstream Audette-engine economics/capture math is UNCHANGED — it now consumes MCP-sourced CapEx instead of placeholder CapEx.

- [ ] **Step 1: Add a lint assertion (failing)** — extend/confirm `scripts/lint-archetype-guidance.mjs` OR add a small `scripts/lint-skill-decarb-costing.mjs` asserting `skills/decarb-plan/SKILL.md` contains the costing-source wiring: substrings `Soapbox Costing`, `get_measure_capex`, `costing skill`, `cost-bases.md` (as fallback), `escalation`, `references`, `does not replace` (the economics). Run → FAIL.
- [ ] **Step 2: Run the lint** → FAIL.
- [ ] **Step 3: Insert the costing-source step** into decarb-plan's screening section (find the measure-screening / cost portion — around the completeness cross-check / screen-down step). Add a clearly-labelled subsection: "**CapEx source — Soapbox Costing.** Before economics, source each measure's CapEx from the `costing` skill (Soapbox Costing MCP): `get_measure_capex` (→ capex low/base/high + cost_breakdown + contingency_pct + escalation + references), `estimate_service_upgrade` for any fuel-switch/electrification (→ electrical_capacity UNVERIFIED range, never collapsed), `get_der_economics` for solar/storage/GHP, and `get_energy_prices`/`get_tariff` for the OpEx delta. Use `cost-bases.md` / engine defaults ONLY where the MCP lacks coverage, flagged low-confidence. This sources CapEx; it does NOT replace the plan's economics (capture, NPV/IRR, exit) which continue to consume these figures." Do NOT delete or restructure the existing economics/capture text.
- [ ] **Step 4: Note the source in `measure-universe.md`** — one line: measure CapEx comes from the Soapbox Costing MCP (`get_measure_capex`), with `cost-bases.md` as the fallback for uncovered cells.
- [ ] **Step 5: Run** the lint → OK. Re-run `node scripts/lint-archetype-guidance.mjs` and `node scripts/lint-skill-quality-review.mjs` → still OK (no regression).
- [ ] **Step 6: Commit** `skills/decarb-plan/SKILL.md skills/decarb-plan/references/measure-universe.md scripts/lint-skill-decarb-costing.mjs`, msg `feat(decarb): source measure CapEx from Soapbox Costing MCP (cost-bases fallback)`.

---

## Finishing (controller — after all tasks + whole-branch review)

- Run ALL soapbox-agent costing/decarb linters + the validator green together.
- **e2e gate:** the standing `soapbox-e2e` skill targets apps/web frontend changes; Plan 6 changes agent SKILLS + schema, not apps/web. The meaningful e2e is a **live decarb run through the costing tools on a test portfolio** — which requires provisioning the updated `soapbox-agent` bundle + `soapbox-costing` plugin to that portfolio (bundles are frozen at install). Present this to the human as the pre-merge gate: (a) provision to a test portfolio and run a decarb plan verifying MCP-sourced CapEx + citations appear, then merge; or (b) merge to `main` now and gate the live e2e on the next portfolio re-sync. Do not claim production impact on merge (frozen bundles).
- Use superpowers:finishing-a-development-branch for the merge decision.

## Self-Review

- **Spec coverage:** implements the design's A→C interlock (costing feeds decarb-plan; quality-review reads it) and the additive contract extension; economics untouched.
- **Placeholder scan:** none — schema/validator/lint assert real content; cost-bases.md is explicitly demoted to fallback, not deleted.
- **Backward-compat:** new schema fields optional; old fixtures pass; decarb-plan economics text preserved (additive insert only).
- **Blast radius:** branch in soapbox-agent; frozen bundles mean no production change until re-sync; live e2e is the pre-merge/pre-resync gate.
