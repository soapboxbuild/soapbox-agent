---
name: capex-analysis
description: >
  Model the cashflow impact of capital interventions and operational changes on a
  real estate asset. Computes Yield on Cost, Investment Spread, IRR delta, and exit
  value change. Requires a base cashflow model built by the cashflow-model skill.
  Triggers on: "what's the impact of [intervention]", "model solar for [asset]",
  "if we renovate [N] units", "what's the yield on cost for [upgrade]",
  "model EV chargers / smart HVAC / tech package / unit reno / amenity upgrade".
version: 1.0.0
---

# Capex Analysis

Model the impact of interventions on a real estate asset's cashflows.
Primary outputs: **Yield on Cost** and **Investment Spread**.

---

## Step 1: Identify Asset and Load Base Model

Get the asset name from context or ask. Compute the asset key
(lowercase, spaces → hyphens).

Load the base model:

```bash
cat .cashflow-models/<asset-key>.json
```

If the file does not exist, say:
> "I don't have a cashflow model for [asset] yet. Would you like me to build one first?"

If yes, invoke the `cashflow-model` skill, then continue.

Extract from the loaded model:
- `dcf_output.annual` — year-by-year cashflows
- `dcf_output.going_in_noi`
- `dcf_output.exit_value`
- `dcf_output.unlevered_irr`
- `exit_cap_rate`

---

## Step 2: Elicit Intervention Details

Ask what intervention(s) the user wants to model. For each, collect:

### ESG / Sustainability

**Solar:**
- System size (kW) or just capex if known
- Gross capex ($) — use $70,000–$100,000 for a typical clubhouse system as a prompt if unknown
- Annual electricity savings ($) — estimate if not known: annual_kwh × local rate ÷ 100
- Start year (default: 1)
- Ask: "Do you have a tax credit (ITC)? In the US, the current ITC is 30%."
  If yes, note it in the scenario description (it does not affect NOI but affects investor returns)

**EV Charging:**
- Number of chargers, capex per charger ($)
- Annual charging revenue (optional)
- Start year

**Smart HVAC / Thermostats:**
- Capex ($/unit × units, or lump sum)
- Energy savings as % of current owner utility expense, or direct $ amount
- Start year

**Green PPA:**
- Annual savings ($ or % rate differential)
- No capex

**Water / Submetering:**
- Capex ($)
- Increase in RUBS/utility recovery ($/unit/month)
- Start year

### Revenue-Enhancing

**Unit Renovation:**
- Capex per unit ($)
- Number of units to renovate
- Expected rent premium per unit per month ($)
  ⚠️ If user says "typical BREEAM/LEED premium" or cites a specific %: ask them to confirm the $
  amount rather than using any published figure — green premium evidence is market-dependent.
- Absorption pace (units renovated per month)
- Vacancy during reno (days per unit)
- Start year

**Amenity Upgrade:**
- Capex ($)
- Expected annual NOI uplift ($ — user must provide this; do not estimate)
- Start year

**Tech Package:**
- Capex per unit ($), number of units
- Rent premium per unit per month ($)
- Start year

### Operational

**Utility Reduction (WasteX, renegotiation):**
- Program cost ($)
- Annual savings ($)
- Start year

**Management Fee Change:**
- New fee % of EGI

---

## Step 3: Confirm Before Computing

List all interventions with their inputs. Ask: "Ready to run the analysis?"

---

## Step 4: Run Intervention Engine

For each intervention, run the engine. Find the script:

```bash
SCRIPT=$(find ~/.claude/plugins -name 'intervention_engine.py' 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  SCRIPT=~/soapbox-agent/scripts/intervention_engine.py
fi
```

Run for each intervention:

```bash
python3 "$SCRIPT" \
  --base '<BASE_MODEL_JSON>' \
  --intervention '<INTERVENTION_JSON>' \
  --market-cap-rate <MARKET_CAP_RATE>
```

Where `<BASE_MODEL_JSON>` contains at minimum:
```json
{
  "asset_name": "...",
  "annual": [...],
  "exit_value": ...,
  "going_in_noi": ...,
  "unlevered_irr": ...,
  "exit_cap_rate": ...
}
```

For multiple interventions, sum the `noi_delta_by_year` arrays and re-run a combined
pass through the engine with the summed deltas as a `custom` intervention type — or
present them individually and then show a combined total.

---

## Step 5: Present Results

Show the summary card from the engine output.

Then show the full year-by-year comparison table if more than one intervention or if
the user asks:

```
Year  Base NOI      Delta      With Intervention
1     $6,947,357   +$67,064   $7,014,421
2     $7,225,251   +$98,800   $7,324,051
...
```

For multiple interventions combined:
- Show individual YOC and Investment Spread per intervention
- Show combined NOI delta and combined IRR delta

---

## Step 6: Explain Investment Spread

After presenting the YOC, always explain the Investment Spread:

> "The Investment Spread of **[X]pp** means your intervention earns [X]pp above what
> the market would pay for a stabilised asset at [cap rate]% cap. A positive spread
> = value creation. A negative spread means you're paying more to create NOI than
> the market will pay for it at exit."

---

## Step 7: Save Scenario

Save the scenario to the model JSON. Load the existing model, append the scenario,
and write it back:

```python
import json, datetime
with open('.cashflow-models/<asset-key>.json') as f:
    model = json.load(f)

scenario_name = '<intervention-type>-<date>'  # e.g. "solar-unit-reno-2026-06-26"
model['scenarios'][scenario_name] = {
    'interventions': [<intervention_dicts>],
    'noi_delta_by_year': [...],
    'yoc': ...,
    'investment_spread': ...,
    'irr_delta': ...,
    'exit_value_delta': ...,
    'run_date': datetime.date.today().isoformat()
}
model['last_updated'] = datetime.date.today().isoformat()

with open('.cashflow-models/<asset-key>.json', 'w') as f:
    json.dump(model, f, indent=2)
```

---

## Rules

- Always load the base model from disk — never recompute it from scratch.
- Never suggest specific green premium percentages. If asked: "Green premium evidence
  is market- and methodology-dependent. Please provide your own assumption or use 0
  for a conservative base case."
- Always show the Investment Spread explanation after presenting YOC.
- Always save the scenario to disk before ending the session.
- If YOC is negative: "This intervention reduces NOI — the costs outweigh the
  savings/revenue at current assumptions. Review the inputs."
- If Investment Spread is negative but YOC is positive: "This intervention creates
  value, but the return (YOC [X]%) is below the market cap rate ([Y]%). You're
  paying more to create NOI than the market will pay for it at exit."
