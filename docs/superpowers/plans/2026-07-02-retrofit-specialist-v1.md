# Retrofit Specialist v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `retrofit` core plugin: an MCP worker (playbooks, provenance-enforced measure evaluation, three-test screening, per-asset measure register, shared reference library) + persona prompt injection, gated by the verifier and remembered via the memory plugin.

**Architecture:** `retrofit-mcp` is a structural clone of `verifier-mcp` (same auth, tenancy, ledger, and test patterns — copy its modules and adapt rather than re-invent). Judgment lives in `RETROFIT_SPECIALIST_PROMPT` (soapbox-api injection); discipline lives in the MCP: evaluation schema rejects economics without deterministic/cited provenance, exit-value math computed server-side, playbooks are versioned data.

**Tech Stack:** TypeScript, @modelcontextprotocol/sdk ^1.12 + express + zod (verifier pattern), @supabase/supabase-js (service role), hindsight REST (`/v1/default/banks/...`), vitest, Railway (soapbox-mcps).

**Scope:** Spec v1 only. OpenStudio/EnergyPlus hooks, portfolio rollups, Paperclip wrapper are OUT.

## Global Constraints

- Reference implementation: `/home/claude/verifier-mcp` — copy `src/index.ts` (auth middleware, trusted-header tenancy, per-request server), `src/ledger.ts` (jsonl+md Files pattern incl. `sanitizeInline`), `src/hindsight.ts` (REST client with tags), `src/registry.ts` (lazy supabase client) and adapt. Do not redesign what it already solved.
- Value test (spec, verbatim): "A measure is value-accretive if it lifts NOI and defensibly lifts exit value (NOI ÷ cap rate); green premium / brown discount priced ONLY with citable evidence."
- Screen labels exactly: `recommended` / `defensive` / `screened-out` / `needs-data`; screened-out must name the failing test.
- Every economic field carries provenance `engine:<id>` or `source:<citation>`; evaluations violating this are REJECTED (loud, field named).
- Citations carry `provenance: 'library' | 'web'`.
- Storage uploads: contentType `text/plain` (bucket allowlist rejects x-ndjson and text/markdown — learned on verifier).
- vitest on this VM: `npx vitest run --pool=forks --poolOptions.forks.singleFork=true`.
- soapbox-platform deploys from **main** on push; do platform work on branch `retrofit-v1`, merge at deploy task.
- Never `git add -A`; stage named files. Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Hindsight: REST base `HINDSIGHT_API_URL` (no /mcp), bearer `HINDSIGHT_API_KEY`; tags survive decomposition, text markers do not.
- New env for retrofit-mcp: same six as verifier (`MCP_SERVER_SECRET, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, HINDSIGHT_API_URL, HINDSIGHT_API_KEY, SOAPBOX_API_URL`) plus `RETROFIT_LIBRARY_ADMIN_KEY` (gates add_reference).
- Never log measure/fact contents (ids and categories only).

## File Structure

```
retrofit-mcp/  (new repo; skeleton copied from verifier-mcp)
  package.json tsconfig.json .gitignore README.md
  playbooks/{hvac,envelope,dhw,controls-rcx,solar-storage,electrification-staging}.json
  playbooks/phases/{walk-the-pca,staging,baseline-discipline}.json
  src/playbooks.ts       getPlaybook(key), listPlaybooks()
  src/evaluation.ts      schema + validateEvaluation() + computeExitMath() (pure)
  src/screening.ts       screenMeasures() (pure)
  src/register.ts        measure register (adapt verifier ledger.ts; Retrofit/measures.jsonl + measures.md)
  src/library.ts         search_reference_library / add_reference (hindsight bank retrofit-library)
  src/candidates.ts      proposeCandidates() (source checklist + normalization + origination prompts)
  src/hindsight.ts       copied from verifier-mcp (tags variant)
  src/registry.ts        copied from verifier-mcp (lazy client; reused for asset-scope validation)
  src/index.ts           server wiring, 8 tools (adapt verifier index.ts)
  test/*.test.ts         one per module + server test

soapbox-platform/apps/api/ (branch retrofit-v1)
  src/services/retrofit-prompt.ts        (new; RETROFIT_SPECIALIST_PROMPT)
  src/services/agent-config.ts           (modify: inject on plugin_retrofit, hash component)
  src/services/portfolio.ts              (modify: corePlugins + env-gated api_key seeding)
  src/lib/connector-rewrites.ts          (modify: mustUseProxy adds plugin_retrofit)
  src/routes/portfolios.ts               (modify: reserved name plugin_retrofit)
  test/services/retrofit-prompt.test.ts  (new) + updates to existing tests

verifier-mcp/ (small change)
  src/expertise.ts       (modify: VALID_DOMAINS += measure-performance, cost-prior, contractor-market)
  test/expertise.test.ts (modify)
```

---

### Task 1: Scaffold + playbooks

**Files:**
- Create: `~/retrofit-mcp/package.json`, `tsconfig.json`, `.gitignore`, `playbooks/*.json` (6 families), `playbooks/phases/*.json` (3 phases), `src/playbooks.ts`
- Test: `~/retrofit-mcp/test/playbooks.test.ts`

**Interfaces:**
- Produces: `getPlaybook(key: string): Playbook` (throws on unknown, listing valid keys), `listPlaybooks(): string[]`, where `Playbook = { key: string; version: string; kind: 'family'|'phase'; doctrine: string[]; origination_prompts: string[]; feasibility_checks: string[]; data_requirements: string[] }`.

- [ ] **Step 1: Scaffold** — `mkdir -p ~/retrofit-mcp/{src,test,playbooks/phases} && cd ~/retrofit-mcp && git init`. Copy `package.json`/`tsconfig.json`/`.gitignore` from `/home/claude/verifier-mcp` verbatim, then edit package.json name to `retrofit-mcp` and add `"RETROFIT"` nothing else; run `npm install`. (Keep `start: node dist/src/index.js` — the tsc layout is identical.)

- [ ] **Step 2: Failing test**

```typescript
// test/playbooks.test.ts
import { describe, it, expect } from 'vitest'
import { getPlaybook, listPlaybooks } from '../src/playbooks.js'

describe('playbooks', () => {
  it('exposes six families and three phases', () => {
    const keys = listPlaybooks().sort()
    expect(keys).toEqual(['baseline-discipline','controls-rcx','dhw','electrification-staging','envelope','hvac','solar-storage','staging','walk-the-pca'].sort())
  })
  it('every playbook has doctrine, checks, and version', () => {
    for (const k of listPlaybooks()) {
      const p = getPlaybook(k)
      expect(p.version).toMatch(/^\d+\.\d+\.\d+$/)
      expect(p.doctrine.length).toBeGreaterThan(2)
      expect(p.feasibility_checks.length).toBeGreaterThan(1)
    }
  })
  it('controls-rcx doctrine prefers measured baselines and low-cost first', () => {
    const d = getPlaybook('controls-rcx').doctrine.join(' ')
    expect(d).toMatch(/measured/i); expect(d).toMatch(/before/i)
  })
  it('unknown key throws listing valid keys', () => {
    expect(() => getPlaybook('nope')).toThrow(/hvac/)
  })
})
```

Run: `npx vitest run` — FAIL (module missing).

- [ ] **Step 3: Author playbooks.** Each family JSON follows this shape (write all nine; doctrine content from the spec's pragmatist principles — measured baselines over modeled savings, boring-proven over novel, stage with capital events, load-reduction before plant replacement, maintainability by on-site staff, tenant disruption named honestly, Shovels contractor-reality check). Example:

```json
// playbooks/controls-rcx.json
{
  "key": "controls-rcx",
  "version": "1.0.0",
  "kind": "family",
  "doctrine": [
    "Controls and retro-commissioning come BEFORE plant replacement: tune what exists, then size what remains",
    "Demand measured baselines (12-mo interval or utility data) before crediting any modeled savings; modeled-only savings are provisional",
    "Prefer measures the on-site operating staff can maintain; a BAS optimization nobody understands decays in 18 months",
    "Typical scope: schedules, setpoints, economizer repair, sensor calibration, VFD additions on constant-volume systems, DCV where occupancy varies"
  ],
  "origination_prompts": [
    "Does the audit or PCA mention economizers, dampers, or actuators in fair/poor condition? RCx candidate.",
    "Are HVAC schedules running 24/7 in the audit's operating description for a property with predictable occupancy?",
    "Constant-speed pumps or fans older than 15 years with variable loads => VFD candidate."
  ],
  "feasibility_checks": [
    "Confirm BAS exists and is programmable (PCA systems description); pneumatic-only controls change the measure scope",
    "Tenant disruption: RCx is low-disruption but schedule changes need property-management sign-off",
    "Check Shovels for local controls contractors' permit activity as a market-availability signal"
  ],
  "data_requirements": ["12-month energy baseline (utility or audit)", "equipment inventory with install years", "operating schedule description"]
}
```

`src/playbooks.ts` mirrors verifier `src/checklists.ts` exactly (JSON imports with `with { type: 'json' }`, `ALL` record, throw-with-valid-keys).

- [ ] **Step 4: Tests pass; commit** — `git add -A` is FORBIDDEN; `git add package.json tsconfig.json .gitignore playbooks src/playbooks.ts test/playbooks.test.ts package-lock.json && git commit -m "feat: scaffold + retrofit playbooks"` + trailer.

---

### Task 2: Evaluation schema + exit math (pure)

**Files:**
- Create: `~/retrofit-mcp/src/evaluation.ts`
- Test: `~/retrofit-mcp/test/evaluation.test.ts`

**Interfaces:**
- Produces:
```typescript
export type Provenance = { engine?: string; source?: string; provenance?: 'library'|'web' }
export type EconField = { value: number; unit: string } & Provenance
export type MeasureEvaluation = {
  id?: string; asset_id: string; measure_family: string; name: string
  candidate_source: 'audette'|'pca'|'audit'|'originated'
  cost: EconField
  owner_savings_annual: EconField          // post LL/TT allocation
  noi_delta_annual: EconField
  cap_rate: EconField                       // source required
  exit_value_delta?: EconField              // computed, engine:'retrofit-mcp/exit-math@1'
  green_premium?: EconField                 // citation required
  incentives?: Array<EconField & { program: string; eligibility_basis: string }>
  feasibility: { score: 1|2|3|4|5; site_conditions: string; disruption: 'none'|'light'|'in-unit'|'vacancy-required'; contractor_reality: string; staging: string; sources: string[] }
  future_proofing: { rationale: string; citations: string[] }
  status?: 'proposed'|'recommended'|'defensive'|'screened-out'|'needs-data'|'implemented'
}
export function validateEvaluation(e: unknown): { ok: true; evaluation: MeasureEvaluation } | { ok: false; errors: string[] }
export function computeExitMath(e: MeasureEvaluation): MeasureEvaluation  // fills exit_value_delta = noi_delta/cap_rate
```

- [ ] **Step 1: Failing tests**

```typescript
// test/evaluation.test.ts
import { describe, it, expect } from 'vitest'
import { validateEvaluation, computeExitMath } from '../src/evaluation.js'

const econ = (v: number, unit: string, prov: object) => ({ value: v, unit, ...prov })
const base = () => ({
  asset_id: 'a1', measure_family: 'controls-rcx', name: 'RCx package', candidate_source: 'audit',
  cost: econ(120000, 'USD', { source: 'audit ECM table p.44' }),
  owner_savings_annual: econ(30000, 'USD/yr', { engine: 'll_allocation@1' }),
  noi_delta_annual: econ(30000, 'USD/yr', { engine: 'dcf_engine@1' }),
  cap_rate: econ(0.055, 'ratio', { source: 'asset metadata (client-provided 2026-06)' }),
  feasibility: { score: 4, site_conditions: 'BAS present per PCA p.12', disruption: 'none', contractor_reality: 'active controls permits in metro (Shovels)', staging: 'independent of capital events', sources: ['pca','shovels'] },
  future_proofing: { rationale: 'reduces base load ahead of Reg 28 targets', citations: ['CO Reg 28 rule text'] },
})

describe('validateEvaluation', () => {
  it('accepts a fully-provenanced evaluation', () => {
    expect(validateEvaluation(base()).ok).toBe(true)
  })
  it('rejects economics without provenance, naming the field', () => {
    const e: any = base(); delete e.cost.source
    const r = validateEvaluation(e)
    expect(!r.ok && r.errors.join(' ')).toMatch(/cost/)
  })
  it('rejects green_premium without a source citation', () => {
    const e: any = { ...base(), green_premium: econ(500000, 'USD', { engine: 'vibes' }) }
    const r = validateEvaluation(e)
    expect(!r.ok && r.errors.join(' ')).toMatch(/green_premium.*source/i)
  })
  it('rejects incentives missing eligibility_basis', () => {
    const e: any = { ...base(), incentives: [{ ...econ(50000,'USD',{source:'IRA 179D'}), program: '179D' }] }
    expect(validateEvaluation(e).ok).toBe(false)
  })
})

describe('computeExitMath', () => {
  it('computes exit_value_delta = noi_delta / cap_rate with engine provenance', () => {
    const v = validateEvaluation(base()); if (!v.ok) throw new Error('setup')
    const out = computeExitMath(v.evaluation)
    expect(out.exit_value_delta!.value).toBeCloseTo(30000 / 0.055, 0)
    expect(out.exit_value_delta!.engine).toBe('retrofit-mcp/exit-math@1')
  })
  it('throws on zero/negative cap rate', () => {
    const v = validateEvaluation({ ...base(), cap_rate: econ(0, 'ratio', { source: 'x' }) })
    if (!v.ok) throw new Error('setup')
    expect(() => computeExitMath(v.evaluation)).toThrow(/cap.rate/i)
  })
})
```

- [ ] **Step 2: Implement with zod** — schema mirrors the type; a refinement per EconField requires `engine || source`; `green_premium` requires `source` specifically (engine not acceptable — premiums are evidence, not computation); incentives require `program` + `eligibility_basis`. `validateEvaluation` returns all errors (zod `.safeParse`, map issues to `path: message`). `computeExitMath` divides, rounds to whole USD, stamps `{ engine: 'retrofit-mcp/exit-math@1' }`, throws `Error('cap_rate must be > 0')` otherwise.

- [ ] **Step 3: Tests pass; commit** `feat: evaluation schema with provenance enforcement + exit math`.

---

### Task 3: Screening (pure)

**Files:**
- Create: `~/retrofit-mcp/src/screening.ts`
- Test: `~/retrofit-mcp/test/screening.test.ts`

**Interfaces:**
- Consumes: `MeasureEvaluation` (Task 2).
- Produces: `screenMeasures(evals: MeasureEvaluation[]): Array<{ id?: string; name: string; label: 'recommended'|'defensive'|'screened-out'|'needs-data'; failing_test?: 'value'|'feasibility'|'future-proofing'; reasons: string[] }>`

- [ ] **Step 1: Failing tests** — four labels:

```typescript
// test/screening.test.ts (fixtures built on Task 2's base())
// value pass = noi_delta_annual.value > 0 AND exit_value_delta present AND simple payback (cost/owner_savings) <= 15y
// feasibility pass = score >= 3
// needs-data = any data_gap: missing exit_value_delta, or feasibility.sources empty
// defensive = fails value AND future_proofing.citations.length > 0 AND feasibility passes
import { describe, it, expect } from 'vitest'
import { screenMeasures } from '../src/screening.js'
// ...fixtures: passing measure => 'recommended';
// cost 2,000,000 / savings 30,000 (67y payback) with citations => 'defensive';
// same but feasibility.score 2 => 'screened-out' with failing_test 'feasibility';
// missing exit_value_delta => 'needs-data'.
it('labels recommended / defensive / screened-out(with failing test) / needs-data', () => { /* four asserts as above */ })
it('reasons always non-empty and name the numbers (payback, score)', () => { /* assert /payback/ in reasons */ })
```

(Write the four fixtures concretely in the test file — copy Task 2's `base()` helper into this test and vary fields as commented.)

- [ ] **Step 2: Implement** — thresholds as named exports (`MAX_SIMPLE_PAYBACK_YEARS = 15`, `MIN_FEASIBILITY_SCORE = 3`) so methodology changes are data-visible. Order: needs-data check first, then feasibility, then value, then defensive fallback.

- [ ] **Step 3: Tests pass; commit** `feat: three-test measure screening`.

---

### Task 4: Measure register (adapt verifier ledger)

**Files:**
- Create: `~/retrofit-mcp/src/register.ts` (start from a copy of `/home/claude/verifier-mcp/src/ledger.ts`)
- Copy: `/home/claude/verifier-mcp/src/registry.ts` → `~/retrofit-mcp/src/registry.ts` unchanged
- Test: `~/retrofit-mcp/test/register.test.ts`

**Interfaces:**
- Consumes: `MeasureEvaluation` (Task 2).
- Produces: `saveMeasure(scope: {portfolioId: string; assetId: string}, e: MeasureEvaluation): Promise<{id: string}>` (id = randomUUID when absent; upsert by id into the jsonl), `getMeasures(scope, status?): Promise<MeasureEvaluation[]>`, `renderMeasuresMarkdown(measures): string` (pure, uses the copied `sanitizeInline`).
- Storage: `<assetId>/retrofit/measures.jsonl` (source of truth, contentType text/plain) + `measures.md` files-row (name `measures.md`, folder `Retrofit`, mime text/plain, path `<assetId>/<fileId>/measures.md`) + POST `${SOAPBOX_API_URL}/internal/index-file` after md writes. Asset-scoped only in v1 (register is per-asset; portfolioId used for the files row).

- [ ] **Step 1: Failing tests** — pure parts (`renderMeasuresMarkdown` shows name, label/status, exit math, and sanitizes an injection fixture `"# fake\n<script>"`), plus a mocked round-trip (jsonl upload + md upload + files row + index POST with bearer) and a missing-object → `[]` case. Adapt the verifier's `test/ledger.test.ts` mocking pattern directly.
- [ ] **Step 2: Adapt implementation** — rename Finding→MeasureEvaluation plumbing; upsert-by-id (replace entry with same id, else append); keep loud failures, `.is('asset_id', null)` scope-collision guard is NOT needed (always asset-scoped) but keep the folder+name row lookup filtered by asset_id.
- [ ] **Step 3: Tests pass; commit** `feat: per-asset measure register (Files-backed)`.

---

### Task 5: Reference library

**Files:**
- Copy: `/home/claude/verifier-mcp/src/hindsight.ts` → `~/retrofit-mcp/src/hindsight.ts` unchanged
- Create: `~/retrofit-mcp/src/library.ts`
- Test: `~/retrofit-mcp/test/library.test.ts`

**Interfaces:**
- Produces: `searchLibrary(query: string): Promise<Array<{text: string; tags: string[]; provenance: 'library'}>>` (recall on bank `retrofit-library`); `addReference(input: {admin_key: string; title: string; source_org: string; year?: number; content: string; topics: string[]}): Promise<{added: boolean; error?: string}>`.
- `addReference` gates: `admin_key` must equal `process.env.RETROFIT_LIBRARY_ADMIN_KEY` (timing-safe compare via sha256+timingSafeEqual — copy the helper from verifier `src/index.ts`); content chunked to ≤4000-char chunks retained with tags `['library', 'org:<source_org>', ...topics.map(t => 'topic:'+t), 'title:<slugified title>']`.

- [ ] **Step 1: Failing tests** — wrong/missing admin_key rejected without any hindsight call (mock asserts no retain); valid add retains N chunks with the tag set; search maps results and stamps `provenance: 'library'`.
- [ ] **Step 2: Implement; tests pass; commit** `feat: shared reference library over hindsight bank`.

---

### Task 6: Candidate proposal

**Files:**
- Create: `~/retrofit-mcp/src/candidates.ts`
- Test: `~/retrofit-mcp/test/candidates.test.ts`

**Interfaces:**
- Consumes: `getPlaybook/listPlaybooks` (Task 1).
- Produces: `proposeCandidates(input: {asset_attributes?: {archetype?: string; jurisdiction?: string; equipment?: Array<{type: string; install_year?: number}>}}): { source_checklist: string[]; origination_prompts: string[]; candidate_schema: object }` — source_checklist is the fixed instruction list (pull Audette measures via your audette tools; search asset files for the PCA capital/immediate-repairs table; search asset files for audit ECM tables); origination_prompts = union of family playbooks' prompts, filtered: equipment older than 15y prioritizes that family first; `normalizeCandidates(raw: Array<{measure_family: string; name: string; source: string; raw_basis: string}>): candidates` validating `source ∈ audette|pca|audit|originated` and `measure_family ∈ listPlaybooks() families`.

- [ ] **Step 1: Failing tests** — checklist mentions Audette/PCA/ECM; equipment `[{type:'RTU', install_year: 2005}]` puts an hvac prompt first; normalize rejects unknown family/source naming the field.
- [ ] **Step 2: Implement; tests pass; commit** `feat: candidate proposal + normalization`.

---

### Task 7: Server wiring (8 tools)

**Files:**
- Create: `~/retrofit-mcp/src/index.ts` (start from a copy of `/home/claude/verifier-mcp/src/index.ts` — keep requireMcpAuth incl. 503-on-missing-secret, scopeFromHeaders, resolveScope asset-validation, per-request server, /health, createApp export + main guard)
- Test: `~/retrofit-mcp/test/server.test.ts`

**Interfaces:**
- Tools (names exact): `propose_candidates {asset_attributes?}`, `evaluate_measure {asset_id, measure}` (validate → computeExitMath → saveMeasure → return persisted evaluation; rejection returns the errors array as tool error), `screen_measures {asset_id, measure_ids?}` (loads register, screens, writes labels back via saveMeasure, returns labels), `get_measure_state {asset_id, status?}`, `update_measure_state {asset_id, measure_id, status, note?}` (status transitions incl. 'implemented'), `get_retrofit_playbook {key}`, `search_reference_library {query}`, `add_reference {admin_key, title, source_org, year?, content, topics}`.
- Scoped tools require the portfolio header + asset_id validated against portfolio (verifier `resolveScope` pattern). Library tools require auth only (client-agnostic).

- [ ] **Step 1: Failing server test** — adapted from verifier `test/server.test.ts`: bearer required (401 without), 8 tool names in tools/list, `get_retrofit_playbook {key:'hvac'}` returns doctrine, `evaluate_measure` with un-provenanced cost returns a tool error naming `cost`.
- [ ] **Step 2: Implement; all suites green (`npx vitest run --pool=forks --poolOptions.forks.singleFork=true`); `npm run build`; smoke `node dist/src/index.js` + curl /health in report; commit** `feat: MCP server wiring (8 tools)`.

---

### Task 8: Platform integration (branch retrofit-v1)

**Files:**
- Create: `~/soapbox-platform/apps/api/src/services/retrofit-prompt.ts`
- Modify: `src/services/agent-config.ts` (inject where VERIFICATION_PROMPT is injected, gated on `plugin_retrofit` connector; portfolio hash gains `:retrofit:${retrofitInstalled}` component beside the `:verifier:` one)
- Modify: `src/services/portfolio.ts` (corePlugins += `{ plugin_id: 'retrofit', name: 'plugin_retrofit', description: 'Retrofit Specialist: playbooks, provenance-enforced measure evaluation, measure register, reference library.', mcp_url: 'https://retrofit-mcp-production.up.railway.app/mcp' }`; api_key seeding: `plugin_retrofit` uses `MCP_SERVER_SECRET` with the same skip-when-missing guard as verifier)
- Modify: `src/lib/connector-rewrites.ts` (`mustUseProxy` hard-pins `plugin_retrofit` too)
- Modify: `src/routes/portfolios.ts` (reserved names += `plugin_retrofit`)
- Test: `test/services/retrofit-prompt.test.ts` + extend `test/lib/connector-rewrites.test.ts`, `test/services/portfolio.test.ts`, `test/routes/portfolios.test.ts`

**Steps:** branch `git checkout -b retrofit-v1 origin/main`; TDD each change (prompt contains the five tool-discipline behaviors AND the doctrine anchors: 'read the PCA', 'measured baselines', 'hold period', 'Shovels', 'tenant disruption'; mustUseProxy('plugin_retrofit', false) === true; seeding skips without MCP_SERVER_SECRET — parametrize the existing verifier tests where cheap); `npx tsc --noEmit` clean; commit per logical change; do NOT push (controller merges at deploy).

The prompt (write verbatim into retrofit-prompt.ts):

```typescript
export const RETROFIT_SPECIALIST_PROMPT = `

## Retrofit Specialist (always active)
You are also Soapbox's Retrofit Specialist — a boots-on-the-ground building-science pragmatist, not a theoretician. When retrofit, capital planning, or decarbonization work arises:
1. WALK THE ASSET FIRST — read the PCA and audits (file search) before proposing anything; get_retrofit_playbook('walk-the-pca') is your checklist. Respect the hold period and existing capital plan.
2. CANDIDATES FROM EVERYWHERE — propose_candidates gives you the source checklist (Audette measures, PCA capital tables, audit ECMs) plus origination prompts for what models miss (controls/RCx, O&M, staging with equipment end-of-life).
3. EVALUATE THROUGH THE TOOLS ONLY — every measure goes through evaluate_measure; economics must come from engines or cited sources, never your own arithmetic. Distrust modeled savings without measured baselines — mark them provisional. Check Shovels for contractor/permit reality. Name tenant disruption honestly.
4. SCREEN AND RECORD — screen_measures applies the three tests (value via NOI + exit math, feasibility, future-proofing); the register in Files is your working state across sessions. Deliverables belong to the calling workflow — you supply evaluated, cited measures.
5. REMEMBER — recall_expertise before estimating costs or performance; retain generalizable lessons (measure-performance, cost-prior, contractor-market domains) via retain_shared_expertise. Search the reference library before the open web; cite provenance either way.`
```

---

### Task 9: Verifier domain extension

**Files:**
- Modify: `~/verifier-mcp/src/expertise.ts` (VALID_DOMAINS += `'measure-performance','cost-prior','contractor-market'`)
- Test: `~/verifier-mcp/test/expertise.test.ts` (new domains accepted; invalid still rejected)

**Steps:** TDD; suites green; commit `feat: retrofit expertise domains`; push (auto-deploys verifier).

---

### Task 10: Deploy + register (controller-run: infra creds live in the main session)

- [ ] `gh repo create soapboxbuild/retrofit-mcp --private --source ~/retrofit-mcp --push`
- [ ] Railway service `retrofit-mcp` in soapbox-mcps (project e5434a34…, env production) from the repo; set the 6 verifier env vars + `RETROFIT_LIBRARY_ADMIN_KEY` (generate 48 hex chars; store in Vaultwarden as "Retrofit Library Admin Key"); create Railway service domain (skip custom domain until the verifier's cert issue is resolved; then add both).
- [ ] Smoke: /health 200; /mcp 401 unauth; tools/list ×8 with bearer.
- [ ] Merge retrofit-v1 → main, push (deploys soapbox-api). Confirm SUCCESS + regression: Cortland assets list, one verifier tool call via proxy.
- [ ] plugin_catalog row (`retrofit`, sort_order 90, railway mcp_url); backfill asset_connectors (`plugin_retrofit`, api_key = MCP_SERVER_SECRET value) + installed_plugins for all portfolios (NOT EXISTS pattern from the verifier backfill).
- [ ] Proxy-chain smoke: tools/list + get_retrofit_playbook through `/mcp/connector/<hmac>/<portfolioId>/plugin_retrofit`.

### Task 11: Library seed + Cortland pilot (controller-run)

- [ ] Seed ≥6 public references via add_reference: DOE Advanced RTU Campaign guidance, PNNL retro-commissioning guide summary, DOE heat pump RTU field results, ACEEE multifamily retrofit study, RMI deep retrofit value methodology, Energize Denver + CO Reg 28 rule summaries (fetch public text, chunk, attribute source_org + year).
- [ ] Pilot on Cortland Westminster (via proxy tools + one live thread):
  1. `propose_candidates` with its equipment (split AHUs 2009, gas DHW 2014) → checklist + prompts sane.
  2. Evaluate TWO measures end-to-end: one audit ECM (from the indexed AEI audit) and one originated controls/RCx measure; economics through engines/citations; confirm a doctored evaluation (uncited green premium) is REJECTED naming the field.
  3. `screen_measures` → labels + reasons; `Retrofit/measures.md` visible in Files and indexed.
  4. Live thread: ask the Westminster agent for retrofit recommendations — confirm it walks the PCA, uses the tools, and the register updates.
  5. Verifier interplay: run the verifier's financial checklist against one evaluation (agent-level), confirm pass; record outcomes in the SDD ledger + memory files.

## Self-Review Notes

- Spec coverage: candidates C (T6), value test B (T2/T3), three-test screen (T3), playbooks/doctrine (T1), register (T4), library C (T5/T11), worker tools (T7), persona (T8), memory domains (T9), core install/backfill (T8/T10), verifier scrutiny (pilot step 5). Open Q1 resolved: hindsight bank (T5). Q2: cap_rate is per-evaluation input with source (T2). Q3: T9. Q4: admin_key env compare (T5).
- Type consistency: `MeasureEvaluation`/`EconField` defined T2, consumed T3/T4/T7; screen labels identical everywhere; tool names T7 = prompt T8.
- No placeholders: clone-and-adapt steps reference exact existing files by path; new logic has code or exact field-level specifications.
