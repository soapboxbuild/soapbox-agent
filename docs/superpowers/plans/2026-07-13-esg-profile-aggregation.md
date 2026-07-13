# ESG Profile Aggregation (Katie/Madison) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend reproduce Madison's manual ESG aggregation — an automated fund-overview + per-sponsor investment ESG Profile (template v3) — then capture it as a live recorded run and re-freeze the demo's `esg` replay fixture.

**Architecture:** Two new spoof-backed MCP connectors (First Street, Microsoft Fabric) fill the `physical_risk` and `questionnaire`/`investment_info`/`governance` slots the esg-profile `registry.json` already declares. The esg-profile skill already specs the full pipeline incl. `fund_overview`; the real gap is multi-sponsor *data*, so we author a spoofed peer-sponsor fund dataset and run `scope: fund`. Materiality moves from a frozen static file to a shared reference owned by the verifier MCP (bank `soapbox-expertise`), read via `verifier__recall_expertise` for generation and by a new verifier render-gate for enforcement. Finally capture the golden run in a NON-demo org and re-freeze `esg.json`.

**Tech Stack:** TypeScript, `@modelcontextprotocol/sdk`, Express + `StreamableHTTPServerTransport` (per-request server), Zod, Railway (`soapbox-mcps` project → `<name>.mcp.soapbox.build`), Supabase (`asset_connectors`), the RSRA scripted-replay pipeline (`build-fixture-from-run.mjs`), hindsight banks.

## Global Constraints

- **MCP repos:** one repo per MCP under `~/`; model First Street on `~/physrisk-mcp`, Fabric on `~/energy-star-mcp`; use the **`~/oyster-mcp` `stubResponse()` spoof pattern** for both (ship tool surface + demo data before real API/creds).
- **Server pattern (verbatim from existing MCPs):** stateless Express; fresh `McpServer` + client **per request**; `StreamableHTTPServerTransport({ sessionIdGenerator: undefined })`; `/health` returns `{ok:true, service}`; POST `/mcp`. Tool signature `server.tool(name, description, zodShape, handler)`, handler returns `{ content: [{ type:'text', text }] }`.
- **Deploy:** `railway.toml` (`startCommand "node dist/index.js"`, `healthcheckPath "/health"`) + `nixpacks.toml` (`nodejs_22`, `npm install --include=dev && npm run build`), Railway service in the `soapbox-mcps` project, domain `<name>.mcp.soapbox.build`. Set Cloudflare CNAME manually after `customDomainCreate`.
- **When cloning a repo, fix stale metadata:** `.mcp.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `package.json` name, `/health` service string, README (cloned repos carry the source's identifiers).
- **esg-profile connector registry:** `~/soapbox-agent/skills/esg-profile/connectors/registry.json` maps `source_id → {kind, tool}`. To wire a connector, edit the registry entry — never edit the skill body.
- **Materiality access:** the shared materiality reference lives in the verifier's `soapbox-expertise` bank; reach it via `verifier__recall_expertise` (an agent-reachable verifier MCP tool) — **NOT** via `plugin_memory` (force-pinned to `org-<id>`, cannot address a shared bank).
- **Anonymize + scrub:** sponsor identity anonymized (Azora/Nestar → pseudonym); every frozen fixture passes `demo-staging/scrub-check.py` (fail-closed).
- **Capture in a NON-demo org:** the deployed scripted-replay intercepts any Demo-org classified prompt and would replay the stale `esg.json`. Capture the golden run in a non-demo org (or the source asset), then re-freeze.
- **Fixture build:** `esg.json` lives at `soapbox-platform/apps/api/src/services/demo-fixtures/esg.json`; the API build copies fixtures into `dist` (fixed 2026-07-13, `postbuild.mjs`).
- **Demo replay note:** connectors + materiality recall fire once during the golden recording and are baked into the fixture — no live-connector/live-recall dependency on stage.

---

# PHASE 1 — Demo-critical path (2 spoof MCPs → peer data → scope:fund run → record → re-freeze)

### Task 1: First Street MCP (spoof-backed)

**Files:**
- Create repo: `~/firststreet-mcp/` (clone structure of `~/physrisk-mcp`)
- Create: `~/firststreet-mcp/src/index.ts`, `~/firststreet-mcp/src/fixtures.ts`, `package.json`, `tsconfig.json`, `railway.toml`, `nixpacks.toml`, `.mcp.json`, `README.md`
- Test: `~/firststreet-mcp/src/__tests__/tools.test.ts`

**Interfaces:**
- Produces MCP tool `get_property_risk({ address?: string, lat?: number, lon?: number })` → JSON shaped to First Street's public risk-summary structure: `{ location, factors: { flood:{score,label}, heat:{...}, wind:{...}, fire:{...}, drought:{...} }, overall: { rating, primary_perils: string[] } }`. This satisfies the esg-profile `physical_risk` contract (`{physical_impact:string, hazards:array}`).

- [ ] **Step 1: Scaffold from physrisk-mcp**

```bash
cp -r ~/physrisk-mcp ~/firststreet-mcp && cd ~/firststreet-mcp
rm -rf .git node_modules dist && git init -q
# strip any physrisk live-API client; we ship spoof-only
```

- [ ] **Step 2: Write the failing test**

```ts
// ~/firststreet-mcp/src/__tests__/tools.test.ts
import { describe, it, expect } from 'vitest'
import { firstStreetRisk } from '../fixtures.js'
describe('firstStreetRisk', () => {
  it('returns First-Street-shaped risk for the demo sponsor address', () => {
    const r = firstStreetRisk({ address: '4400 Prairie Crossing, Prairieton TX' })
    expect(r.overall.rating).toBeTypeOf('string')
    expect(Array.isArray(r.overall.primary_perils)).toBe(true)
    expect(r.factors.flood.score).toBeTypeOf('number')
    expect(Object.keys(r.factors)).toEqual(expect.arrayContaining(['flood','heat','wind','fire','drought']))
  })
})
```

- [ ] **Step 3: Run test → FAIL** — `cd ~/firststreet-mcp && npx vitest run` → cannot find `../fixtures.js`.

- [ ] **Step 4: Implement `src/fixtures.ts`** (spoof data shaped to First Street; Spain/BTR-appropriate perils for the Azora sponsor + neutral defaults)

```ts
// ~/firststreet-mcp/src/fixtures.ts
export type FSRisk = {
  location: string
  factors: Record<'flood'|'heat'|'wind'|'fire'|'drought', { score: number; label: string }>
  overall: { rating: string; primary_perils: string[] }
}
const L = (s: number) => (s >= 8 ? 'Severe' : s >= 5 ? 'Major' : s >= 3 ? 'Moderate' : 'Minimal')
export function firstStreetRisk(q: { address?: string; lat?: number; lon?: number }): FSRisk {
  // Demo sponsor portfolio is Spanish residential/BTR → wind/heat/drought material, flood/fire low.
  const f = { flood: 2, heat: 6, wind: 6, fire: 3, drought: 6 }
  return {
    location: q.address ?? `${q.lat},${q.lon}`,
    factors: Object.fromEntries(Object.entries(f).map(([k, v]) => [k, { score: v, label: L(v) }])) as FSRisk['factors'],
    overall: { rating: 'Moderate', primary_perils: ['Wind', 'Heat', 'Drought'] },
  }
}
```

- [ ] **Step 5: Implement `src/index.ts`** (Express + per-request MCP, one tool, spoof handler — model on `~/physrisk-mcp/src/index.ts` and `~/oyster-mcp` stub pattern)

```ts
import express from 'express'
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'
import { z } from 'zod'
import { firstStreetRisk } from './fixtures.js'
const app = express(); app.use(express.json())
app.get('/health', (_req, res) => res.json({ ok: true, service: 'firststreet-mcp' }))
app.post('/mcp', async (req, res) => {
  const server = new McpServer({ name: 'firststreet-mcp', version: '1.0.0' })
  server.tool('get_property_risk',
    'First Street physical climate risk summary for a property (peril-level scores + overall rating).',
    { address: z.string().optional(), lat: z.number().optional(), lon: z.number().optional() },
    (p) => ({ content: [{ type: 'text', text: JSON.stringify(firstStreetRisk(p)) }] }))
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined })
  res.on('close', () => { server.close().catch(() => {}) })
  await server.connect(transport)
  await transport.handleRequest(req, res, req.body)
})
const port = Number(process.env.PORT ?? 8080)
app.listen(port, () => console.log(`firststreet-mcp on ${port}`))
```

- [ ] **Step 6: Run test → PASS**, then `npm run build` (tsc) → no errors.
- [ ] **Step 7: Local smoke** — `node dist/index.js &` then `curl -s localhost:8080/health` → `{"ok":true,...}`; a `tools/call` for `get_property_risk` returns the JSON. Kill the process.
- [ ] **Step 8: Fix cloned metadata** (`.mcp.json` url → `https://firststreet.mcp.soapbox.build/mcp`; `.claude-plugin/plugin.json` name/description; `package.json` name `firststreet-mcp`; README).
- [ ] **Step 9: Commit** — `git add -A && git commit -m "feat: First Street physical-risk MCP (spoof-backed)"`.
- [ ] **Step 10: Deploy to Railway `soapbox-mcps`** — `railway up` (link to soapbox-mcps project, new service `firststreet-mcp`), add domain, set Cloudflare CNAME. Verify `curl https://firststreet.mcp.soapbox.build/health`.

---

### Task 2: Microsoft Fabric MCP (spoof-backed)

**Files:**
- Create repo: `~/fabric-mcp/` (clone `~/energy-star-mcp` structure; spoof via oyster pattern)
- Create: `~/fabric-mcp/src/index.ts`, `~/fabric-mcp/src/fixtures.ts`, config files as Task 1
- Test: `~/fabric-mcp/src/__tests__/tools.test.ts`

**Interfaces:**
- Produces three MCP tools, shaped to a Fabric Data-Agent/warehouse query result:
  - `get_questionnaire_responses({ sponsor: string, year: number })` → the GRESB-style questionnaire answers (pillars, policies, initiatives) for the sponsor-year.
  - `get_investment_info({ sponsor: string })` → `{ asset_class, location, size_sqft, projected_exit, standing_assets, developments }`.
  - `get_governance_rights({ sponsor: string })` → `{ annual_budget, leasing, capex_variance, contractor_engagement }` (each Yes/No/"Not provided").
- Satisfies esg-profile `questionnaire`, `investment_info`, `governance` contracts.

- [ ] **Step 1: Scaffold** — `cp -r ~/energy-star-mcp ~/fabric-mcp`; `rm -rf .git node_modules dist src/espm-client.ts src/cbecs-benchmarks.ts`; `git init -q`.

- [ ] **Step 2: Write the failing test**

```ts
// ~/fabric-mcp/src/__tests__/tools.test.ts
import { describe, it, expect } from 'vitest'
import { questionnaire, investment, governance } from '../fixtures.js'
describe('fabric fixtures', () => {
  it('questionnaire has pillar scores for the demo sponsor-year', () => {
    const q = questionnaire('Azora', 2025)
    expect(q.pillars.policy_strategy).toBeTypeOf('number')
    expect(q.pillars.monitoring_reporting).toBe(100)
  })
  it('investment info returns the shape the skill expects', () => {
    expect(Object.keys(investment('Azora'))).toEqual(
      expect.arrayContaining(['asset_class','location','size_sqft','projected_exit','standing_assets','developments']))
  })
  it('governance rights all "Not provided" for a no-control JV', () => {
    expect(governance('Azora').annual_budget).toMatch(/not provided/i)
  })
})
```

- [ ] **Step 3: Run test → FAIL.**

- [ ] **Step 4: Implement `src/fixtures.ts`** — spoof records for the demo sponsor + peers, drawn from the real engagement notes (pillars 2025: policy 96.2, governance 70.83, portfolio 82.41, monitoring 100; total 90.45). Pseudonymized names.

```ts
// ~/fabric-mcp/src/fixtures.ts
export function questionnaire(sponsor: string, year: number) {
  return { sponsor, year,
    total_score: 90.45,
    pillars: { policy_strategy: 96.2, governance_resourcing: 70.83, portfolio_management: 82.41, monitoring_reporting: 100 },
    initiatives: { completed: ['ENERGY STAR / EPC upgrades (Project EREB)','asset-level E/W/W/GHG tracking, third-party assured'],
                   in_progress: ['CRREM stranding analysis','gas-to-electric / aerothermal switching','Net Zero policy development'],
                   planned: ['Formalize green-lease language','Climate adaptation plan','Embodied-carbon integration'] },
    policies: { environmental: true, social: true, governance: true, green_leases: 'informal only' } }
}
export function investment(sponsor: string) {
  return { sponsor, asset_class: 'Residential / BTR', location: 'Spain', size_sqft: 6_900_000,
    projected_exit: 'Fund VII active; Fund VI exited 2025', standing_assets: 169, developments: 43 }
}
export function governance(sponsor: string) {
  return { sponsor, annual_budget: 'Not provided (no JV control rights)', leasing: 'Not provided (no JV control rights)',
    capex_variance: 'Not provided (no JV control rights)', contractor_engagement: 'Not provided (no JV control rights)' }
}
```

- [ ] **Step 5: Implement `src/index.ts`** — three `server.tool(...)` defs wrapping the fixtures (same Express/per-request pattern as Task 1; `service:'fabric-mcp'`).
- [ ] **Step 6: Run test → PASS; `npm run build`.**
- [ ] **Step 7: Local smoke** (`/health`, one `tools/call` each).
- [ ] **Step 8: Fix cloned metadata** (energy-star identifiers → fabric; url `https://fabric.mcp.soapbox.build/mcp`).
- [ ] **Step 9: Commit** — `feat: Microsoft Fabric MCP (spoof-backed: questionnaire, investment, governance)`.
- [ ] **Step 10: Deploy** to `soapbox-mcps` → `fabric.mcp.soapbox.build`; verify `/health`.

---

### Task 3: Wire connectors into the esg-profile registry + attach to the run portfolio

**Files:**
- Modify: `~/soapbox-agent/skills/esg-profile/connectors/registry.json`
- Ops: `asset_connectors` rows (Supabase) for the capture portfolio

**Interfaces:**
- Consumes: First Street tool `firststreet get_property_risk`; Fabric tools `fabric get_questionnaire_responses|get_investment_info|get_governance_rights`.

- [ ] **Step 1: Repoint the registry adapters** — set `physical_risk.default_live_adapter` to `{"kind":"mcp","tool":"firststreet get_property_risk"}`; `questionnaire` → `{"kind":"mcp","tool":"fabric get_questionnaire_responses"}`; `investment_info` → `{"kind":"mcp","tool":"fabric get_investment_info"}`; `governance` → `{"kind":"mcp","tool":"fabric get_governance_rights"}`. Leave `energy` (ESPM), `green_street`, `gresb`/`peer_benchmark`, `crrem`, `bps` pointing at their existing MCPs.

- [ ] **Step 2: Commit** the registry change (`~/soapbox-agent`): `feat(esg): point physical_risk→First Street, questionnaire/investment/governance→Fabric`.

- [ ] **Step 3: Attach connectors to the capture portfolio** — insert `asset_connectors` rows (scope portfolio) for `firststreet` and `fabric` pointing at their `*.mcp.soapbox.build/mcp` urls. Model on `portfolios.ts` insert; do it via Supabase MCP filtered to the capture portfolio.

- [ ] **Step 4: Verify** — with a fresh thread on the capture asset, confirm the agent lists `firststreet` + `fabric` tools (or check `asset_connectors` rows enabled). Do not run the full profile yet.

---

### Task 4: Spoofed peer-sponsor fund dataset (unblocks fund_overview)

**Files:**
- Create: `~/soapbox-agent/skills/esg-profile/demo/madison/fund-peers.json` (the multi-sponsor input for the Madison fund)
- Reference: existing `skills/esg-profile/demo/example-fund.json` (schema-valid target shape)

**Interfaces:**
- Produces a fund-level dataset the skill's Fund-rollup aggregates into `fund_overview`: `sponsor_metrics[]` rows (keys per `example-fund.json`: `sponsor, green_cert_pct, energy_rating_pct, gresb_status, net_zero_policy_status, energy_data_coverage, renewable_pct, mieppi, mir`), plus the Azora row derived from the connector run.

- [ ] **Step 1: Author `fund-peers.json`** — Azora (pseudonymized) + 3–4 spoofed peers (Sponsor A/B/D/E) with believable, differentiated metrics and a MIR benchmark row, so `ranking[]` and `underperformers[]` are meaningful (Azora ranks near top at 90.45%; ≥1 underperformer). Keep values internally consistent with the template's `stats` (avg CRREM stranding year, response rate, YoY). All names fictional; run `scrub-check.py` on it.

- [ ] **Step 2: Validate the target shape** — `node ~/soapbox-agent/skills/esg-profile/scripts/validate-esg-profile.mjs` against a hand-assembled `fund_overview` built from `fund-peers.json` (asserts schema-valid, ranking ≥2, ≥2 sponsors, ≥1 underperformer). Expected: PASS.

- [ ] **Step 3: Commit** — `feat(esg): spoofed peer-sponsor fund dataset for Madison fund overview`.

---

### Task 5: esg-profile skill — produce fund_overview under scope:fund

**Files:**
- Modify (if needed): `~/soapbox-agent/skills/esg-profile/SKILL.md` (Fund-rollup phase), `state-schema.json`
- Test: `~/soapbox-agent/skills/esg-profile/scripts/smoke-esg-profile.mjs` (existing)

**Interfaces:**
- Consumes: Task 4 `fund-peers.json`; the connector outputs (Tasks 1–3).
- Produces: a `fill_report(esg-profile)` data object with BOTH `sponsor` (Azora deep-dive) and populated `fund_overview`.

- [ ] **Step 1: Confirm the documented Fund-rollup path** — SKILL.md already specifies aggregating `stats/sponsor_metrics/ranking/underperformers` when `config.scope: 'fund'`. Add an explicit instruction: when `scope: 'fund'`, read `fund-peers.json` for peer `sponsor_metrics`, merge the connector-derived Azora row, compute `ranking` + `underperformers`, and set `fund_overview`. Keep the sponsor deep-dive too (combined fund+investment render).
- [ ] **Step 2: Smoke** — run `node skills/esg-profile/scripts/smoke-esg-profile.mjs` and extend/confirm it asserts fund content present. Expected: PASS.
- [ ] **Step 3: Re-sync gate** — null `anthropic_skill_id` on the capture portfolio's `installed_plugins` soapbox-agent row + restart soapbox-api (or `_resync.cjs`) so the managed agent picks up the SKILL.md change. (Template + registry are live-fetched; SKILL.md is the frozen bundle.)
- [ ] **Step 4: Commit** — `feat(esg): scope:fund produces populated fund_overview from peer dataset`.

---

### Task 6: Golden run → verify → record → re-freeze `esg.json`

**Files:**
- Ops; produces `soapbox-platform/apps/api/src/services/demo-fixtures/esg.json` (replaces the meta+sponsor-only fixture)
- Tools: `~/soapbox-agent/demo-staging/build-fixture-from-run.mjs`, `verify-replay.mjs`, `scrub-check.py`

- [ ] **Step 1: Run the profile live in a NON-demo org** — on the capture asset, prompt: "Run the ESG Profile for the Madison fund and the Azora sponsor — fund overview plus the sponsor investment profile." Confirm the agent visibly calls ESPM, GreenStreet, First Street, Fabric, GRESB, CRREM, fines&regs, reconciles the discrepancies, and renders template v3 with a populated fund overview + sponsor profile.
- [ ] **Step 2: Verify the artifact** — `report_data` has `meta` + `sponsor` + `fund_overview` (with `sponsor_metrics[]`, `ranking[]`, `underperformers[]`); the sponsor page has risk profile (First Street physical impact, GreenStreet transition, CRREM stranding), initiatives, governance rights.
- [ ] **Step 3: Scrub-gate** — extract narration + `render.data`, run against the esg denylist; SCRUB CLEAN required (no Azora/Nestar/real names).
- [ ] **Step 4: Build the fixture** — `build-fixture-from-run.mjs --artifact <id> --conversation <id> --workflow esg --target-ms 85000 --out /tmp/esg.json`; validate via the loader (`validateFixture`).
- [ ] **Step 5: Freeze** — copy to `soapbox-platform/apps/api/src/services/demo-fixtures/esg.json`; commit; deploy soapbox-api.
- [ ] **Step 6: E2E on stage path** — `verify-replay.mjs --workflow esg` on a fresh Demo-org thread → confirms the replay now renders the full fund+sponsor profile in ~85s. Clean up throwaway conversations.

---

# PHASE 2 — Materiality reference + verifier gate (production robustness; NOT required for the recorded demo)

> Deferrable: the recorded demo bakes the materiality-informed output into the fixture, so stage does not need live materiality. Phase 2 makes real production runs enforce materiality coverage.

### Task 7: Shared materiality reference (verifier-owned)

**Files:**
- Modify: `~/verifier-mcp/src/expertise.ts` (add a materiality recall), `~/soapbox-agent/skills/esg-profile/connectors/registry.json` (materiality adapter)

- [ ] **Step 1: Seed the materiality reference** into the `soapbox-expertise` bank — the SASB/ISSB real-estate materiality map keyed by asset class × market (e.g. `residential-btr / spain`), each topic `{topic, relevance, rationale}` (seed content = the existing `reference/materiality.json`). Write via the verifier's `retainSharedExpertise` path (or `hindsight__retain` to `soapbox-expertise`) with domain/tier tags.
- [ ] **Step 2: Expose materiality via `verifier__recall_expertise`** — confirm `recall_expertise(query="materiality residential-btr spain")` returns the considerations. (No new tool needed if recall already covers it; else add a thin `recall_materiality` tool in `verifier-mcp/src/index.ts`.)
- [ ] **Step 3: Point the skill's materiality generation at the verifier** — update `registry.json` `materiality` adapter from `{"kind":"file",...}` to `{"kind":"mcp","tool":"verifier recall_expertise"}` (query keyed by asset class + market); keep the file as the demo/offline fallback.
- [ ] **Step 4: Redeploy `verifier-mcp`; commit both repos.**

### Task 8: Verifier materiality-coverage gate

**Files:**
- Create: `~/verifier-mcp/checklists/materiality.json`; Modify: `~/verifier-mcp/src/checklists.ts`
- Modify: `~/soapbox-platform/apps/api/src/services/verification-gate.ts`, `render-report.ts`

- [ ] **Step 1: Add the checklist** — `materiality.json` (model on `regulatory.json`): rubric = "for the investment's asset class + market, the profile addresses each High-materiality topic and flags material regressions"; `auto_fail` = an unaddressed High topic or an unflagged material regression. Register in `checklists.ts` `ALL` map.
- [ ] **Step 2: Add the render gate** — new `evaluateEsgMaterialityGate(mcpServers, assetId, reportData)` in `verification-gate.ts` modeled on `evaluateDecarbVerificationGate`: recall the materiality reference, check the report's `sponsor`/`fund_overview` covers the High topics + flags regressions; fail closed on a gap. Add `esg-profile` to a gated-templates set and wire into `render-report.ts`.
- [ ] **Step 3: Tests** — unit-test the gate: a report missing a High-materiality topic → blocked; a complete report → allowed. (Vitest in soapbox-platform apps/api.)
- [ ] **Step 4: Deploy** — redeploy `verifier-mcp` + `soapbox-api`; null `anthropic_skill_id` + restart for any skill-prose change.
- [ ] **Step 5: Commit** both repos.

---

## Self-Review

**Spec coverage:**
- Connector map (ESPM/GreenStreet/GRESB/CRREM/fines&regs reused; First Street + Fabric new) → Tasks 1–3.
- Fund_overview populated via spoofed peers → Tasks 4–5.
- Materiality shared reference + verifier gate → Tasks 7–8 (Phase 2), with the **access-path correction** (verifier MCP, not org-pinned memory MCP) captured in Global Constraints + Task 7.
- Anonymize/scrub, non-demo-org capture, re-freeze → Task 6 + Global Constraints.
- Non-goals (no production Fabric/First Street wiring; no Paperclip twins; no standalone materiality skill) → respected (spoof-backed; MCP-only; verifier-owned).

**Placeholder scan:** MCP + fixture + gate steps carry real code; ops steps (deploy, attach, capture, freeze) carry exact commands/paths. Peer-dataset authoring (Task 4) is content produced to the `example-fund.json` shape, validated by the existing script.

**Type consistency:** tool names (`firststreet get_property_risk`; `fabric get_questionnaire_responses|get_investment_info|get_governance_rights`) match between the MCP defs (Tasks 1–2) and the registry wiring (Task 3). Fixture shapes match the esg-profile connector `produces` contracts and the `fund_overview` schema (`stats/sponsor_metrics/ranking/underperformers`) used in Tasks 4–6.

## Open decision (surface before executing)
Phase 2 (materiality reference + verifier gate) is **not required to record the demo**. Options: (a) build Phase 1 now, record the demo, do Phase 2 after; (b) build both before recording (materiality then genuinely shapes the recorded narration + is enforced). Recommend (a) for demo timeline.
