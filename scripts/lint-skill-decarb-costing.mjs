import { readFileSync } from 'node:fs'

const s = readFileSync(new URL('../skills/decarb-plan/SKILL.md', import.meta.url), 'utf8')
const must = [
  'Soapbox Costing',
  'get_measure_capex',
  'costing skill',
  'cost-bases.md',
  'escalation',
  'references',
  'does not replace',
]
const miss = must.filter(sub => !s.includes(sub))
if (miss.length) throw new Error('SKILL.md missing decarb-costing wiring: ' + miss.join(', '))
console.log('decarb-costing lint OK')
