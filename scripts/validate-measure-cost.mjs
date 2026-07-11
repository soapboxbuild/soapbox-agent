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
  if (m.cost.electrical_capacity && m.cost.electrical_capacity.service_capacity_known === false && m.cost.electrical_capacity.flag !== 'UNVERIFIED') {
    failed = true; console.error(`✗ ${m.measure_id}: service_capacity_known=false requires flag=UNVERIFIED`)
  }
  if (m.measure_kind === 'fuel_switch') {
    if (!m.cost.electrical_capacity) { failed = true; console.error(`✗ ${m.measure_id}: fuel_switch missing electrical_capacity`) }
    else if (m.cost.electrical_capacity.flag === 'UNVERIFIED' && m.cost.electrical_capacity.upgrade_cost.low === m.cost.electrical_capacity.upgrade_cost.high) {
      failed = true; console.error(`✗ ${m.measure_id}: UNVERIFIED capacity must be a range, not a point`)
    }
    if (!m.cost.efficiency_alternative) { failed = true; console.error(`✗ ${m.measure_id}: fuel_switch missing efficiency_alternative`) }
  }
  if (m.cost.escalation) {
    if (!Number.isInteger(m.cost.escalation.escalated_to)) {
      failed = true; console.error(`✗ ${m.measure_id}: escalation.escalated_to must be an integer year`)
    }
    if (typeof m.cost.escalation.index_vintage !== 'string' || m.cost.escalation.index_vintage.length === 0) {
      failed = true; console.error(`✗ ${m.measure_id}: escalation.index_vintage must be a non-empty string`)
    }
  }
  if (m.cost.cost_breakdown) {
    const { material, labour, equipment } = m.cost.cost_breakdown
    const sum = material + labour + equipment
    if (Math.abs(sum - 1.0) > 0.011) {
      failed = true; console.error(`✗ ${m.measure_id}: cost_breakdown shares sum to ${sum}, must be within 0.011 of 1.0`)
    }
  }
}
if (failed) { process.exit(1) }
console.log('measure-cost contract OK')
