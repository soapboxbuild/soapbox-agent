# Decarb Plan demo fixtures — "4th & Madison"

Pseudonymous demo fixture set for the Decarb Plan workflow (Task 2.3). Ready to hydrate a fresh
demo workspace (`projects/<asset-key>/decarb-plan.json` = `decarb_plan_state.json`) at
`phase: "done"` so the render gate / resume flow can be demoed end-to-end without running a live
engagement.

## Files

| File | Purpose |
|---|---|
| `building_setup.json` | Asset identity + Audette equipment-survey payload (existing/pre-retrofit conditions). All 10 equipment groups present; `central_plant_heater_type: "hydronic_furnace"` used natively per `audette-modeling-recipes.md` §5a. |
| `baseline.json` | Calibrated P1 energy baseline (kWh + kWh/m², tCO2e, peer benchmark from BPD). |
| `measures.json` | The ideated P3 measure set — envelope, chiller efficiency, central-plant heat-pump electrification, DHW HPWH, lighting/RCx controls, rooftop solar (VNM). Phased roadmap tied to natural equipment-replacement triggers. |
| `economics.json` | Value-creation waterfall + 10-year annual cashflow + IRR, gross vs. landlord-share capture, solar VNM 0.80. Includes `headline_pct` / `measure_reconciled_pct` (both 21.1%, reconciled). |
| `costing_cache.json` | Costing-MCP-style CapEx results per measure (invented unit costs, not redistributed RSMeans data). |
| `citations.json` | Provenance for every baseline/measure/target claim (`{claim, source, provenance, url}`). |
| `decarb_plan_state.json` | **The state ledger** — conforms to `../state-schema.json`, assembled from all files above, `phase: "done"`. This is the file to stage into Files/the project record to hydrate the demo workspace. |

## Pseudonym mapping (private — do not publish alongside a real client asset)

| Fixture value | Real-world reference (from `~/inbox/4th and Madison.zip`, read-only) |
|---|---|
| Owner "JP Metro Asset Management" | Fictional — invented for this demo. The real ownership entity name visible in the reference zip's fuel invoice filenames is NOT used, quoted, or referenced anywhere in these fixtures. |
| Asset name "4th & Madison" | Kept — generic street-name label, judged acceptable per task brief (does not itself identify a real building without the owner/portfolio context). |
| Archetype: Office, 1 building, ~83,000 m² GFA, built 2003 | Derived from the reference ESPM-style export (Office, 1 building, 82,738.9 m² GFA, built 2002) — GFA/year lightly perturbed, all other figures independently derived/invented, not copied. |
| Baseline electricity ~9.3 GWh/yr | Loosely modeled on the reference export's ~30,700–31,000 GJ/yr weather-normalized electricity (≈8.5–8.6 GWh/yr) — increased and rounded for the demo narrative (to create a peer-benchmark gap worth retrofitting), not a reproduction of the real figure. |
| Regulatory driver "Metro City BPS" | Entirely fictional ordinance (city name, cap, fine rate, compliance year all invented) — modeled on the *structure* of real large-building carbon-performance standards, not any specific real jurisdiction's filing. |
| Equipment (hydronic furnace, water-cooled chiller, central gas DHW) | Archetype-plausible for a 2003-era office central plant; not transcribed from the reference zip's actual equipment schedules (those were not extracted — only the small ESPM-style metrics export was opened for reference, per the read-only reference-file constraint). |
| Stakeholder / contact names | Entirely fictional placeholders (`demo-contact@example.com`). No real names, emails, or firms from the reference zip appear anywhere in these fixtures. |

Only one small file was extracted from the 936MB reference zip for context: the ESPM-style
"Audette Data Request" metrics export (property type, GFA, year built, monthly electricity —
no tenant, contact, or financial detail). It was read in a scratch directory outside this repo
and not copied into any fixture verbatim; all fixture numbers are independently derived/rounded/
invented from it. No other file in the zip (invoices, condition reports, capital plans, electrical
studies, floor plans) was opened.

## Numbers/standards followed

- Energy reported in **kWh + kWh/m² only** (no GJ/therms/kBtu/sqft) throughout.
- **≤2 significant figures** on displayed baseline/target figures (full precision retained in
  underlying derivation for the reconciliation check).
- Peer benchmark sourced from the **Building Performance Database (BPD)**, filtered by property
  type + comparable climate zone/size class — never a national median.
- **IRR** = incremental cost + landlord-share utility savings + BPS fine avoidance (PV) +
  conditional exit value (capitalized at the 6.0% exit cap), per
  `audette-modeling-recipes.md` §8's waterfall/cashflow convention.
- **Solar VNM capture = 0.80** to landlord (`capture_map.rooftop_solar.owner_capture_pct: 80`);
  all other measures at 100% owner capture (central-plant / common-area systems are landlord-paid
  regardless of lease structure, per the capture_map convention in `state-schema.json`).
- **Headline reconciliation**: `economics.json.headline_pct` (21.1%, full-implementation baseline-
  vs-target emissions reduction) equals `measure_reconciled_pct` (21.1%, bottom-up sum of the 6
  measures' per-measure emissions deltas) — verified by the check script below.

## Honest economics note

The full 3-phase plan's `net_value_creation_usd` is **negative** (−$5.70M) and `irr_incremental_pct`
is **negative** (−9.6%). This is intentional and realistic, not a fixture bug: a genuine deep central-
plant electrification retrofit (Phase 3, the largest capex line at $4.7M incremental) is frequently
NOI-capitalization-negative on pure opex savings — gas $ saved is largely offset by electricity $
added at the modeled heat-pump COP and blended utility rates. The plan is economically justified by
**BPS fine-avoidance risk** (still $693k PV even after the plan closes most of the gap) and asset
repositioning ahead of the 2032 compliance deadline, not by direct IRR. Phase 1 alone (envelope +
DHW HPWH + lighting/controls, $3.65M incremental) has materially better standalone economics and is
called out as independently executable in `measures.json.roadmap_phases`.

## Verification run (2026-07-11)

```
$ node -e "JSON.parse(require('fs').readFileSync('skills/decarb-plan/demo/decarb_plan_state.json')); console.log('STATE_JSON_PARSES')"
STATE_JSON_PARSES

$ node -e "const e=require('./skills/decarb-plan/demo/economics.json'); if(Math.abs(e.headline_pct-e.measure_reconciled_pct)>0.5) throw 'MISMATCH'; console.log('RECONCILED')"
RECONCILED
```

Required top-level `state-schema.json` fields present in `decarb_plan_state.json`: `phase` (✓,
`"done"`), `asset` (✓, `id`+`name`+`portfolio_id`). Optional-but-populated: `kickoff`, `documents`,
`baseline`, `capture_map`, `conflicts`, `targets`, `measures`, `audette`, `citations`, `report`,
`helper`. Plus two additive extensions: `economics`, `costing` (root schema does not restrict
additional properties).
