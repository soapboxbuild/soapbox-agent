# Decarbonization Report Workflow — Design Spec

**Date:** 2026-07-03
**Status:** Approved by Christopher (brainstorm session)
**Pilot:** Cortland Westminster, with Christopher at both gates.

---

## Problem

Producing a client decarbonization report today requires manually conducting a
dozen capabilities that all exist but are unorchestrated: project scoping,
document evidence, Audette physics modelling, retrofit evaluation, data
verification, jurisdiction research, and templated report rendering. There is
no durable engagement state, no defined human checkpoints, and no guarantee
the report's numbers survived verification.

## Approved decisions

- **Scope (C):** asset-level workflow; outputs (measure register ids, report
  data JSON, state ledger) designed for later portfolio roll-up consumption.
- **Conferral (B):** kickoff + two mid-flight gates — Gate 1 after baseline
  reconciliation (baseline, conflicts, targets), Gate 2 after measure
  screening (roster, roadmap, economics). Final report-review loop for
  revisions.
- **Reconciliation (B):** human adjudicates ALL cross-source conflicts at
  Gate 1. The precedence hierarchy (measured actuals > audit 12-mo > Audette
  modeled > estimates) is presented as the suggested resolution only. Every
  conflict is also recorded as a verifier finding; adjudications call
  verifier__resolve_finding and are stored with {value, source,
  adjudicated_by, date}.
- **Audette (B):** full modelling loop — pull model/survey/measures, run
  measure design + compliance/finance analyses as needed, and WRITE BACK the
  confirmed roadmap as an Audette custom plan (create_custom_plan /
  update_custom_plan_measures); submit equipment-survey corrections from
  adjudicated conflicts.
- **Packaging (Approach 3):** one orchestration skill + a durable phase-state
  ledger; no new services.

## Architecture

New skill `soapbox-agent/skills/decarb-plan/SKILL.md` + new project type
`soapbox-agent/skills/project-kickoff/project-types/decarb-plan.md`. The
skill conducts existing deployed capabilities only:

| Capability | Provider (exists) |
|---|---|
| Scoping | project-kickoff skill (new decarb-plan type) |
| Documents/evidence | asset files + RAG tools |
| Physics/modelling | Audette MCP (model, measures, design/compliance/finance analyses, custom plans, survey submission) |
| Measure evaluation | Retrofit Specialist plugin (retrofit__* tools; provenance-enforced) |
| Verification & gating | Verifier plugin (verifier__* tools; findings ledger; verification_status render gate) |
| Memory | memory plugin (org bank) + verifier__recall/retain_shared_expertise |
| Research | reference library (retrofit__search_reference_library) first, brave-search/web second; citations required |
| Report | template-mcp `decarb` template + report-renderer subagent + report-review subagent (render → revise → export PDF/PPTX) |

### State ledger

`projects/<asset-key>/decarb-plan.json` (+ human-readable decarb-plan.md
companion registered in Files). Shape:

```json
{
  "phase": "P0|P1|P2|GATE1|P3|GATE2|P4|P5|done",
  "asset": {"id": "", "name": "", "portfolio_id": ""},
  "kickoff": {"goal": "", "drivers": [], "target": {"type": "crrem|percent|bps-fine-avoidance|net-zero-year", "value": null, "basis": ""}, "hold_period_years": null, "budget_ceiling": null, "capital_events": [], "stakeholders": [], "documents_expected": []},
  "documents": [{"name": "", "type": "audit|pca|utility|other", "storage_path": "", "read": false}],
  "baseline": {"<field>": {"value": null, "unit": "", "source": ""}},
  "conflicts": [{"field": "", "candidates": [{"value": null, "source": ""}], "suggested": {"value": null, "source": "", "rule": ""}, "adjudication": {"value": null, "source": "", "adjudicated_by": "user", "date": ""}, "finding_id": ""}],
  "targets": {"trajectory": [], "bps_milestones": [], "fine_exposure": {}, "confirmed_at": null},
  "measures": {"register_ids": [], "roadmap_phases": [], "gap_statement": "", "gate2_confirmed_at": null},
  "audette": {"building_uid": "", "custom_plan_id": "", "survey_corrections_submitted": []},
  "report": {"data_json_path": "", "verification_status": null, "render_iterations": 0, "exports": []}
}
```

Updated at every phase boundary. Any session/thread resumes by reading it
first — every phase is idempotent against it. Post-Gate-1 changes to baseline
data reopen Gate 1.

### Phases

- **P0 Kickoff** — invoke project-kickoff with type decarb-plan. The project
  type file defines the decarb-specific questions: decarbonization drivers
  (BPS compliance / investor mandate / net-zero commitment / refinance),
  target definition (one of the four target types), hold period + capital
  plan + budget ceiling, known constraints (tenant profile, equipment
  commitments), document inventory, stakeholders + timeline. Kickoff already
  checks existing asset data before asking.
- **P1 Evidence sweep** — read every relevant asset document (audits, PCAs,
  utility data); load the retrofit measure register and verification findings
  ledger; pull the Audette building model, equipment survey, available
  measures, and any existing carbon-reduction plan; pull ESPM actuals where
  linked; recall org-bank memory and shared expertise; research jurisdiction
  rules and incentives — reference library FIRST, web second, every claim
  cited with provenance (library|web).
- **P2 Baseline reconciliation** — assemble the baseline table: energy by
  fuel (with 12-month basis), energy costs, GFA, unit count, equipment
  inventory with install years, emissions (factors via Audette/CRREM
  tooling). Every cross-source disagreement → one conflict row AND one
  verifier finding (verifier__record_finding, kind data-quality). Suggested
  resolution computed from the hierarchy; nothing auto-resolved.
- **Gate 1 (user)** — present: verified baseline, ALL conflicts with
  suggestions, proposed target trajectory (CRREM curve points, BPS milestone
  table, fine-exposure math — computed via engines/Audette, never LLM
  arithmetic). User adjudicates each conflict and confirms targets.
  Adjudications → state + resolve_finding; targets.confirmed_at set.
- **P3 Measure plan** — retrofit__propose_candidates; pull all candidate
  sources; run Audette run_measure_design_analysis for candidates needing
  modeled physics (savings/carbon), marking modeled savings provisional per
  baseline-discipline playbook; retrofit__evaluate_measure for EVERY
  candidate (asset_id = Soapbox asset id; feasibility.score integer 1-5);
  retrofit__screen_measures. Roadmap: phase measures against capital events
  and equipment end-of-life per the staging playbook; compute the target gap
  (does the recommended set reach the confirmed target; what defensive
  additions close it and at what cost — engine math only).
- **Gate 2 (user)** — roster (recommended/defensive/screened-out with
  failing-test reasons), phased roadmap with per-phase capital and NOI/exit
  impact, target-gap statement. User confirms or edits the selection;
  edits update measure statuses via retrofit__update_measure_state.
- **P4 Write-back + verification** — create_custom_plan (or
  update_custom_plan_measures) in Audette with the confirmed measure set;
  submit equipment-survey corrections for adjudicated equipment conflicts;
  record what was written back in state. Render gate:
  verifier__verification_status for the asset must pass, or every open
  high-severity finding carries a documented override recorded in state.
  HARD GATE — no render without it.
- **P5 Report** — assemble report data JSON per the decarb template schema
  (read `templates/decarb/layout-agent.html` for the authoritative field
  set; extend the template via the soapbox-report meta-skill ONLY if a
  required section is missing): executive summary, verified baseline,
  target trajectory chart data, measure roadmap table + phasing timeline,
  economics (capital, NOI delta, exit impact, incentives), data-quality
  appendix (all findings + adjudications), methodology + citations.
  Dispatch report-renderer; iterate through report-review (user revisions,
  then PDF/PPTX export); register the deliverable in Files; write
  report.exports to state; retain generalizable lessons via
  verifier__retain_shared_expertise (gated).

### Failure handling

Named blockers, never silent: Audette/verifier/renderer outages halt the
phase with the standing reconnect message; the state file always reflects the
last completed step. The render gate fails CLOSED. Conflicting data
discovered after Gate 1 reopens Gate 1 rather than silently updating the
baseline.

## Non-goals (v1)

- Portfolio roll-up report (consumes this workflow's outputs later).
- New MCP services or template-engine changes (template content edits only if
  the decarb schema is missing required sections).
- Proactive/scheduled runs (this is a user-initiated engagement).

## Testing

- Skill review pass (structure, tool names incl. verifier__/retrofit__
  prefixes, state-file schema consistency, resume logic).
- Project-type file exercised via a project-kickoff dry run.
- **Pilot:** full Cortland Westminster engagement with Christopher at Gate 1
  and Gate 2, through render + export. Success = exported report whose every
  number carries provenance, with the conflicts we already know exist (unit
  count 504 vs 530, gas split Medium-confidence) surfaced and adjudicated at
  Gate 1.

## Open questions for implementation

1. decarb template schema coverage — verify layout-agent.html has sections
   for trajectory + roadmap + data-quality appendix; extend via
   soapbox-report meta-skill if not (lean: extend only what's missing).
2. project-kickoff type registration — confirm how project-types are
   discovered (directory listing vs explicit list in SKILL.md) and follow it.
3. Asset-key convention for projects/ paths — reuse whatever project-kickoff
   writes today (inspect during implementation).
