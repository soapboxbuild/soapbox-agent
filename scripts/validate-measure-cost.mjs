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
