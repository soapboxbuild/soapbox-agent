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

const lab = readFileSync(new URL('../skills/decarb-plan/references/archetypes/lab.md', import.meta.url), 'utf8')
const mustLab = [
  'excluded by default', 'site observation', 'corridor', 'negatively pressurized',
  'makeup air', 'Fume-hood', 'Chiller-plant optimization', 'VFD',
  'exhaust heat recovery', 'only if observed', 'electrical service capacity'
]
const missLab = mustLab.filter(s => !lab.includes(s))
if (missLab.length) throw new Error('lab.md missing: ' + missLab.join(', '))

const log = readFileSync(new URL('../skills/decarb-plan/references/archetypes/logistics.md', import.meta.url), 'utf8')
const mustLog = ['rooftop solar', 'cool-roof', 'High-bay', 'LED', 'Low process load', 'minimal HVAC', 'electrical service capacity']
const missLog = mustLog.filter(s => !log.includes(s))
if (missLog.length) throw new Error('logistics.md missing: ' + missLog.join(', '))
console.log('archetype-guidance lint OK (all)')
