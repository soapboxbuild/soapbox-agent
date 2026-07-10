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
