# Project Type: Retrofit Analysis

## Q1 — Project Goal

**Question:** "What is the primary goal of this retrofit project?"

AskUserQuestion options:
- Energy reduction target (specify % or kWh target)
- Carbon neutrality / net-zero by a specific year
- Regulatory compliance deadline (specify regulation)
- CapEx planning and budget development
- Other (describe)

**Follow-up (always):** "What is the primary driver behind this project?"
AskUserQuestion options:
- Owner or board mandate
- Financing or refinancing requirement (e.g. green loan, Fannie Mae Green Rewards)
- Regulatory requirement (local law, building performance standard)
- ESG reporting / investor requirement
- Proactive capital planning

Ask this as a separate AskUserQuestion turn, after Q1 is answered.

Store as: `goal_type`, `goal_driver`, and any free-text detail.

---

## Q2 — Data Sources

**Pre-flight check:** Surface any equipment schedules, existing conditions reports,
or utility data found in the scan. For each found item:
> "I found [filename] — is this the [document type] we should use?"
> Options: Yes, use this | I have a newer version | Skip this one

**Question (for sources not found in pre-flight):**
"Which data sources will we need for this analysis?"

AskUserQuestion multi-select options:
- Equipment schedules (HVAC, lighting, envelope)
- Existing conditions report
- Utility history (12–24 months)
- Building automation / BMS export
- Prior energy model or simulation
- Other

**For each selected source:** Ask separately:
> "Who will provide the [source name]?"
> Options: Client provides | Engineering firm provides | Soapbox pulls from ESPM | TBD

Store as: `data_sources` — list of `{source, provider, status}`.

---

## Q3 — Financial Assumptions

**Pre-flight check:** If `has_cashflow_model` is true:
> "I found a cashflow model for this asset. Should we use its financial parameters
> as the starting point for this analysis?"
> Options: Yes, use existing parameters | No, we'll use custom assumptions

**Question:**
Ask each financial parameter individually (one AskUserQuestion per parameter):

1. **Discount rate:** Free text (e.g. "7.5%") — or "Use Soapbox standard (7%)"
2. **Utility escalation rate:** Free text (e.g. "3% per year") — or "Use Soapbox standard (3%/yr)"
3. **Hold period:** Options: 3 years | 5 years | 7 years | 10 years | Other
4. **Incentive assumptions:**
   Options (multi-select): IRA / federal tax credits | State incentive programs |
   Utility rebates | None | TBD — research needed

**Provider:** After all parameters:
> "Who will own / sign off on these financial assumptions?"
> Options: Client CFO / finance team | Soapbox standard assumptions | Joint — client reviews Soapbox defaults

Store as: `financial_assumptions` — `{discount_rate, escalation_rate, hold_period, incentives, provider}`.

---

## Q4 — Existing CapEx / Engineering Documents

**Pre-flight check (primary):** List all documents found in scan:
> "I found the following documents in your asset folder:"
> [List each found doc with its inferred type]
> "Are these the documents we should work from, or are there others?"
> Options: These are correct | Some are outdated — I'll provide updates | There are additional documents coming

**Question (if nothing found, or to capture additional):**
"Are there any existing CapEx plans or engineering documents we should incorporate?"

AskUserQuestion multi-select:
- Property Condition Assessment (PCA)
- Prior energy audit
- Existing retrofit scope or capital plan
- Equipment inventory
- None — starting fresh

For each selected: "Who holds this document and when can we expect it?"
Free text answer.

Store as: `existing_docs` — list of `{type, filename_or_description, provider, status}`.

---

## Q5 — Timeline & Milestones

**Question:** Ask each milestone individually:

1. **Report delivery needed by:**
   Options: Within 2 weeks | Within 1 month | Within 3 months | No hard deadline | Specific date (free text)

2. **Target construction / implementation start:**
   Options: This year | Next year | Not yet defined | Specific date (free text)

3. **Phasing constraints:**
   Options (multi-select): Occupied building (tenant disruption limits) | Seasonal constraints |
   Funding or grant deadline | Regulatory deadline | No constraints

4. **Funding deadline (if applicable):**
   Options: Yes — specify date | No deadline | TBD

Store as: `milestones` — `{report_by, construction_start, phasing_constraints, funding_deadline}`.

---

## Q6 — Team & Point of Contact

**Question:** "Who is involved in delivering this project?"

AskUserQuestion multi-select roles:
- Soapbox lead
- Client project manager
- Engineering firm
- Owner's representative
- Sustainability consultant
- General contractor
- Other

For each selected role: Ask "Who fills this role?" — free text (name and firm).

Then: "Who is the primary client point of contact?"
Free text: name and email address.

Store as: `team` — list of `{role, name_firm}` + `primary_contact: {name, email}`.

---

## Output Template

Use this template to write the project file. Fill every section from the Q&A answers.

```markdown
# <Asset Name> — Retrofit Analysis Kickoff
**Date:** YYYY-MM-DD
**Conducted by:** <agent name>
**Project type:** Retrofit Analysis

## Executive Summary

<2–3 sentence narrative covering: what the retrofit project is aiming to achieve,
the primary driver (owner mandate / regulatory / financing), key constraints or
timeline pressures, and who is leading delivery on the client side.>

---

## 1. Project Goal

**Primary goal:** <goal_type>
**Driver:** <goal_driver>
<Any additional detail provided>

## 2. Data Sources

| Source | Provider | Status |
|--------|---------|--------|
<One row per source: source name | provider | Confirmed / Pending / TBD>

## 3. Financial Assumptions

| Parameter | Value | Source |
|-----------|-------|--------|
| Discount rate | <value> | <provider> |
| Utility escalation | <value>/yr | <provider> |
| Hold period | <value> years | <provider> |
| Incentives | <list> | <provider> |

## 4. Existing Documents

| Document | Description / Filename | Provider | Status |
|----------|----------------------|---------|--------|
<One row per document>

## 5. Timeline & Milestones

| Milestone | Target | Notes |
|-----------|--------|-------|
| Report delivery | <date or timeframe> | |
| Construction start | <date or timeframe> | |
| Phasing constraints | — | <list constraints> |
| Funding deadline | <date or N/A> | |

## 6. Team & Point of Contact

| Role | Name / Firm | Contact |
|------|-------------|---------|
<One row per team member>

**Primary client contact:** <name> — <email>

---
*Generated by project-kickoff skill v1.0.0 — <date>*
```
