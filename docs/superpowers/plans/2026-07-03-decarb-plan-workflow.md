# Decarbonization Report Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `decarb-plan` orchestration skill (+ project-kickoff project type, template gap-fill) so a full asset decarbonization engagement runs kickoff → evidence → human-adjudicated reconciliation → retrofit plan → Audette write-back → verified templated report, resumable via a phase-state ledger.

**Architecture:** Pure orchestration — no new services. A soapbox-agent skill conducts existing capabilities (project-kickoff, asset RAG, Audette MCP, `retrofit__*`, `verifier__*`, memory, library/web research, template-mcp `decarb` template, report-renderer/report-review subagents), checkpointing every phase to `projects/<asset-key>/decarb-plan.json`.

**Tech Stack:** Markdown skills (soapbox-agent conventions), JSON state ledger, existing MCP tools. No executable code except an example data JSON.

## Global Constraints

- Spec is authoritative: `docs/superpowers/specs/2026-07-03-decarb-plan-workflow-design.md`. Its state-ledger JSON shape, phase definitions (P0–P5 + GATE1/GATE2), and approved decisions (asset-level/C; kickoff+2 gates/B; human adjudicates ALL conflicts/B; full Audette loop with write-back/B) must be encoded verbatim in the skill.
- Tool names as deployed: `retrofit__propose_candidates`, `retrofit__evaluate_measure` (asset_id = SOAPBOX asset id; feasibility.score INTEGER 1–5), `retrofit__screen_measures`, `retrofit__get_measure_state`, `retrofit__update_measure_state`, `retrofit__get_retrofit_playbook`, `retrofit__search_reference_library`; `verifier__record_finding`, `verifier__resolve_finding`, `verifier__verification_status`, `verifier__get_verification_checklist`, `verifier__recall_expertise`, `verifier__retain_shared_expertise`; Audette: `list_buildings`/`get_building_model_details`/`get_equipment_survey`/`get_available_measures`/`run_measure_design_analysis`/`run_compliance_analysis`/`run_finance_analysis`/`create_custom_plan`/`update_custom_plan_measures`/`submit_equipment_survey`.
- Reconciliation hierarchy (suggestion only, verbatim): measured utility/ESPM actuals > audit-reported 12-mo > Audette modeled > estimates. EVERY conflict → verifier finding + Gate-1 adjudication; adjudications call `verifier__resolve_finding` and store `{value, source, adjudicated_by: 'user', date}`.
- Render gate is HARD: `verifier__verification_status` pass (or documented overrides in state) before report-renderer dispatch. No LLM arithmetic anywhere — engines/Audette/template math only.
- Never fail silently: outages halt the phase with the standing reconnect message; state file always reflects last completed step; post-Gate-1 baseline changes reopen Gate 1.
- Skill conventions: follow existing soapbox-agent skills (YAML frontmatter with name/description(triggers)/version; imperative sections; bash-checkable steps). Match `rsra`/`portfolio-analysis` in tone and structure.
- Repo: ~/soapbox-agent on main; commit per task with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; push after each task (docs repo, no deploy risk).
- projects/ convention: follow whatever `skills/project-kickoff/SKILL.md` prescribes for `<asset-key>` and kickoff file naming — read it, don't invent.

## File Structure

```
soapbox-agent/
  skills/project-kickoff/project-types/decarb-plan.md   (T1 — new)
  skills/decarb-plan/SKILL.md                            (T2 — new, the orchestrator)
  skills/decarb-plan/state-schema.json                   (T2 — the ledger JSON Schema, copied from spec)
  templates/decarb/layout-agent.html                     (T3 — extend ONLY if sections missing)
  templates/decarb/example-data.json                     (T3 — new, authoritative example payload)
```

---

### Task 1: `decarb-plan` project type

**Files:**
- Create: `~/soapbox-agent/skills/project-kickoff/project-types/decarb-plan.md`
- Read first: `skills/project-kickoff/SKILL.md` (how types are loaded: `cat skills/project-kickoff/project-types/<type-key>.md`), and BOTH existing type files (`retrofit-analysis.md`, `portfolio-analysis.md`) — match their exact structure (any frontmatter, question-block format, data-check instructions).

**Interfaces:**
- Produces: a type file the kickoff skill loads for `type-key: decarb-plan`. Task 2's skill invokes project-kickoff with this type and expects the kickoff output saved as `projects/<asset-key>/decarb-plan-kickoff.md` (per the kickoff skill's `<type-key>-kickoff.md` convention).

- [ ] **Step 1:** Read the three files above; note the exact section/question format.
- [ ] **Step 2:** Author `decarb-plan.md` in that format, covering (content requirements — phrase as kickoff questions with why-it-matters notes, checking existing asset data before asking, per the kickoff skill's rules):
  1. Decarbonization driver(s): BPS compliance (which ordinance) / investor–fund mandate / net-zero commitment (target year) / refinance–green-loan / disposition prep.
  2. Target definition — exactly one primary: `crrem` (pathway + scenario year) | `percent` (% reduction vs baseline year, which metric: energy or carbon) | `bps-fine-avoidance` (jurisdiction milestones) | `net-zero-year`. Secondary targets allowed but labeled.
  3. Hold period (years) + planned capital events (roof, repositioning, refinance dates) + equipment commitments already made.
  4. Budget ceiling (total and/or per-phase) and financing appetite (cash / green loan / C-PACE / incentives-dependent).
  5. Tenant/occupancy constraints (turn schedule, disruption tolerance: none/light/in-unit/vacancy-required vocabulary).
  6. Document inventory: confirm audits/PCAs/utility data on file (list what the asset already has FIRST); ask only for gaps (12-mo utility actuals if no ESPM link, equipment invoices, prior studies).
  7. Cap rate + source for exit math (client-provided beats survey; record source string verbatim).
  8. Stakeholders, review cadence, deadline.
- [ ] **Step 3:** Verify by dry-run instruction check: `cat skills/project-kickoff/project-types/decarb-plan.md` renders cleanly; every question block matches the sibling files' format (diff the STRUCTURE against retrofit-analysis.md by eye).
- [ ] **Step 4:** Commit: `feat(kickoff): decarb-plan project type` + trailer. Push.

---

### Task 2: `decarb-plan` orchestration skill + state schema

**Files:**
- Create: `~/soapbox-agent/skills/decarb-plan/SKILL.md`
- Create: `~/soapbox-agent/skills/decarb-plan/state-schema.json`

**Interfaces:**
- Consumes: Task 1's project type; all deployed tools listed in Global Constraints; report-renderer/report-review subagents (dispatch by name as other skills do — check how `rsra`'s SKILL.md hands off to the renderer and mirror it).
- Produces: the engagement workflow. State ledger at `projects/<asset-key>/decarb-plan.json` conforming to `state-schema.json` (copy the JSON shape from the spec's "State ledger" section VERBATIM into a JSON Schema with `required` per phase); human companion `projects/<asset-key>/decarb-plan.md`.

- [ ] **Step 1:** Write `state-schema.json` — JSON Schema (draft-07) for the spec's ledger shape. Every phase section optional at the top level but with a `phase` enum `["P0","P1","P2","GATE1","P3","GATE2","P4","P5","done"]`; conflicts array items require `field`, `candidates`, `suggested`, `finding_id`; adjudication requires `value`, `source`, `adjudicated_by`, `date` when present.
- [ ] **Step 2:** Author `SKILL.md` with this exact section plan (frontmatter description triggers: "decarbonization report", "decarb plan", "decarbonization roadmap", "full decarb report", "net zero plan for [asset]", "BPS compliance plan"; state that RSRA is the SCREENING product and this is the full ENGAGEMENT product so the two don't mis-trigger):
  - **Resume protocol (first)**: `cat projects/<asset-key>/decarb-plan.json` — if present, validate phase and resume there; never redo a completed phase; post-Gate-1 baseline changes set `phase` back to `GATE1` and re-present only the changed items.
  - **P0**: invoke project-kickoff with type decarb-plan; write kickoff results into state.kickoff; create the state file (phase P0→P1).
  - **P1 Evidence sweep**: enumerate + read asset documents (list_files/search_files/read_file/search_documents); load `retrofit__get_measure_state` and `verifier__` findings; Audette pulls (building model, equipment survey, available measures, existing plans — respect the property→building resolution: one property may hold several buildings, aggregate floor-area-weighted); ESPM actuals where linked; `verifier__recall_expertise` + org memory recall; research: `retrofit__search_reference_library` FIRST then web, jurisdiction rules + incentives, every claim cited with provenance library|web. Record document inventory + citations in state.
  - **P2 Reconciliation**: build the baseline table (fields: electricity kWh/yr + $, gas (native units + GJ) + $, owner/tenant splits, GFA, units, floors, year built, equipment inventory w/ install years, emissions tCO2e with factor source). For each field, gather ALL candidate values with sources; agreement → record with source; disagreement → conflict row (suggested = hierarchy rule, named) + `verifier__record_finding` (kind data-quality, severity by materiality). NO auto-resolution.
  - **GATE 1**: present three blocks — (a) verified baseline, (b) every conflict as a numbered decision with candidates/sources/suggestion, (c) target trajectory computed from kickoff target type (CRREM pathway points via crrem tooling, BPS milestone table + fine-exposure via engines/Audette compliance analysis — never LLM arithmetic). Wait for the user. Write adjudications to state + `verifier__resolve_finding`; set targets.confirmed_at.
  - **P3 Measure plan**: `retrofit__propose_candidates` with real asset attributes → pull all source candidates → Audette `run_measure_design_analysis` for candidates needing modeled physics (mark modeled savings provisional per the baseline-discipline playbook; `retrofit__get_retrofit_playbook('baseline-discipline')`) → `retrofit__evaluate_measure` per candidate (REMIND: asset_id = Soapbox asset id; score integer 1–5; every econ field engine/source-provenanced; cap rate from kickoff with its source) → `retrofit__screen_measures` → roadmap phasing against capital events/equipment EOL per `staging` playbook → target-gap statement (recommended set vs confirmed target; defensive closures priced).
  - **GATE 2**: present roster (all four labels with reasons), phased roadmap (per-phase capex, NOI delta, exit impact — engine numbers), target-gap statement. User confirms/edits; edits via `retrofit__update_measure_state`; set measures.gate2_confirmed_at.
  - **P4 Write-back + verification**: Audette `create_custom_plan` (or update) with confirmed measures — record custom_plan_id; `submit_equipment_survey` corrections for adjudicated equipment conflicts — record submissions; render gate: `verifier__verification_status` must pass or each open high finding carries a documented override `{finding_id, override_reason, approved_by}` in state. HARD GATE.
  - **P5 Report**: assemble data JSON per `templates/decarb/example-data.json` (Task 3's authoritative schema); sections mapped: Baseline Performance ← state.baseline; Decarbonization Feasibility ← targets + trajectory; Recommended Measures + CRREM-Aligned Measures ← register; exit-value scenarios ← engine outputs; Data Quality & Adjudications appendix ← conflicts + findings; Methodology & Sources ← citations. Dispatch report-renderer (mirror rsra's handoff), loop report-review (revisions → export PDF/PPTX), register deliverable in Files, write report.exports; `verifier__retain_shared_expertise` for generalizable lessons (it will refuse identifying content — do not work around refusals).
  - **Failure handling** section: verbatim spec rules (named blockers, fail-closed render gate, Gate-1 reopen).
- [ ] **Step 3:** Consistency pass: every tool name in the skill greps against Global Constraints list (`grep -oE '(retrofit|verifier)__[a-z_]+' skills/decarb-plan/SKILL.md | sort -u` — no unknown names); state fields used in prose all exist in state-schema.json.
- [ ] **Step 4:** Commit: `feat(skills): decarb-plan orchestration workflow` + trailer. Push.

---

### Task 3: decarb template gap-fill + example data

**Files:**
- Read: `~/soapbox-agent/templates/decarb/layout-agent.html` (whole file)
- Modify: same file ONLY if a required section is missing
- Create: `~/soapbox-agent/templates/decarb/example-data.json`

**Interfaces:**
- Consumes: the spec's P5 section list. Known present (verified): Baseline Performance, Decarbonization Feasibility, Recommended Measures, Impact on Asset Value at Exit (Scenarios 1+2), CRREM-Aligned Measures.
- Produces: template covering all P5 sections + `example-data.json` — the authoritative payload the skill's P5 references (field names exactly as the template consumes them).

- [ ] **Step 1:** Inventory the template: extract its full section list and every data placeholder/slot convention it uses (it is an agent-filled layout — determine whether it uses `{{tokens}}`, HTML comments, or prose-slot conventions; document in a comment header if absent).
- [ ] **Step 2:** Gap check against P5's required sections: phased roadmap/timeline, data-quality & adjudications appendix, methodology & sources. For each MISSING section, add it matching the template's existing `class="section"` + `section-label`/`section-title` structure and visual style (inspect adjacent sections; keep the established CSS, no new frameworks). Do not restructure existing sections.
- [ ] **Step 3:** Author `example-data.json`: a complete realistic payload (fictional asset "Example Gardens", NOT Cortland data) with every field the template consumes, including conflicts/adjudications rows for the appendix and citation entries. This file IS the schema documentation for skill P5.
- [ ] **Step 4:** Verify: render sanity — open the modified template and confirm well-formed HTML (`python3 -c "import html.parser; p=html.parser.HTMLParser(); p.feed(open('templates/decarb/layout-agent.html').read()); print('parsed ok')"`); every section named in example-data.json exists in the template (grep each section title).
- [ ] **Step 5:** Commit: `feat(templates): decarb template roadmap + data-quality sections, example payload` + trailer. Push. NOTE: template-mcp serves from the repo raw URL with a 5-minute cache — changes go live on push, no deploy.

---

### Task 4: Registration + cross-references

**Files:**
- Modify: `~/soapbox-agent/skills/project-kickoff/SKILL.md` (only if it enumerates types explicitly — read first; if types are discovered by directory, no change)
- Modify: `~/soapbox-agent/skills/rsra/SKILL.md` + `~/soapbox-agent/skills/portfolio-analysis/SKILL.md` — add one-line cross-references ("full engagement → decarb-plan skill" / "asset-level decarb engagement → decarb-plan skill") so triggers route correctly; NO other edits.
- Verify: how soapbox-agent skills reach platform agents (grep `skills_repo` in soapbox-platform apps/api + the installed_plugins row for soapbox-agent) — document the finding in the commit message; if registration is automatic from the repo, nothing to do; if a skills list needs bumping, do it.

- [ ] **Step 1:** Read + apply per above (each modification is ≤3 lines).
- [ ] **Step 2:** Commit: `feat: register decarb-plan across kickoff types and sibling skills` + trailer. Push.

---

### Task 5: Cortland Westminster pilot — Phases P0→GATE 1 (controller + Christopher)

**No repo files. This is the acceptance run; Christopher must be present at Gate 1, so the task INITIATES the engagement and STOPS at the gate.**

- [ ] **Step 1:** In a Claude Code session (this one), run the decarb-plan skill for Cortland Westminster (asset 02848996-666e-41c9-9687-fd70edaf0653): P0 kickoff conversationally with Christopher (target likely `bps-fine-avoidance` on CO Reg 28 — his call), P1 evidence sweep (documents already indexed; register has 2 measures; findings ledger has the gas-split HIGH), P2 reconciliation.
- [ ] **Step 2:** Confirm the known conflicts surface as Gate-1 decisions: unit count (504 platform vs 530 audit vs 504 helper), owner/tenant gas split (Medium confidence), any GFA/equipment discrepancies found.
- [ ] **Step 3:** Present Gate 1 to Christopher. STOP — the remainder (P3→P5) runs after his adjudications, continuing the same state file.
- [ ] **Step 4:** Record pilot observations in the SDD ledger; skill fixes discovered during the pilot are committed as `fix(decarb-plan): ...`.

---

## Self-Review Notes

- Spec coverage: decisions C/B/B/B encoded in T2 phase text; state ledger (T2 schema, verbatim shape); project type (T1); template sections + example payload (T3); registration (T4); pilot-to-Gate-1 (T5, gates need the human so full P3–P5 completes post-adjudication by design. Open Q1 resolved in T3 (gap-fill only), Q2/Q3 resolved by read-first instructions in T1/T4.
- No placeholders: every authored artifact has its content requirements enumerated; read-first steps name exact files.
- Type consistency: tool names centralized in Global Constraints; state fields defined once in the spec shape and referenced by path.
