# Project Type: Portfolio Analysis

## Pre-flight (portfolio scope)

Instead of filesystem scans, run these before Q1:

```
query_portfolio_data(include_metadata: true, analysis_ready_only: false)
search_portfolio("exit year cap rate hold period fund")
search_portfolio("IRR hurdle rate discount rate")
search_portfolio("ESG sustainability net zero emissions target")
```

Track:
- `found_exit_params` — true if exit years / cap rates appear in search results
- `found_irr_hurdle` — true if an IRR hurdle rate appears
- `found_org_goal` — true if a sustainability goal appears
- `audette_linked_count` — count of assets with non-null `audette_property_id`
- `existing_kickoff` — `search_portfolio("portfolio analysis kickoff")` returns a prior kickoff file

**Re-run handling:** If `existing_kickoff` is found, ask before proceeding:
> "I found a prior portfolio analysis kickoff. What would you like to do?"
> Options: Use existing parameters | Start fresh

---

## Q1 — Financial Model Assumptions

**Pre-flight check:** Surface any IRR hurdle found in docs.

**Questions** (ask each as a separate turn):

1. **IRR hurdle rate** — "What is the minimum IRR to greenlight a decarbonization measure?"
   Free text (e.g. "15%") — default shown: 15%

2. **Utility escalation** — "What annual utility cost escalation rate should we use?"
   Options: 3%/yr (standard) | 2%/yr | 4%/yr | Other

3. **Value method** — "How should we calculate value creation at exit?"
   Options:
   - Value-inclusive: NOI uplift capitalised at exit cap + added to terminal cash flow (recommended)
   - Savings-only: IRR on annual savings alone, no exit value

Store as: `irr_hurdle`, `utility_escalation`, `value_method`.

---

## Q2 — Exit Parameters

**Pre-flight check:** If `found_exit_params`, surface it:
> "I found exit years and cap rates in the portfolio documents. Should I use those,
> or do you have a spreadsheet to share?"
> Options: Use what's in the docs | I'll share a spreadsheet now | Enter manually

**If no prior data found:**
"How would you like to provide exit years and exit cap rates?"
Options:
- Share a spreadsheet now (I'll parse it)
- Enter by fund (I'll ask fund by fund)
- Use a single portfolio-wide cap rate (I'll ask for the rate)

**Follow-up if spreadsheet:** "Please share the file — I'll parse exit years, cap rates, and fund assignments from it."
*(No further question needed — user shares inline.)*

**Follow-up if by fund or single rate:** ask for the values (one turn per fund or one turn for the single rate).

Store as: `exit_params_source` (spreadsheet / by-fund / single), plus extracted values once provided.

---

## Q3 — Hold Period & Retrofit Timing

**Questions** (ask each as a separate turn):

1. **Exit year floor** — "What is the minimum exit year? Assets exiting before this date will be analysed to this floor."
   Options: 2027 | 2028 | 2029 | 2030 | No floor

2. **Retrofit lead time** — "How many months lead time do major capital measures (HVAC, electrification, envelope) require?"
   Options: 12 months | 18 months (standard) | 24 months | Other

Store as: `exit_year_floor`, `retrofit_lead_months`.

---

## Q4 — Optional Add-Ons

**Question (multi-select):**
"Which optional analyses should we include?"

Options (multi-select):
- CRREM pathway analysis — emissions trajectory chart, stranding risk vs. 1.5°C pathway
- Building Performance Standards (BPS) exposure — compliance cost and fine avoidance per asset
- Neither — financial analysis only

**If CRREM selected:** "Which target years should we report against?"
Options (multi-select): 2030 | 2035 | 2040 | 2050

**If org goal desired:** "Is there a custom sustainability goal to track progress against? (e.g. 'net zero by 2040', '50% reduction by 2035')"
Options: Yes — enter goal | No

Store as: `include_crrem` (bool), `include_bps` (bool), `target_years` (list), `org_goal` (string or null).

---

## Q5 — Audette Account

**Pre-flight check:** Report `audette_linked_count` from query.
> "[N] of [total] assets are linked to Audette."

**Question:** "What is the Audette customer account slug for this portfolio?"
Free text (e.g. "greystar", "bclc")

**If unknown:** "If you're not sure, I can list available accounts once the analysis starts. Leave this blank and I'll look it up."
Options: Enter slug now | Look it up at runtime

Store as: `audette_account` (string or "runtime-lookup").

---

## Q6 — Scope

**Questions** (ask each as a separate turn):

1. **Fund filter** — "Should we analyse all funds, or specific ones?"
   Options: All funds | Specific funds (list them)

2. **Top-N table** — "How many assets should appear in the 'top assets by value creation' table?"
   Options: 5 | 10 (standard) | 15 | All

Store as: `fund_filter`, `top_n_assets`.

---

## Output Template

```markdown
# Portfolio Analysis — Run Parameters
**Date:** YYYY-MM-DD
**Portfolio:** <portfolio name>

## Financial Model
| Parameter | Value |
|-----------|-------|
| IRR hurdle | <irr_hurdle>% |
| Utility escalation | <utility_escalation>/yr |
| Value method | <value_method> |
| Exit year floor | <exit_year_floor> |
| Retrofit lead time | <retrofit_lead_months> months |

## Exit Parameters
Source: <exit_params_source>
<Summary of exit years and cap rates, or "See attached spreadsheet">

## Optional Add-ons
| Add-on | Included |
|--------|----------|
| CRREM pathway analysis | <yes/no> |
| BPS exposure analysis | <yes/no> |
| Org goal | <org_goal or none> |
| Target years | <target_years or N/A> |

## Audette Account
Slug: <audette_account>

## Scope
Fund filter: <fund_filter>
Top-N table: <top_n_assets>

---
*Generated by project-kickoff skill — <date>*
```
