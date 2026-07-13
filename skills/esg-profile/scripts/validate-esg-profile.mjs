#!/usr/bin/env node
// Validates a fund_overview / sponsor fixture against templates/esg-profile/schema.json.
// Usage: node validate-esg-profile.mjs [path-to-fixture.json]
// Defaults to skills/esg-profile/demo/madison/fund-peers.json.
// Asserts (for fund_overview fixtures): schema-valid, ranking.length >= 2,
// sponsor_metrics.length >= 2, underperformers.length >= 1.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import Ajv from "ajv";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const schemaPath = path.join(repoRoot, "templates", "esg-profile", "schema.json");

const target = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(repoRoot, "skills", "esg-profile", "demo", "madison", "fund-peers.json");

const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const ajv = new Ajv({ allErrors: true, strict: false });
const validate = ajv.compile(schema);

const data = JSON.parse(readFileSync(target, "utf8"));
const fundOverview = data.fund_overview;

if (!fundOverview) {
  console.error(`FAIL — ${target} has no top-level "fund_overview" key.`);
  process.exit(1);
}

// The full schema is required={sponsor, fund_overview?} at top level via oneOf-ish shape;
// here we validate the fund_overview sub-schema directly using the schema's own definition.
const fundOverviewSchema = schema.properties.fund_overview;
const validateFund = ajv.compile(fundOverviewSchema);
const schemaValid = validateFund(fundOverview);

const errors = [];
if (!schemaValid) errors.push(...validateFund.errors.map((e) => `${e.instancePath} ${e.message}`));

const ranking = fundOverview.ranking || [];
const sponsors = fundOverview.sponsor_metrics || [];
const underperformers = fundOverview.underperformers || [];

if (ranking.length < 2) errors.push(`ranking.length ${ranking.length} < 2`);
if (sponsors.length < 2) errors.push(`sponsor_metrics.length ${sponsors.length} < 2`);
if (underperformers.length < 1) errors.push(`underperformers.length ${underperformers.length} < 1`);

if (errors.length) {
  console.error(`FAIL — ${target}`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}

console.log(
  `PASS — ${path.relative(repoRoot, target)}: schema-valid, sponsors=${sponsors.length}, ranking=${ranking.length}, underperformers=${underperformers.length}`
);
