# Training-data extraction — Cortland Rosslyn decarb (thread d1036a67)

**Asset:** Cortland Rosslyn (Phase 2 / EVO Apartments), 1771 N Pierce St, Arlington VA — 455-unit, 27-floor, LEED-Gold 2021 high-rise. Central **WSHP loop** (2× 130-ton AAON + Kelvion HX), individual electric air handlers per unit, 3× Lochinvar Crest gas condensing boilers (central DHW), 4-level/1,026-space garage. GRESB + compliance driver; "max decarb profitably"; no mandatory BPS in Arlington.

This thread is a strong corpus because the agent (a) caught four real Audette-model errors, (b) self-corrected on garage-code logic, but (c) needed user pushes ("only 2 measures?") and user-supplied domain facts (Parity, elevators = 100% landlord). Extraction is organized against the three training surfaces.

---

## 0. The meta-lesson (drives ~70% of everything below)

**Per-end-use landlord-capture attribution.** Audette applies ONE account-default landlord split (here 15%) to EVERY measure. But owner capture is a property of the *end-use's payer*, not the account:

| End-use | Who pays | Owner capture |
|---|---|---|
| Central gas boiler plant (heating + DHW) | Landlord | **100%** |
| Elevators, garage vent, corridors, amenities (spa/pool), common laundry | Landlord | **100%** |
| In-unit electric (HVAC air handlers, in-unit W/D, plug loads) | Tenant (sub-metered) | **~15%** |

Almost every finding in this thread is a single instance of this principle:
- Gas share 15% → **100%** (HIGH finding) — undervalued every gas measure.
- Elevator regen IRR **−6% → +11-12%** (common-area load) — flipped screened-out → recommended.
- Dryer ASHP swung 17yr → 2.5yr *if* laundry were common (it's in-unit → stayed screened out; resolved via apartments.com).
- DHW ASHP economics wrong until gas + 100% capture applied.

**This should be a first-class step and a verifier check, not an ad-hoc catch.**

---

## 1. WORKFLOW  → `skills/decarb-plan/SKILL.md`

1. **Build a per-end-use metering/capture map at Gate 1, before any screening.** A required table: every landlord-paid vs tenant-paid end-use → owner capture %. Never inherit Audette's account-default split into a measure's IRR without checking the end-use's actual payer. (This is the single highest-leverage workflow change.)
2. **Enumerate the full measure universe from a system-type candidate library, THEN screen down.** The agent presented 2 measures and the user pushed "*Only 2? Nothing else?*" — after which 4+ more surfaced (garage DCV, lighting controls, EV expansion, spa HPHX, RECs). Screening should start from a complete candidate list for the building's systems (WSHP loop, central gas DHW, enclosed garage, elevators, amenities, envelope, controls, on-site generation, procurement), not from whatever Audette's optimizer returned. Especially for GRESB deliverables.
3. **Proactively mine public listing/reference sources as primary evidence** — apartments.com, Zillow, cortland.com, PlugShare/Blink, Reddit, the architect's project page (Hickok Cole here). They resolved: in-unit vs common laundry, spa/hot-tub presence, existing EV chargers (28 L2, public-priced), heated-pool status, roof/amenity-deck geometry. Cite them.
4. **Expect Audette equipment-survey / building-attribute edits to trigger async remodels that exceed the call timeout.** Submit, then poll plan state; don't treat the timeout as failure (the survey "landed server-side despite the timeout"). Bake this into the workflow so it doesn't burn turns re-submitting.
5. **Disambiguate property-UID vs building-model-UID.** Session context carried the *property* UID (`ab7ee6c2…`); the *building-model* UID was different (`f0d2e282…`). Verify the building-model UID before edits — a stale UID cost several turns.
6. **When the user says "use Audette market research," pull it explicitly and cite it.** The agent fell back to an unlabeled 4.25% cap-rate proxy; the source should be a real retrieved figure, not a hedge.

---

## 2. BUILDING SCIENCE  → shared expertise bank (`verifier__retain_shared_expertise`) + retrofit reference library

Retain these as **generalizable, client-anonymous** expertise (system-type keyed):

- **WSHP-loop RCx / ongoing commissioning is the #1 near-term measure for recently-built (≤5 yr) mis-tuned WSHP towers** — ~1–2 yr payback; owner capture is 100% where the condenser loop is gas-heated. *(Already validated expertise — the agent recalled it. Reinforce.)*
- **Vendor: Parity** — subscription / $0-CapEx RCx + ongoing commissioning for WSHP high-rises; earns **PJM demand-response revenue** in PJM territory. Comp: **525 W 52nd St, NYC** (24-floor / 392-unit WSHP tower) — Year-1 actual **$67,702** savings vs $40k projected, 42 tCO₂, **$35k DR**, 10-month payback. *(NEW — user-supplied; retain as the named solution for this system type.)*
- **Gas-DHW → HPWH screens out as premature for mid-life condensing boilers** (2021 Lochinvar Crest, ~19 yr RUL): forced mid-life swap fails IRR though carbon is compelling (~290 tCO₂e/yr ≈ 14% of baseline). **Stage at EOL (~2040–2045); flag as a committed long-range GRESB action.** *(Already validated — reinforce.)*
- **Enclosed parking garages in 2018-IMC / 2021-code buildings, >10,000 cfm exhaust → VFD + CO-sensor DCV was code-required, so it almost certainly already exists.** The opportunity is **commissioning verification of setpoints/BAS integration (folds into RCx), NOT a capital install.** (Cortland's ~255,000 cfm design is 25× the threshold.) *(NEW — agent self-corrected here via code research; retain the rule so it's caught up front, not after proposing a capital measure.)*
- **LED + occupancy/daylight controls are near-certain in LEED-2021 buildings** (EAc credits): assume present, flag to verify; only small incremental if gaps exist. Don't model a full LED retrofit for such vintages.
- **Rooftop solar on amenity-deck high-rises usually screens out on area**: after the mechanical penthouse + amenity deck (pool/lounge/cabanas), net roof is often <300 m² → sub-50 kW → NPV-negative, compounded by low owner electric capture. Screen via Overture/architect roof geometry before modeling.
- **Elevator regen drives = 100% owner-capture common-area load**; clears a 10% hurdle at true capture (carbon impact is tiny but IRR is real).

---

## 3. VERIFIERS  → verifier checklist + auto-finding rules (`verifier__get_verification_checklist`, gate)

Add these checks; the first three would have auto-surfaced this thread's four HIGH issues without relying on the agent to notice:

1. **Landlord-capture-vs-end-use mismatch (HIGH).** Flag any measure whose `landlord_share` equals the account default while its end-use payer differs (central gas plant, elevators, garage, common amenities → should be ~100%). *(Caught here for gas 15%→100%; elevator was NOT auto-caught and only surfaced via the user.)*
2. **Equipment-type-vs-documented-system contradiction (HIGH).** Flag a measure whose equipment type contradicts the PCA/as-built system: an **RTU ASHP measure on a WSHP-loop building**; **DHW modeled electric when the PCA states gas boilers**. Cross-check the Audette equipment survey against the PCA before screening.
3. **Model-calibration gate.** Flag when the model's first-year energy is > ~10% off ESPM actuals; require ESPM upload + calibration before economics run. *(Here 35% over → corrected to within 4%.)*
4. **Measure-universe completeness.** Require the roster to be screened *from* the system-type candidate library; flag if fewer than N candidates were evaluated for a GRESB/portfolio deliverable. *(The "only 2 measures?" gap.)*
5. **Landlord-paid amenity/end-use coverage.** Confirm every landlord-paid load was assessed — spa/pool heating, common laundry, garage ventilation, corridor lighting, elevators — before the roster is called complete.

---

## Suggested encoding order (highest leverage first)
1. Workflow #1 + Verifier #1 (per-end-use capture map + mismatch finding) — fixes the dominant error class.
2. Verifier #2 + #3 (equipment-vs-doc, calibration gate) — the other three HIGH catches, automated.
3. Building-science retains (Parity + comp, garage-DCV-code rule, solar/LED/lighting presumptions).
4. Workflow #2 (measure-universe library) + Verifier #4/#5 (completeness/coverage).
