---
name: cashflow-model
description: >
  Build a multi-year DCF cashflow model for a real estate asset from natural
  language inputs. Supports multifamily, office, industrial, retail, and hotel
  across US and international markets. Saves the model to the workspace for use
  by capex-analysis. Triggers on: "build a model for [asset]", "what are the
  financials on [asset]", "model [asset]'s cashflows", "what's the IRR on [asset]",
  or when capex-analysis finds no base model for the asset.
version: 1.0.0
---

# Cashflow Model

Build a multi-year DCF for a real estate asset. Saves the model to
`.cashflow-models/<asset-key>.json` in the workspace.

---

## Step 1: Identify the Asset

Ask for the asset name if not already clear from context. The asset name becomes
the memory key (e.g. "Prose Frontier" → key `prose-frontier`).

Check whether `.cashflow-models/<asset-key>.json` already exists:

```bash
ls .cashflow-models/<asset-key>.json 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

If it exists, ask:
> "I have an existing model for [asset]. Would you like to update it, or use it as-is?"

If "use as-is", stop here. The model is ready for `capex-analysis`.

---

## Step 2: Establish Asset Profile

Ask three questions (one at a time):

**Q1 — Asset type:**
> "What type of asset is [name]?"
> 1. Multifamily / Residential
> 2. Office
> 3. Industrial
> 4. Retail
> 5. Hotel
> 6. Mixed-use

**Q2 — Region:**
> "Where is the asset located?"
> 1. United States
> 2. United Kingdom
> 3. Germany
> 4. France
> 5. Australia
> 6. Other Europe
> 7. Asia-Pacific / Other

**Q3 — Hold convention:**
> "What level of analysis do you want?"
> 1. Unlevered (NOI and IRR only — no debt)
> 2. Levered (add debt terms)
> 3. Full waterfall (debt + LP/GP splits)

Store the profile:
```json
{
  "asset_type": "<type>",
  "region": "<region>",
  "currency": "<USD|GBP|EUR|AUD|...>",
  "hold_convention": "<unlevered|levered|levered-with-waterfall>"
}
```

---

## Step 3: Check for Uploaded Documents

Before eliciting inputs, check whether the user has uploaded an Excel model or PDF.
If yes, extract the relevant figures from it:
- For Excel: identify sheets named "Summary", "Cash Flow", "Operating Budget", or similar.
  Read key fields: unit mix, market rents, vacancy %, opex line items, hold period, exit cap rate.
- For PDF (OM): read the "Financial Analysis" / "Pro Forma" section for stabilized NOI,
  unit mix, and operating expenses.

Pre-populate inputs from documents and skip elicitation questions for fields already found.
Note which fields came from the document vs. were assumed.

---

## Step 4: Elicit Inputs

Ask only for fields not already extracted from documents. Group by template:

### Multifamily inputs:
- Unit mix: for each unit type — count, avg SF, current market rent/unit/month
- Going-in occupancy % and loss-to-lease %
- Vacancy %, concessions %, bad debt %
- Other income per unit per year (RUBS, parking, fees, pet — can use $2,000–$2,500 as a starting benchmark for US suburban Class A)
- Opex: payroll $/unit, O&M $/unit, marketing $/unit, G&A $/unit, utilities $/unit, mgmt fee % of EGI, insurance $/unit, taxes $/unit, reserves $/unit
- Hold period (years), exit cap rate, sale costs %

### Office / Industrial / Retail inputs:
- Total rentable SF, current occupancy %
- Passing rent $/SF/year, market (ERV) rent $/SF/year
- Lease structure: gross / NNN / net
- Opex $/SF (gross leases), capex $/SF/year, TI at renewal $/SF, LC % of lease value
- Avg lease term, renewal probability
- Hold period (years), exit cap rate, sale costs %

### Hotel inputs:
- Number of rooms
- ADR (Average Daily Rate), going-in occupancy %
- Rooms expense %, undistributed expense %, management fee % of total revenue
- FF&E reserve % of total revenue (typically 3–5%)
- Insurance $/room/year, taxes $/room/year
- Other revenue % of rooms revenue (F&B, spa, etc.)
- Hold period (years), exit cap rate, sale costs %

### Regional rent growth defaults (suggest to user, let them override):
| Region | Rent growth | Expense growth |
|---|---|---|
| US (Yr 1–2) | 4.0% | 3.0% |
| US (Yr 3+) | 3.0% | 3.0% |
| UK | ERV growth per MSCI/JLL submarket data | 3.0% |
| Germany | CPI (10-point trigger) | 3.0% |
| France | INSEE ILC/ILAT statutory | 3.0% |

If the user does not provide growth rates, use the regional defaults above and note them explicitly.

---

## Step 5: Confirm Before Computing

Present a confirmation table of all inputs. Note which came from documents vs. assumed.
Ask: "Ready to build the model with these inputs?"

---

## Step 6: Run DCF Engine

Find and execute the DCF engine:

```bash
SCRIPT=$(find ~/.claude/plugins -name 'dcf_engine.py' 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  SCRIPT=$(find ~/soapbox-agent -name 'dcf_engine.py' 2>/dev/null | head -1)
fi
python3 "$SCRIPT" --inputs '<INPUTS_JSON>'
```

Replace `<INPUTS_JSON>` with the full inputs object including `asset_name` and `profile`.

Parse the JSON stdout. If the script fails, show the stderr to the user and stop.

---

## Step 7: Handle Levered / Waterfall (if requested)

If hold_convention is `levered` or `levered-with-waterfall`, ask for:
- Loan amount or LTC %, interest rate, I/O period (months), amortization (years), closing costs %

Compute levered cashflows:
- Annual debt service = compute from loan terms (I/O: rate × principal; amortizing: standard mortgage formula)
- Levered CF = Unlevered CF − Debt Service
- DSCR Year 1 = NOI Year 1 / Annual Debt Service (flag if < 1.20)

If waterfall:
- Ask for: LP % equity, GP % equity, hurdle tiers (rate, promote %)
  (Common US structure: 10%/13%/16% hurdles, 20%/30%/40% promotes)
- Compute tiered distributions across the hold period

Present levered IRR and LP/GP IRRs in the summary card.

---

## Step 8: Save Model

Create the `.cashflow-models/` directory if it does not exist:

```bash
mkdir -p .cashflow-models
```

Write the model JSON:

```json
{
  "asset_name": "<name>",
  "asset_key": "<key>",
  "profile": { ... },
  "unit_mix": [ ... ],
  "going_in_occupancy": 0.95,
  "loss_to_lease_pct": 0.02,
  "vacancy_pct": 0.05,
  "concessions_pct": 0.01,
  "bad_debt_pct": 0.0015,
  "other_income_per_unit": 2049,
  "opex": { ... },
  "growth": { "rent": [...], "expense": [...] },
  "hold_period_years": 5,
  "exit_cap_rate": 0.05,
  "sale_costs_pct": 0.015,
  "debt": null,
  "waterfall": null,
  "dcf_output": { "annual": [...], "going_in_noi": ..., "stabilized_noi": ..., "exit_value": ..., "unlevered_irr": ... },
  "scenarios": {},
  "last_updated": "<ISO date>"
}
```

---

## Step 9: Present Summary Card

Show the summary card from the DCF engine output.

Then say:
> "Model saved for [asset name]. Use `capex-analysis` to model the impact of any interventions — solar, unit renovations, EV chargers, operational changes, etc."

---

## Rules

- Never fabricate inputs — ask if missing. The only exception is regional rent growth defaults which must be stated explicitly.
- Always note which inputs came from uploaded documents vs. user-provided vs. defaults.
- Never assert specific green premium percentages — these must be user-provided.
- Always confirm inputs before running the engine.
- Always write the model JSON to disk before presenting the summary card.
- If the engine produces an IRR outside 0–30%, flag it: "The IRR of X% is outside typical range — please review the inputs."
- Hotel assets: remind the user this is an investor-level model, not a hotel management system.
