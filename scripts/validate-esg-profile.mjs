import Ajv from 'ajv'
import { readFileSync } from 'node:fs'
const ajv = new Ajv({ allErrors: true, strict: false })
const load = p => JSON.parse(readFileSync(new URL(p, import.meta.url)))

// 1. registry shape
const registry = load('../skills/esg-profile/connectors/registry.json')
const REQUIRED_SOURCES = ['energy','green_street','physical_risk','bps','questionnaire','peer_benchmark','materiality','investment_info','governance','crrem']
for (const s of REQUIRED_SOURCES) {
  if (!registry[s]) throw new Error(`registry missing source_id: ${s}`)
  if (!registry[s].produces) throw new Error(`registry.${s} missing 'produces'`)
  if (!registry[s].default_live_adapter) throw new Error(`registry.${s} missing 'default_live_adapter'`)
}
if (!registry.crrem.gap_filler || !registry.physical_risk.gap_filler || !registry.green_street.gap_filler)
  throw new Error('crrem, physical_risk, green_street must be marked gap_filler:true')
console.log('registry OK:', Object.keys(registry).length, 'sources')

// 2. schema + fixture
const schema = load('../templates/esg-profile/schema.json')
const validate = ajv.compile(schema)
const fixture = load('../skills/esg-profile/demo/example-sponsor.json')
if (!validate(fixture)) { console.error(validate.errors); throw new Error('example-sponsor.json fails schema') }
console.log('schema + fixture OK')
