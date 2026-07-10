---
name: construction-costing
description: >
  Estimate construction cost (CapEx and annual OpEx delta) for a decarbonization measure or a
  full measure roster, emitting the `measure.cost` object consumed by `decarb-plan` measure
  screening and read by `quality-review`. Handles fuel-switch / electrification measures with an
  explicit electrical service-capacity model (demand increase, headroom-vs-new-service
  UNVERIFIED range, never a collapsed point estimate) and always pairs a fuel-switch measure
  with a non-switching `efficiency_alternative`. Triggers on: "estimate construction cost",
  "what's the CapEx for", "cost this measure", "cost this roster", "how much would this retrofit
  cost", "electrical service upgrade cost".
version: 1.0.0
---

# Construction Costing

You are estimating **construction cost** for one or more decarbonization measures — the
`capex` (low/base/high) and `opex_delta_yr` (annual OpEx change, **positive = OpEx rises**,
negative = OpEx falls) that feed the `decarb-plan` measure-screening economics, and that
`quality-review` reads back when auditing a plan. This skill does **not** invent numbers: every
`base` capex and `opex_delta_yr` comes from the seeded lookup table in
`references/cost-bases.md`, keyed by `archetype`, `climate`, and `size` — not from LLM
estimation or memory of "typical" retrofit costs.

**Positioning:** `construction-costing` is a narrow, mechanical costing method, not a full
economic-feasibility engine. It produces the `measure.cost` object; `decarb-plan` owns the
downstream NPV/IRR/payback math and landlord-share capture logic. Do not compute IRR or
discounted paybacks here — that belongs to the plan's economics step, which consumes this
skill's output.

---

## Ground rules

1. **No invented cost figures.** Every capex/opex number traces to a row in
   `references/cost-bases.md` or the electrical service-capacity `$/kW` curve in that same
   file. If a measure has no matching row (archetype/climate/size combination not covered),
   say so explicitly and flag it for a human to add a row — do not guess a number to fill the
   gap.
2. **cost-bases.md is seeded and provisional.** Every dollar figure in that reference file is a
   PLACEHOLDER pending tuning by Christopher against real bids and utility tariffs. When you
   report a cost estimate to a user, note that the underlying basis is a seeded default, not a
   verified market price — never present these numbers as authoritative pricing.
3. **`opex_delta_yr` sign convention is fixed:** positive means OpEx *rises* (e.g., more
   expensive electricity displacing cheap gas), negative means OpEx *falls*. Never flip this
   sign when composing or comparing measures.
4. **Electrical service capacity is never guessed away.** Any fuel-switch / electrification
   measure that increases electrical demand must carry an explicit electrical service capacity
   assessment. When the actual service capacity is unknown, the upgrade cost is an honest
   `range`, and it must **never** collapse to a point estimate — see Step 3.
5. **Every fuel-switch measure gets a non-switching sibling.** Any `measure_kind: fuel_switch`
   row must also emit an `efficiency_alternative` — the standard high-efficiency,
   non-fuel-switching option (e.g., a condensing boiler instead of an ASHP plant) — so the plan
   can screen "switch fuels" against "just get more efficient at the same fuel."
6. **Validate before handing off.** Every `measure.cost` object this method emits must validate
   against `skills/construction-costing/schema/measure-cost.schema.json` via
   `node scripts/validate-measure-cost.mjs` before it is considered done.

---

## Method

### Step 1: Load the measure roster and the Audette model

Read the measure roster for the engagement (the candidate list produced upstream by
`decarb-plan`'s measure generation) and the corresponding Audette building model, specifically:
end-use energy breakdown, peak electrical demand by end use, and — where available — existing
electrical service capacity (panel schedule, service entrance rating, or utility
interconnection headroom). If the roster or model is missing required fields (e.g., no peak
demand data for a candidate fuel-switch measure), flag it rather than filling the gap with an
assumption.

### Step 2: Look up the parametric base per measure

For each measure, determine its **archetype** (`multifamily`, `office`, `lab`, `mixed_use`),
**climate** zone band (`cold`, `mixed`, `hot`), and building **size** band (`small`, `mid`,
`large`), then look up the matching row in `references/cost-bases.md`. That row gives you
`capex {low, base, high}` and `opex_delta_yr` (again: **positive = OpEx rises**) scaled to a
reference building size — scale linearly by GSF or unit count relative to that reference unless
the table notes a different unit basis (e.g., "per 100 hoods" for fume-hood VAV).

If no row matches the archetype × climate × size combination, do not extrapolate silently from
an unrelated row — surface the gap explicitly (e.g., "no cost-bases.md row for `lab` × `hot` ×
`large`; using the nearest `mixed` climate row as an approximation, flagged for review").

### Step 3: Fuel-switch / electrification measures — the electrical service capacity model

For any measure that switches fuel (e.g., gas boiler → ASHP, gas furnace → VRF):

1. Compute `demand_increase_kw` — the delta between the new electrified end-use's peak
   electrical demand and the existing electrical peak demand at that panel/service entrance,
   from the Audette model.
2. Check whether **actual electrical service capacity is known** for this building
   (`service_capacity_known: true/false`):
   - **Known** (a real electrical survey, panel schedule, or interconnection study confirms
     available headroom): emit a **point** `upgrade_cost` (the single confirmed cost, which may
     be $0 if headroom covers the increase, or the confirmed upgrade quote otherwise) and
     `flag: 'VERIFIED'`.
   - **Unknown**: emit a **range** — `upgrade_cost.low = 0` (best case: assume existing service
     has enough headroom, no service upgrade required) and `upgrade_cost.high` = the full new
     electrical service cost, computed from the `$/kW` (or `$/A`) parametric curve in
     `references/cost-bases.md` Section 5.1 as `demand_increase_kw × region_$/kW`. Set
     `flag: 'UNVERIFIED'`.
3. **Never** collapse an `UNVERIFIED` range to a point estimate — e.g., never average
   `low`/`high` into a single number, and never silently pick `high` (or `low`) as "the" cost
   when capacity is unknown. The range itself communicates real risk to the plan's economics
   step and to `quality-review`; collapsing it hides that risk.

### Step 4: Always emit the efficiency alternative

For every fuel-switch measure, also produce the standard **non-switching**, high-efficiency
option at the same archetype/climate/size (e.g., a condensing boiler replacement instead of an
ASHP plant conversion — see `references/cost-bases.md` Section 3 for the boiler-replacement
rows that pair with Section 2's electrification rows). Emit it as the `efficiency_alternative`
object with its own `capex` (a single number — the alternative's `base` estimate, not a
low/base/high spread) and its own `opex_delta_yr`. This lets the downstream plan compare
"switch fuels" against "stay on the same fuel but get more efficient" on equal footing.

Non-fuel-switch measures (LED, DCV, fume-hood VAV, chiller optimization, envelope) do not need
an `efficiency_alternative` — they already *are* the efficiency option.

### Step 5: Emit the `measure.cost` object and validate

Assemble the full `measure.cost` object per measure, matching the shape defined in
`schema/measure-cost.schema.json`:

```json
{
  "measure_id": "central-ashp",
  "measure_kind": "fuel_switch",
  "cost": {
    "capex": { "low": 1400000, "base": 2100000, "high": 3200000 },
    "opex_delta_yr": 48000,
    "electrical_capacity": {
      "demand_increase_kw": 420,
      "service_capacity_known": false,
      "upgrade_cost": { "low": 0, "high": 1800000 },
      "flag": "UNVERIFIED"
    },
    "efficiency_alternative": {
      "measure": "high-efficiency condensing boiler replacement",
      "capex": 520000,
      "opex_delta_yr": -14000
    }
  }
}
```

Non-fuel-switch measures omit `electrical_capacity` and `efficiency_alternative` entirely (see
`skills/construction-costing/example-data.json`'s `led-upgrade` entry for the minimal shape).

Before handing the roster's `measure.cost` objects downstream, validate them by running:

```bash
node scripts/validate-measure-cost.mjs
```

This checks the JSON Schema shape **and** the contract rules beyond the schema — notably that
every `fuel_switch` measure has both `electrical_capacity` and `efficiency_alternative`, and
that an `UNVERIFIED` electrical capacity never has `upgrade_cost.low === upgrade_cost.high`
(i.e., it is never a disguised point estimate). Fix any measure that fails validation before
proceeding — do not hand an invalid `measure.cost` object downstream.

### Step 6: Hand off

The `measure.cost` objects this method produces are consumed by `decarb-plan`'s measure
screening step (which combines them with energy-savings estimates to compute NPV/IRR/payback,
applying landlord-share capture separately) and are read by `quality-review` when auditing a
plan's cost basis for defensibility. This skill's job ends at producing a validated
`measure.cost` per `schema/measure-cost.schema.json` — it does not itself rank, screen, or
render measures.
