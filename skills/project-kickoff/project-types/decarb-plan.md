# Project Type: Decarb-Plan

## Q1 — Decarbonization Driver(s)

**Why it matters:** the driver determines which downstream requirements (BPS compliance
math, fund reporting cadence, lender green-loan covenants) gate the plan.

**Pre-flight check:** If the asset's jurisdiction is already known (from address on file),
surface the applicable BPS ordinance before asking:
> "This asset is in [jurisdiction] — that falls under [ordinance, e.g. Energize Denver /
> NYC LL97 / CO Reg 28]. Is BPS compliance with this ordinance a driver for this plan?"
> Options: Yes | No | Not sure — check anyway

**Question:** "What is driving this decarbonization plan?"

AskUserQuestion multi-select options:
- BPS compliance (specify which ordinance, e.g. Energize Denver, NYC LL97, CO Reg 28)
- Investor / fund mandate
- Net-zero commitment (specify target year)
- Refinance / green-loan requirement
- Disposition prep (specify anticipated sale timing)
- Other (describe)

For each selected driver requiring detail (ordinance name, target year, sale timing):
ask a follow-up free-text question.

Store as: `drivers` — list of `{driver_type, detail}`.

---

## Q2 — Target Definition

**Why it matters:** downstream Gate-1 math branches entirely on which target type is
primary — this cannot be ambiguous or multi-valued.

**Question:** "What is the single primary target for this plan?"

AskUserQuestion options (exactly one selectable):
- CRREM alignment (pathway + scenario year)
- Percent reduction vs. a baseline year
- BPS fine-avoidance (meet jurisdiction milestones without penalty)
- Net-zero by a specific year

**Follow-up (based on primary selection — ask as a separate turn):**
- If CRREM: "Which CRREM pathway and scenario year?" Free text (e.g. "1.5°C pathway, 2030").
- If Percent: "Percent reduction of what metric, vs. which baseline year?"
  Options: Energy (kWh/kBtu) | Carbon (kgCO2e) — then free text for % and baseline year.
- If BPS fine-avoidance: "Which jurisdiction milestones must be met?" Free text
  (e.g. "Energize Denver 2027 and 2030 targets").
- If Net-zero: "What is the target year?" Free text.

**Secondary targets (optional):** "Are there any secondary targets to track alongside the
primary one? (exclude the primary you already chose). These will be reported but won't drive the compliance math."
AskUserQuestion multi-select:
- CRREM alignment
- Percent reduction
- BPS fine-avoidance
- Net-zero year
- None

For each selected secondary target: ask the same detail follow-up as above, one at a time.

Store as: `goal` — one sentence synthesized from drivers and primary target; `primary_target` — `{type: crrem|percent|bps-fine-avoidance|net-zero-year, value, basis}` (exactly one); and `secondary_targets` — list of `{type, value, basis}` (may be empty).

**Field details:**
- `type`: crrem | percent | bps-fine-avoidance | net-zero-year
- `value`: the target value — pathway scenario year (CRREM), percent (percent reduction), target year (net-zero-year), or null (bps-fine-avoidance)
- `basis`: provenance string — metric + baseline year (percent), pathway name (crrem), jurisdiction + ordinance (bps-fine-avoidance), commitment source (net-zero-year)

---

## Q3 — Hold Period & Capital Events

**Pre-flight check:** If a cashflow model exists (`has_cashflow_model`), surface any hold
period or capital event data found in it before asking.

**Question:** Ask each item individually:

1. **Hold period (years):** Free text or Options: 3 years | 5 years | 7 years | 10 years | Other
2. **Planned capital events:** "Are there any planned capital events (roof replacement,
   repositioning, refinance) with known or target dates?"
   AskUserQuestion multi-select: Roof | Repositioning | Refinance | Other | None planned
   For each selected: ask for the target date (free text).
3. **Equipment commitments already made:** "Has any equipment already been ordered,
   contracted, or committed to (even if not yet installed)?" Free text description, or "None."

Store as: `hold_period_years`, `capital_events` — list of `{event, target_date}`,
`equipment_commitments` (free text or null).

---

## Q4 — Budget & Financing

**Question:** Ask each item individually:

1. **Budget ceiling:** "What is the budget ceiling for this plan?"
   Free text — accept total, per-phase, or both (e.g. "$2M total, $500K Phase 1").
2. **Financing appetite:** "How does the client intend to finance the work?"
   AskUserQuestion multi-select options:
   - Cash / balance sheet
   - Green loan
   - C-PACE
   - Incentives-dependent (grants, rebates, tax credits)
   - TBD

Store as: `budget_ceiling` (free text), `financing_appetite` — list of selected options.

---

## Q5 — Tenant / Occupancy Constraints

**Question:** Ask each item individually:

1. **Turn schedule:** "What is the unit/space turn schedule we should plan retrofit work
   around?" Free text (e.g. "20% of units turn annually", "no turns — single tenant NNN").
2. **Disruption tolerance:** "How much tenant disruption can this retrofit tolerate?"
   AskUserQuestion options (exactly one):
   - none — no tenant-facing disruption permitted
   - light — brief/occasional disruption acceptable (e.g. hallway work, short outages)
   - in-unit — contractors may enter occupied units with notice
   - vacancy-required — work requires the unit or space to be vacant

Store as: `turn_schedule` (free text), `disruption_tolerance`
(exactly one of `none|light|in-unit|vacancy-required`).

---

## Q6 — Document Inventory

**Pre-flight check (primary):** List all documents found in scan, and confirm any ESPM
link on file, before asking anything:
> "I found the following on file for this asset:"
> [List each found doc/link with its inferred type — audits, PCAs, utility data, ESPM link]
> "Are these current, or is anything outdated / missing?"
> Options: These are current and complete | Some are outdated — I'll provide updates | Nothing on file — starting fresh

**Question (only for gaps not covered by pre-flight):**
"Which of these do we still need to gather?"

AskUserQuestion multi-select — ask only about items not already confirmed present:
- 12-month utility actuals (if no ESPM link found)
- Equipment invoices
- Prior energy audits or studies
- Property Condition Assessment (PCA)
- None — everything needed is on file

For each selected gap: "Who will provide this, and by when?" Free text.

Store as: `existing_docs` — list of `{type, status: on_file|outdated|missing}`,
`documents_expected` — list of `{type, provider, expected_date}`.

---

## Q7 — Cap Rate & Source

**Why it matters:** exit-value economics (NOI ÷ cap rate) are provenance-enforced
downstream — the cap rate value alone isn't usable without its source recorded verbatim.

**Pre-flight check:** If a cashflow model or prior kickoff already records a cap rate,
surface it:
> "I found a cap rate of [value] from [source] on file — should we use this?"
> Options: Yes, use this | I have an updated value | No, use a different source

**Question:** "What cap rate should we use for exit-value math, and where does it come
from?"

Ask as two linked free-text prompts (client-provided beats survey data):
1. "What is the cap rate?" Free text (e.g. "5.25%").
2. "What is the source? Please give the exact source string as it should be cited
   (e.g. 'Client-provided, Q2 2026 appraisal' or 'CBRE Cap Rate Survey, H1 2026,
   Class B multifamily, [market]')." Free text — record verbatim, do not paraphrase.

Store as: `cap_rate` — `{value, source}` (source recorded exactly as given).

---

## Q8 — Stakeholders, Review Cadence & Deadline

**Question:** Ask each item individually:

1. **Stakeholders:** "Who is involved in this decarbonization plan?"
   AskUserQuestion multi-select roles:
   - Soapbox lead
   - Client asset manager
   - Client sustainability/ESG lead
   - Engineering firm
   - Owner's representative
   - Lender (if green loan involved)
   - Other

   For each selected role: ask "Who fills this role?" — free text (name and firm).

2. **Review cadence:** "How often should we check in on progress?"
   Options: Weekly | Biweekly | Monthly | Quarterly | Ad hoc / as needed

3. **Deadline:** "Is there a hard deadline for this plan (e.g. BPS compliance date,
   fund reporting cycle, disposition date)?"
   Free text, or "No hard deadline."

Then: "Who is the primary client point of contact?"
Free text: name and email address.

Store as: `stakeholders` — list of `{role, name_firm}`, `review_cadence`,
`deadline` (free text or null), `primary_contact` — `{name, email}`.

---

## Output Template

Use this template to write the project file. Fill every section from the Q&A answers.

```markdown
# <Asset Name> — Decarb-Plan Kickoff
**Date:** YYYY-MM-DD
**Conducted by:** <agent name>
**Project type:** Decarb-Plan

## Executive Summary

<2–3 sentence narrative covering: what is driving this decarbonization plan, the primary
target and how it will be measured, key budget/timeline constraints, and who is leading
delivery on the client side.>

---

## 1. Decarbonization Driver(s)

| Driver | Detail |
|--------|--------|
<One row per driver>

## 2. Target Definition

**Primary target:** <primary_target.type> — <primary_target.detail>

**Secondary targets:**
| Type | Detail |
|------|--------|
<One row per secondary target, or "None">

## 3. Hold Period & Capital Events

**Hold period:** <hold_period_years> years

| Capital event | Target date |
|---------------|-------------|
<One row per event, or "None planned">

**Equipment commitments already made:** <equipment_commitments or "None">

## 4. Budget & Financing

**Budget ceiling:** <budget_ceiling>
**Financing appetite:** <financing_appetite list>

## 5. Tenant / Occupancy Constraints

**Turn schedule:** <turn_schedule>
**Disruption tolerance:** <disruption_tolerance>

## 6. Document Inventory

| Document | Status |
|----------|--------|
<One row per document: type | on file / outdated / missing>

| Gap | Provider | Expected date |
|-----|----------|---------------|
<One row per gap, or "None">

## 7. Cap Rate & Source

**Cap rate:** <cap_rate.value>
**Source:** <cap_rate.source> *(recorded verbatim)*

## 8. Stakeholders, Review Cadence & Deadline

| Role | Name / Firm |
|------|-------------|
<One row per stakeholder>

**Review cadence:** <review_cadence>
**Deadline:** <deadline or "No hard deadline">
**Primary client contact:** <name> — <email>

---
*Generated by project-kickoff skill v1.0.0 — <date>*
```
