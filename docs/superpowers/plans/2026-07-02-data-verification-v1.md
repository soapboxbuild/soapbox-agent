# Data Verification Agent v1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `memory` and `verifier` core plugins (spec v1.0 stage): hindsight MCP with server-side org-bank pinning, verifier MCP (checklists, Files-based findings ledger, code-gated shared expertise bank), core install + backfill, and verification prompt injection.

**Architecture:** Two plugins. `memory` = the existing hindsight deployment exposed through soapbox-api's connector proxy, which rewrites every JSON-RPC call to pin `bank_id: org-<orgId>`. `verifier` = new Node/TS MCP server (repo `verifier-mcp`, deployed to Railway project soapbox-mcps as `verifier.mcp.soapbox.build`) owning checklists, ledger, and the only write path to the shared `soapbox-expertise` hindsight bank. Thread agents do research with their existing connectors.

**Tech Stack:** TypeScript, `@modelcontextprotocol/sdk` ^1.12, express (brave-search-mcp pattern), vitest, Supabase JS (service role), hindsight 0.5.1 (JSON-RPC MCP at agent-memory.soapbox.build), Hono (soapbox-api), Railway.

**Scope note:** Spec sections "Proactive loops" (v1.1) and "Report gate" (v1.2) are explicitly OUT of this plan — separate plans after the Cortland pilot.

## Global Constraints

- soapbox-api deploys from branch **main** of `soapboxbuild/soapbox-platform` (NOT master). Commit there.
- Tier gate: shared-bank retention requires **≥2 independent sources** or a confirmed-finding reference — verbatim from spec.
- Anonymization gate rejects: client names, org names, asset names, street addresses, coordinates, uids/ids, client financial figures, any string matching platform org/asset registries. Rejection must be **loud** (structured error), never silent.
- Auto-verify threshold 0.85 / review 0.40 (shared with frontend wizard) — used in checklist rubrics.
- Fiduciary recall defaults to tier `validated` only.
- Agents must NEVER reach the shared bank except via `retain_shared_expertise` / `recall_expertise`.
- The memory connector must never let an agent choose a bank: proxy pins `bank_id = org-<organization_id>` and blocks `list_banks` / `create_bank` / `delete_bank`.
- All new soapbox-api code: vitest tests in `apps/api/test/`, run with `cd ~/soapbox-platform/apps/api && npx vitest run <file>`.
- verifier-mcp: `"type": "module"`, build `tsc`, tests vitest, port from `process.env.PORT ?? 8080`.
- Never log fact contents or client names in verifier-mcp (log ids/categories only).
- Env/secrets: from Vaultwarden (`vw get password "<item>"`), never committed. New secrets go INTO Vaultwarden.

## File Structure

```
soapbox-platform/apps/api/
  src/lib/connector-rewrites.ts        (new — pure: bank pinning + trusted headers)
  src/index.ts                         (modify — proxy wiring @ ~line 340-465; internal index route)
  src/services/portfolio.ts            (modify — corePlugins list @ ~line 49)
  src/services/agent-config.ts         (modify — VERIFICATION_PROMPT injection @ ~434, ~828)
  test/lib/connector-rewrites.test.ts  (new)
  test/services/verification-prompt.test.ts (new)

verifier-mcp/  (new repo)
  package.json, tsconfig.json
  src/index.ts          (express + MCP wiring, trusted-header context)
  src/checklists.ts     (get_verification_checklist)
  checklists/*.json     (versioned rubric data)
  src/anonymize.ts      (pure gate)
  src/registry.ts       (org/asset name lists from Supabase, 1h cache)
  src/hindsight.ts      (JSON-RPC client for agent-memory.soapbox.build)
  src/expertise.ts      (retain_shared_expertise, recall_expertise)
  src/ledger.ts         (record/list/resolve finding; jsonl+md via Supabase)
  src/status.ts         (verification_status)
  test/*.test.ts        (one per module)
```

---

### Task 1: Connector rewrite helpers (soapbox-api, pure functions)

**Files:**
- Create: `~/soapbox-platform/apps/api/src/lib/connector-rewrites.ts`
- Test: `~/soapbox-platform/apps/api/test/lib/connector-rewrites.test.ts`

**Interfaces:**
- Produces: `pinMemoryBank(bodyText: string, orgId: string): { body: string } | { blocked: string }` and `applyTrustedContext(headers: Headers, portfolioId: string, orgId: string): void`. Task 2 consumes both.

- [ ] **Step 1: Write the failing tests**

```typescript
// test/lib/connector-rewrites.test.ts
import { describe, it, expect } from 'vitest'
import { pinMemoryBank, applyTrustedContext } from '../../src/lib/connector-rewrites.js'

const call = (name: string, args: Record<string, unknown> = {}) => JSON.stringify({
  jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args },
})

describe('pinMemoryBank', () => {
  it('overrides bank_id on tools/call with the org bank', () => {
    const out = pinMemoryBank(call('retain', { content: 'x', bank_id: 'someone-elses-bank' }), 'abc-123')
    expect('body' in out && JSON.parse(out.body).params.arguments.bank_id).toBe('org-abc-123')
  })
  it('injects bank_id when absent', () => {
    const out = pinMemoryBank(call('recall', { query: 'q' }), 'abc-123')
    expect('body' in out && JSON.parse(out.body).params.arguments.bank_id).toBe('org-abc-123')
  })
  it('blocks bank management tools', () => {
    for (const name of ['list_banks', 'create_bank', 'delete_bank']) {
      const out = pinMemoryBank(call(name), 'abc-123')
      expect('blocked' in out && out.blocked).toContain(name)
    }
  })
  it('passes through non-tools/call methods unchanged', () => {
    const body = JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'tools/list' })
    const out = pinMemoryBank(body, 'abc-123')
    expect('body' in out && out.body).toBe(body)
  })
  it('passes through unparseable bodies unchanged', () => {
    const out = pinMemoryBank('not json', 'abc-123')
    expect('body' in out && out.body).toBe('not json')
  })
})

describe('applyTrustedContext', () => {
  it('strips inbound x-soapbox-* and sets trusted values', () => {
    const h = new Headers({ 'x-soapbox-portfolio-id': 'spoofed', 'x-soapbox-organization-id': 'spoofed' })
    applyTrustedContext(h, 'pf-1', 'org-1')
    expect(h.get('x-soapbox-portfolio-id')).toBe('pf-1')
    expect(h.get('x-soapbox-organization-id')).toBe('org-1')
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd ~/soapbox-platform/apps/api && npx vitest run test/lib/connector-rewrites.test.ts`
Expected: FAIL — cannot resolve `../../src/lib/connector-rewrites.js`

- [ ] **Step 3: Implement**

```typescript
// src/lib/connector-rewrites.ts
const BLOCKED_MEMORY_TOOLS = new Set(['list_banks', 'create_bank', 'delete_bank'])

// Pin every hindsight tools/call to the caller's org bank. Agents must never
// address another bank; bank management is proxy-blocked entirely.
export function pinMemoryBank(bodyText: string, orgId: string): { body: string } | { blocked: string } {
  let rpc: any
  try { rpc = JSON.parse(bodyText) } catch { return { body: bodyText } }
  if (rpc?.method !== 'tools/call' || !rpc.params) return { body: bodyText }
  const name = rpc.params.name as string
  if (BLOCKED_MEMORY_TOOLS.has(name)) return { blocked: `${name} is not available through the memory plugin` }
  rpc.params.arguments = { ...(rpc.params.arguments ?? {}), bank_id: `org-${orgId}` }
  return { body: JSON.stringify(rpc) }
}

export function applyTrustedContext(headers: Headers, portfolioId: string, orgId: string): void {
  headers.delete('x-soapbox-portfolio-id')
  headers.delete('x-soapbox-organization-id')
  headers.set('x-soapbox-portfolio-id', portfolioId)
  headers.set('x-soapbox-organization-id', orgId)
}
```

- [ ] **Step 4: Run tests — expect PASS**
- [ ] **Step 5: Commit**

```bash
cd ~/soapbox-platform && git add apps/api/src/lib/connector-rewrites.ts apps/api/test/lib/connector-rewrites.test.ts && git commit -m "feat(api): connector rewrite helpers for memory bank pinning"
```

---

### Task 2: Wire pinning + trusted headers into the connector proxy

**Files:**
- Modify: `~/soapbox-platform/apps/api/src/index.ts` (the `/mcp/connector/:token/:portfolioId/:connectorName` handler, ~lines 340–470)

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces: proxy behavior — for connector `plugin_memory`, body rewritten + blocked tools answered locally; for ALL connectors, trusted context headers set on forward. Verifier (Task 8) reads `x-soapbox-portfolio-id` / `x-soapbox-organization-id`.

- [ ] **Step 1: Modify the handler.** After the connector row is fetched (it already selects by portfolioId), fetch the org id once and apply the helpers inside `forward()`:

```typescript
// add to imports at top of index.ts:
import { pinMemoryBank, applyTrustedContext } from './lib/connector-rewrites.js'

// inside the handler, after `if (!connector?.url) ...`:
const { data: pf } = await supabase
  .from('portfolios').select('organization_id').eq('id', portfolioId).single()
const orgId = pf?.organization_id as string | undefined

let forwardBody = bodyBuf
if (connectorName === 'plugin_memory' && orgId && bodyText) {
  const pinned = pinMemoryBank(bodyText, orgId)
  if ('blocked' in pinned) {
    const rpcId = (() => { try { return JSON.parse(bodyText).id ?? 1 } catch { return 1 } })()
    return c.json({ jsonrpc: '2.0', id: rpcId, error: { code: -32601, message: pinned.blocked } }, 200)
  }
  forwardBody = new TextEncoder().encode(pinned.body).buffer as ArrayBuffer
}

// inside forward(), after headers.set('Authorization', ...):
if (orgId) applyTrustedContext(headers, portfolioId, orgId)
// and change the fetch body to use forwardBody:
return fetch(upstream, { method: c.req.method, headers, body: forwardBody })
```

(Replace both existing `body: bodyBuf` usages with `forwardBody`.)

- [ ] **Step 2: Typecheck**

Run: `cd ~/soapbox-platform/apps/api && npx tsc --noEmit`
Expected: only the two pre-existing `Cannot find module 'xlsx'` errors (local dep-resolution noise).

- [ ] **Step 3: Run full test suite** — `npx vitest run` — expect PASS.
- [ ] **Step 4: Commit** — `git commit -m "feat(api): pin memory connector to org bank, inject trusted context headers"`

---

### Task 3: Internal reindex route (lets verifier-mcp trigger ledger indexing)

**Files:**
- Modify: `~/soapbox-platform/apps/api/src/index.ts` (add route near other `app.post` registrations, before the connector proxy block)
- Test: `~/soapbox-platform/apps/api/test/lib/internal-index.test.ts`

**Interfaces:**
- Produces: `POST /internal/index-file` `{fileId}` with `Authorization: Bearer <MCP_SERVER_SECRET>` → looks up the file row, enqueues the indexing job. Task 7's ledger calls this after writing `findings.md`.

- [ ] **Step 1: Write failing test** (unit-test the auth guard logic; the route body is thin)

```typescript
// test/lib/internal-index.test.ts
import { describe, it, expect } from 'vitest'
import { verifyMcpAuth } from '../../src/lib/mcp-auth.js'

describe('internal index-file auth', () => {
  it('rejects a missing or wrong bearer', () => {
    expect(verifyMcpAuth(undefined)).toBe(false)
    expect(verifyMcpAuth('Bearer wrong')).toBe(false)
  })
})
```

Run: `npx vitest run test/lib/internal-index.test.ts` — if `verifyMcpAuth` import fails check its actual export name in `src/lib/mcp-auth.ts` and adjust the test to match (it exists; Task authored from repo inspection).

- [ ] **Step 2: Add the route**

```typescript
// index.ts — near other route registrations
app.post('/internal/index-file', async (c) => {
  if (!verifyMcpAuth(c.req.header('Authorization'))) return c.json({ error: 'Unauthorized' }, 401)
  const { fileId } = await c.req.json().catch(() => ({}))
  if (!fileId) return c.json({ error: 'fileId required' }, 400)
  const { data: f } = await supabase
    .from('files').select('id, asset_id, portfolio_id, mime_type').eq('id', fileId).single()
  if (!f) return c.json({ error: 'Not found' }, 404)
  await indexingQueue.add('index-file', {
    fileId: f.id,
    ...(f.asset_id ? { assetId: f.asset_id } : { portfolioId: f.portfolio_id }),
    mimeType: f.mime_type,
  })
  return c.json({ ok: true })
})
```

(`verifyMcpAuth`, `supabase`, `indexingQueue` are already imported in index.ts — verify with grep and add any missing import.)

- [ ] **Step 3: Typecheck + tests pass; commit** — `git commit -m "feat(api): internal index-file endpoint for MCP services"`

---

### Task 4: verifier-mcp scaffold + checklists

**Files:**
- Create: `~/verifier-mcp/package.json`, `tsconfig.json`, `vitest.config.ts`, `src/checklists.ts`, `checklists/energy.json`, `checklists/equipment.json`, `checklists/physical.json`, `checklists/regulatory.json`, `checklists/financial.json`, `checklists/opportunity.json`
- Test: `~/verifier-mcp/test/checklists.test.ts`

**Interfaces:**
- Produces: `getChecklist(dataType: string): Checklist` where `Checklist = { data_type: string; version: string; rubric: string[]; sources: string[]; factored_note: string; auto_fail: string[] }`. Task 8 registers it as tool `get_verification_checklist`.

- [ ] **Step 1: Scaffold** — copy the brave-search-mcp pattern:

```bash
mkdir -p ~/verifier-mcp/{src,test,checklists} && cd ~/verifier-mcp && git init
```

```json
// package.json
{
  "name": "verifier-mcp",
  "version": "1.0.0",
  "type": "module",
  "scripts": { "build": "tsc", "start": "node dist/index.js", "dev": "tsx src/index.ts", "test": "vitest run" },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.12.0",
    "@supabase/supabase-js": "^2.45.0",
    "express": "^4.21.0"
  },
  "devDependencies": { "tsx": "^4.7.0", "typescript": "^5.3.0", "vitest": "^3.0.0", "@types/express": "^4.17.0", "@types/node": "^20.0.0" }
}
```

```json
// tsconfig.json
{ "compilerOptions": { "target": "ES2022", "module": "NodeNext", "moduleResolution": "NodeNext", "outDir": "dist", "rootDir": "src", "strict": true, "resolveJsonModule": true, "esModuleInterop": true }, "include": ["src"] }
```

Run `npm install`.

- [ ] **Step 2: Write failing test**

```typescript
// test/checklists.test.ts
import { describe, it, expect } from 'vitest'
import { getChecklist, listDataTypes } from '../src/checklists.js'

describe('checklists', () => {
  it('returns the energy rubric with BPD plausibility check', () => {
    const c = getChecklist('energy')
    expect(c.rubric.join(' ')).toMatch(/BPD/)
    expect(c.factored_note).toMatch(/without the original draft/i)
  })
  it('financial rubric auto-fails LLM-computed numbers', () => {
    expect(getChecklist('financial').auto_fail.join(' ')).toMatch(/LLM-computed/i)
  })
  it('unknown type throws with the list of valid types', () => {
    expect(() => getChecklist('nope')).toThrow(/energy/)
  })
  it('exposes all six v1 types', () => {
    expect(listDataTypes().sort()).toEqual(['energy','equipment','financial','opportunity','physical','regulatory'])
  })
})
```

Run: `npx vitest run` — FAIL (module missing).

- [ ] **Step 3: Implement.** Checklist JSONs are the versioned methodology. Example (write all six; each follows this shape, content from the spec's rubric table):

```json
// checklists/equipment.json
{
  "data_type": "equipment",
  "version": "1.0.0",
  "rubric": [
    "Cross-check install year against Shovels permits for the asset address (permit dates may lag installs 3-6 months)",
    "Cross-check against the equipment survey and audit text in asset files (RAG search)",
    "Two independent sources agreeing => verified; single source => provisional; conflict => open finding with both citations"
  ],
  "sources": ["shovels", "asset-files-rag", "audette-equipment-survey"],
  "auto_fail": [],
  "factored_note": "Verify each claim without the original draft's reasoning attached — check the bare claim against sources (CoVe factored verification)."
}
```

```json
// checklists/financial.json
{
  "data_type": "financial",
  "version": "1.0.0",
  "rubric": [
    "Every financial figure must originate from a deterministic engine (DCF engine, cashflow MCP, CRREM MCP) or a cited source document",
    "Recompute spot-checks through the engine where possible",
    "Utility cost figures: cross-check audit tables against ESPM/citizen-energy where connected"
  ],
  "sources": ["cashflow-mcp", "crrem-mcp", "asset-files-rag", "espm"],
  "auto_fail": ["Any LLM-computed number (arithmetic performed by the model rather than an engine or source) is an automatic verification failure"],
  "factored_note": "Verify each claim without the original draft's reasoning attached — check the bare claim against sources (CoVe factored verification)."
}
```

(energy.json: BPD plausibility bands + audit/ESPM cross-check; physical.json: Overture/ESPM/audit agreement on address/GFA/floors; regulatory.json: BPS rules via bps-compliance data, jurisdiction confirmation; opportunity.json: primary-source citation required for any incentive/opportunity claim. Write full rubrics from spec section "Methodology tools".)

```typescript
// src/checklists.ts
import energy from '../checklists/energy.json' with { type: 'json' }
import equipment from '../checklists/equipment.json' with { type: 'json' }
import physical from '../checklists/physical.json' with { type: 'json' }
import regulatory from '../checklists/regulatory.json' with { type: 'json' }
import financial from '../checklists/financial.json' with { type: 'json' }
import opportunity from '../checklists/opportunity.json' with { type: 'json' }

export type Checklist = {
  data_type: string; version: string; rubric: string[]
  sources: string[]; auto_fail: string[]; factored_note: string
}
const ALL: Record<string, Checklist> = { energy, equipment, physical, regulatory, financial, opportunity }

export function listDataTypes(): string[] { return Object.keys(ALL) }
export function getChecklist(dataType: string): Checklist {
  const c = ALL[dataType]
  if (!c) throw new Error(`Unknown data_type "${dataType}". Valid: ${listDataTypes().sort().join(', ')}`)
  return c
}
```

- [ ] **Step 4: Tests pass; commit** — `git add -A && git commit -m "feat: scaffold + verification checklists"`

---

### Task 5: Anonymization gate + registry

**Files:**
- Create: `~/verifier-mcp/src/anonymize.ts`, `~/verifier-mcp/src/registry.ts`
- Test: `~/verifier-mcp/test/anonymize.test.ts`

**Interfaces:**
- Produces: `anonymizeFact(text: string, registry: string[]): { ok: true; text: string } | { ok: false; reasons: string[] }` (pure) and `getRegistry(): Promise<string[]>` (org+asset names from Supabase, 1h in-memory cache). Task 6 consumes both.

- [ ] **Step 1: Failing tests (adversarial fixtures)**

```typescript
// test/anonymize.test.ts
import { describe, it, expect } from 'vitest'
import { anonymizeFact } from '../src/anonymize.js'

const REG = ['Cortland', 'Greystar', 'Cortland Belmar']

describe('anonymizeFact', () => {
  it('rejects registry names, possessive and case-insensitive', () => {
    for (const t of ["cortland's audits use GJ", 'the GREYSTAR portfolio shows...']) {
      const r = anonymizeFact(t, REG)
      expect(r.ok).toBe(false)
    }
  })
  it('rejects street addresses embedded in prose', () => {
    expect(anonymizeFact('the building at 445 S Saulsbury St underperforms', REG).ok).toBe(false)
  })
  it('rejects uuids anywhere, including in URLs', () => {
    expect(anonymizeFact('see https://x.io/b/8521896a-5aa6-48cf-92d6-54d2ef3b5617', REG).ok).toBe(false)
  })
  it('rejects coordinates and dollar amounts', () => {
    expect(anonymizeFact('at 39.91989,-105.02 the load is high', REG).ok).toBe(false)
    expect(anonymizeFact('gas spend was $371,948/yr', REG).ok).toBe(false)
  })
  it('accepts a generalized fact and reports all reasons on mixed input', () => {
    expect(anonymizeFact('AEI audits report gas in GJ; cost tables can double-count owner/tenant splits', REG).ok).toBe(true)
    const r = anonymizeFact('Cortland spent $371,948 at 445 S Saulsbury St', REG)
    expect(!r.ok && r.reasons.length >= 3).toBe(true)
  })
})
```

Run — FAIL.

- [ ] **Step 2: Implement**

```typescript
// src/anonymize.ts
const PATTERNS: Array<[string, RegExp]> = [
  ['uuid', /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i],
  ['street address', /\b\d{2,6}\s+(?:[NSEW]\.?\s+)?[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Way|Ct|Court|Pl|Place)\b/],
  ['coordinates', /-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}/],
  ['dollar amount', /\$\s?\d[\d,]*(?:\.\d+)?/],
  ['zip in address context', /\b[A-Z]{2}\s+\d{5}\b/],
]

export function anonymizeFact(text: string, registry: string[]): { ok: true; text: string } | { ok: false; reasons: string[] } {
  const reasons: string[] = []
  const lower = text.toLowerCase()
  for (const name of registry) {
    if (name.length >= 4 && lower.includes(name.toLowerCase())) reasons.push(`registry name: category=client/asset identifier`)
  }
  for (const [label, re] of PATTERNS) if (re.test(text)) reasons.push(label)
  return reasons.length ? { ok: false, reasons: [...new Set(reasons)] } : { ok: true, text }
}
```

```typescript
// src/registry.ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!)
let cache: { at: number; names: string[] } | null = null

export async function getRegistry(): Promise<string[]> {
  if (cache && Date.now() - cache.at < 3_600_000) return cache.names
  const [orgs, assets] = await Promise.all([
    supabase.from('organizations').select('name'),
    supabase.from('assets').select('name, building_name, street_address'),
  ])
  const names = [
    ...(orgs.data ?? []).map(o => o.name),
    ...(assets.data ?? []).flatMap(a => [a.name, a.building_name, a.street_address]),
  ].filter((n): n is string => !!n && n.length >= 4)
  cache = { at: Date.now(), names }
  return names
}
```

- [ ] **Step 3: Tests pass; commit** — `git commit -m "feat: anonymization gate + registry"`

---

### Task 6: Hindsight client + shared-expertise tools

**Files:**
- Create: `~/verifier-mcp/src/hindsight.ts`, `~/verifier-mcp/src/expertise.ts`
- Test: `~/verifier-mcp/test/expertise.test.ts`

**Interfaces:**
- Consumes: `anonymizeFact`, `getRegistry` (Task 5).
- Produces:
  - `hindsightCall(tool: string, args: Record<string, unknown>): Promise<any>` — JSON-RPC `tools/call` POST to `process.env.HINDSIGHT_MCP_URL` with `Authorization: Bearer ${process.env.HINDSIGHT_API_KEY}`, parses `data:`-prefixed SSE or plain JSON response, returns `result.structuredContent ?? JSON.parse(result.content[0].text)`.
  - `retainSharedExpertise(input: { fact: string; domain: 'vendor-quirk'|'jurisdiction'|'benchmark-prior'|'methodology'|'source-reliability'; evidence: Array<{ source: string; ref: string }>; confirmed_finding_id?: string }): Promise<{ retained: boolean; tier?: 'validated'; action?: 'add'|'update'|'noop'; error?: string; reasons?: string[] }>`
  - `recallExpertise(input: { query: string; tiers?: string[]; fiduciary?: boolean }): Promise<Array<{ text: string; tier: string; provenance: string }>>`

- [ ] **Step 1: Failing tests** (hindsight mocked with vitest `vi.mock`)

```typescript
// test/expertise.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../src/hindsight.js', () => ({ hindsightCall: vi.fn(async () => ({ results: [] })) }))
vi.mock('../src/registry.js', () => ({ getRegistry: vi.fn(async () => ['Cortland']) }))
import { retainSharedExpertise } from '../src/expertise.js'
import { hindsightCall } from '../src/hindsight.js'

beforeEach(() => vi.clearAllMocks())

describe('retainSharedExpertise', () => {
  const evidence = [{ source: 'audit', ref: 'doc-a' }, { source: 'shovels', ref: 'permit-b' }]

  it('rejects with fewer than 2 sources and no confirmed finding', async () => {
    const r = await retainSharedExpertise({ fact: 'generic fact', domain: 'methodology', evidence: [evidence[0]] })
    expect(r.retained).toBe(false)
    expect(r.error).toMatch(/2 independent sources/i)
  })
  it('rejects identifying facts loudly with reasons', async () => {
    const r = await retainSharedExpertise({ fact: 'Cortland audits are wrong', domain: 'vendor-quirk', evidence })
    expect(r.retained).toBe(false)
    expect(r.reasons?.length).toBeGreaterThan(0)
  })
  it('retains a clean dual-source fact into the shared bank', async () => {
    const r = await retainSharedExpertise({ fact: 'AEI audits report gas in GJ', domain: 'vendor-quirk', evidence })
    expect(r).toMatchObject({ retained: true, tier: 'validated', action: 'add' })
    const retainCall = (hindsightCall as any).mock.calls.find((c: any[]) => c[0] === 'retain')
    expect(retainCall[1].bank_id).toBe('soapbox-expertise')
  })
  it('NOOPs when a near-duplicate already exists', async () => {
    ;(hindsightCall as any).mockImplementation(async (tool: string) =>
      tool === 'recall' ? { results: [{ text: 'AEI audits report gas in GJ', score: 0.97 }] } : {})
    const r = await retainSharedExpertise({ fact: 'AEI audits report gas in GJ', domain: 'vendor-quirk', evidence })
    expect(r.action).toBe('noop')
  })
})
```

Run — FAIL.

- [ ] **Step 2: Implement hindsight client**

```typescript
// src/hindsight.ts
let rpcId = 0
export async function hindsightCall(tool: string, args: Record<string, unknown>): Promise<any> {
  const res = await fetch(process.env.HINDSIGHT_MCP_URL!, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      Authorization: `Bearer ${process.env.HINDSIGHT_API_KEY}`,
    },
    body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: 'tools/call', params: { name: tool, arguments: args } }),
    signal: AbortSignal.timeout(30_000),
  })
  if (!res.ok) throw new Error(`hindsight ${tool}: HTTP ${res.status}`)
  const raw = await res.text()
  const json = raw.startsWith('event:') || raw.includes('\ndata: ')
    ? JSON.parse(raw.slice(raw.indexOf('data: ') + 6).split('\n')[0])
    : JSON.parse(raw)
  if (json.error) throw new Error(`hindsight ${tool}: ${json.error.message}`)
  const r = json.result
  if (r?.structuredContent) return r.structuredContent
  try { return JSON.parse(r?.content?.[0]?.text ?? '{}') } catch { return r?.content?.[0]?.text }
}
```

**Verification sub-step (executor):** confirm hindsight's actual `retain`/`recall` argument names before finalizing `expertise.ts`:
`curl -s -X POST $HINDSIGHT_MCP_URL -H "Authorization: Bearer $HINDSIGHT_API_KEY" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | grep -o '"name":"retain".*"required":\[[^]]*\]' | head -c 400`
(URL/key from Vaultwarden item "Hindsight Memory (Railway)". Expected per memory-layer-evaluation: recall takes `{bank_id, query}`; retain takes `{bank_id, content|input}` — adjust the two call sites to the schema you observe.)

- [ ] **Step 3: Implement expertise tools**

```typescript
// src/expertise.ts
import { hindsightCall } from './hindsight.js'
import { anonymizeFact } from './anonymize.js'
import { getRegistry } from './registry.js'

const BANK = 'soapbox-expertise'
const DUP_THRESHOLD = 0.9

type Evidence = { source: string; ref: string }
type RetainInput = { fact: string; domain: string; evidence: Evidence[]; confirmed_finding_id?: string }

export async function retainSharedExpertise(input: RetainInput) {
  const distinctSources = new Set(input.evidence.map(e => e.source)).size
  if (distinctSources < 2 && !input.confirmed_finding_id) {
    return { retained: false, error: 'Tier gate: requires evidence from >=2 independent sources or a confirmed_finding_id. Retain to the org bank via the memory plugin instead.' }
  }
  const gate = anonymizeFact(input.fact, await getRegistry())
  if (!gate.ok) {
    return { retained: false, error: 'Anonymization gate: fact contains identifying information and was NOT retained.', reasons: gate.reasons }
  }
  const similar = await hindsightCall('recall', { bank_id: BANK, query: gate.text })
  const top = (similar?.results ?? [])[0]
  if (top && (top.score ?? 0) >= DUP_THRESHOLD) return { retained: true, tier: 'validated' as const, action: 'noop' as const }
  await hindsightCall('retain', {
    bank_id: BANK,
    content: `[tier:validated] [domain:${input.domain}] [valid-from:${new Date().toISOString().slice(0, 10)}] ${gate.text} (provenance: ${input.evidence.map(e => e.source).join(' + ')}, de-identified)`,
  })
  return { retained: true, tier: 'validated' as const, action: 'add' as const }
}

export async function recallExpertise(input: { query: string; tiers?: string[]; fiduciary?: boolean }) {
  const out = await hindsightCall('recall', { bank_id: BANK, query: input.query })
  const wanted = input.fiduciary ? ['validated'] : (input.tiers ?? ['validated', 'provisional'])
  return (out?.results ?? [])
    .map((r: any) => ({
      text: r.text as string,
      tier: (r.text?.match(/\[tier:(\w+)\]/)?.[1] ?? 'provisional') as string,
      provenance: r.text?.match(/\(provenance: ([^)]+)\)/)?.[1] ?? 'unknown',
    }))
    .filter((r: any) => wanted.includes(r.tier))
}
```

- [ ] **Step 4: Tests pass; commit** — `git commit -m "feat: shared-expertise retention with tier + anonymization gates"`

---

### Task 7: Findings ledger

**Files:**
- Create: `~/verifier-mcp/src/ledger.ts`
- Test: `~/verifier-mcp/test/ledger.test.ts`

**Interfaces:**
- Consumes: Supabase service client; soapbox-api `POST /internal/index-file` (Task 3) with `Authorization: Bearer ${process.env.MCP_SERVER_SECRET}`.
- Produces:
  - `recordFinding(scope: { portfolioId: string; assetId?: string }, finding: { claim: string; verdict: 'verified'|'refuted'|'conflict'|'unverifiable'; severity: 'low'|'medium'|'high'; kind: 'risk'|'opportunity'|'data-quality'; evidence: string[]; sources: string[] }): Promise<{ id: string }>`
  - `listFindings(scope, status?: 'open'|'confirmed'|'dismissed'): Promise<Finding[]>`
  - `resolveFinding(scope, id: string, resolution: 'confirmed'|'dismissed', note: string): Promise<Finding>`
  - `verificationStatus(scope): Promise<{ pass: boolean; open_high: number; open_total: number }>` (pass = zero open high-severity findings)
- Storage model: one storage object per scope at `<assetId | 'portfolio-'+portfolioId>/verification/findings.jsonl` in bucket `asset-files` (read-modify-write; findings volume is small), plus a rendered `findings.md` registered as a `files` row (folder `Verification`) and reindexed via the internal endpoint after every change. The jsonl is the source of truth; the md is the client-visible render.

- [ ] **Step 1: Failing tests** — test the pure parts (`renderMarkdown`, `applyResolution`, `computeStatus`) with fixtures; mock Supabase for one `recordFinding` round-trip asserting a `files` upsert and an index call.

```typescript
// test/ledger.test.ts
import { describe, it, expect } from 'vitest'
import { renderMarkdown, applyResolution, computeStatus, type Finding } from '../src/ledger.js'

const f = (over: Partial<Finding> = {}): Finding => ({
  id: 'f1', ts: '2026-07-02T00:00:00Z', claim: 'DHW installed 2014', verdict: 'conflict',
  severity: 'high', kind: 'risk', evidence: ['audit says 2014', 'permit says 2016'],
  sources: ['audit', 'shovels'], status: 'open', ...over,
})

describe('ledger pure functions', () => {
  it('renders markdown with status badges and sources', () => {
    const md = renderMarkdown([f()])
    expect(md).toContain('DHW installed 2014')
    expect(md).toMatch(/open/i)
    expect(md).toContain('shovels')
  })
  it('applyResolution sets status + note and is idempotent-safe', () => {
    const done = applyResolution([f()], 'f1', 'confirmed', 'client verified')
    expect(done.find(x => x.id === 'f1')!.status).toBe('confirmed')
    expect(() => applyResolution(done, 'missing', 'dismissed', '')).toThrow(/not found/i)
  })
  it('computeStatus fails only on open high severity', () => {
    expect(computeStatus([f()]).pass).toBe(false)
    expect(computeStatus([f({ severity: 'medium' })]).pass).toBe(true)
    expect(computeStatus([f({ status: 'confirmed' })]).pass).toBe(true)
  })
})
```

- [ ] **Step 2: Implement** — pure functions + Supabase I/O:

```typescript
// src/ledger.ts (shape; I/O uses @supabase/supabase-js storage + files table)
import { createClient } from '@supabase/supabase-js'
import { randomUUID } from 'node:crypto'

export type Finding = {
  id: string; ts: string; claim: string
  verdict: 'verified' | 'refuted' | 'conflict' | 'unverifiable'
  severity: 'low' | 'medium' | 'high'; kind: 'risk' | 'opportunity' | 'data-quality'
  evidence: string[]; sources: string[]
  status: 'open' | 'confirmed' | 'dismissed'; resolution_note?: string
}

export function renderMarkdown(findings: Finding[]): string {
  const line = (x: Finding) =>
    `## ${x.kind === 'opportunity' ? '💡' : '⚠️'} ${x.claim}\n\n` +
    `- **Verdict:** ${x.verdict} · **Severity:** ${x.severity} · **Status:** ${x.status}\n` +
    `- **Sources:** ${x.sources.join(', ')}\n` +
    x.evidence.map(e => `- ${e}`).join('\n') +
    (x.resolution_note ? `\n- **Resolution:** ${x.resolution_note}` : '') + '\n'
  return `# Verification Findings\n\n_Maintained by the Soapbox verifier plugin. Confirm or dismiss findings in any thread._\n\n${findings.map(line).join('\n')}`
}

export function applyResolution(findings: Finding[], id: string, resolution: 'confirmed' | 'dismissed', note: string): Finding[] {
  const idx = findings.findIndex(x => x.id === id)
  if (idx === -1) throw new Error(`finding ${id} not found`)
  const next = [...findings]
  next[idx] = { ...next[idx], status: resolution, resolution_note: note }
  return next
}

export function computeStatus(findings: Finding[]): { pass: boolean; open_high: number; open_total: number } {
  const open = findings.filter(x => x.status === 'open')
  const openHigh = open.filter(x => x.severity === 'high')
  return { pass: openHigh.length === 0, open_high: openHigh.length, open_total: open.length }
}
```

I/O half (same file): `loadFindings(scope)` reads the jsonl storage object (`[]` if absent); `saveFindings(scope, findings)` writes jsonl + md to storage, upserts the `files` row for `findings.md` (name `findings.md`, folder `Verification`, mime `text/markdown`, `asset_id` or `portfolio_id` per scope, size from buffer), then POSTs `${process.env.SOAPBOX_API_URL}/internal/index-file` with the files row id. Exported `recordFinding` / `listFindings` / `resolveFinding` / `verificationStatus` compose load→mutate→save. On any hindsight/API failure: throw — the MCP layer converts to a structured tool error (never silent).

- [ ] **Step 3: Tests pass; commit** — `git commit -m "feat: findings ledger with Files-backed jsonl+md"`

---

### Task 8: MCP server wiring

**Files:**
- Create: `~/verifier-mcp/src/index.ts`
- Test: `~/verifier-mcp/test/server.test.ts`

**Interfaces:**
- Consumes: all prior modules.
- Produces: streamable-HTTP MCP at `/mcp` exposing tools `get_verification_checklist`, `record_finding`, `list_findings`, `resolve_finding`, `verification_status`, `retain_shared_expertise`, `recall_expertise`. Scope context comes ONLY from trusted headers `x-soapbox-portfolio-id` / `x-soapbox-organization-id` (injected by the connector proxy, Task 2); `asset_id` is a tool parameter validated to belong to that portfolio (Supabase lookup).

- [ ] **Step 1: Failing test** — spin the express app on an ephemeral port, POST a `tools/list`, assert all seven tool names; POST `tools/call get_verification_checklist {data_type:'energy'}` with the trusted headers and assert a rubric comes back.

```typescript
// test/server.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { createApp } from '../src/index.js'
import type { Server } from 'node:http'

let server: Server, base: string
beforeAll(async () => {
  server = createApp().listen(0)
  base = `http://localhost:${(server.address() as any).port}`
})
afterAll(() => server.close())

const rpc = (method: string, params?: any) =>
  fetch(`${base}/mcp`, { method: 'POST', headers: {
    'Content-Type': 'application/json', Accept: 'application/json, text/event-stream',
    'x-soapbox-portfolio-id': 'pf-test', 'x-soapbox-organization-id': 'org-test',
  }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) }).then(r => r.text())

describe('verifier mcp server', () => {
  it('lists all seven tools', async () => {
    const raw = await rpc('tools/list')
    for (const t of ['get_verification_checklist','record_finding','list_findings','resolve_finding','verification_status','retain_shared_expertise','recall_expertise'])
      expect(raw).toContain(t)
  })
  it('serves a checklist', async () => {
    const raw = await rpc('tools/call', { name: 'get_verification_checklist', arguments: { data_type: 'energy' } })
    expect(raw).toMatch(/BPD/)
  })
})
```

- [ ] **Step 2: Implement `createApp()`** — express + `McpServer` + `StreamableHTTPServerTransport` (stateless mode), following `~/brave-search-mcp/src/index.ts` as the wiring reference. Register each tool with a zod schema; handlers pull `portfolioId`/`orgId` from the request headers via express middleware that stashes them in AsyncLocalStorage (or per-request transport instantiation, matching whichever pattern brave-search-mcp uses — copy it). `main()` guard: `if (process.argv[1] === fileURLToPath(import.meta.url))` listen on `process.env.PORT ?? 8080`; export `createApp` for tests. Health route `GET /health` → `{ok:true}`.

- [ ] **Step 3: Tests pass; `npm run build` clean; commit** — `git commit -m "feat: MCP server wiring with trusted-header tenancy"`

---

### Task 9: Verification prompt injection (soapbox-api)

**Files:**
- Modify: `~/soapbox-platform/apps/api/src/services/agent-config.ts` (asset prompt assembly ~line 434 area; portfolio prompt ~line 828)
- Test: `~/soapbox-platform/apps/api/test/services/verification-prompt.test.ts`

**Interfaces:**
- Produces: exported `VERIFICATION_PROMPT: string`, appended to asset and portfolio system prompts whenever the portfolio has an enabled `plugin_verifier` connector (same detection pattern as the Audette degraded check — grep `AUDETTE_DEGRADED_PROMPT` usage and mirror it).

- [ ] **Step 1: Failing test**

```typescript
// test/services/verification-prompt.test.ts
import { describe, it, expect } from 'vitest'
import { VERIFICATION_PROMPT } from '../../src/services/agent-config.js'

describe('VERIFICATION_PROMPT', () => {
  it('encodes the five behaviors', () => {
    for (const needle of ['recall_expertise', 'get_verification_checklist', 'retain', 'record_finding', 'provisional'])
      expect(VERIFICATION_PROMPT).toContain(needle)
  })
})
```

- [ ] **Step 2: Implement** — add to agent-config.ts:

```typescript
export const VERIFICATION_PROMPT = `

## Data Verification (always active)
You have verifier and memory tools. Apply them continuously:
1. RECALL BEFORE ASSERT — before stating a data fact, check memory: recall (org bank) and recall_expertise (shared knowledge). Cite tier; never present a provisional fact as settled.
2. VERIFY DATA CLAIMS — for any material data claim (energy figures, equipment, physical attributes, regulatory status, financials, incentives), fetch get_verification_checklist for the data type and follow its rubric using your data tools. Financial figures must come from deterministic engines or cited sources — never compute numbers yourself.
3. RECORD FINDINGS — when verification produces a verdict (verified, refuted, conflict, unverifiable), call record_finding. Risks AND opportunities both count. When the user confirms or dismisses a finding, call resolve_finding.
4. RETAIN WHAT YOU LEARN — validated client-specific facts go to memory (retain). Generalizable lessons (vendor quirks, jurisdiction gotchas, benchmark priors) go to retain_shared_expertise — it will refuse anything identifying; do not work around a refusal.
5. NEVER FAIL SILENTLY — if verifier or memory tools error, tell the user which capability is degraded.`
```

Append it in both prompt-assembly sites, conditioned on the verifier connector being installed+enabled (mirror the existing `audetteDegraded` connector lookup — same query, `name = 'plugin_verifier'`).

- [ ] **Step 3: Tests + typecheck pass; commit** — `git commit -m "feat(api): verification prompt injection for asset+portfolio agents"`

---

### Task 10: Deploy verifier-mcp + register both plugins

**Files:**
- Create: `~/verifier-mcp/README.md` (env table + deploy notes)
- Modify: `~/soapbox-platform/apps/api/src/services/portfolio.ts` (corePlugins array, ~line 49)

**Steps:**

- [ ] **Step 1: Push repo** — create `soapboxbuild/verifier-mcp` (private) via `gh repo create`, push main.
- [ ] **Step 2: Deploy to Railway** — project **soapbox-mcps** (`e5434a34…`, per standing rule ALL MCPs go here): create service `verifier-mcp` from the GitHub repo; set env `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (vault "Supabase Service Role Key"), `HINDSIGHT_MCP_URL` + `HINDSIGHT_API_KEY` (vault "Hindsight Memory (Railway)"), `MCP_SERVER_SECRET` (vault "Soapbox Platform MCP Server Secret"), `SOAPBOX_API_URL=https://soapbox-api-production.up.railway.app`. Custom domain `verifier.mcp.soapbox.build` **and immediately add the CNAME in Cloudflare** (Railway does not set DNS — standing rule).
- [ ] **Step 3: Smoke** — `curl -s https://verifier.mcp.soapbox.build/health` → `{"ok":true}`; `tools/list` via curl returns 7 tools.
- [ ] **Step 4: Core plugins list** — append to the `corePlugins` array in `createPortfolio`:

```typescript
{ plugin_id: 'memory',   name: 'plugin_memory',   description: 'Persistent validated memory (hindsight) — org-scoped bank, pinned server-side.', mcp_url: process.env.HINDSIGHT_MCP_URL ?? 'https://agent-memory.soapbox.build/mcp' },
{ plugin_id: 'verifier', name: 'plugin_verifier', description: 'Data verification: checklists, findings ledger, shared expertise memory.',        mcp_url: 'https://verifier.mcp.soapbox.build/mcp' },
```

Then check how `installed_plugins` rows become `asset_connectors` rows for MCP plugins (grep `installed_plugins` → connector creation in apps/api; the energy-star/audette connectors carry `api_key`). For `plugin_memory` the connector `api_key` must be the hindsight API key (server-side only — the proxy strips and re-adds it upstream); for `plugin_verifier` no upstream key is needed (proxy token auth alone) — set `api_key` null and confirm the proxy forwards without Authorization in that case (it does: `if (accessToken)` guard).

- [ ] **Step 5: plugin_catalog rows + backfill existing portfolios** — run via Supabase MCP:

```sql
insert into plugin_catalog (plugin_id, name, description, mcp_url) values
 ('memory','Memory','Persistent validated memory (hindsight), org-scoped.','https://agent-memory.soapbox.build/mcp'),
 ('verifier','Data Verification Agent','Checklists, findings ledger, shared expertise.','https://verifier.mcp.soapbox.build/mcp');

-- backfill: one asset_connectors row per existing portfolio per plugin
insert into asset_connectors (portfolio_id, scope, name, url, description, enabled, plugin_id, api_key)
select p.id, 'portfolio', 'plugin_memory', 'https://agent-memory.soapbox.build/mcp', 'Persistent validated memory', true, 'memory', '<HINDSIGHT_API_KEY from vault>'
from portfolios p where not exists (select 1 from asset_connectors ac where ac.portfolio_id=p.id and ac.name='plugin_memory');

insert into asset_connectors (portfolio_id, scope, name, url, description, enabled, plugin_id)
select p.id, 'portfolio', 'plugin_verifier', 'https://verifier.mcp.soapbox.build/mcp', 'Data verification agent', true, 'verifier'
from portfolios p where not exists (select 1 from asset_connectors ac where ac.portfolio_id=p.id and ac.name='plugin_verifier');
```

(Before running: confirm `plugin_catalog` column names with `select * from plugin_catalog limit 1` and adapt — the catalog also drives auto-provisioning per [[feedback-plugin-strategy]]; if a `core`/`auto_install` flag column exists, set it.)

- [ ] **Step 6: Push soapbox-platform main; confirm Railway deploy SUCCESS; commit-verify loop.**

---

### Task 11: E2E pilot on Cortland

**No new files — verification task. Evidence required for every claim (verification-before-completion).**

- [ ] **Step 1:** In app.soapbox.build (service account, Cortland org), open a thread on `Cortland Westminster` and prompt: "Verify the DHW heater install year in our data against permits and the audit." Confirm the agent: calls `get_verification_checklist`, uses Shovels + RAG, calls `record_finding`.
- [ ] **Step 2:** Confirm `Verification/findings.md` appears in the asset's Files view and its `files` row reaches `indexing_status='indexed'`.
- [ ] **Step 3:** Ask the agent to generalize a lesson; confirm `retain_shared_expertise` succeeds for a clean fact AND is refused (with reasons) when the fact names Cortland — check verifier Railway logs show category-only logging.
- [ ] **Step 4:** New session, same asset: "What do we know about AEI audit quirks?" — confirm `recall_expertise` surfaces the retained fact with tier + de-identified provenance.
- [ ] **Step 5:** Attempt cross-tenant memory: in a Greystar thread, `recall` must NOT return Cortland org-bank facts (bank pinning proof). Record the transcript refs in the completion report.
- [ ] **Step 6:** Update memory files ([[cortland-onboarding]], new [[verifier-plugin]] memory) with deployed state + gotchas.

---

## Self-Review Notes

- Spec coverage: memory plugin (Tasks 1,2,10), verifier tools (4–8), prompt injection (9), core install + backfill (10), pilot (11). Loops + report gate intentionally deferred (spec rollout v1.1/v1.2). Open question 1 (bank auto-creation): resolved lazily — hindsight creates banks on first retain; verify during Task 11 Step 4.
- Type consistency: `Finding`, `Checklist`, tool names checked across Tasks 4–9.
- No placeholders: the two "confirm schema/columns" steps carry exact commands and expected shapes — they are verification steps, not deferrals.
