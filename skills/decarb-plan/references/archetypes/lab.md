# Archetype: Laboratory buildings

Lab-specific overrides to the measure universe. Labs are high-ACH, exhaust-dominated, and
have distinct pressurization physics that change which measures are real.

## Pressurization & envelope air-sealing — EXCLUDED BY DEFAULT
Labs are **negatively pressurized relative to the corridor**, not the exterior. Fume-hood
and general exhaust **makeup air is drawn from the corridor / positive-pressure office
zones**, not through the building envelope. Therefore envelope air-sealing / air-barrier
measures do **not** yield the infiltration savings a normal building would — the leakage
path they target isn't the dominant makeup-air path.

- **Rule:** envelope air-sealing / infiltration measures are **excluded by default** for
  labs. Admit one only when **site observation** confirms a real exterior-adjacent leakage
  path (e.g. failed perimeter glazing on exposed lab areas), and then **bound the savings to
  that observed path only** — never to whole-lab air changes.
- The 245 First lab-envelope sealant ($200K capex / ~$50K/yr claimed) is excluded under
  this rule.

## Ventilation
- **Fume-hood VAV / occupancy setback** and sash-management are usually the largest lab
  energy levers — evaluate before envelope.
- High baseline ACH; reheat energy is large. DCV where lab-safety allows.

## Central plant
- **Chiller-plant optimization > chiller VFDs.** Prefer plant-level optimization
  (staging, condenser-water/loop-temp reset, RCx) over the prior-audit VFD-only measure.
- **Central exhaust heat recovery** is often infeasible in labs (supply/exhaust loop
  geometry, run lengths, contamination). Recommend **only if observed** to be feasible on
  site; do not propose it speculatively.

## Electrification
- Lab electrification routinely fails on **electrical service capacity** upgrade cost (high
  process + exhaust loads → large service). The `electrical_capacity` gate from the
  cross-archetype rules applies with force here.
