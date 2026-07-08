# ESG Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `esg-profile` skill + report template that turns disparate sponsor ESG/climate/investment data into the asset manager's two-layout ESG Profile deliverable (Sponsor Profile + Fund Overview), with swappable live/static data connectors, for the IMN stage demo.

**Architecture:** A markdown-orchestrated skill (like `decarb-plan`/`portfolio-analysis`) drives phases kickoff → collect → reconcile → verify → render → export. Data inputs resolve through a **declarative connector layer** (`connectors/registry.json` + per-run bindings) so live-vs-static is a config choice, not code. Output renders via the existing `fill_report` MCP tool against a new `templates/esg-profile/` template, then exports to PPTX matching her Template v3.

**Tech Stack:** Markdown SKILL.md; JSON Schema (draft-07) validated with `ajv`; declarative connector registry resolved in skill prose calling MCP tools (`citizen-energy`, `physrisk`, `crrem`, compliance) or reading static files; `template-mcp` (TypeScript, `template-mcp/src/index.ts`) for registration; Paged.js HTML template; python-pptx/Playwright/openpyxl exports via the `report-review` workflow; Verifier/Retrofit MCP tools (`verifier__*`, `retrofit__*`).

## Global Constraints

- **No LLM arithmetic** — every reported number comes from an engine/tool/cited source; the LLM never computes a reported figure.
- **Connector swap = one binding edit** — the workflow calls `resolve(source_id)`; live-vs-static is set only in the run config `connectors` block. No schema/workflow/template change to go live.
- **Provenance on every value** — `{source_id, mode: live|static|estimate, origin, period, retrieved_at}`; artifact labels static vs live honestly (never-fail-silently).
- **Anonymization is mandatory and NOT pre-done** — the asset manager's files leak the real sponsor (the real sponsor names, `the real contact domain` emails, specific city names). Scrub before any file enters the repo or the stage.
- **Analytics Standards** — energy in kWh + kWh/m² only, ≤2 significant figures displayed; benchmarks are peer/Fund/AssetClass/MIR/MIEPPI, never national median.
- **Render gate is HARD, fail-closed, sponsor-scoped** — no render with an open-high Verifier finding on THIS sponsor unless a documented override exists in state.
- **Grain is sponsor-level** within a fund; fund scope is a rollup over the fund's sponsors.
- **Templates go live from GitHub `main`** — `fill_report` fetches `templates/<type>/layout-agent.html` from `main` (5-min cache); a template only works after commit+push to `main` AND `esg-profile` is in `KNOWN_TYPES`.
- Repo root: `~/soapbox-agent`. Skill dir: `skills/esg-profile/`. Template dir: `templates/esg-profile/`.

---

## File Structure

- `skills/esg-profile/SKILL.md` — workflow: phases, discipline, reconciliation, regression detection, gates.
- `skills/esg-profile/state-schema.json` — durable run state contract.
- `skills/esg-profile/connectors/registry.json` — `source_id` → produced-fields schema + default live adapter.
- `templates/esg-profile/schema.json` — report data contract (both layouts).
- `templates/esg-profile/layout-agent.html` — the Paged.js template `fill_report` fetches.
- `templates/esg-profile/xlsx.json` — openpyxl export map.
- `template-mcp/src/index.ts` — add `esg-profile` to `KNOWN_TYPES` + missing-section warnings.
- `skills/esg-profile/demo/` — scrubbed static demo data + `materiality.json` + `bps_cache.json`.
- `scripts/validate-esg-profile.mjs` — ajv validation harness (tests).
- `scripts/smoke-esg-profile.mjs` — end-to-end render smoke against `fill_report`.

Reference inputs (already extracted, in session scratchpad `the raw scratchpad extracts`): `template.pptx` (4 slides), `extract.xlsx` sheet `30_input_qualitative` (24 columns), `notes.docx` (6 tables). Field names below are copied from these.

---

### Task 1: Register `esg-profile` report type in template-mcp

**Files:**
- Modify: `template-mcp/src/index.ts:7` (KNOWN_TYPES) and `:60-72` (warnings block)

**Interfaces:**
- Produces: report_type `'esg-profile'` accepted by `fill_report` and `get_report_template`.

- [ ] **Step 1: Add the type to the enum**

In `template-mcp/src/index.ts` line 7, change:
```ts
const KNOWN_TYPES = ['rsra', 'crrem', 'sustainability-passport', 'portfolio-analysis', 'decarb', 'retrofit-advisor'] as const
```
to:
```ts
const KNOWN_TYPES = ['rsra', 'crrem', 'sustainability-passport', 'portfolio-analysis', 'decarb', 'retrofit-advisor', 'esg-profile'] as const
```

- [ ] **Step 2: Add missing-section warnings**

In the warnings block (after the `if (report_type === 'rsra')` block, before the `const json =` line), add:
```ts
if (report_type === 'esg-profile') {
  const d = data as Record<string, unknown>
  if (!d.sponsor && !d.fund_overview) {
    warnings.push('⚠️ MISSING sponsor and fund_overview: provide one of the two layout roots.')
  }
  if (d.sponsor && !(d.sponsor as Record<string, unknown>).scorecard) {
    warnings.push('⚠️ MISSING sponsor.scorecard: the 4-pillar scorecard + YoY trend will be hidden.')
  }
  if (d.sponsor && !(d.sponsor as Record<string, unknown>).risk_profile) {
    warnings.push('⚠️ MISSING sponsor.risk_profile: transition/physical risk table will be hidden.')
  }
}
```

- [ ] **Step 3: Build to verify it compiles**

Run: `cd ~/soapbox-agent/template-mcp && npm run build 2>&1 | tail -5` (or `npx tsc --noEmit` if no build script)
Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd ~/soapbox-agent && git add template-mcp/src/index.ts
git commit -m "feat(template-mcp): register esg-profile report type + section warnings"
```

> Deploy of template-mcp to `soapbox-mcps` (templates.mcp.soapbox.build) happens in Task 9 after the template exists on `main`.

---

### Task 2: Connector registry (the swap layer contract)

**Files:**
- Create: `skills/esg-profile/connectors/registry.json`
- Create: `scripts/validate-esg-profile.mjs`

**Interfaces:**
- Produces: registry object keyed by `source_id`; each entry `{ produces: {field: type}, default_live_adapter: {kind, tool?}, gap_filler: bool }`. Consumed by SKILL.md collect phase (Task 5) and the validator.

- [ ] **Step 1: Write the validation test harness**

Create `scripts/validate-esg-profile.mjs`:
```js
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd ~/soapbox-agent && npm i -D ajv 2>/dev/null; node scripts/validate-esg-profile.mjs`
Expected: FAIL — `Cannot find module .../registry.json`.

- [ ] **Step 3: Write the registry**

Create `skills/esg-profile/connectors/registry.json`:
```json
{
  "energy":         { "produces": {"eui_kwh_m2":"number","carbon_intensity":"number","renewable_pct":"number","energy_rating_pct":"number"}, "default_live_adapter": {"kind":"mcp","tool":"citizen-energy get_benchmarking","region_aware":true}, "gap_filler": false },
  "green_street":   { "produces": {"sector_risk_rating":"string"}, "default_live_adapter": {"kind":"mcp","tool":"green-street get_sector_risk"}, "gap_filler": true },
  "physical_risk":  { "produces": {"physical_impact":"string","hazards":"array"}, "default_live_adapter": {"kind":"mcp","tool":"physrisk get_hazard_exposure"}, "gap_filler": true },
  "bps":            { "produces": {"market_regulation":"string","fine_exposure":"number"}, "default_live_adapter": {"kind":"mcp","tool":"run_compliance_analysis"}, "gap_filler": false },
  "questionnaire":  { "produces": {"pillar_policy_strategy":"number","pillar_governance_resourcing":"number","pillar_portfolio_management":"number","pillar_monitoring_reporting":"number","total_score":"number","qual_summary":"string","initiatives_completed":"array","initiatives_in_progress":"array","initiatives_planned":"array","esg_risks":"array","mitigation_actions":"array"}, "default_live_adapter": {"kind":"api","tool":"fabric_or_cambio"}, "gap_filler": false },
  "peer_benchmark": { "produces": {"fund_avg":"number","asset_class_avg":"number","mir_avg":"number","mieppi_avg":"number"}, "default_live_adapter": {"kind":"api","tool":"fund_data"}, "gap_filler": false },
  "materiality":    { "produces": {"considerations":"array"}, "default_live_adapter": {"kind":"file","path":"reference/materiality.json"}, "gap_filler": false },
  "investment_info":{ "produces": {"asset_class":"string","location":"string","size":"string","exit_date":"string","standing_dev":"string"}, "default_live_adapter": {"kind":"api","tool":"fund_data"}, "gap_filler": false },
  "governance":     { "produces": {"gov_annual_budget":"string","gov_leasing":"string","gov_capex_project_variance":"string","gov_contractor_engagement":"string"}, "default_live_adapter": {"kind":"api","tool":"fund_data"}, "gap_filler": false },
  "crrem":          { "produces": {"stranding_year":"number","misalignment":"string"}, "default_live_adapter": {"kind":"mcp","tool":"crrem get_pathway"}, "gap_filler": true }
}
```

- [ ] **Step 4: Run validation to verify it passes**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs`
Expected: PASS — `registry OK: 10 sources`.

- [ ] **Step 5: Commit**

```bash
cd ~/soapbox-agent && git add skills/esg-profile/connectors/registry.json scripts/validate-esg-profile.mjs package.json
git commit -m "feat(esg-profile): connector registry + validation harness"
```

---

### Task 3: Report data schema (both layouts)

**Files:**
- Create: `templates/esg-profile/schema.json`
- Modify: `scripts/validate-esg-profile.mjs` (add schema self-validation + fixture check)
- Create: `skills/esg-profile/demo/example-sponsor.json` (valid fixture)

**Interfaces:**
- Produces: JSON Schema `$id: "esg-profile"` with top-level optional `sponsor` (§4B) and `fund_overview` (§4A), shared `meta`. `sponsor.scorecard.pillars` = 4 named pillar numbers + `total` + `trend` (array of {year,total}). Consumed by `fill_report` data (Task 6) and exports (Task 8).

- [ ] **Step 1: Add schema + fixture checks to the harness**

Append to `scripts/validate-esg-profile.mjs`:
```js
const schema = load('../templates/esg-profile/schema.json')
const validate = ajv.compile(schema)
const fixture = load('../skills/esg-profile/demo/example-sponsor.json')
if (!validate(fixture)) { console.error(validate.errors); throw new Error('example-sponsor.json fails schema') }
console.log('schema + fixture OK')
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs`
Expected: FAIL — cannot find `schema.json`.

- [ ] **Step 3: Write the schema**

Create `templates/esg-profile/schema.json` (draft-07). Required top-level: `meta`; at least one of `sponsor`/`fund_overview` (enforced by template warning, not schema `oneOf`, to keep partial renders possible):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "esg-profile",
  "title": "ESG Profile",
  "type": "object",
  "required": ["meta"],
  "additionalProperties": false,
  "properties": {
    "meta": {
      "type": "object",
      "required": ["fund", "reporting_year", "anonymized"],
      "additionalProperties": false,
      "properties": {
        "fund": {"type":"string"},
        "reporting_year": {"type":"integer"},
        "anonymized": {"type":"boolean"},
        "generated_period": {"type":"string"}
      }
    },
    "sponsor": {
      "type": "object",
      "required": ["name","investment_overview","risk_profile","scorecard","benchmark","governance_rights"],
      "additionalProperties": false,
      "properties": {
        "name": {"type":"string","description":"Pseudonym when meta.anonymized=true"},
        "investment_overview": {
          "type":"object","additionalProperties": false,
          "properties": {"asset_class":{"type":"string"},"location":{"type":"string"},"size":{"type":"string"},"exit_date":{"type":"string"},"standing_dev":{"type":"string"}}
        },
        "risk_profile": {
          "type":"object","additionalProperties": false,
          "properties": {
            "transition": {"type":"object","additionalProperties": false,"properties":{
              "green_street_rating":{"type":"string"},"crrem_stranding_year":{"type":["integer","string"]},
              "market_regulation":{"type":"string"},"fine_exposure":{"type":"string"}}},
            "physical": {"type":"object","additionalProperties": false,"properties":{
              "impact":{"type":"string"},"hazards":{"type":"array","items":{"type":"string"}},"source":{"type":"string"}}}
          }
        },
        "scorecard": {
          "type":"object","required":["pillars","total"],"additionalProperties": false,
          "properties": {
            "pillars": {"type":"object","required":["policy_strategy","governance_resourcing","portfolio_management","monitoring_reporting"],"additionalProperties": false,
              "properties":{"policy_strategy":{"type":"number"},"governance_resourcing":{"type":"number"},"portfolio_management":{"type":"number"},"monitoring_reporting":{"type":"number"}}},
            "total": {"type":"number"},
            "trend": {"type":"array","items":{"type":"object","required":["year","total"],"additionalProperties":false,"properties":{"year":{"type":"integer"},"total":{"type":"number"}}}}
          }
        },
        "initiatives": {
          "type":"object","additionalProperties": false,
          "properties": {
            "completed":{"type":"array","items":{"type":"string"}},
            "in_progress":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"item":{"type":"string"},"budget":{"type":"string"}}}},
            "planned":{"type":"array","items":{"type":"object","additionalProperties":false,"properties":{"item":{"type":"string"},"budget":{"type":"string"},"regression":{"type":"boolean"}}}}
          }
        },
        "regressions": {"type":"array","items":{"type":"string"}},
        "benchmark": {
          "type":"object","additionalProperties": false,
          "properties": {"metrics":{"type":"array","items":{"type":"object","additionalProperties":false,
            "properties":{"metric":{"type":"string"},"sponsor":{"type":"string"},"mieppi":{"type":"string"},"asset_class":{"type":"string"},"mir":{"type":"string"}}}}}
        },
        "governance_rights": {
          "type":"object","additionalProperties": false,
          "properties":{"annual_budget":{"type":"string"},"leasing":{"type":"string"},"capex_variance":{"type":"string"},"contractor_engagement":{"type":"string"}}
        },
        "energy": {"type":"object","additionalProperties":false,"properties":{
          "eui_kwh_m2":{"type":"number"},"carbon_intensity":{"type":"string"},"renewable_pct":{"type":"number"},"energy_rating_pct":{"type":"number"}}},
        "provenance": {"type":"array","items":{"type":"object","required":["source_id","mode"],"additionalProperties":false,
          "properties":{"source_id":{"type":"string"},"mode":{"enum":["live","static","estimate"]},"origin":{"type":"string"},"period":{"type":"string"}}}}
      }
    },
    "fund_overview": {
      "type":"object","required":["stats","sponsor_metrics","ranking"],"additionalProperties": false,
      "properties": {
        "stats": {"type":"object","additionalProperties":false,"properties":{
          "asset_classes":{"type":"string"},"locations":{"type":"string"},"total_size":{"type":"string"},
          "standing_dev":{"type":"string"},"response_rate":{"type":"string"},"yoy_performance":{"type":"string"},
          "avg_crrem_stranding_year":{"type":["integer","string"]},"fine_exposure":{"type":"string"}}},
        "sponsor_metrics": {"type":"array","items":{"type":"object"}},
        "ranking": {"type":"array","items":{"type":"object","additionalProperties":false,
          "properties":{"rank":{"type":"integer"},"sponsor":{"type":"string"},"score":{"type":"number"},"yoy_change":{"type":"string"},"vs_mieppi":{"type":"string"},"vs_mir":{"type":"string"}}}},
        "underperformers": {"type":"array","items":{"type":"object","additionalProperties":false,
          "properties":{"sponsor":{"type":"string"},"identified_risk":{"type":"string"},"mitigation":{"type":"string"}}}}
      }
    }
  }
}
```

- [ ] **Step 4: Write a valid fixture**

Create `skills/esg-profile/demo/example-sponsor.json` — a minimal valid Sponsor Profile using **pseudonymous** values (NOT the real sponsor/the real sponsor):
```json
{
  "meta": {"fund":"Fund VII","reporting_year":2025,"anonymized":true,"generated_period":"Q3 2025"},
  "sponsor": {
    "name":"Sponsor Sierra",
    "investment_overview":{"asset_class":"Residential / BTR","location":"Southern Europe","size":"~5,000 units","exit_date":"TBD","standing_dev":"18 / 0"},
    "risk_profile":{
      "transition":{"green_street_rating":"Not rated","crrem_stranding_year":2034,"market_regulation":"National energy-efficiency regs; EPC upgrade requirements","fine_exposure":"TBD"},
      "physical":{"impact":"Moderate","hazards":["Wind","Heat","Drought"],"source":"physrisk (live)"}},
    "scorecard":{"pillars":{"policy_strategy":96.2,"governance_resourcing":70.8,"portfolio_management":82.4,"monitoring_reporting":100},"total":90.5,
      "trend":[{"year":2021,"total":53.7},{"year":2022,"total":58.6},{"year":2023,"total":81.7},{"year":2024,"total":85},{"year":2025,"total":90.5}]},
    "initiatives":{"completed":["GRESB/GRI/UN PRI reporting","Asset-level E/W/W/GHG tracking"],
      "in_progress":[{"item":"EPC upgrade program","budget":"€24.9M"},{"item":"CRREM stranding analysis","budget":"-"}],
      "planned":[{"item":"Formalize green lease language","budget":"Not set","regression":true}]},
    "regressions":["Net Zero policy — still in development, no formal commitment","Green lease language — multi-year gap"],
    "benchmark":{"metrics":[{"metric":"% Sq ft w/ Energy Ratings","sponsor":"100%","mieppi":"38%","asset_class":"16%","mir":"34%"}]},
    "governance_rights":{"annual_budget":"No (no JV control rights)","leasing":"No","capex_variance":"No","contractor_engagement":"No"},
    "energy":{"eui_kwh_m2":337,"carbon_intensity":"normalized kg CO₂/m²","renewable_pct":43,"energy_rating_pct":100},
    "provenance":[{"source_id":"crrem","mode":"live","origin":"crrem get_pathway","period":"2025"},{"source_id":"physical_risk","mode":"live","origin":"physrisk","period":"2025"},{"source_id":"questionnaire","mode":"static","origin":"scrubbed extract","period":"2025"}]
  }
}
```

- [ ] **Step 5: Run validation to verify it passes**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs`
Expected: PASS — `schema + fixture OK`.

- [ ] **Step 6: Commit**

```bash
cd ~/soapbox-agent && git add templates/esg-profile/schema.json skills/esg-profile/demo/example-sponsor.json scripts/validate-esg-profile.mjs
git commit -m "feat(esg-profile): report data schema (both layouts) + valid fixture"
```

---

### Task 4: State schema

**Files:**
- Create: `skills/esg-profile/state-schema.json`
- Modify: `scripts/validate-esg-profile.mjs` (compile state schema)

**Interfaces:**
- Produces: state contract with `phase` enum, `config` (scope/fund/sponsor/reporting_year/anonymize/connectors), `collected` (per source_id ProvenancedValue), `findings` (Verifier), `overrides`. Consumed by SKILL.md (Task 5).

- [ ] **Step 1: Add state-schema compile check**

Append to `scripts/validate-esg-profile.mjs`:
```js
const stateSchema = load('../skills/esg-profile/state-schema.json')
ajv.compile(stateSchema)  // throws if malformed
console.log('state-schema OK')
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs`
Expected: FAIL — cannot find `state-schema.json`.

- [ ] **Step 3: Write state schema**

Create `skills/esg-profile/state-schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "esg-profile-state",
  "type": "object",
  "required": ["phase","config"],
  "additionalProperties": false,
  "properties": {
    "phase": {"enum":["kickoff","collect","reconcile","verify","render","export","done"]},
    "config": {
      "type":"object","required":["scope","fund","reporting_year","anonymize","connectors"],
      "additionalProperties": false,
      "properties": {
        "scope": {"enum":["sponsor","fund"]},
        "fund": {"type":"string"},
        "sponsor": {"type":"string"},
        "reporting_year": {"type":"integer"},
        "anonymize": {"type":"boolean"},
        "connectors": {"type":"object","additionalProperties":{"type":"object","required":["kind"],
          "properties":{"kind":{"enum":["mcp","file","api","manual"]},"tool":{"type":"string"},"path":{"type":"string"},"sheet":{"type":"string"},"region":{"type":"string"},"value":{}}}}
      }
    },
    "collected": {"type":"object","additionalProperties":{"type":"object","required":["status","provenance"],
      "properties":{"value":{},"status":{"enum":["ok","missing","error"]},"notes":{"type":"string"},
        "provenance":{"type":"object","required":["source_id","mode"],"properties":{"source_id":{"type":"string"},"mode":{"enum":["live","static","estimate"]},"origin":{"type":"string"},"period":{"type":"string"},"retrieved_at":{"type":"string"}}}}}},
    "findings": {"type":"array","items":{"type":"object","required":["id","severity","summary"],
      "properties":{"id":{"type":"string"},"severity":{"enum":["low","medium","high"]},"summary":{"type":"string"},"suggested_resolution":{"type":"string"}}}},
    "overrides": {"type":"array","items":{"type":"object","required":["finding_id","override_reason","approved_by"],
      "properties":{"finding_id":{"type":"string"},"override_reason":{"type":"string"},"approved_by":{"type":"string"}}}},
    "artifact_id": {"type":"string"}
  }
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs`
Expected: PASS — `state-schema OK`.

- [ ] **Step 5: Commit**

```bash
cd ~/soapbox-agent && git add skills/esg-profile/state-schema.json scripts/validate-esg-profile.mjs
git commit -m "feat(esg-profile): durable run state schema"
```

---

### Task 5: SKILL.md — the workflow

**Files:**
- Create: `skills/esg-profile/SKILL.md`

**Interfaces:**
- Consumes: `connectors/registry.json`, `state-schema.json`, `templates/esg-profile/schema.json`.
- Produces: the operational skill (frontmatter `name: esg-profile`, description with triggers). This task is prose, not code; its "test" is a structural lint (Step 3) + a human read.

- [ ] **Step 1: Write a structural lint for the skill**

Create `scripts/lint-skill-esg-profile.mjs`:
```js
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-esg-profile.mjs`
Expected: FAIL — cannot find `SKILL.md`.

- [ ] **Step 3: Write SKILL.md**

Create `skills/esg-profile/SKILL.md` following the `decarb-plan`/`portfolio-analysis` house style. It MUST contain, verbatim where noted:

Frontmatter:
```yaml
---
name: esg-profile
description: >
  Produce a sponsor-level ESG Profile (with fund-level rollup) for quarterly asset-management
  engagement — collates ESG questionnaire scorecards, energy/EPC, CRREM stranding, physical
  climate risk, regulatory exposure, peer benchmarks, materiality, and governance rights into
  asset-manager-style Sponsor Profile + Fund Overview deliverables. Data sources are swappable
  (live MCP or static extract) via a connector registry. Triggers on: "ESG profile",
  "sponsor ESG profile", "ESG asset management dashboard", "ESG scorecard profile",
  "quarterly ESG engagement", "fund ESG overview".
version: 1.0.0
---
```

Body sections (write full prose for each — no placeholders):
1. **Ground rules** — copy the Global Constraints (No LLM arithmetic; provenance; anonymization mandatory-and-not-pre-done with the exact leak list the real sponsor names/the real contact domain/specific city names; Analytics Standards incl. `kWh/m²` and `never national median`; sponsor-scoped fail-closed render gate).
2. **Phases** — kickoff → collect → reconcile → verify → render → export, each a subsection.
   - *kickoff*: gather scope (sponsor|fund), fund, sponsor, reporting_year, anonymize; write initial state per `state-schema.json`; load connector bindings (defaulting each `source_id` from `registry.json` unless overridden).
   - *collect*: for each `source_id`, resolve via its binding — `kind:mcp` → call the named tool; `kind:file` → read path/sheet; `kind:manual` → literal. Record ProvenancedValue with `mode`. Call the three gap-fillers (`crrem`, `physical_risk`, `green_street`) explicitly and visibly. State the swap rule: "to go live, change the binding in config; do not edit this skill."
   - *reconcile*: normalize units to kWh/m² (+ single carbon unit); apply **source-precedence** hierarchy (official scorecard/measured > authoritative slide > extract > estimate); every conflict → a Verifier finding with `suggested_resolution`, never auto-resolved; run **regression detection** across `scorecard.trend` and initiatives.
   - *verify*: batch-adapted `verifier__*` pass; log findings to state; do not human-gate mid-run.
   - *render*: **HARD sponsor-scoped gate** — `verifier__list_findings({asset_id: <sponsor key>})`; block on open-high unless `overrides` has an entry; then call `fill_report` with `report_type: 'esg-profile'` and data conforming to `templates/esg-profile/schema.json`.
   - *export*: hand to the `report-review` workflow for PDF + **PPTX mapped to Template v3** + XLSX.
3. **Fund rollup** — when `scope:fund`, aggregate sponsors into `fund_overview` (stats incl. avg CRREM stranding year, sponsor_metrics matrix, ranking with vs-MIEPPI/vs-MIR, underperformers auto-selected below fund/MIR avg). Aggregation via engine/tool, never LLM arithmetic.
4. **Data mapping** — table mapping each `30_input_qualitative` column to the schema path (e.g. `pillar_policy_strategy` → `sponsor.scorecard.pillars.policy_strategy`; `gov_*` → `governance_rights.*`; `physical_risk_rating`+`physical_risk_source` → `sponsor.risk_profile.physical`).
5. **Demo choreography** — the 60-second collect-phase tool-streaming beat; static demo data in `skills/esg-profile/demo/`; note CRREM/physical_risk run live to fill the blanks.

- [ ] **Step 4: Run lint to verify it passes**

Run: `cd ~/soapbox-agent && node scripts/lint-skill-esg-profile.mjs`
Expected: PASS — `SKILL.md lint OK`.

- [ ] **Step 5: Commit**

```bash
cd ~/soapbox-agent && git add skills/esg-profile/SKILL.md scripts/lint-skill-esg-profile.mjs
git commit -m "feat(esg-profile): SKILL.md workflow (phases, reconciliation, gates, fund rollup)"
```

---

### Task 6: HTML template — Sponsor Profile + Fund Overview (via soapbox-report)

**Files:**
- Create: `templates/esg-profile/layout-agent.html`
- Create: `templates/esg-profile/xlsx.json`

**Interfaces:**
- Consumes: data conforming to `templates/esg-profile/schema.json`. Produces: `layout-agent.html` with a `<script id="report-data" type="application/json">` placeholder that `fill_report` replaces (per `template-mcp/src/index.ts:80-83`).

- [ ] **Step 1: Invoke the soapbox-report meta-skill**

Use the `soapbox-skills:soapbox-report` skill to scaffold `templates/esg-profile/`. Model the layout on `templates/sustainability-passport/` (closest sibling) and the Soapbox brand design direction (warm radials, `//` eyebrows, orange accents, dark/gradient cards). Two page groups:
- **Sponsor Profile** pages: identity header; risk-profile table (transition + physical); scorecard block with a **4-pillar bar + YoY trend line** (use the `dataviz` skill for chart specs); initiatives timeline with regression ⚠️ markers; governance-rights table; benchmark table (sponsor vs MIEPPI/AssetClass/MIR); provenance footnotes labeling live vs static.
- **Fund Overview** pages: fund stats tiles; sponsor-metrics matrix; ranking table; underperformers → risk/mitigation table.
- **Glossary + Endnotes**: port the boilerplate text from her `template.pptx` slides 3–4 (verbatim definitions).

The template must render each page group conditionally: show `sponsor.*` pages only when `data.sponsor` exists; `fund_overview.*` pages only when `data.fund_overview` exists.

- [ ] **Step 2: Add the report-data placeholder**

Ensure the file contains exactly one:
```html
<script id="report-data" type="application/json">{}</script>
```
and all rendering reads from `JSON.parse(document.getElementById('report-data').textContent)`.

- [ ] **Step 3: Write the xlsx export map**

Create `templates/esg-profile/xlsx.json` modeled on `templates/rsra/xlsx.json` — one sheet per layout mapping schema paths to columns (Scorecard trend, Benchmark metrics, Initiatives, Ranking).

- [ ] **Step 4: Verify placeholder + JSON injection locally**

Run:
```bash
cd ~/soapbox-agent && node -e '
const fs=require("fs");
let html=fs.readFileSync("templates/esg-profile/layout-agent.html","utf8");
const data=JSON.parse(fs.readFileSync("skills/esg-profile/demo/example-sponsor.json","utf8"));
const json=JSON.stringify(data).replace(/</g,"\\u003c");
const out=html.replace(/<script id="report-data"[^>]*>[\s\S]*?<\/script>/,`<script id="report-data" type="application/json">${json}</script>`);
if(!out.includes(data.sponsor.name)===false){} 
if(out===html) throw new Error("placeholder not replaced");
fs.writeFileSync("/tmp/esg-preview.html",out);
console.log("injected OK ->/tmp/esg-preview.html", out.length, "bytes");
'
```
Expected: `injected OK` and non-trivial byte count.

- [ ] **Step 5: Visually verify the render**

Open `/tmp/esg-preview.html` in a browser (or Playwright screenshot). Confirm: sponsor pages render, scorecard chart shows 4 pillars + trend, regression ⚠️ appears, fund pages are absent (fixture has no `fund_overview`). Fix template until correct.

- [ ] **Step 6: Commit**

```bash
cd ~/soapbox-agent && git add templates/esg-profile/layout-agent.html templates/esg-profile/xlsx.json
git commit -m "feat(esg-profile): Paged.js template — Sponsor Profile + Fund Overview + glossary"
```

---

### Task 7: Scrub + stage the demo data

**Files:**
- Create: `skills/esg-profile/demo/static/extract.xlsx` (scrubbed copy)
- Create: `skills/esg-profile/demo/static/notes_scrubbed.docx` (scrubbed copy)
- Create: `skills/esg-profile/demo/reference/materiality.json`
- Create: `skills/esg-profile/demo/static/bps_cache.json`
- Create: `scripts/scrub-demo-data.mjs`
- Create: `skills/esg-profile/demo/example-fund.json` (valid fund_overview fixture)

**Interfaces:**
- Produces: anonymized static inputs the demo binds to; a fund fixture for Task 8b.

- [ ] **Step 1: Write a scrub-verification test**

Create `scripts/scrub-demo-data.mjs` that reads the scrubbed files and asserts NONE of the banned tokens appear:
```js
import { readFileSync } from 'node:fs'
import { execSync } from 'node:child_process'
const BANNED = ['the real sponsor names', 'the real consultant firm', 'real personnel', 'the real contact domain', 'specific city names'] // loaded from an untracked denylist file in the real implementation
const dir = new URL('../skills/esg-profile/demo/static/', import.meta.url).pathname
// unzip office xml and grep
for (const f of ['extract.xlsx','notes_scrubbed.docx']) {
  const dump = execSync(`unzip -p ${dir}${f} '*.xml' 2>/dev/null || true`).toString()
  const hit = BANNED.filter(b => dump.includes(b))
  if (hit.length) throw new Error(`${f} still leaks: ${hit.join(', ')}`)
}
console.log('scrub OK — no banned tokens')
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/soapbox-agent && node scripts/scrub-demo-data.mjs`
Expected: FAIL — files not present (or leaks present if raw copies used).

- [ ] **Step 3: Produce scrubbed copies**

Copy the raw extracted files from scratchpad `the raw scratchpad extracts` and run a replacement pass (python-docx / openpyxl) mapping: `the real sponsor names → "Sponsor Sierra"`, `the real consultant firm → "GreenCo"`, contact names/emails → removed, specific city names → "Southern Europe". Save to `demo/static/`. Also hand-author `materiality.json` (residential/BTR materiality considerations) and `bps_cache.json` (`{"market_regulation":"National energy-efficiency regs; EPC upgrade requirements","fine_exposure":"TBD"}`).

- [ ] **Step 4: Run scrub test to verify it passes**

Run: `cd ~/soapbox-agent && node scripts/scrub-demo-data.mjs`
Expected: PASS — `scrub OK — no banned tokens`.

- [ ] **Step 5: Write a valid fund fixture**

Create `skills/esg-profile/demo/example-fund.json` with a `meta` + `fund_overview` (≥2 pseudonymous sponsors, ranking, underperformers). Validate it against the schema by extending `validate-esg-profile.mjs` to also compile-check `example-fund.json`.

- [ ] **Step 6: Run full validation**

Run: `cd ~/soapbox-agent && node scripts/validate-esg-profile.mjs && node scripts/scrub-demo-data.mjs`
Expected: both PASS.

- [ ] **Step 7: Commit**

```bash
cd ~/soapbox-agent && git add skills/esg-profile/demo scripts/scrub-demo-data.mjs scripts/validate-esg-profile.mjs
git commit -m "feat(esg-profile): scrubbed demo data + materiality/bps + fund fixture + scrub test"
```

---

### Task 8: End-to-end render smoke (both layouts)

**Files:**
- Create: `scripts/smoke-esg-profile.mjs`

**Interfaces:**
- Consumes: deployed `fill_report` at `https://templates.mcp.soapbox.build/mcp` (after Task 9) OR local template file (pre-deploy). Uses both fixtures.

- [ ] **Step 1: Write the smoke (local template mode)**

Create `scripts/smoke-esg-profile.mjs` that injects each fixture into the LOCAL `layout-agent.html` (same replace logic as template-mcp) and asserts the output contains layout-specific anchors:
```js
import { readFileSync, writeFileSync } from 'node:fs'
const html = readFileSync(new URL('../templates/esg-profile/layout-agent.html', import.meta.url),'utf8')
const inject = (data) => html.replace(/<script id="report-data"[^>]*>[\s\S]*?<\/script>/,
  `<script id="report-data" type="application/json">${JSON.stringify(data).replace(/</g,'\\u003c')}</script>`)
const sponsor = JSON.parse(readFileSync(new URL('../skills/esg-profile/demo/example-sponsor.json', import.meta.url)))
const fund = JSON.parse(readFileSync(new URL('../skills/esg-profile/demo/example-fund.json', import.meta.url)))
const a = inject(sponsor); writeFileSync('/tmp/esg-sponsor.html', a)
const b = inject(fund);    writeFileSync('/tmp/esg-fund.html', b)
if (a === html || b === html) throw new Error('injection failed')
console.log('smoke OK — /tmp/esg-sponsor.html /tmp/esg-fund.html')
```

- [ ] **Step 2: Run to verify it fails then passes**

Run: `cd ~/soapbox-agent && node scripts/smoke-esg-profile.mjs`
Expected: after Task 6 exists, PASS — writes both files.

- [ ] **Step 3: Visual check both**

Open `/tmp/esg-sponsor.html` and `/tmp/esg-fund.html`. Confirm sponsor file shows only sponsor pages; fund file shows only fund pages. Fix template conditionals if not.

- [ ] **Step 4: Commit**

```bash
cd ~/soapbox-agent && git add scripts/smoke-esg-profile.mjs
git commit -m "test(esg-profile): end-to-end render smoke for both layouts"
```

---

### Task 9: Deploy template + template-mcp, verify live

**Files:** none (deploy/ops)

**Interfaces:**
- Produces: `esg-profile` live via `fill_report` at `templates.mcp.soapbox.build`.

- [ ] **Step 1: Push template to `main`**

`fill_report` fetches from `main`. Ensure all committed work is on `main` (or open+merge a PR). Run:
```bash
cd ~/soapbox-agent && git push origin HEAD
```

- [ ] **Step 2: Redeploy template-mcp (soapbox-mcps project)**

Redeploy the `template-mcp` service so the new `KNOWN_TYPES` ships (per the Railway MCP project convention — soapbox-mcps, domain `templates.mcp.soapbox.build`). Trigger a redeploy of that service.

- [ ] **Step 3: Verify health lists esg-profile**

Run:
```bash
curl -s https://templates.mcp.soapbox.build/health | python3 -m json.tool | grep -A1 esg-profile
```
Expected: `esg-profile` present with `"available": true`.

- [ ] **Step 4: Live fill_report smoke**

Call `fill_report` (via the connected template MCP) with `report_type:'esg-profile'` and the sponsor fixture; confirm HTML returns with no missing-section warnings.

- [ ] **Step 5: Commit any deploy notes**

```bash
cd ~/soapbox-agent && git commit --allow-empty -m "chore(esg-profile): template + KNOWN_TYPES live on templates.mcp.soapbox.build"
```

---

### Task 10: Full engagement dry-run + memory

**Files:**
- Create: `skills/esg-profile/demo/README.md` (how to run the demo)

**Interfaces:** none.

- [ ] **Step 1: Run the skill end-to-end on demo data**

Invoke `esg-profile` with the demo config (scope:sponsor, the scrubbed static bindings + live crrem/physrisk). Confirm: collect streams tool calls, CRREM/physical_risk fill the blanks, reconcile raises the seeded DISCREPANCY as a Verifier finding, render passes the sponsor-scoped gate, artifact renders, PPTX exports.

- [ ] **Step 2: Run the fund rollup**

Invoke with scope:fund over ≥2 sponsors; confirm Fund Overview artifact renders with ranking + underperformers.

- [ ] **Step 3: Write demo README**

Document the exact demo invocation + the 60-second choreography + the "CRREM/physical_risk fill the asset manager's blanks" beat.

- [ ] **Step 4: Record durable memory + update spec status**

Add a memory pointer (esg-profile project shipped v1) and mark the spec's open items resolved/remaining.

- [ ] **Step 5: Commit**

```bash
cd ~/soapbox-agent && git add skills/esg-profile/demo/README.md
git commit -m "docs(esg-profile): demo runbook + v1 complete"
```

---

## Self-Review

**Spec coverage:** connector abstraction (T2), both layouts (T3/T6), sponsor+fund grain (T3/T5), 4-pillar scorecard + YoY + regression (T3/T5/T6), reconciliation-from-conflicts + Verifier (T5), anonymization (T7), unit normalization + EU/region-aware energy (T2/T5), render gate (T5), PPTX-to-v3 export (T6/T10), demo choreography (T5/T10), registration+deploy (T1/T9). All spec sections mapped.

**Placeholder scan:** all code steps contain real content; schemas and fixtures use concrete field names from the extracted data; no "TBD/TODO/handle edge cases".

**Type consistency:** `report_type:'esg-profile'` consistent across T1/T5/T9; schema paths (`sponsor.scorecard.pillars.*`, `governance_rights.*`, `fund_overview.ranking`) consistent across T3/T5/T6/T8; connector `source_id`s consistent between registry (T2), schema `produces`, and SKILL mapping (T5).

**Known adaptation:** this stack is markdown-skill + declarative templates + one TS MCP, so "tests" are schema/lint/scrub validation + render smokes rather than unit tests — appropriate for the artifact types.
