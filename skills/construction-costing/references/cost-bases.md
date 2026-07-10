# Construction Cost Bases

> PLACEHOLDER cost bases — seeded defaults for Christopher to tune; not authoritative.

Every `$` figure in this document is a **seeded placeholder**. The archetype × climate ×
size table below and the electrical service-capacity `$/kW` curve are starting points drawn
from generic industry ranges (RSMeans-style order-of-magnitude, ASHRAE/NREL retrofit cost
studies, and vendor rules of thumb), not a market-verified cost book for any specific region
or contractor pool. Treat every number as **to be confirmed** against real bids, local labor
rates, and utility tariffs before it is used for anything beyond screening-level ranking.
Do not present these figures to a client as authoritative pricing — they exist so the
`construction-costing` method has *a* number to run with while the real cost basis is built out.

Each row gives `capex` as `{low, base, high}` in USD, scaled per unit noted, and
`opex_delta_yr` (USD/yr, **positive = OpEx rises**, negative = OpEx falls) at a reference
building size. Scale both linearly by building GSF or unit count relative to the reference
size unless a measure-specific note says otherwise.

## Climate zone key

Climate buckets follow ASHRAE/IECC climate zones, collapsed to three bands for this seed
table: `cold` (zones 5–8, e.g. Northeast/Upper Midwest), `mixed` (zones 3–4, e.g. Mid-Atlantic/
Southeast interior), `hot` (zones 1–2, e.g. Gulf Coast/Southwest). `climate` is a required
lookup key alongside `archetype` and `size` for every row.

## Archetype key

`archetype` values used below: `multifamily`, `office`, `lab` (wet/dry lab or vivarium),
`mixed_use`. Building `size` bands: `small` (<50k GSF), `mid` (50k–250k GSF), `large`
(>250k GSF).

---

## 1. Envelope (air sealing, insulation, window/glazing upgrades)

| archetype | climate | size | capex low | capex base | capex high | opex_delta_yr | unit basis |
|---|---|---|---|---|---|---|---|
| multifamily | cold | mid | 350,000 | 550,000 | 850,000 | -22,000 | per 100k GSF |
| multifamily | mixed | mid | 220,000 | 380,000 | 600,000 | -14,000 | per 100k GSF |
| office | cold | mid | 400,000 | 620,000 | 950,000 | -26,000 | per 100k GSF |
| office | mixed | mid | 260,000 | 420,000 | 650,000 | -16,000 | per 100k GSF |
| lab | cold | mid | 500,000 | 780,000 | 1,150,000 | -30,000 | per 100k GSF; excluded by default absent site-observed leakage (see `archetypes/lab.md`) |
| mixed_use | hot | mid | 150,000 | 260,000 | 420,000 | -9,000 | per 100k GSF (glazing/shading dominant, insulation minor) |

**PLACEHOLDER note:** envelope $/GSF ratios are seeded from generic deep-retrofit studies;
confirm against local glazing/insulation vendor quotes before quoting to a client — tune per
region.

## 2. HVAC plant electrification (fuel-switch: boiler/furnace → ASHP or VRF)

| archetype | climate | size | capex low | capex base | capex high | opex_delta_yr | unit basis |
|---|---|---|---|---|---|---|---|
| multifamily | cold | mid | 1,400,000 | 2,100,000 | 3,200,000 | 48,000 | central ASHP plant, per 100k GSF |
| multifamily | mixed | mid | 1,000,000 | 1,550,000 | 2,300,000 | 30,000 | central ASHP plant, per 100k GSF |
| office | cold | mid | 1,600,000 | 2,400,000 | 3,600,000 | 55,000 | VRF/ASHP plant, per 100k GSF |
| lab | cold | large | 3,200,000 | 4,800,000 | 7,200,000 | 140,000 | heat-recovery chiller + ASHP hybrid plant, per 250k GSF; high ventilation load drives opex up |
| mixed_use | hot | mid | 700,000 | 1,050,000 | 1,600,000 | 12,000 | packaged heat-pump plant, per 100k GSF |

These are `measure_kind: fuel_switch`. Every row here **must** also emit an
`efficiency_alternative` (Section 4) and an electrical service-capacity assessment (Section 5)
per the SKILL method — this table alone is not a complete `measure.cost` object.

**PLACEHOLDER note:** plant electrification capex is the least mature line in this seed set —
these ranges are order-of-magnitude only; tune hard before use, especially the lab row (heat
recovery plant design varies enormously by process load).

## 3. High-efficiency boiler (non-switching efficiency upgrade)

| archetype | climate | size | capex low | capex base | capex high | opex_delta_yr | unit basis |
|---|---|---|---|---|---|---|---|
| multifamily | cold | mid | 380,000 | 520,000 | 720,000 | -14,000 | condensing boiler replacement, per 100k GSF |
| office | cold | mid | 420,000 | 600,000 | 850,000 | -18,000 | condensing boiler replacement, per 100k GSF |
| lab | cold | large | 900,000 | 1,300,000 | 1,900,000 | -35,000 | condensing boiler + economizer, per 250k GSF |

This is the default `efficiency_alternative` counterpart to Section 2's fuel-switch rows —
same archetype/climate/size lookup key.

## 4. Efficiency alternatives — LED, DCV, fume-hood VAV, chiller optimization

| measure | archetype | climate | size | capex low | capex base | capex high | opex_delta_yr | unit basis |
|---|---|---|---|---|---|---|---|---|
| LED upgrade | any | any | mid | 60,000 | 78,000 | 95,000 | -12,000 | per 100k GSF, full fixture replacement |
| Demand-controlled ventilation (DCV) | office/mixed_use | any | mid | 90,000 | 140,000 | 210,000 | -20,000 | per 100k GSF, CO2 sensors + BAS integration |
| Fume-hood VAV retrofit | lab | any | mid | 250,000 | 400,000 | 600,000 | -60,000 | per 100 hoods; opex swing dominated by lab exhaust fan energy |
| Chiller plant optimization (controls + VFD) | office/lab/mixed_use | any | mid | 120,000 | 190,000 | 280,000 | -18,000 | per 100k GSF or per plant, whichever is larger |

**PLACEHOLDER note:** the `any` climate placeholder rows are intentionally under-differentiated
by climate zone — tune with region-specific labor/equipment cost indices before use.

---

## 5. Electrical service-capacity cost basis

Fuel-switch measures increase electrical demand at the building or plant. This section is the
parametric basis the SKILL method uses to price that increase when the panel/service capacity
headroom is not independently confirmed.

### 5.1 Parametric $/kW curve by region

| region tier | $/kW of new/upgraded service | notes |
|---|---|---|
| low-cost (rural / low-density) | 900 | shorter utility queue, simpler transformer/panel upgrades |
| standard metro | 1,400 | typical urban infill utility interconnection + switchgear |
| high-cost metro (e.g. NYC, SF, Boston core) | 2,200 | utility interconnection queue premium, union labor, vault/switchgear congestion |

`$/kW` scales the **full new-service** cost estimate: `full_new_service_cost ≈ demand_increase_kw
× region_$/kW`. Where amperage is the known unit instead of kW, treat `$/A ≈ $/kW × (nameplate
voltage / 1000)` as an equivalent parametric proxy for a **service upgrade** sized by ampacity
rather than load.

**PLACEHOLDER note:** the three region tiers and their `$/kW` figures are seeded rules of thumb,
not utility-tariff-verified numbers — tune per utility territory (interconnection cost varies
enormously by utility) before using in a client-facing estimate.

### 5.2 Headroom-vs-new-service decision logic

For every fuel-switch measure, compute `demand_increase_kw` from the Audette model (delta
between new electrified end-use peak demand and existing electrical peak demand at that panel
or service entrance).

- If the actual electrical service capacity **is known** (from a site electrical survey, panel
  schedule, or utility interconnection study): compare `demand_increase_kw` against confirmed
  headroom. Emit a **point** `upgrade_cost` (a single confirmed number, not a range) and
  `flag: VERIFIED`.
- If the actual electrical service capacity **is not known**: emit a **range**, never a point
  estimate — `upgrade_cost.low = 0` (assume best case: existing service has enough headroom to
  absorb the load, no service upgrade needed) and `upgrade_cost.high` = the full new-service
  cost from the `$/kW` curve above (assume worst case: a full service upgrade is required).
  Set `flag: UNVERIFIED`. This range must never collapse to a point estimate while
  `service_capacity_known` is false — doing so would silently hide capacity risk from the
  measure screen.

This logic is implemented by the `construction-costing` SKILL method (Step 3) and enforced as
a contract rule in `scripts/validate-measure-cost.mjs`.
