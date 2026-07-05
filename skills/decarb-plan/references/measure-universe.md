# Measure universe — candidate library for completeness screening (P3 step 1a)

Purpose: `retrofit__propose_candidates` + Audette's optimizer return a *starting* set, not the whole
opportunity space. Before screening down to a roster, walk this library for the building's actual
systems and confirm every applicable category was **evaluated / screened-out-with-reason /
not-applicable** — don't let the roster be thin just because the optimizer returned few. Especially
for GRESB / portfolio deliverables.

This is a *checklist to think against*, not a mandate to include everything. Screen each by owner
economics (per-end-use capture — see the 2C capture map), carbon, feasibility, and RUL timing.

## Categories (walk all that apply)

1. **Envelope** — roof/wall insulation (incremental over a re-roof at RUL), window/glazing upgrades,
   air-sealing, cool-roof. Usually EOL-timed; incremental cost only.
2. **HVAC plant** — heating/cooling plant electrification (ASHP/WSHP), high-efficiency replacement at
   RUL, heat-recovery/economizers. For a **central WSHP loop**: loop-temperature reset, heat-recovery
   chiller, condenser-water optimization.
3. **HVAC distribution & ventilation** — VAV/DCV, ERV/HRV, MAU scheduling, **parking-garage CO-sensor
   DCV** (⚠ in 2018-IMC / 2021-code buildings >10,000 cfm this was code-required → almost certainly
   already installed; the opportunity is commissioning verification, not a capital install).
4. **Controls & retro-commissioning (RCx)** — BAS tune-up, setpoint/schedule optimization, ongoing
   (monitoring-based) commissioning. For recently-built mis-tuned **WSHP towers this is typically the
   #1 near-term measure** (~1–2 yr payback); vendor **Parity** (subscription, $0 CapEx, PJM
   demand-response revenue in PJM territory). Garage DCV verification folds in here.
5. **DHW** — gas→HPWH (⚠ screens out as premature for mid-life condensing boilers; **stage at EOL**),
   recirculation-pump scheduling, drain-water heat recovery, low-flow fixtures.
6. **Lighting** — LED retrofit (⚠ presume already 100% in LEED-2021 vintages; flag to verify, don't
   model a full retrofit) + **lighting controls** (occupancy/daylight; also often already present for
   LEED EAc — verify).
7. **Plug / appliance** — ENERGY STAR appliances, in-unit vs common-laundry ASHP dryers (capture flips
   on who's metered — check the 2C map), elevator regen drives (**100% common-area capture** — clears
   hurdle at true capture even though carbon is small).
8. **Common-area / amenity loads** (all 100% owner if landlord-paid) — spa/pool heating (electric
   resistance → HPHX swap), pool covers, common-area HVAC, corridor lighting, garage ventilation.
   Verify each amenity's presence and heat source via PCA + listing sites (apartments.com/Zillow).
9. **On-site generation & storage** — rooftop/carport solar (⚠ on amenity-deck high-rises net roof
   after mechanical penthouse + amenity deck is often <300 m² → sub-50 kW → NPV-negative at low owner
   electric capture; screen via roof geometry first), battery storage, solar-thermal.
10. **EV charging** — expansion of L2, DCFC, managed charging. Often a **NOI/revenue** story (host
    agreements at $0 owner CapEx via Blink/ChargePoint) and a GRESB credit, not just carbon.
11. **Procurement / market** — green tariffs, RECs, PPAs (⚠ confirm scope with the client — RECs are
    frequently *out of scope* for a physical decarb study; the Cortland Rosslyn client removed them).
    GRESB-specific: ESPM data-coverage refresh, green-lease data-sharing clauses (no CapEx).

## Screening reminders
- Each measure's savings basis = its **end-use's** owner capture (2C capture map), never the
  building's blended in-unit split.
- Modeled savings are provisional until measured (baseline-discipline playbook).
- Sequence by decarb logic + RUL (staging playbook), not independent IRR.
- Record each category's disposition so the roster is demonstrably screened from a complete set.
