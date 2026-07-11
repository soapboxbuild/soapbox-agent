import { readFileSync } from 'node:fs'
const md = readFileSync(new URL('../skills/quality-review/SKILL.md', import.meta.url), 'utf8')
const must = [
  'Decarb measure-recommendation gates',
  'BLOCK', 'WARN',
  'electrical_capacity', 'UNVERIFIED', 'firm recommendation',
  'Physically-unsupported', 'lab envelope', 'site-observation',
  'opex_delta_yr', 'efficiency_alternative', 'NPV', 'carbon', 'weighting',
  'Stale cost', 'escalation'
]
const missing = must.filter(s => !md.includes(s))
if (missing.length) throw new Error('quality-review SKILL.md missing decarb gates: ' + missing.join(', '))
console.log('quality-review lint OK')
