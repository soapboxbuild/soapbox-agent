import { readFileSync } from 'node:fs'
const md = readFileSync(new URL('../skills/esg-profile/SKILL.md', import.meta.url), 'utf8')
const must = [
  'name: esg-profile', 'No LLM arithmetic', 'anonymiz', 'render gate',
  'kickoff', 'collect', 'reconcile', 'verify', 'render', 'export',
  'registry.json', 'fill_report', "report_type: 'esg-profile'",
  'regression', 'source-precedence', 'kWh/m', 'never national median',
  'sponsor-scoped', 'verifier__list_findings'
]
const missing = must.filter(s => !md.includes(s))
if (missing.length) throw new Error('SKILL.md missing required content: ' + missing.join(', '))
if (md.length < 4000) throw new Error('SKILL.md suspiciously short')
console.log('SKILL.md lint OK')
