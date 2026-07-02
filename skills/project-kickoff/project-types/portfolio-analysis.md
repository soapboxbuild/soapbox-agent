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

**Questions** (ask each as a separate turn via AskUserQuestion):

1. **IRR hurdle rate**
   ```
   AskUserQuestion:
     question: "What is the minimum IRR to greenlight a decarbonization measure?"
     header: "IRR Hurdle"
     options:
       - label: "15% (recommended)" — typical institutional threshold
       - label: "10%"
       - label: "20%"
       - label: "Other" — free text
   ```

2. **Utility escalation**
   ```
   AskUserQuestion:
     question: "What annual utility cost escalation rate should we use?"
     header: "Utility Escalation"
     options:
       - label: "3%/yr (recommended)" — standard Audette default
       - label: "2%/yr"
       - label: "4%/yr"
       - label: "Other" — free text
   ```

3. **Discount rate**
   ```
   AskUserQuestion:
     question: "What discount rate should we use for NPV calculations?"
     header: "Discount Rate"
     options:
       - label: "7% (recommended)"
       - label: "6%"
       - label: "8%"
       - label: "Other" — free text
   ```

4. **Value method**
   ```
   AskUserQuestion:
     question: "How should we calculate value creation at exit?"
     header: "Value Method"
     options:
       - label: "Value-inclusive (recommended)" — NOI uplift capitalised at exit cap + added to terminal cash flow
       - label: "Savings-only" — IRR on annual savings alone, no exit value
   ```

Store as: `irr_hurdle`, `utility_escalation`, `discount_rate`, `value_method`.

---

## Q2 — Exit Parameters

**Pre-flight check:** If `found_exit_params`, surface it:
```
AskUserQuestion:
  question: "I found exit years and cap rates in the portfolio documents — should I use those?"
  header: "Exit Params"
  options:
    - label: "Use what's in the docs"
    - label: "I'll share a spreadsheet" — user will paste/attach file
    - label: "Enter manually"
```

**If no prior data found:**
```
AskUserQuestion:
  question: "How would you like to provide exit years and exit cap rates?"
  header: "Exit Params"
  options:
    - label: "Share a spreadsheet" — I'll parse exit years, cap rates, and fund assignments
    - label: "Enter by fund" — I'll ask fund by fund
    - label: "Single portfolio-wide cap rate" — I'll ask for the rate
```

**Follow-up if spreadsheet:** "Please share the file — I'll parse exit years, cap rates, and fund assignments from it."
*(No further AskUserQuestion needed — user shares inline.)*

**Follow-up if by fund or single rate:** ask for the values (one turn per fund or one turn for the single rate).

Store as: `exit_params_source` (spreadsheet / by-fund / single), plus extracted values once provided.

---

## Q2b — Gross Asset Value (GAV)

Ask immediately after exit params are collected.

```
AskUserQuestion:
  question: "Do you have Gross Asset Value (GAV) per asset? This unlocks a 'Value Impact as % of GAV' column in the report."
  header: "GAV"
  options:
    - label: "It's in the spreadsheet I shared" — parse from exit params file
    - label: "I'll enter them manually" — I'll ask asset by asset
    - label: "Search for it" — I'll query portfolio data and public records
    - label: "Leave blank" — skip % of GAV column (recommended if unavailable)
```

**If "It's in the spreadsheet":** extract GAV column when parsing exit params file (no extra turn needed).

**If "Enter manually":** ask once per asset in the portfolio, one at a time.
> "What is the GAV for [Asset Name]? (e.g. '$42M' or '42000000')"

**If "Search for it":** run `search_portfolio("gross asset value GAV property value")` and surface what is found; confirm each value with the user before storing.

**If "Leave blank":** skip; set `gav_source: none` — the % of GAV column will be omitted from the report.

Store as: `gav_source` (spreadsheet / manual / search / none), plus extracted values if provided.

---

## Q3 — Hold Period & Retrofit Timing

**Questions** (ask each as a separate turn via AskUserQuestion):

1. **Exit year floor**
   ```
   AskUserQuestion:
     question: "What is the minimum exit year? Assets exiting before this date will be analysed to this floor."
     header: "Exit Year Floor"
     options:
       - label: "2028 (recommended)"
       - label: "2027"
       - label: "2029"
       - label: "2030"
       - label: "No floor"
   ```

2. **Retrofit lead time**
   ```
   AskUserQuestion:
     question: "How many months lead time do major capital measures (HVAC, electrification, envelope) require?"
     header: "Lead Time"
     options:
       - label: "18 months (recommended)"
       - label: "12 months"
       - label: "24 months"
       - label: "Other" — free text
   ```

Store as: `exit_year_floor`, `retrofit_lead_months`.

---

## Q4 — Optional Add-Ons

```
AskUserQuestion:
  question: "Which optional analyses should we include?"
  header: "Add-Ons"
  multiSelect: true
  options:
    - label: "CRREM pathway analysis" — emissions trajectory chart, stranding risk vs. 1.5°C pathway
    - label: "Building Performance Standards (BPS)" — compliance cost and fine avoidance per asset
```

**If CRREM selected:**
```
AskUserQuestion:
  question: "Which CRREM target years should we report against?"
  header: "CRREM Years"
  multiSelect: true
  options:
    - label: "2030 (recommended)"
    - label: "2035 (recommended)"
    - label: "2040"
    - label: "2050"
```

**If org goal desired:**
```
AskUserQuestion:
  question: "Is there a custom sustainability goal to track progress against?"
  header: "Org Goal"
  options:
    - label: "Yes — I'll describe it" — free text (e.g. 'net zero by 2040', '50% reduction by 2035')
    - label: "No"
```

Store as: `include_crrem` (bool), `include_bps` (bool), `target_years` (list), `org_goal` (string or null).

---

## Q5 — Audette Account

**Pre-flight check:** Report `audette_linked_count` from query.
> "[N] of [total] assets are linked to Audette."

```
AskUserQuestion:
  question: "What is the Audette customer account slug for this portfolio?"
  header: "Audette Account"
  options:
    - label: "Enter slug now" — free text (e.g. 'greystar', 'bclc')
    - label: "Look it up at runtime" — I'll find it when the analysis starts
```

Store as: `audette_account` (string or "runtime-lookup").

---

## Q6 — Scope

**Questions** (ask each as a separate turn via AskUserQuestion):

1. **Fund filter**
   ```
   AskUserQuestion:
     question: "Should we analyse all funds, or specific ones?"
     header: "Fund Filter"
     options:
       - label: "All funds (recommended)"
       - label: "Specific funds" — free text: list fund names
   ```

2. **Top-N table**
   ```
   AskUserQuestion:
     question: "How many assets should appear in the 'top assets by value creation' table?"
     header: "Top-N"
     options:
       - label: "10 (recommended)"
       - label: "5"
       - label: "15"
       - label: "All"
   ```

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
| Discount rate | <discount_rate>% |
| Value method | <value_method> |
| Exit year floor | <exit_year_floor> |
| Retrofit lead time | <retrofit_lead_months> months |

## Exit Parameters
Source: <exit_params_source>
<Summary of exit years and cap rates, or "See attached spreadsheet">

## Gross Asset Value (GAV)
Source: <gav_source>
<List of per-asset GAV values, or "Not provided — % of GAV column omitted from report">

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
