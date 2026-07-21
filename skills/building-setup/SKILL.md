---
name: building-setup
description: >
  Reusable workflow for creating the Audette building(s) for an asset — single or
  multi-building — with evidence-gathered profile enrichment and verified account/property
  linkage. Triggers on: "create a building", "set up the building", "onboard this building
  in Audette", "create Audette building", "multi-building site".
version: 0.1.0
---

# Building Setup

You are creating the Audette building(s) for one asset. This workflow gathers evidence,
detects footprints, creates the building(s) in Audette, and verifies + persists the
account/property linkage so future threads bind correctly. It ends when the asset is linked
to correctly-created Audette building(s) backed by an enriched, cited building profile.

Out of scope (separate skills/steps): energy-data compilation, full report generation.

## Method

### Step 1 — Resolve account context

Call `switch_customer_account` to the portfolio's Audette account before touching anything
else. If the asset already has an `audette_property_id`, verify it resolves on that account —
do not trust a stored UID blindly. If it doesn't resolve (wrong account, stale link), surface
the mismatch to the user and treat the linkage as unverified rather than proceeding as if it
were good.

### Step 2 — Evidence gathering

Pointer: see `references/evidence-gathering.md` for the full recipes.

Consolidate ONE cited building profile from three sources, in authority order:
**documents > listings/records > general web**:
1. **Documents** (highest authority) — `search_documents` + reading the asset's files.
2. **Lease listings** (lease specs, tenancy, and lease structure) — brave-search on CRE
   listing sites.
3. **General web** — brave-search broadly (assessor records, owner sites, permits, news).

Every field in the profile carries **provenance** (source + **retrieval date**). Conflicts
between sources are **surfaced, not silently overwritten** — conflicts are reported to the
user rather than silently resolved by picking a winner yourself. Gaps stay unknown; **never
invent** a value that isn't backed by a document, listing, record, or Audette.

### Step 3 — Footprint detection

Always detect footprints before creating anything in Audette:
1. `list_buildings` — check for existing footprints first.
2. Else `overture__nearby_buildings(lat, lon, radius_m=120)` — pull candidate footprints from
   Overture.
3. `save_building` per footprint returned, marking the largest footprint `is_primary`.
4. If Overture returns nothing, fall back to a single point-footprint for the asset's address.

### Step 4 — Create Audette building(s)

- **Single footprint** → one building, named after the asset.
- **Multiple footprints** → one building per footprint, named `"<asset> — Bldg N"`, passing
  height/floors/class from the saved footprint plus the Step-2 profile specs wherever Audette
  accepts them.

### Step 4b — Equipment survey

Populate each building's equipment via `submit_equipment_survey({ building_model_uid, equipment_survey })`,
extracting from the PCA / Energy Audit / survey docs (Step-2 evidence); unknown stays `null`, never
invented. The payload validates nothing client-side but the backend inferrer **throws on any missing
key**, so it must be complete.

⚠️ **NEVER trust an existing survey's units.** First call `get_equipment_survey`. If one already
exists, do NOT report it as "already correctly sized" and move on — **audit every `*_size` against the
units rule below**, because prior runs stored wrong units. Tell-tale prior-run errors: a
`domestic_hot_water_heater_size` that equals the tank volume in liters/gallons (e.g. `169` for 40–50 gal
tanks); a `terminal_heater_size`/`_cooler_size` far below the load implied by the equipment (e.g. `268`
when 254 units × 36 MBH ÷ 12 ≈ 762 tons, or `199` when the DX load is 565 tons — those are kW-scaled, not
tons). When a stored value fails the units check, **re-derive in tons and OVERWRITE via
`submit_equipment_survey`** (it replaces the survey); do not accept it. A complete-looking survey in the
wrong units is worse than none — it silently drives the whole energy model.

Follow the AUTHORITATIVE schema in
`skills/decarb-plan/references/audette-modeling-recipes.md` (**recipe 5** — the single source of
truth for this payload; this section restates its units rule so no cross-skill read is required).
Non-negotiables:
- **All 10 groups present**, each with its `<group>_exists` boolean even when absent (`_exists: false`):
  `air_handling_equipment`, `central_plant_cooler`, `central_plant_heater`, `central_plant_heat_pump`,
  `domestic_hot_water_heater`, `terminal_cooler`, `terminal_heater`, `rooftop_unit`, `heat_pump`,
  `other_equipment`. `other_equipment` needs `clothes_dryers_exists`, `clothes_washers_exists`,
  `elevators_exists`, `escalator_exists`, `rooftop_photovoltaics_exists`. `domestic_hot_water_heater`
  also needs `_central_distribution` + `_type` + `_size` + `_average_installation_year`.
- **Capacity UNITS — the #1 survey error. There are exactly TWO units and NOTHING else:**
  - `air_handling_equipment` + `rooftop_unit` → **AIRFLOW in CFM** via `*_supply_air_rate` (no tons
    field exists for them; never convert an RTU to tons).
  - **EVERY OTHER `*_size` = refrigeration TONS** (1 ton = 12,000 Btu/h). This includes
    `central_plant_heater_size`, `central_plant_cooler_size`, `central_plant_heat_pump_size`,
    `heat_pump_size`, `terminal_cooler_size`, `terminal_heater_size`, `terminal_heater_cooler_size`,
    **and `domestic_hot_water_heater_size`**. The inferrer's coverage math is entirely in tons and does
    ZERO unit conversion at submit — whatever number you send is read as tons.
  - **Convert BEFORE submitting** (identical to recipe 5): MBH ÷ 12 = tons; kBtu/h ÷ 12 = tons;
    kW ÷ 3.517 = tons; a gas heater/boiler rated in **input BTU/hr** → apply efficiency, then ÷ 12,000.
  - **DHW is the trap — READ THIS.** `domestic_hot_water_heater_size` is **tons of thermal capacity,
    NOT tank volume.** NEVER submit gallons, liters, or tank size in it (a "50-gal" water heater is
    NOT `50`, and NOT `189`). Use the heater's rated input BTU/hr ÷ 12,000. If the input rating isn't
    in the docs, submit `null` and let the model infer DHW size from floor area — that is correct and
    preferred over guessing from volume.
  - **NEVER** put kW, MBH, kBtu, CFM, gallons, or liters in any `*_size` field; **NEVER** put tons in
    a `*_supply_air_rate` (CFM) field. `rooftop_photovoltaics_size` is the lone exception = system kW.
- **Blank size/year = `null`, never `0`** (0 → divide-by-zero in the inferrer).
- **Enum values are lowercase_snake** (e.g. `central_plant_heater_type`: `gas_boiler` |
  `condensing_gas_boiler` | `electric_resistance_boiler` | …; `domestic_hot_water_heater_type`:
  `gas_heater` | `electric_heater` | `indirect_heater`) — full enum lists in the recipe.
Present the intended survey to the user for confirmation before submitting (they may correct sizing/units).

### Step 5 — Verify + persist linkage

Confirm each created building UID resolves on the account, then **auto-link** the asset by writing
the **PROPERTY UID** back to `audette_property_id` via `update_asset_fields` (this now persists —
`audette_property_id` is an allowed field — so no manual linking step is needed):
- Write the Audette **property_uid** that groups the building(s) — the one returned/used by
  `create_property_for_building` / `assign_property_to_building`, NOT a `building_model_uid`.
  This holds for **single and multi-building alike** — even one building belongs to a property.
- ⚠️ **Never write a building UID into `audette_property_id`.** A property is not a building;
  downstream tools that treat `audette_property_id` as a property (get_property, list its
  buildings) will 404 if it's a building UID. Record the individual building_model_uids in
  `metadata.audette_building_uids` for the roster instead.

This closes the mid-session/stale-link failure mode so the next thread binds correctly at
session-create — and the asset is linked automatically at the end of setup.

## Guardrails

- **No fabrication** — every profile attribute comes from a document, listing, record, or
  Audette; unknown stays unknown and is flagged, never invented.
- **Provenance on every field** — source + retrieval date, always.
- **Conflicts surfaced, not overwritten** — reconciliation reports disagreements for the user
  to adjudicate.
- **Footprints before creation** — never create a building in Audette without completing
  Step 3 first.
- **Linkage integrity** — never trust a stored `audette_property_id` that doesn't resolve on
  the current account.

## Degraded modes

- **Audette connector expired/degraded** — stop at Step 1 and tell the user to reconnect;
  never create buildings against a dead or unverified account.
- **Overture returns nothing** — use the single point-footprint fallback (Step 3).
- **No documents and no web coverage** — proceed with whatever resolves, flag the profile as
  thin; do not invent specs to fill it out.
- **Linkage write errors** — `update_asset_fields` DOES persist `audette_property_id` (it is an
  allowed top-level field), so **auto-link by default** (Step 5). Only if the write returns an
  actual error: retry once, then report the property UID for manual linking and flag the failure.
  Do not skip auto-linking pre-emptively — the "can't persist" limitation no longer applies.
