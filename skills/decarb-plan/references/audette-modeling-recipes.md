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

#### `submit_equipment_survey` payload — AUTHORITATIVE schema (from Audette source, verified 2026-07-04)

The tool takes `{ building_model_uid, equipment_survey }`. The `equipment_survey` object's JSON
schema is free-form (`additionalProperties: true`) — it does NOT validate keys — but the backend
`EquipmentSurveyDTO.from_dict` inferrer **requires all 10 equipment groups to be present** and
bracket-accesses specific sub-keys. A missing group or required sub-key throws
`EquipmentSurveyInfererError` / `KeyError: '<key>'` (this is what repeatedly failed when the agent
guessed keys like `domestic_hot_water`). Rules:

- **All 10 groups are REQUIRED even when the equipment doesn't exist** — include the group with just
  its `_exists: false`: `air_handling_equipment`, `central_plant_cooler`, `central_plant_heater`,
  `central_plant_heat_pump`, `domestic_hot_water_heater`, `terminal_cooler`, `terminal_heater`,
  `rooftop_unit`, `heat_pump`, `other_equipment`. (`generic_hvac_equipment` list + `equipment_survey_uid`
  are optional.)
- **Every group needs its `<group>_exists` boolean.** Type/units fields are optional (default null).
- **`domestic_hot_water_heater` additionally REQUIRES** `domestic_hot_water_heater_central_distribution`
  (bool) and `domestic_hot_water_heater_average_installation_year` (key must be present; value may be null).
- **Enum values are the lowercase_snake_case member name.** Valid values:
  - `central_plant_heater_type`: `condensing_gas_boiler` | `electric_furnace` | `electric_resistance_boiler` | `gas_boiler` | `gas_furnace` | `high_efficiency_gas_furnace` | **`hydronic_furnace`**
  - `air_handling_equipment_type`: `make_up_air_unit` | `packaged_air_handling_unit` | `split_air_handling_unit` | `suite_air_exchangers` | `suite_energy_recovery_ventilator` | **`exhaust_only_air_handling_unit`**
  - `air_handling_equipment_heating_type`: `electric_resistance` | `gas` | `hydronic`; `_cooling_type`: `direct_expansion` | `hydronic`
  - `terminal_cooler_units`: `cooling_ptac` | **`split_air_conditioner`** | `window_air_conditioner`
  - `terminal_heater_units`: `condensing_gas_unit_heater` | `electric_baseboard` | `electric_resistance_ptac` | `electric_unit_heater` | `gas_ptac` | `gas_unit_heater`
  - `domestic_hot_water_heater_type`: `electric_heater` | **`gas_heater`** | `indirect_heater`
  - `central_plant_*_terminal_units`: `baseboards` | `constant_volume_boxes` | `fan_coil_units` | `variable_air_volume_boxes`
  - `central_plant_cooler_type`: `air_cooled_chiller` | `water_cooled_chiller`; `central_plant_heat_pump_type`: `air_source_heat_pump` | `ground_source_heat_pump`
  - `rooftop_unit_heating_type`: `electric_resistance` | `gas`; `rooftop_unit_cooling_type`: `direct_expansion`
  - `clothes_dryers_type`: `electric` | `gas`; `heat_pump_type`: `water_loop_heat_pump` | `split_air_source_heat_pump`
- **Sizes/years left blank must be `null`, NOT `0`** — a `0` size triggers a divide-by-zero in the inferrer.
- `other_equipment` REQUIRES: `clothes_dryers_exists`, `clothes_washers_exists`, `elevators_exists`,
  `escalator_exists`, `rooftop_photovoltaics_exists` (all booleans).

**Exact A4 / Type-A hydronic-furnace payload** (copy this shape for every residential building; adjust
sizes/years per building):

```json
{
  "air_handling_equipment": { "air_handling_equipment_exists": true, "air_handling_equipment_type": "exhaust_only_air_handling_unit", "air_handling_equipment_heating_type": null, "air_handling_equipment_cooling_type": null, "air_handling_equipment_supply_air_rate": null, "air_handling_equipment_average_installation_year": null },
  "central_plant_heater": { "central_plant_heater_exists": true, "central_plant_heater_type": "hydronic_furnace", "central_plant_heater_terminal_units": null, "central_plant_heater_average_installation_year": null },
  "central_plant_cooler": { "central_plant_cooler_exists": false },
  "central_plant_heat_pump": { "central_plant_heat_pump_exists": false },
  "domestic_hot_water_heater": { "domestic_hot_water_heater_exists": true, "domestic_hot_water_heater_central_distribution": false, "domestic_hot_water_heater_type": "gas_heater", "domestic_hot_water_heater_size": null, "domestic_hot_water_heater_average_installation_year": null },
  "terminal_cooler": { "terminal_cooler_exists": true, "terminal_cooler_units": "split_air_conditioner" },
  "terminal_heater": { "terminal_heater_exists": false },
  "rooftop_unit": { "rooftop_unit_exists": false },
  "heat_pump": { "heat_pump_exists": false },
  "other_equipment": { "clothes_dryers_exists": true, "clothes_dryers_type": "electric", "clothes_washers_exists": true, "elevators_exists": false, "escalator_exists": false, "rooftop_photovoltaics_exists": false }
}
```

### 5b. True in-unit combi with fan-coil distribution (no forced-air furnace)

ONLY when the in-unit gas water heater serves both DHW and space heat via **fan coils / hydronic
terminals** (not a ducted furnace) and there is no literal match, model as
`central_plant_heater = gas_boiler + fan_coil_units`. This is a proxy for fuel/distribution
fidelity, not a physical description. Document it explicitly in `state` so it isn't read as a data
error. Do not apply this to hydronic furnaces — use 5a.

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
