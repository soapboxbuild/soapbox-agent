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
