# Decarb Economic-Realism Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the decarb pipeline economically and physically honest by default — a new construction-costing skill that treats electrical service-capacity as a first-class, honest cost driver; archetype building-science guidance (general + lab + logistics); and tiered verifier gates that catch the misses from the 245 First review.

**Architecture:** All deliverables are skills / reference docs / JSON contract / shared memory in `soapbox-agent` — no platform-core code. A shared `measure.cost` JSON contract is the spine: the construction-costing skill emits it, and the verifier gates on it. Guidance lives in versioned reference docs (deterministic) plus the shared hindsight memory bank (accreting). Built general-first with labs and logistics as archetype modules.

**Tech Stack:** Markdown skills (SKILL.md + `references/`), JSON Schema validated with `ajv` (the repo's only devDep), bespoke `node scripts/*.mjs` lint/validation scripts (mirroring `scripts/lint-skill-esg-profile.mjs`), hindsight MCP for shared memory.

## Global Constraints

- No platform-core / server code. Everything is a skill, reference doc, JSON contract, lint script, or memory write in `soapbox-agent`.
- Cost **numbers** in `cost-bases.md` and the $/kW service curve are **seeded placeholders flagged for Christopher to tune** — never presented as authoritative. Engineering **rules** are durable.
- `electrical_capacity` block is REQUIRED on any fuel-switch/electrification measure. When `service_capacity_known = false`, `flag = "UNVERIFIED"` and `upgrade_cost` MUST be a range (never a point).
- `efficiency_alternative` is REQUIRED on any fuel-switch measure.
- Lab envelope air-sealing / infiltration measures are **excluded by default** — admitted only with a site-observation basis for exterior leakage.
- Verifier tiers: **BLOCK** on missing-capacity-basis and physically-unsupported savings; **WARN** on OpEx-up, missing efficiency-alternative, and weighting mismatch.
- "Tests" are `node` lint/validate scripts run from repo root (`node scripts/<name>.mjs`); each prints `... OK` and exits non-zero on failure. Follow the existing lint-skill pattern.

---

### Task 1: Shared `measure.cost` contract (schema + fixture + validator)

Locks the spine first so Tasks 2 and 6 build against a fixed contract.

**Files:**
- Create: `skills/construction-costing/schema/measure-cost.schema.json`
- Create: `skills/construction-costing/example-data.json`
- Create: `scripts/validate-measure-cost.mjs`

**Interfaces:**
- Produces: the `measure.cost` object shape consumed by construction-costing (Task 2) and quality-review (Task 6): `capex{low,base,high}`, `opex_delta_yr`, optional `electrical_capacity{demand_increase_kw,service_capacity_known,upgrade_cost{low,high},flag}`, optional `efficiency_alternative{measure,capex,opex_delta_yr}`.

- [ ] **Step 1: Write the schema (this is the failing target — validator + fixture reference it)**

`skills/construction-costing/schema/measure-cost.schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "measure-cost.schema.json",
  "type": "object",
  "required": ["measure_id", "cost"],
  "properties": {
    "measure_id": { "type": "string" },
    "measure_kind": { "type": "string", "enum": ["fuel_switch", "efficiency", "envelope", "controls", "other"] },
    "cost": {
      "type": "object",
      "required": ["capex", "opex_delta_yr"],
      "additionalProperties": false,
      "properties": {
        "capex": {
          "type": "object",
          "required": ["low", "base", "high"],
          "additionalProperties": false,
          "properties": {
            "low": { "type": "number" },
            "base": { "type": "number" },
            "high": { "type": "number" }
          }
        },
        "opex_delta_yr": { "type": "number", "description": "Annual OpEx change USD; POSITIVE = OpEx rises" },
        "electrical_capacity": {
          "type": "object",
          "required": ["demand_increase_kw", "service_capacity_known", "upgrade_cost", "flag"],
          "additionalProperties": false,
          "properties": {
            "demand_increase_kw": { "type": "number" },
            "service_capacity_known": { "type": "boolean" },
            "upgrade_cost": {
              "type": "object",
              "required": ["low", "high"],
              "additionalProperties": false,
              "properties": { "low": { "type": "number" }, "high": { "type": "number" } }
            },
            "flag": { "type": "string", "enum": ["VERIFIED", "UNVERIFIED"] }
          }
        },
        "efficiency_alternative": {
          "type": "object",
          "required": ["measure", "capex", "opex_delta_yr"],
          "additionalProperties": false,
          "properties": {
            "measure": { "type": "string" },
            "capex": { "type": "number" },
            "opex_delta_yr": { "type": "number" }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write the fixture** — `skills/construction-costing/example-data.json` (a roster exercising every rule: a fuel-switch with UNVERIFIED capacity + efficiency alternative; a plain efficiency measure; a lab envelope measure that is excluded, represented as screened-out with reason):
```json
{
  "measures": [
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
    },
    {
      "measure_id": "led-upgrade",
      "measure_kind": "efficiency",
      "cost": { "capex": { "low": 60000, "base": 78000, "high": 95000 }, "opex_delta_yr": -12000 }
    }
  ],
  "screened_out": [
    { "measure_id": "lab-envelope-sealant", "reason": "lab envelope air-sealing excluded by default — no site-observed exterior leakage basis (see archetypes/lab.md)" }
  ]
}
```

- [ ] **Step 3: Write the validator** — `scripts/validate-measure-cost.mjs`:
```js
import Ajv from 'ajv'
import { readFileSync } from 'node:fs'
const schema = JSON.parse(readFileSync(new URL('../skills/construction-costing/schema/measure-cost.schema.json', import.meta.url), 'utf8'))
const data = JSON.parse(readFileSync(new URL('../skills/construction-costing/example-data.json', import.meta.url), 'utf8'))
const ajv = new Ajv({ allErrors: true })
const validate = ajv.compile(schema)
let failed = false
for (const m of data.measures) {
  if (!validate(m)) { failed = true; console.error(`✗ ${m.measure_id}:`, ajv.errorsText(validate.errors)) }
  // Contract rules beyond JSON Schema:
  if (m.measure_kind === 'fuel_switch') {
    if (!m.cost.electrical_capacity) { failed = true; console.error(`✗ ${m.measure_id}: fuel_switch missing electrical_capacity`) }
    else if (m.cost.electrical_capacity.flag === 'UNVERIFIED' && m.cost.electrical_capacity.upgrade_cost.low === m.cost.electrical_capacity.upgrade_cost.high) {
      failed = true; console.error(`✗ ${m.measure_id}: UNVERIFIED capacity must be a range, not a point`)
    }
    if (!m.cost.efficiency_alternative) { failed = true; console.error(`✗ ${m.measure_id}: fuel_switch missing efficiency_alternative`) }
  }
}
if (failed) { process.exit(1) }
console.log('measure-cost contract OK')
```

- [ ] **Step 4: Run — verify it PASSES** (schema + fixture are self-consistent by construction; this is the green baseline the contract must hold):

Run: `cd ~/soapbox-agent && npm ls ajv >/dev/null 2>&1 || npm i; node scripts/validate-measure-cost.mjs`
Expected: `measure-cost contract OK`

- [ ] **Step 5: Prove the rule-checks bite (RED then restore)** — temporarily delete `efficiency_alternative` from `central-ashp` in the fixture, run the validator, confirm it exits non-zero with `missing efficiency_alternative`, then restore the fixture and re-run to `OK`.

- [ ] **Step 6: Commit**
```bash
cd ~/soapbox-agent && git add skills/construction-costing/schema/measure-cost.schema.json skills/construction-costing/example-data.json scripts/validate-measure-cost.mjs && git commit -m "feat(costing): measure.cost contract schema + validator"
```

---

### Task 2: `construction-costing` skill (method + seeded cost bases)

**Files:**
- Create: `skills/construction-costing/SKILL.md`
- Create: `skills/construction-costing/references/cost-bases.md`
- Create: `scripts/lint-skill-construction-costing.mjs`

**Interfaces:**
- Consumes: the Task 1 contract (`schema/measure-cost.schema.json`, `example-data.json`).
- Produces: a documented method the decarb-plan workflow invokes to emit `measure.cost` per measure.

- [ ] **Step 1: Write the lint (failing target)** — `scripts/lint-skill-construction-costing.mjs`:
```js
import { readFileSync } from 'node:fs'
const md = readFileSync(new URL('../skills/construction-costing/SKILL.md', import.meta.url), 'utf8')
const bases = readFileSync(new URL('../skills/construction-costing/references/cost-bases.md', import.meta.url), 'utf8')
const must = [
  'name: construction-costing',
  'electrical service capacity', 'demand_increase_kw', 'service_capacity_known',
  'UNVERIFIED', 'range', 'never', 'point estimate',
  'efficiency_alternative', 'fuel-switch', 'opex_delta_yr',
  'archetype', 'climate', 'measure-cost.schema.json'
]
const missing = must.filter(s => !md.includes(s))
if (missing.length) throw new Error('construction-costing SKILL.md missing: ' + missing.join(', '))
if (!/PLACEHOLDER|tune|to be confirmed/i.test(bases)) throw new Error('cost-bases.md must flag seeded numbers as placeholders to tune')
if (!/\$\/kW|\$\/A|service upgrade/i.test(bases)) throw new Error('cost-bases.md must include an electrical service-capacity cost basis')
if (md.length < 3000) throw new Error('SKILL.md suspiciously short')
console.log('construction-costing lint OK')
```

- [ ] **Step 2: Run to verify it FAILS**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-construction-costing.mjs`
Expected: throws `ENOENT` / missing content (files not yet created).

- [ ] **Step 3: Write `references/cost-bases.md`** — seeded, explicitly-placeholder cost bases. Include: a per-measure $/unit table keyed by archetype × climate × size (envelope, HVAC plant electrification, high-eff boiler, LED, DCV, fume-hood VAV, chiller optimization); and an **electrical service-capacity cost basis** section giving a parametric `$/kW` (or `$/A` of new service) curve by region, plus the headroom-vs-new-service logic. Header MUST state: `> PLACEHOLDER cost bases — seeded defaults for Christopher to tune; not authoritative.` Include the words `$/kW` and `service upgrade`.

- [ ] **Step 4: Write `SKILL.md`** — frontmatter `name: construction-costing` + description with triggers ("estimate construction cost", "what's the CapEx for", "cost this measure/roster"). Body method:
  1. Load the measure roster + the Audette model (end-use kW, peak demand).
  2. For each measure, look up the parametric base from `references/cost-bases.md` (archetype × climate × size) → `capex{low,base,high}` and `opex_delta_yr` (POSITIVE = OpEx rises).
  3. **Fuel-switch / electrification measures:** compute `demand_increase_kw` from the model; if actual service capacity provided → point `upgrade_cost`, `flag: VERIFIED`; else `upgrade_cost {low: 0 (assume headroom), high: full new service from the $/kW basis}`, `flag: UNVERIFIED`. **Never** collapse an UNVERIFIED range to a point estimate.
  4. **Always** emit the `efficiency_alternative` (the standard non-switching high-efficiency option) with its own `capex` + `opex_delta_yr`.
  5. Emit the `measure.cost` object per `schema/measure-cost.schema.json`; validate with `node scripts/validate-measure-cost.mjs`.
  6. Note it is consumed by `decarb-plan` measure screening and read by `quality-review`.
  Reference `measure-cost.schema.json` by name in the text.

- [ ] **Step 5: Run to verify it PASSES**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-construction-costing.mjs`
Expected: `construction-costing lint OK`

- [ ] **Step 6: Commit**
```bash
cd ~/soapbox-agent && git add skills/construction-costing/SKILL.md skills/construction-costing/references/cost-bases.md scripts/lint-skill-construction-costing.mjs && git commit -m "feat(costing): construction-costing skill with electrical-capacity cost model"
```

---

### Task 3: Cross-archetype rules in `measure-universe.md`

**Files:**
- Modify: `skills/decarb-plan/references/measure-universe.md` (append a section)
- Create: `scripts/lint-archetype-guidance.mjs`

**Interfaces:**
- Consumes: the contract field names from Task 1 (`electrical_capacity`, `efficiency_alternative`, `opex_delta_yr`) — referenced in the guidance so the verifier and costing agree on terms.

- [ ] **Step 1: Write the lint (failing target)** — `scripts/lint-archetype-guidance.mjs` (covers Tasks 3–5; assert only Task-3 content now, extend in 4 & 5):
```js
import { readFileSync } from 'node:fs'
const u = readFileSync(new URL('../skills/decarb-plan/references/measure-universe.md', import.meta.url), 'utf8')
const mustUniverse = [
  'Cross-archetype economic-realism rules',
  'electrical service capacity', 'first-class', 'feasibility gate',
  'always pair', 'efficiency', 'fuel-switch',
  'OpEx', 'electricity-cost'
]
const miss = mustUniverse.filter(s => !u.includes(s))
if (miss.length) throw new Error('measure-universe.md missing cross-archetype rules: ' + miss.join(', '))
console.log('archetype-guidance lint OK (universe)')
```

- [ ] **Step 2: Run to verify it FAILS**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: throws `measure-universe.md missing cross-archetype rules: ...`.

- [ ] **Step 3: Append the rules** to `skills/decarb-plan/references/measure-universe.md`:
```markdown

## Cross-archetype economic-realism rules (apply to every building)

These three rules are portfolio-general (they apply to most cold-climate buildings, not
just labs). Enforced by the construction-costing skill and the quality-review verifier.

1. **Electrical service capacity is a first-class cost and feasibility gate — not a
   contingency line.** Any fuel-switch / electrification measure MUST carry an
   `electrical_capacity` block (`demand_increase_kw`, `service_capacity_known`,
   `upgrade_cost {low,high}`, `flag`). At portfolio screening the service capacity is
   usually unknown → `flag: UNVERIFIED` and a cost **range**, never a false point estimate.
   Historically, electrification of substantial heating plant repeatedly blows the budget on
   the service upgrade; make that visible up front.
2. **Always pair a fuel-switch with its efficiency-upgrade alternative.** Whenever an
   electrification/fuel-switch measure is on the table (e.g. ASHP for a failing boiler),
   also present the standard high-efficiency non-switching option (e.g. condensing boiler),
   each with its own capex and `opex_delta_yr`, so the decision is explicit.
3. **OpEx-viability caveat.** In high-electricity-cost markets, electrification frequently
   *raises* OpEx even when capex pencils. Surface `opex_delta_yr` against the org's
   investment criterion (pay-for-itself vs. carbon-weighted). A measure that raises OpEx is
   not automatically wrong — but it must be flagged, not hidden.
```

- [ ] **Step 4: Run to verify it PASSES**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: `archetype-guidance lint OK (universe)`

- [ ] **Step 5: Commit**
```bash
cd ~/soapbox-agent && git add skills/decarb-plan/references/measure-universe.md scripts/lint-archetype-guidance.mjs && git commit -m "feat(decarb): cross-archetype economic-realism rules in measure-universe"
```

---

### Task 4: Lab archetype module (`archetypes/lab.md`)

**Files:**
- Create: `skills/decarb-plan/references/archetypes/lab.md`
- Modify: `scripts/lint-archetype-guidance.mjs` (add lab assertions)

- [ ] **Step 1: Extend the lint (failing target)** — add to `scripts/lint-archetype-guidance.mjs` before the final `console.log`:
```js
const lab = readFileSync(new URL('../skills/decarb-plan/references/archetypes/lab.md', import.meta.url), 'utf8')
const mustLab = [
  'excluded by default', 'site observation', 'corridor', 'negatively pressurized',
  'makeup air', 'fume-hood', 'chiller-plant optimization', 'VFD',
  'exhaust heat recovery', 'only if observed', 'electrical service capacity'
]
const missLab = mustLab.filter(s => !lab.includes(s))
if (missLab.length) throw new Error('lab.md missing: ' + missLab.join(', '))
console.log('archetype-guidance lint OK (lab)')
```
(Remove the old trailing `console.log('archetype-guidance lint OK (universe)')` so the script ends on the lab line — the universe assertions above it still run.)

- [ ] **Step 2: Run to verify it FAILS**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: throws (lab.md missing / ENOENT).

- [ ] **Step 3: Write `skills/decarb-plan/references/archetypes/lab.md`**:
```markdown
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
```

- [ ] **Step 4: Run to verify it PASSES**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: ends `archetype-guidance lint OK (lab)`

- [ ] **Step 5: Commit**
```bash
cd ~/soapbox-agent && git add skills/decarb-plan/references/archetypes/lab.md scripts/lint-archetype-guidance.mjs && git commit -m "feat(decarb): lab archetype guidance (envelope excluded-by-default)"
```

---

### Task 5: Logistics archetype module (`archetypes/logistics.md`, seeded)

**Files:**
- Create: `skills/decarb-plan/references/archetypes/logistics.md`
- Modify: `scripts/lint-archetype-guidance.mjs` (add logistics assertions)

- [ ] **Step 1: Extend the lint (failing target)** — add before the final lab `console.log`, and change the final log to `(all)`:
```js
const log = readFileSync(new URL('../skills/decarb-plan/references/archetypes/logistics.md', import.meta.url), 'utf8')
const mustLog = ['rooftop solar', 'cool-roof', 'high-bay', 'LED', 'low process load', 'minimal HVAC', 'electrical service capacity']
const missLog = mustLog.filter(s => !log.includes(s))
if (missLog.length) throw new Error('logistics.md missing: ' + missLog.join(', '))
```
Change the trailing `console.log('archetype-guidance lint OK (lab)')` to `console.log('archetype-guidance lint OK (all)')`.

- [ ] **Step 2: Run to verify it FAILS**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: throws (logistics.md missing / ENOENT).

- [ ] **Step 3: Write `skills/decarb-plan/references/archetypes/logistics.md`**:
```markdown
# Archetype: Logistics / warehouse buildings

Representative of ~60–70% of the Clarion portfolio (e.g. Kingsland). Large-footprint,
low-intensity buildings — the electrification calculus is very different from labs.

## Profile
- **Large roof** → rooftop solar and **cool-roof** are usually the headline measures
  (roof area is the asset). Solar economics benefit from any virtual-net-metering recovery.
- **Low process load, minimal HVAC**, large conditioned volume, often unit heaters / RTUs.
- **High-bay LED** + controls (occupancy/daylight) is typically high-ROI and low-risk.

## Electrification
- Heating plant is small relative to the building, so the **electrical service capacity**
  demand increase from electrification is usually modest vs. a lab — but the same
  `electrical_capacity` gate still applies; confirm the roof/solar interconnection capacity
  too. Pair any RTU→heat-pump-RTU switch with a high-efficiency RTU efficiency alternative.

## Screening notes
- Prioritize envelope (roof), lighting, and controls before fuel-switching.
- This is a stub seeded for the Kingsland run; extend with measured findings once Kingsland
  is analyzed.
```

- [ ] **Step 4: Run to verify it PASSES**

Run: `cd ~/soapbox-agent && node scripts/lint-archetype-guidance.mjs`
Expected: ends `archetype-guidance lint OK (all)`

- [ ] **Step 5: Commit**
```bash
cd ~/soapbox-agent && git add skills/decarb-plan/references/archetypes/logistics.md scripts/lint-archetype-guidance.mjs && git commit -m "feat(decarb): seed logistics archetype guidance (Kingsland)"
```

---

### Task 6: Verifier gates in `quality-review`

**Files:**
- Modify: `skills/quality-review/SKILL.md` (append a decarb gate section)
- Create: `scripts/lint-skill-quality-review.mjs`

**Interfaces:**
- Consumes: the Task 1 contract field names (`electrical_capacity`, `flag`, `opex_delta_yr`, `efficiency_alternative`) and the Task 4 lab exclude-by-default rule — referenced verbatim so the gate checks match the emitted data and guidance.

- [ ] **Step 1: Write the lint (failing target)** — `scripts/lint-skill-quality-review.mjs`:
```js
import { readFileSync } from 'node:fs'
const md = readFileSync(new URL('../skills/quality-review/SKILL.md', import.meta.url), 'utf8')
const must = [
  'Decarb measure-recommendation gates',
  'BLOCK', 'WARN',
  'electrical_capacity', 'UNVERIFIED', 'firm recommendation',
  'physically-unsupported', 'lab envelope', 'site-observation',
  'opex_delta_yr', 'efficiency_alternative', 'NPV', 'carbon', 'weighting'
]
const missing = must.filter(s => !md.includes(s))
if (missing.length) throw new Error('quality-review SKILL.md missing decarb gates: ' + missing.join(', '))
console.log('quality-review lint OK')
```

- [ ] **Step 2: Run to verify it FAILS**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-quality-review.mjs`
Expected: throws `quality-review SKILL.md missing decarb gates: ...`.

- [ ] **Step 3: Append the gate section** to `skills/quality-review/SKILL.md`:
```markdown

## Decarb measure-recommendation gates

When reviewing a decarb plan / measure roster, apply these tiered gates in addition to the
general critique. They read the `measure.cost` contract (see the `construction-costing`
skill) and the archetype guidance (`decarb-plan/references/archetypes/`).

### BLOCK — do not let the plan proceed until resolved
- **Missing electrical-capacity basis.** A fuel-switch / electrification measure recommended
  with no `electrical_capacity` block, OR with `flag: UNVERIFIED` while presented as a
  **firm recommendation** (it must instead surface the flag and the `upgrade_cost` range).
- **Physically-unsupported savings.** A measure whose savings assume a mechanism the
  building's config doesn't support, checked against archetype guidance. Specifically: a
  **lab envelope** air-sealing / infiltration measure recommended **without a
  site-observation basis** for exterior leakage (default-excluded per `archetypes/lab.md`).

### WARN — surface in the report, non-blocking (these are org-policy calls, not errors)
- **OpEx increase vs criterion.** A recommended measure with `opex_delta_yr > 0` under a
  pay-for-itself criterion, without an exit-value / NOI justification.
- **No efficiency alternative.** A fuel-switch recommended without its
  `efficiency_alternative` shown alongside.
- **Weighting mismatch.** The NPV vs carbon weighting doesn't match the org's stated
  criterion (e.g. defaulted carbon-weighted 35/65 when the org's criterion is
  pay-for-itself) — suggest reweighting.
```

- [ ] **Step 4: Run to verify it PASSES**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-quality-review.mjs`
Expected: `quality-review lint OK`

- [ ] **Step 5: Commit**
```bash
cd ~/soapbox-agent && git add skills/quality-review/SKILL.md scripts/lint-skill-quality-review.mjs && git commit -m "feat(verifier): tiered decarb measure-recommendation gates"
```

---

### Task 7: Retain durable lessons into shared memory

**Files:** none (runtime MCP writes to the hindsight `soapbox` bank).

**Interfaces:** Consumes the rules authored in Tasks 3–4 (states them as durable, cross-engagement lessons).

- [ ] **Step 1: Retain the three durable lessons** via the hindsight MCP `retain` tool into bank `soapbox` (write-policy: no secrets/PII). Retain exactly these three, each tagged `decarb`, `economic-realism`:
  1. *"Electrification / fuel-switch decarb measures must treat electrical service-capacity upgrade cost as a first-class cost + feasibility gate. At portfolio screening the service capacity is usually unknown → present an UNVERIFIED cost range, never a point estimate. This is the historical budget-killer for cold-climate electrification (esp. labs)."*
  2. *"Labs are negatively pressurized relative to the corridor, not the exterior; exhaust makeup air comes from the corridor/office zones. Envelope air-sealing / infiltration measures are excluded by default for labs — admit only with site-observed exterior leakage, bounded to that path."*
  3. *"A decarb measure that raises OpEx (opex_delta_yr > 0) must be flagged against the org's investment criterion; in high-electricity-cost markets electrification frequently raises OpEx even when capex pencils. Always pair a fuel-switch with its efficiency-upgrade alternative."*

- [ ] **Step 2: Verify** via the hindsight `recall`/`list_memories` tool that all three are present in bank `soapbox` with the `decarb` tag.

- [ ] **Step 3: Record completion** — no commit (memory is external); note in the progress ledger that Task 7 retained 3 lessons and the recall check passed.

---

## Final Verification (after all tasks)

- [ ] `cd ~/soapbox-agent && node scripts/validate-measure-cost.mjs && node scripts/lint-skill-construction-costing.mjs && node scripts/lint-archetype-guidance.mjs && node scripts/lint-skill-quality-review.mjs` — all print `OK`.
- [ ] Sanity: the fixture's `central-ashp` carries an `UNVERIFIED` capacity range and an `efficiency_alternative`; `lab-envelope-sealant` is in `screened_out` with the exclude reason.
- [ ] Confirm no files were touched outside `skills/`, `scripts/`, `docs/` (no platform-core code).

## Self-Review Notes

- **Spec coverage:** contract (T1) ✓; construction-costing skill + electrical-capacity model + seeded-placeholder bases (T2) ✓; cross-archetype rules (T3) ✓; lab exclude-by-default (T4) ✓; logistics seed (T5) ✓; tiered verifier gates (T6) ✓; shared-memory retention (T7) ✓; utility-cost ingestion correctly OUT of scope.
- **Naming consistency:** `electrical_capacity`, `service_capacity_known`, `upgrade_cost{low,high}`, `flag` (VERIFIED|UNVERIFIED), `efficiency_alternative`, `opex_delta_yr` are identical across schema (T1), costing SKILL (T2), and verifier gates (T6).
- **Test model:** matches repo convention — `ajv` schema validation + `node scripts/lint-*.mjs` content assertions (mirrors `lint-skill-esg-profile.mjs`); no fabricated pytest/vitest.
