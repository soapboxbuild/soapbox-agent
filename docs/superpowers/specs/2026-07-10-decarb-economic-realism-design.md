# Decarb Economic-Realism Upgrade — Design

**Date:** 2026-07-10
**Status:** Approved design, pending implementation plan
**Origin:** Expert review of the 245 First (Clarion) decarb demo. The technical measure
list was largely right; the failures were **economic and physical realism** —
electrification CapEx was undersized (electrical service-capacity upgrades are the
budget-killer and no capacity data existed), a fuel-switch that *raised* OpEx wasn't
flagged, lab air-sealing savings assumed exterior infiltration that doesn't occur, and
no efficiency-upgrade alternative was shown next to the fuel-switch.

## Goal

Make the decarb pipeline economically and physically honest by default, at portfolio
screening scale, without a site visit per asset — and encode the expert judgment as
reusable, versioned guidance the agents inherit, not one-off tweaks.

Three interlocking components, **general-first** (rules that apply to most cold-climate
buildings) with **labs and logistics as archetype modules**. All work lives in
`soapbox-agent` as skills / reference docs / shared memory — **no platform-core code**.

Non-goals (YAGNI): a site-survey workflow; per-utility rate ingestion (utility cost
refinement is out of scope here — noted as a follow-up); changing Audette's optimizer.

## Shared data contract (the spine)

The cost capability emits a structured block per measure that the roster **and** the
verifier consume. This contract is the coupling point between all three components.

```
measure.cost = {
  capex: { low, base, high },          # construction cost range, USD
  opex_delta_yr,                       # annual OpEx change, USD; POSITIVE = OpEx rises
  electrical_capacity: {               # REQUIRED on any fuel-switch / electrification measure
    demand_increase_kw,                # modeled peak-kW increase from the Audette model
    service_capacity_known: boolean,   # did we have actual service/switchgear data?
    upgrade_cost: { low, high },       # low = assume headroom ($0); high = full new service
    flag: "VERIFIED" | "UNVERIFIED"
  },
  efficiency_alternative: {            # REQUIRED alongside any fuel-switch measure
    measure,                           # e.g. "high-efficiency condensing boiler"
    capex, opex_delta_yr
  }
}
```

Rules:
- `electrical_capacity` is **required** on fuel-switch/electrification measures; absent →
  a verifier BLOCK.
- When `service_capacity_known = false`, `flag = "UNVERIFIED"` and `upgrade_cost` MUST be a
  range (never collapsed to a point). Recommending such a measure as *firm* → verifier BLOCK.
- `efficiency_alternative` is **required** on any fuel-switch; absent → verifier WARN.

## Component A — Construction-costing skill (new)

**New skill `skills/construction-costing/`** (confirmed: dedicated skill, not folded into
`decarb-plan`). Replaces the hand-rolled per-measure costing.

- `SKILL.md` — method: take the building's Audette model + measure roster, produce the
  `measure.cost` block above for each measure. Deterministic, parametric, portfolio-scalable.
- `references/cost-bases.md` — per-measure construction cost bases as **$/unit keyed to
  archetype × climate × size** (versioned, editable). Seeded with reasonable defaults,
  explicitly flagged as **placeholder numbers for Christopher to tune** — the authoritative
  figures are domain expertise, not invented constants buried in code.
- **Electrical service-capacity sub-model** (the crux):
  - Input: modeled peak-kW demand increase for the electrified end-use (from Audette).
  - If actual service capacity is provided (switchgear photo / service size + metered peak
    kW headroom): compute a point upgrade cost, `flag = VERIFIED`.
  - If not (the portfolio-screening default): emit `upgrade_cost = { low: $0 (assume
    headroom), high: full-new-service cost }` parametrically ($/kW or $/A of service by
    region), `flag = UNVERIFIED`.
  - Never collapse the range to a false point estimate when unverified.
- **Efficiency-alternative pairing:** for every fuel-switch measure, also cost the
  standard high-efficiency non-switching option (e.g. condensing boiler vs ASHP), each with
  its own `capex` and `opex_delta_yr`, so the go/no-go decision is explicit.
- Consumed by the `decarb-plan` workflow during measure screening; output attaches to the
  roster and is read by `quality-review`.

## Component B — Building-science guidance (reference docs + shared memory)

**Cross-archetype rules** appended to `skills/decarb-plan/references/measure-universe.md`:
- Cold-climate electrification → electrical service capacity is a **first-class cost and
  feasibility gate**, not a contingency line. Require the `electrical_capacity` block.
- **Always pair** a fuel-switch with its efficiency-upgrade alternative.
- OpEx-viability caveat: in high-electricity-cost markets, electrification frequently raises
  OpEx; surface `opex_delta_yr` against the org's investment criterion.

**New `skills/decarb-plan/references/archetypes/lab.md`** (module):
- Lab exhaust makeup air is drawn from the **corridor/positive-pressure zones, not the
  exterior**; labs are negatively pressurized relative to the corridor, not the envelope.
  → Envelope air-sealing / infiltration measures are **excluded by default** for labs: the
  savings mechanism (exterior infiltration reduction) doesn't hold, so the measure is
  screened out unless **site observation** confirms exterior-adjacent leakage — and then the
  savings are bounded to that observed leakage path only. (The 245 First $200K/$50K measure
  is excluded under this rule.)
- Fume-hood VAV / occupancy setback; high ACH baseline.
- Lab electrification routinely blocked by electrical service-capacity upgrade cost.
- **Chiller-plant optimization > chiller VFDs** (VFDs were the prior-audit rec).
- Central exhaust heat recovery is often infeasible (loop geometry / run lengths);
  recommend only if observed on site.

**New `skills/decarb-plan/references/archetypes/logistics.md`** (seeded now — Kingsland /
60–70% of the Clarion portfolio):
- Large roof (rooftop solar, cool-roof), low process load, high-bay LED, minimal HVAC /
  large volume. Electrification calculus differs (smaller heating plant, different capacity
  story). Seeded so Kingsland is ready to run.

**Shared memory:** retain the durable, cross-engagement lessons into the hindsight
`soapbox` expertise bank so every portfolio's agents inherit them (write-policy: no
secrets/PII):
- The electrification → electrical-service-capacity cost failure mode (general).
- Lab pressurization / infiltration-savings rule.
- OpEx-viability: fuel-switch that raises OpEx must be flagged against the criterion.

## Component C — Verifier training (`quality-review`)

Add a **decarb / measure-recommendation gate section** to `skills/quality-review/SKILL.md`,
reading the `measure.cost` contract + archetype rules. **Tiered** (confirmed):

**BLOCK (must resolve before the plan proceeds):**
- A fuel-switch/electrification measure recommended with **no `electrical_capacity` basis**,
  or with `flag = UNVERIFIED` while presented as a firm recommendation (must surface the
  flag and the cost range instead).
- A measure whose savings assume a **physical mechanism the building's config doesn't
  support** — checked against archetype guidance. Specifically, a **lab envelope
  air-sealing / infiltration measure recommended without a site-observation basis** for
  exterior leakage (these are default-excluded per `lab.md`) → BLOCK.

**WARN (surfaced in the report, non-blocking — org-policy calls, not errors):**
- A recommended measure **raises OpEx** (`opex_delta_yr > 0`) versus a pay-for-itself
  criterion, without an exit-value/NOI justification.
- A fuel-switch recommended **without its `efficiency_alternative`** shown.
- **NPV/carbon weighting** not aligned to the org's stated criterion (e.g. defaulted 35/65
  carbon-weighted when the org's criterion is pay-for-itself → suggest reweighting).

## Interlocks

- **A → C:** costing emits `electrical_capacity`, `efficiency_alternative`, `opex_delta_yr`;
  the verifier gates on their presence and values.
- **B → A:** archetype docs supply the cost model's archetype parameters (lab ACH, logistics
  roof/plant profile) and the physical rules.
- **B → C:** archetype docs define the physical-realism rules the verifier checks (the
  lab-infiltration BLOCK).

## Testing / acceptance

- **Cost contract:** a fixture measure roster (one fuel-switch, one efficiency, one lab
  envelope) run through construction-costing yields a well-formed `measure.cost` block per
  measure; the fuel-switch carries `electrical_capacity` (UNVERIFIED range when no capacity
  data) and an `efficiency_alternative`.
- **Verifier gates:** table-driven — a roster that recommends electrification with no
  capacity basis → BLOCK; a lab-envelope measure claiming exterior-infiltration savings →
  BLOCK; an OpEx-raising electrification without NOI justification → WARN; a fuel-switch with
  no efficiency alternative → WARN. Each asserts the exact tier.
- **Guidance:** the 245 First lab-envelope measure, re-run against `lab.md`, is trimmed;
  a boiler-vs-ASHP screen surfaces both options with capex + opex_delta.
- Skill-lint passes (mirror existing `scripts/lint-skill-*` conventions).

## Rollout

- Ship the reference docs + verifier gates + costing skill together (they share the
  contract).
- Numbers in `cost-bases.md` and the $/kW service curves are seeded placeholders — Christopher
  tunes them; the structure and gates are the durable deliverable.
- Follow-ups (not in this spec): actual-utility-cost ingestion to refine `opex_delta_yr`;
  a switchgear-data intake to flip `electrical_capacity` to VERIFIED at scale.
