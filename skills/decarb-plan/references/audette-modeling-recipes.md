# Audette modeling recipes

Practical mechanics for working with the Audette platform during decarb-plan engagements.
Verified live against the Audette API/tools on 2026-07-03/04. Read this before P1.5
building-model fixes, P3 measure/share configuration, or any large Audette batch.

## 1. Building GFA is NOT editable in place

`edit_building_attributes` has no GFA key — you cannot fix a wrong gross floor area on an
existing building record. If the building geometry is wrong (see P1.5 validation), the fix is
a rebuild, not an edit:

1. `create_building` with the **correct** `gross_floor_area_square_feet` computed from the real
   footprint × stories (per the ALTA/PCA reconciliation in P1.5).
2. `assign_property_to_building` to the **existing** `property_uid`. Never call
   `create_property_for_building` when the property already exists — that creates a duplicate
   property record instead of attaching the corrected building to the real one.
3. `delete_building_model` on the old, wrong building set. This requires the `DELETE_BUILDING`
   permission — verified available on the platform account as of 2026-07.
4. Re-upload utility data and re-apply landlord/tenant shares and exit assumptions to the new
   buildings. **Nothing carries over** from the deleted buildings — treat the rebuild as a clean
   slate for every downstream setting.

## 2. Landlord/tenant share fields

Two independent levels, easy to confuse:

- **Building level** — `edit_building_attributes` updates:
  - `default_landlord_share_electricity`
  - `default_landlord_share_natural_gas`
  - `default_landlord_share_steam`
  - `default_landlord_share_cost`
  All are 0–1 floats.
- **Measure level** — `landlord_share_*` fields (no `default_` prefix) on each measure inside
  `create_custom_plan` / `update_custom_plan_measures`. These override the building default for
  that specific measure. Also set `like_for_like_cost` per measure — this is the incremental-cost
  basis the IRR is computed against.

**Common agent error**: trying `landlord_share_*` (missing `default_` prefix) at the *building*
level throws an `AttributeError`, which gets misread as "shares are account-level only, not
per-building." That conclusion is wrong — shares are configurable at both building and measure
level, just with different field names. Use `default_landlord_share_*` for buildings and
`landlord_share_*` for measures.

### 2a. `landlord_share` is PER MEASURE, keyed to WHERE THE LOAD SITS — never one building-wide split

Audette computes `annual_mean_landlord_utility_cost_savings` / `annual_mean_tenant_utility_cost_savings`
from **each measure's authored `landlord_share`**. So the owner/tenant savings split is decided
measure-by-measure at write-back time (`create_custom_plan` / `update_custom_plan_measures`) — NOT
by a single property/building-wide default stamped onto every measure. Applying one blended split to
all measures is the exact bug that credits ~95% of a **common-area LED** or **house-metered solar**
to *tenants*: those are landlord loads, but they inherit a whole-building split dominated by in-unit
tenant meters. **Set `landlord_share` per measure from the measure's end-use, keyed to what the load
SERVES** (not to "is it on a master meter" as a monolith).

**End-use → default `landlord_share` (the floor — override per real metering/RUBS when confirmed):**

| End-use / where the load sits | Default `landlord_share` |
| --- | --- |
| Common-area / house-metered / amenity: corridor & exterior lighting, garage, elevator, pool/spa, clubhouse, common ventilation | **0.9–1.0** |
| BTM solar offsetting the **house/common meter** (owner-paid load) | **0.9–1.0** |
| Solar under **Virtual Net Metering (VNM)** (credits distributed to tenant accounts) | **0.80** (verify VNM tariff exists — recipe/2C; if only BTM NEM, treat as the house-meter offset above) |
| In-unit / tenant-metered: in-unit HVAC, in-unit DHW, in-unit lighting/appliances (residents pay the meter) | **0.0–0.1** |
| Mixed / central plant serving **in-unit residential** load (central heating/DHW delivered to units) | **split by served load**; where the residential-served consumption is **rebillable via RUBS and RUBS is verified**, net owner ≈ **0.10** on that share (the Rosslyn/Cortland rule — see SKILL.md 2C). ~1.0 only where the owner genuinely absorbs it (gross lease / RUBS barred). |
| BPS fine avoidance | 1.0 (100% owner, regardless of metering) |

The map is the **floor by physical load-location**; the agent overrides per real metering evidence and
per the jurisdiction's verified RUBS/VNM status (2C capture map, Gate 1). The RUBS ~10% recovery applies
**only to master-metered load that is actually residential consumption** (central plant → units) — it
does **not** apply to genuine common-area/house/amenity loads, which stay with the owner (0.9–1.0).
**Never** set a common-area or house-metered measure to the building's blended in-unit split.

**Verification cue:** after authoring, any measure the map assigns a HIGH owner share
(common-area / house-metered / amenity / BTM-solar-on-house-meter) whose Audette savings land mostly on
**tenants** is a red flag — that is the signature of the building-wide split leaking in; re-check that
measure's `landlord_share`. (Central-plant-serving-in-unit measures whose savings land mostly on tenants
are *correct* under RUBS and are NOT the red flag.)

## 3. Exit assumptions per building

Set via `edit_building_attributes`:
- `assumed_exit_cap_rate`
- `assumed_exit_year`
- `assumed_gross_asset_value`

**Important**: Audette's measure-level IRR output does **not** include residual/exit value or
BPS fine avoidance, even when these exit fields are populated — they inform other Audette
outputs but are not folded into the measure IRR. Per the IRR doctrine, any exit value or fine
avoidance used in a report must be layered on manually, with every IRR stating its bases
explicitly (energy savings only, vs. + exit value, vs. + fine avoidance).

## 4. Batch size / token fragility

Large parallel Audette tool-call bursts (~27+ simultaneous calls in one turn) have repeatedly
killed the OAuth token mid-batch. Until refresh-persistence is fixed platform-side:

- Batch **≤8–10 Audette calls per turn**.
- Checkpoint progress in `state` after every batch — record which buildings/measures are done
  vs. pending, not just an aggregate count.
- Expect to need a reconnect and resume mid-engagement on large portfolios; design the workflow
  so resuming from the checkpoint is mechanical, not a re-derivation.

## 5. Equipment survey — map to the real system, don't reach for a proxy first

**Identify the actual heating system before modeling.** The most common error is defaulting to
a proxy (or to the tool's electric-heat default) when Audette has a literal match for the real
equipment. Check the PCA/MEP drawings for what the space-heating system actually is, then map it.

### 5a. Hydronic furnaces (garden-style forced-air served by a hot-water/combi source)

Audette **has a native match** — do NOT use the fan-coil proxy for these. A hydronic furnace is a
ducted forced-air furnace whose heat exchanger is a hot-water coil (fed by a boiler or combi water
heater). The correct A4/Type-A survey pattern (Cortland Westminster, adjudicated by Christopher
2026-07-04) is:

| Audette survey field | Value |
|---|---|
| Central plant → **Boiler** | **Hydronic furnace** ← the space-heating system lives here |
| **Air handler** | Exhaust-only air handler (ventilation only — it is NOT the heat source) |
| Terminal units → **Cooling** | Split air conditioner |
| Domestic water heater | Gas heater; **Central distribution: No** (individual in-unit gas DHW) |
| Packaged rooftop units | Not defined |
| Additional equipment | Clothes dryers: Electric; clothes washers: Yes (+ ASHRAE densities/ages) |

This yields the correct fuel (`NATURAL_GAS` heating + gas DHW), separates cooling (electric split
AC) from heating, and keeps DHW as a distinct gas load — all of which drive the electrification
measures (heating → air-to-water / heat-pump furnace; DHW → HPWH) and BPS/carbon results.

#### `submit_equipment_survey` payload — see the Audette skill (single source of truth)

The full payload schema — all 10 required groups, every enum value, the **tons** capacity units
(incl. DHW; airflow in CFM for AHU/RTU), the `null`-not-`0` rule, the mandatory-ventilation-path
validation, and the *audit-an-existing-survey's-units-and-overwrite* rule — lives in the Audette
**`audette-equipment-survey`** skill (bundled with the Audette MCP: `references/submission-guide.md`
+ `references/equipment-schema.md`). **Read that skill and copy its payload template before any
`submit_equipment_survey` call** — do not restate or guess the schema here. This recipe covers only
the decarb-specific *system→topology mapping* decisions above (5a/5b/5c); the audette skill owns the
schema, enums, and units.

### 5b. True in-unit combi with fan-coil distribution (no forced-air furnace)

ONLY when the in-unit gas water heater serves both DHW and space heat via **fan coils / hydronic
terminals** (not a ducted furnace) and there is no literal match, model as
`central_plant_heater = gas_boiler + fan_coil_units`. This is a proxy for fuel/distribution
fidelity, not a physical description. Document it explicitly in `state` so it isn't read as a data
error. Do not apply this to hydronic furnaces — use 5a.

### 5c. Water-source heat pumps (WSHP / water-loop heat pumps) — the units live in `heat_pump`

A WSHP building has distributed reversible heat-pump units in each zone/suite tied to a common
condenser-water loop. The loop is kept in range by a gas boiler (winter top-up) and a cooling tower
(summer rejection), and ventilation is a make-up-air unit (MAU). The units do **both** zone heating
and zone cooling, electrically. **Verified from Audette source 2026-07-07.**

**The native match:** the WSHP units are `heat_pump` with `heat_pump_type = water_loop_heat_pump`
(class `WaterLoopHeatPump`) — a skin-heating **and** skin-cooling device that owns both. Do NOT use
`central_plant_heat_pump` for them (that field is only `air_source_heat_pump | ground_source_heat_pump`
and represents a *central plant conditioning the loop* — e.g. geothermal — not the distributed units).
Do NOT split the units into `terminal_cooler` (split AC) + a separate heater — one reversible unit does
both; a `terminal_cooler` would double-count cooling.

**The condenser-loop boiler** is modeled as `central_plant_heater = gas_boiler`. Keeping it alongside
the WLHP is correct — the survey path auto-balances the skin-heating split. Source facts:
- `central_plant_heater_terminal_units` (`fan_coil_units` etc.) is **never read** during boiler
  construction — only `size`/`installation_year` are. Don't agonize over the terminal-unit label for a
  WSHP loop boiler; it has no effect.
- **Auto-balance:** `normalize_equipment_list._update_heating_load_ratio` runs in the survey path. When
  a `HeatPump` **and** a heater (`Boiler`/`Furnace`/`UnitHeater`/`ElectricBaseboard`) are both present:
  if the heat pump's heating load ratio is `1.0` it is scaled to **0.85** and the heater gets `1 − 0.85
  = 0.15`. With a heat pump and **no** heater, the heat pump is forced to `1.0`. So leaving
  `heat_pump_heating_load_ratio = null` + a loop boiler yields **~85% electric skin heat (WLHP) / 15%
  gas (boiler)** automatically, and `verify_load_ratios` passes.
- **To control the split**, set `heat_pump_heating_load_ratio` to your target **≠ 1.0** (e.g. `0.90` →
  boiler auto-takes `0.10`). You **cannot** get 100% electric skin heat while a boiler exists — the
  `1.0 → 0.85` cap always leaves the boiler ≥15%. For fully-electric skin heat, **drop the boiler**
  (`central_plant_heater_exists = false`) and carry residual gas on the MAU
  (`air_handling_equipment_heating_type = gas`, an outdoor-air-heating end use that doesn't compete
  with the WLHP). Either way, **verify the modelled gas/electric split against the meters** (submit →
  read fuel split → adjust). Note this normalization covers **heating only**; skin cooling relies on
  the WLHP's inferred `cooling_load_ratio` (leave `null` unless the readback shows it off).

**Cooling tower has no enum** — it's folded into the loop. A WSHP building has `central_plant_cooler_exists
= false` (the WLHP + tower reject heat to the loop; there is no chiller).

**WSHP office payload — MAU-carries-gas variant** (one valid approach: loop boiler dropped, residual
gas on the gas MAU. The other valid approach keeps `central_plant_heater = gas_boiler` and tunes
`heat_pump_heating_load_ratio` per the note above.) Sizes are **tons** (245 First — Office, Clarion
Partners; adjust COPs/sizes/years/MAU rate per building — heating COP 3.7 per audit, cooling COP est. 3.5):

```json
{
  "air_handling_equipment": { "air_handling_equipment_exists": true, "air_handling_equipment_type": "make_up_air_unit", "air_handling_equipment_heating_type": "gas", "air_handling_equipment_cooling_type": null, "air_handling_equipment_supply_air_rate": <cfm to hit measured gas>, "air_handling_equipment_average_installation_year": null },
  "central_plant_heater": { "central_plant_heater_exists": false },
  "central_plant_cooler": { "central_plant_cooler_exists": false },
  "central_plant_heat_pump": { "central_plant_heat_pump_exists": false },
  "domestic_hot_water_heater": { "domestic_hot_water_heater_exists": true, "domestic_hot_water_heater_central_distribution": <per audit>, "domestic_hot_water_heater_type": "<gas_heater|electric_heater|indirect_heater>", "domestic_hot_water_heater_size": null, "domestic_hot_water_heater_average_installation_year": null },
  "terminal_cooler": { "terminal_cooler_exists": false },
  "terminal_heater": { "terminal_heater_exists": false },
  "rooftop_unit": { "rooftop_unit_exists": false },
  "heat_pump": { "heat_pump_exists": true, "heat_pump_type": "water_loop_heat_pump", "heat_pump_heating_coefficient_of_performance": 3.7, "heat_pump_cooling_coefficient_of_performance": 3.5, "heat_pump_heating_load_ratio": 1.0, "heat_pump_cooling_load_ratio": 1.0, "heat_pump_size": null, "heat_pump_installation_year": <year> },
  "other_equipment": { "clothes_dryers_exists": false, "clothes_washers_exists": false, "elevators_exists": <per audit>, "escalator_exists": false, "rooftop_photovoltaics_exists": false }
}
```

`heat_pump_*_load_ratio = 1.0` makes the WLHP own 100% of skin heating + cooling deterministically
(verify passes: skin heating 1.0 = WLHP, OA heating 1.0 = gas MAU, OA cooling 0.0). `load_ratio` must
be `0 < x ≤ 1` — never `0`. **Then calibrate empirically:** submit, read back the modelled fuel split,
and tune the MAU `supply_air_rate` (drives gas) so modelled gas ≈ measured and electricity rises to
match — don't ship on the inference alone.

## 6. Utility allocation recipe (never-even-split rule)

1. Carve out audit-identified common/amenity loads first (typical magnitude: ~4% of electricity,
   ~2–3% of gas for garden-style multifamily — confirm against the specific audit, don't assume).
2. Allocate the remainder **GFA-weighted** across residential buildings — never an even split
   per building.
3. Within each building, apply the property's real monthly seasonal profile (not a flat
   12-way split) scaled to that building's annual share.
4. Unconditioned utility/mechanical buildings get **no** utility data assigned.
5. Verify: sum of all building-level allocations must reconcile to the source (ESPM/utility
   bill) total with zero variance. Any nonzero delta means the allocation math is wrong, not
   that there's an acceptable rounding gap.

## 7. Soapbox asset link after a building rebuild

After any rebuild (recipe 1), `assets.metadata.audette_building_uids` on the Soapbox side must
be repointed to the new UID set. This is a platform-side update. Generate the new UID list
programmatically from the freshly created buildings' API responses — never hand-transcribe
UUIDs from logs or chat output; a single transposed character silently breaks the asset-to-model
link with no error at write time.

## 8. Direct-cap value-creation waterfall + cashflow (from Audette investment models)

The economics deliverable is a **value-creation bridge** (waterfall chart) backed by an annual
cashflow, mirroring the Audette per-asset investment models ("Plan N Waterfall Chart Data" +
"Plan N Cashflow" + "Plan N Summary"). Reverse-engineered from 40 live models 2026-07-04.

### Waterfall components → Impact on Asset Value at Exit
Start at the incremental capex and bridge to net value creation:

| Bar | Sign | Computation |
|---|---|---|
| Incremental Capital Expenses | − | Σ **incremental cost over like-for-like** across the plan's measures |
| Capitalized Subscription | − | Subscription-model measures (e.g. Parity RCx): stabilized annual **subscription fee ÷ exit cap**. Separate, transparent cost drag — the savings it enables stay GROSS in Capitalized Utility Savings. Omit / 0 if no subscription measures. |
| Incentives | + | rebates/incentives offsetting capex |
| Capitalized Utility Savings | + | stabilized annual **owner-share** utility $ savings **÷ exit cap** (GROSS of any subscription fee) |
| Capitalized Ancillary Revenue | + | stabilized annual solar/EV revenue **÷ exit cap** |
| PV of BPS Fine Avoidance | + | **discounted present value** of the avoided-fine stream |

**Also populate `baseline_capex`** = Σ **like-for-like** replacement cost across the plan's measures
(POSITIVE) — the spend that happens anyway, that the incremental sits on top of. It is
**context/disclosure only**: the scenario comparison table must show BOTH baseline and incremental
capex, but `baseline_capex` is **NOT** a bridge bar and is **NOT** summed into net value creation.

`net_value_creation` = incremental_capex + capitalized_subscription + incentives +
capitalized_utility_savings + capitalized_ancillary_revenue + pv_bps_fine_avoidance.

**Capitalize vs PV — the rule the skill kept getting wrong:** recurring/perpetual NOI changes
(utility savings, ancillary revenue, and a subscription fee) are **capitalized** (÷ exit cap →
perpetuity value at exit); the BPS fine-avoidance stream is a **present value** (discounted, finite)
because fines are a *scheduled* penalty, not a perpetual NOI change. Never capitalize fine avoidance.

### Cashflow (annual) — the model underneath the waterfall
Columns: `Year | Revenue | Utility Savings | Like-for-like CapEx | Incremental CapEx | Incentives | BPS Fine Avoidance | NOI Impact | Unlevered Incremental Cashflow | Cumulative | Asset Value Impact`.
- **NOI Impact** = Revenue + Utility Savings + BPS Fine Avoidance
- **Unlevered Incremental Cashflow** = NOI Impact − Incremental CapEx + Incentives
- **Asset Value Impact** is booked in the **exit year** = capitalized NOI uplift at exit
- **IRR on Incremental Spend** = `irr(annual incremental cashflows + terminal Asset Value Impact)`.
  The waterfall and the IRR are the SAME model viewed two ways.
- **Apply utility-rate escalation** to the Utility Savings stream year-over-year — savings are NOT
  flat-nominal over the hold. Use the **confirmed `kickoff.utility_escalation`** (Soapbox defaults
  3%/yr electricity, 4%/yr gas, confirmed/overridden at kickoff — never silently chosen) and
  **state the assumption + its source** in the report. Flat-nominal savings understate later-year
  cashflow AND the capitalized exit value (the terminal Asset Value Impact caps the escalated
  stabilized savings). Escalation compounds over a 10-yr hold — it materially favors the
  longer-hold / deep-decarb path, so it must be explicit, not omitted.

### Measure-type treatment (universal: incremental cost over like-for-like)
Each measure carries Total cost, Like-for-like cost, Incremental cost (= Total − LfL). Only the
**incremental** hits capex/IRR.
- **Replacement-at-RUL** (ASHP heating/DHW, HP dryers, roof insulation, advanced glazing, LED):
  nonzero like-for-like → only the **premium** counts; **stage the install year to equipment RUL**.
- **Add-ons** (controls, RCx, elevator regen drives, EV chargers, weatherization, DWHR):
  like-for-like = 0 → full cost is incremental.
- **Electrification / fuel-switching** (ASHP heating & DHW): electricity reduction is **negative**
  (elec rises), gas reduction large positive; value the net at owner-share prices; carbon from gas.
- **Solar PV / EV charging** → a **Revenue** stream → Capitalized Ancillary Revenue (not "savings").
  **EV charging ALWAYS carries owner-side CapEx — never show $0 total capex.** Even under a
  third-party host agreement (Blink/ChargePoint fund + own the hardware), the owner pays
  **make-ready**: electrical service/panel upgrades, conduit, trenching, transformer, striping.
  Model that make-ready as the measure's capex (it's an add-on → largely incremental); the operator
  host agreement zeroes *hardware*, not make-ready. A $0-capex EV line is a red flag.
- **Subscription-model measures** (Parity RCx, monitoring-based commissioning): $0 owner CapEx but a
  recurring **subscription fee**. Do NOT show zero economic impact. Gross owner-share savings →
  Capitalized Utility Savings; the capitalized subscription fee → **Capitalized Subscription**
  (negative); any PJM/grid demand-response revenue → Capitalized Ancillary Revenue.
  **Judge a subscription on the ANNUAL NET, not the capitalized fee vs. savings-alone.** Capitalizing
  a *cancellable* subscription at the exit cap (fee ÷ cap) treats it as a perpetual liability and will
  routinely make the fee "exceed" the capitalized utility savings — an artifact, not a verdict. Show
  the annual net cashflow (gross owner savings + risk-adjusted DR − fee) and note the fee is
  cancellable. A subscription is justified by **DR monetization + $0 capex + savings persistence
  (continuous commissioning stops drift)**, NOT by first-order utility savings. When the subscription
  is net-marginal without DR, present a **one-time retro-commissioning alternative** (a capex project,
  no perpetual fee) alongside it so the reader sees the structuring choice.
- **Ancillary / demand-response revenue is SOFT — risk-adjust it; do not capitalize as a perpetuity.**
  PJM/grid DR and EV-charging revenue depend on enrollment, clearing prices, and utilization — not
  contractual perpetual NOI. Do NOT run `annual ÷ exit cap` on them the way you would utility savings.
  Take a haircut or PV over a defined/contract term, **break out the sources** (DR vs EV) in the
  report, and show a **sensitivity WITH and WITHOUT ancillary revenue** so the reader sees how much of
  net value hinges on it. A plan whose net value creation depends mostly on capitalized DR is fragile —
  say so.
- **Emissions measures under a binding BPS** → reduce the penalty → BPS Fine Avoidance stream → PV.

Every $ savings/revenue stream is taken at the **locked Gate-1 owner-share split** before
capitalizing — tenant-paid savings never enter the owner's waterfall.

### Plans (scenarios) + exit
Carry **Plan 1 / Plan 2** as **genuinely different STRATEGIC PATHS, not hold-period sensitivities.**
The same measure bundle shown at a 5-yr vs 10-yr hold is NOT two plans — it's one plan with two exit
assumptions (identical capex, carbon, and ancillary revenue = a tell you got this wrong). Two plans
must drive **materially different outcomes** and differ in the comparison table on **capex, GHGI
reduction %, incremental IRR, AND CRREM/stranding status**. The canonical fork for a decarb asset:
- **Plan 1 — Operational / Capital-Light:** controls/RCx (+DR), revenue add-ons (EV), elevator/lighting.
  Near-zero net capex, HIGH IRR, immediate GRESB — but modest carbon, so **CRREM stranding is deferred**
  (crosses later). Fits a shorter value-add hold.
- **Plan 2 — Deep Decarbonization / CRREM-Aligned:** Plan 1 PLUS committed electrification (DHW→HPWH,
  heating) timed to RUL/pulled forward. LARGE capex, LOWER near-term IRR, but MAJOR carbon cut,
  **CRREM-aligned / non-stranded**, stronger green-financing/ESG-buyer exit. Fits a longer core hold.
The hold period **maps to** the path; it is not itself the differentiator. Each plan gets its own
waterfall + cashflow + summary. Exit Cap and Exit Year from kickoff/Inputs; capitalization uses the
exit cap.

**Show BOTH paths on the emissions-trajectory chart.** Populate `targets.trajectory` points with
`planned_1` (Plan 1) and `planned_2` (Plan 2) — not a single `planned` — plus `bau` and the CRREM
pathway, and set `targets.plan1_label`/`plan2_label`. The contrast is the point: Plan 1 flattens
modestly and crosses (strands against) the CRREM curve; Plan 2 bends down and stays under it. The
template renders both curves automatically when planned_1/planned_2 are present.

### Render (mirror RSRA's process exactly)
Do NOT hand-draw the chart. The economics data object is passed to `fill_report` and the
`templates/decarb/layout.html` template's JS renders the waterfall as inline SVG (floating bars +
cumulative connectors, green adds / distinct capex decrement / anchor totals), plus the cashflow
table and plan comparison — the same fill_report + client-rendering path RSRA uses.

## 9. Utility uploads REPLACE, don't append — dedupe legacy rows

`add_building_utility_data` **appends**. Re-uploading a corrected/clean set on top of an existing
one leaves BOTH on the building — e.g. a legacy null-cost row AND the clean costed row for the
same fuel/period — which **double-counts energy and cost** and silently corrupts the baseline,
calibration, and all downstream economics. This blocked the Westminster Gate-2 economics
(most residential buildings carried duplicate utility data: legacy null-cost + clean-costed).

Rules:
- **Before uploading utility data to a building, clear/replace any existing utility data for that
  building** (delete the prior dataset, or upload a full clean replacement) — never append onto an
  unknown prior state. On a rebuild (recipe 1) new buildings start clean, but re-runs/resumes on
  existing buildings must dedupe first.
- **After upload, verify each building has exactly ONE utility dataset per fuel/period** — no
  null-cost + costed pairs, no overlapping periods. Reconcile the per-building totals back to the
  ESPM/utility source (recipe 6, zero variance); a doubled building is an immediate tell.
- Treat this as part of the P2 2B upload step and any P4 re-upload: replace-and-verify, not append.

## 10. Custom & generic measures — lifetime + effects schema (from create_custom_plan.py)

For `create_custom_plan` / `update_custom_plan_measures`:

- **Every custom measure REQUIRES a non-zero `lifetime`** (int, years). A missing/zero lifetime
  throws a `non-zero lifetime` error (hit on the generic smart-thermostat measure). Set the real
  measure life per measure — e.g. smart thermostat ≈10, LED ≈15, ASHP/HP-RTU ≈15–20, DHW HPWH ≈15,
  BTM solar ≈25, envelope (insulation/glazing) ≈25–30. Lifetime drives the engine's NPV/replacement.
- **Generic measures (`crm_id="generic"`)** must also carry effect specs (used for e.g. smart
  thermostats, RCx, or any measure without a native CRM):
  - `consumption_reduction_effects`: `[{endUse, fuel, percentReduction}]`
  - `load_reduction_effects`: `[{endUse, percentReduction}]`
  - `fuel_cost_reduction_effects`: `[{fuel, percentReduction, [absoluteReduction]}]`
  - `carbon_intensity_reduction_effects`: `[{fuel, percentReduction}]`
- **`endUse` and `fuel` are CASE-SENSITIVE lowercase_snake enum values — NOT free text.**
  `'heating'` / `'Heating'` are INVALID. Valid **EndUses**: `electricity`, `natural_gas`, `steam`,
  `outdoor_air_heating`, `skin_heating`, `outdoor_air_cooling`, `skin_cooling`, `refrigeration`,
  `domestic_hot_water`, `fans`, `pumps`, `lighting`, `plug_load`, `process`, `renewable`. Valid
  **fuel**: `electricity`, `natural_gas`, `steam`. For a heating-affecting measure use
  `outdoor_air_heating` / `skin_heating` (there is NO bare `heating`); cooling → `outdoor_air_cooling`
  / `skin_cooling`. `percentReduction` is a fraction (e.g. 0.00315 = 0.315%).
- Prefer a **native CRM id** (e.g. `lighting.led.led_lighting`, `heating-cooling.heatpump.rtu_ashp_electric_backup`)
  over generic whenever one exists — generic is the fallback that needs full effect specs + lifetime.
