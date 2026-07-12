# Stage Demo Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the three stage demos (RSRA, ESG Profile, Decarb) render their deliverable deterministically within a ~60–90s window by replaying a recorded, verified golden run instead of a variable live agent run.

**Architecture:** A short-circuit branch at the top of the managed-agent runtime's `sendMessage` generator: when the thread belongs to the Demo org and the prompt classifies to a known workflow with a frozen fixture, yield the fixture's recorded `RuntimeEvent` timeline on a scaled schedule, then call the real `renderReport(...)` with the fixture's captured `fill_report` payload (rendering onto the live asset through the existing template + gate path), yield the resulting `artifact` and `done`, and `return` before the live Anthropic session ever opens. Fixtures are recorded from real service-account runs by an ops script, scrub-gated, and committed into the API repo as JSON so the demo is offline-deterministic. Client is unchanged — replayed events flow through the existing SSE parser.

**Tech Stack:** TypeScript (Node/NodeNext ESM, `.js` import specifiers), Vitest 3, Hono API (`soapbox-platform/apps/api`), Supabase, Anthropic Sessions API. Fixture recorder is a Node ESM script in `soapbox-agent/demo-staging`.

## Global Constraints

- **Demo org id:** `8ebc72a7-dca1-4cb1-be02-eed12f38340f`. All replay behavior gated to this org; unreachable elsewhere.
- **Shared write DB:** Supabase ref `fplbvanvwvnviczozwhz` backs BOTH prod and stage. Every fixture-capture write MUST be filtered to the Demo org/portfolio (portfolio `3b683c32-ea8e-4851-b350-fd7b85a60e2e`).
- **Scrub gate:** every frozen fixture's narration text MUST pass `demo-staging/scrub-check.py` (fail-closed) before commit. Pseudonyms only.
- **`artifacts.asset_id` is NOT NULL** (`supabase/migrations/20260612000004_artifacts.sql:7`). Replay must render onto a non-null asset UUID (`params.assetId`); a portfolio-scope thread (`assetId === null`) must fall through to the live path, never attempt a demo render.
- **Import specifiers:** intra-package imports use explicit `.js` extension (NodeNext), e.g. `import { isDemoOrg } from '../lib/demo.js'`.
- **Fixture reflects current verified output:** a fixture may only be frozen from a run that passes the Phase 9.9 report-integrity checks (separated VaR block, stepped/distinct sensitivity, Cambium grid factor, sane measure sizing). The stale fallback artifact `86943ce4` is NOT a valid fixture source.
- **No behavior change for real orgs:** the live path (open Anthropic session, stream, persist) must be byte-for-byte unchanged when `isDemoOrg` is false or no fixture matches.

---

### Task 1: Demo org constant + workflow classifier (`lib/demo.ts`)

**Files:**
- Create: `soapbox-platform/apps/api/src/lib/demo.ts`
- Test: `soapbox-platform/apps/api/src/lib/__tests__/demo.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `const DEMO_ORG_ID: string` (`process.env.DEMO_ORG_ID ?? '8ebc72a7-dca1-4cb1-be02-eed12f38340f'`)
  - `function isDemoOrg(orgId: string | null | undefined): boolean`
  - `type DemoWorkflow = 'rsra' | 'esg' | 'decarb'`
  - `function classifyDemoWorkflow(prompt: string): DemoWorkflow | null`

- [ ] **Step 1: Write the failing test**

```ts
// soapbox-platform/apps/api/src/lib/__tests__/demo.test.ts
import { describe, it, expect } from 'vitest'
import { isDemoOrg, classifyDemoWorkflow, DEMO_ORG_ID } from '../demo.js'

describe('isDemoOrg', () => {
  it('matches the demo org id', () => {
    expect(isDemoOrg(DEMO_ORG_ID)).toBe(true)
  })
  it('rejects other / missing ids', () => {
    expect(isDemoOrg('11111111-1111-1111-1111-111111111111')).toBe(false)
    expect(isDemoOrg(null)).toBe(false)
    expect(isDemoOrg(undefined)).toBe(false)
  })
})

describe('classifyDemoWorkflow', () => {
  it('classifies RSRA prompts', () => {
    expect(classifyDemoWorkflow('Run a rapid sustainability risk assessment.')).toBe('rsra')
    expect(classifyDemoWorkflow('Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder.')).toBe('rsra')
  })
  it('classifies ESG prompts', () => {
    expect(classifyDemoWorkflow('Run the ESG Profile assessment for the Madison sponsor. Produce the sponsor ESG profile report.')).toBe('esg')
  })
  it('classifies decarb prompts', () => {
    expect(classifyDemoWorkflow('Show me the decarbonization plan for 4th & Madison — walk me through the measures.')).toBe('decarb')
  })
  it('returns null for unrelated prompts', () => {
    expect(classifyDemoWorkflow('What is the EUI of this building?')).toBeNull()
    expect(classifyDemoWorkflow('')).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soapbox-platform/apps/api && npx vitest run src/lib/__tests__/demo.test.ts`
Expected: FAIL — cannot resolve `../demo.js`.

- [ ] **Step 3: Write minimal implementation**

```ts
// soapbox-platform/apps/api/src/lib/demo.ts
// Demo-org scoped stage-demo support. Reachable ONLY for the Demo org id below.
export const DEMO_ORG_ID = process.env.DEMO_ORG_ID ?? '8ebc72a7-dca1-4cb1-be02-eed12f38340f'

export function isDemoOrg(orgId: string | null | undefined): boolean {
  return !!orgId && orgId === DEMO_ORG_ID
}

export type DemoWorkflow = 'rsra' | 'esg' | 'decarb'

// Ordered most-specific first. A demo prompt is presenter-typed and predictable,
// so keyword matching is sufficient and avoids any model dependency on stage.
const WORKFLOW_PATTERNS: Array<{ workflow: DemoWorkflow; re: RegExp }> = [
  { workflow: 'decarb', re: /\b(decarb|decarboni[sz]ation)\b/i },
  { workflow: 'esg', re: /\besg\b/i },
  { workflow: 'rsra', re: /\b(rsra|rapid sustainability risk)\b/i },
]

export function classifyDemoWorkflow(prompt: string): DemoWorkflow | null {
  const text = prompt ?? ''
  for (const { workflow, re } of WORKFLOW_PATTERNS) {
    if (re.test(text)) return workflow
  }
  return null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soapbox-platform/apps/api && npx vitest run src/lib/__tests__/demo.test.ts`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
cd soapbox-platform && git add apps/api/src/lib/demo.ts apps/api/src/lib/__tests__/demo.test.ts
git commit -m "feat(demo): demo-org constant + workflow classifier"
```

---

### Task 2: Fixture format + loader/validator (`services/demo-replay.ts`, part 1)

**Files:**
- Create: `soapbox-platform/apps/api/src/services/demo-replay.ts`
- Test: `soapbox-platform/apps/api/src/services/__tests__/demo-replay.load.test.ts` (uses inline fixture objects; no fixture files needed until Task 6+)

**Interfaces:**
- Consumes: `DemoWorkflow` from `../lib/demo.js`; `RuntimeEvent` from `../lib/types.js`.
- Produces:
  - `type DemoFixtureEvent = { t: number; event: RuntimeEvent }` (`t` = ms offset from run start, as recorded)
  - `type DemoRender = { template: string; title?: string; data: Record<string, unknown> }`
  - `type DemoFixture = { workflow: DemoWorkflow; version: number; targetDurationMs: number; recordedTotalMs: number; events: DemoFixtureEvent[]; render: DemoRender }`
  - `function validateFixture(raw: unknown): DemoFixture` (throws `Error` on malformed input)
  - `function loadDemoFixture(workflow: DemoWorkflow): DemoFixture | null` (reads `./demo-fixtures/<workflow>.json`; returns null if absent)

- [ ] **Step 1: Write the failing test**

```ts
// soapbox-platform/apps/api/src/services/__tests__/demo-replay.load.test.ts
import { describe, it, expect } from 'vitest'
import { validateFixture, loadDemoFixture } from '../demo-replay.js'

const good = {
  workflow: 'rsra', version: 1, targetDurationMs: 75000, recordedTotalMs: 160000,
  events: [
    { t: 0, event: { type: 'model_start' } },
    { t: 1200, event: { type: 'text_delta', delta: 'Reading the offering memorandum…' } },
    { t: 4000, event: { type: 'tool_call', toolName: 'fill_report', input: { template: 'rsra' } } },
  ],
  render: { template: 'rsra', title: 'Sample — RSRA', data: { property: { name: 'Sample' } } },
}

describe('validateFixture', () => {
  it('accepts a well-formed fixture', () => {
    const fx = validateFixture(good)
    expect(fx.workflow).toBe('rsra')
    expect(fx.events).toHaveLength(3)
    expect(fx.render.template).toBe('rsra')
  })
  it('rejects missing render payload', () => {
    expect(() => validateFixture({ ...good, render: undefined })).toThrow(/render/)
  })
  it('rejects empty events', () => {
    expect(() => validateFixture({ ...good, events: [] })).toThrow(/events/)
  })
  it('rejects non-monotonic event offsets', () => {
    const bad = { ...good, events: [{ t: 10, event: { type: 'model_start' } }, { t: 5, event: { type: 'done' } }] }
    expect(() => validateFixture(bad)).toThrow(/monotonic/)
  })
})

describe('loadDemoFixture', () => {
  it('returns null when no fixture file exists for a workflow', () => {
    // 'esg' fixture is not committed at this point in the plan
    expect(loadDemoFixture('esg')).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/demo-replay.load.test.ts`
Expected: FAIL — cannot resolve `../demo-replay.js`.

- [ ] **Step 3: Write minimal implementation**

```ts
// soapbox-platform/apps/api/src/services/demo-replay.ts
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import type { DemoWorkflow } from '../lib/demo.js'
import type { RuntimeEvent } from '../lib/types.js'

export type DemoFixtureEvent = { t: number; event: RuntimeEvent }
export type DemoRender = { template: string; title?: string; data: Record<string, unknown> }
export type DemoFixture = {
  workflow: DemoWorkflow
  version: number
  targetDurationMs: number
  recordedTotalMs: number
  events: DemoFixtureEvent[]
  render: DemoRender
}

export function validateFixture(raw: unknown): DemoFixture {
  const o = raw as Record<string, unknown>
  if (!o || typeof o !== 'object') throw new Error('demo fixture: not an object')
  if (o.workflow !== 'rsra' && o.workflow !== 'esg' && o.workflow !== 'decarb') {
    throw new Error(`demo fixture: bad workflow "${String(o.workflow)}"`)
  }
  if (typeof o.targetDurationMs !== 'number' || o.targetDurationMs <= 0) throw new Error('demo fixture: bad targetDurationMs')
  if (typeof o.recordedTotalMs !== 'number' || o.recordedTotalMs <= 0) throw new Error('demo fixture: bad recordedTotalMs')
  if (!Array.isArray(o.events) || o.events.length === 0) throw new Error('demo fixture: events must be a non-empty array')
  let prev = -1
  for (const e of o.events as DemoFixtureEvent[]) {
    if (typeof e?.t !== 'number' || !e.event || typeof (e.event as RuntimeEvent).type !== 'string') {
      throw new Error('demo fixture: malformed event entry')
    }
    if (e.t < prev) throw new Error('demo fixture: event offsets must be monotonic')
    prev = e.t
  }
  const render = o.render as DemoRender | undefined
  if (!render || typeof render.template !== 'string' || typeof render.data !== 'object' || !render.data) {
    throw new Error('demo fixture: render payload {template, data} is required')
  }
  return {
    workflow: o.workflow,
    version: typeof o.version === 'number' ? o.version : 1,
    targetDurationMs: o.targetDurationMs,
    recordedTotalMs: o.recordedTotalMs,
    events: o.events as DemoFixtureEvent[],
    render,
  }
}

const FIXTURE_DIR = join(dirname(fileURLToPath(import.meta.url)), 'demo-fixtures')

export function loadDemoFixture(workflow: DemoWorkflow): DemoFixture | null {
  try {
    const raw = readFileSync(join(FIXTURE_DIR, `${workflow}.json`), 'utf8')
    return validateFixture(JSON.parse(raw))
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === 'ENOENT') return null
    throw err // malformed committed fixture should fail loudly, not silently fall through
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/demo-replay.load.test.ts`
Expected: PASS. (The `loadDemoFixture('esg')` case passes because no `esg.json` exists yet.)

- [ ] **Step 5: Commit**

```bash
cd soapbox-platform && git add apps/api/src/services/demo-replay.ts apps/api/src/services/__tests__/demo-replay.load.test.ts
git commit -m "feat(demo): fixture format + loader/validator"
```

---

### Task 3: Replay timeline generator (`services/demo-replay.ts`, part 2)

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/demo-replay.ts`
- Test: `soapbox-platform/apps/api/src/services/__tests__/demo-replay.stream.test.ts`

**Interfaces:**
- Consumes: `DemoFixture`; `RuntimeEvent`; `renderReport`, `RenderReportResult` from `./render-report.js`.
- Produces:
  - `type ReplayCtx = { conversationId: string; assetId: string; userId: string; portfolioId: string; mcpServers?: Array<{ name: string; url: string }> }`
  - `async function* replayDemoFixture(fixture: DemoFixture, ctx: ReplayCtx): AsyncGenerator<RuntimeEvent>`
  - Injectable deps for testing via an optional 3rd arg `deps: { sleep?: (ms: number) => Promise<void>; render?: typeof renderReport } = {}`.

Behavior:
1. Scale each recorded `t` by `factor = targetDurationMs / recordedTotalMs`; before each event, `sleep(scaledT - lastScaledT)`.
2. Yield each `fixture.events[i].event` in order.
3. After the last event, call `render({ data, template, title, artifactId: randomUUID(), conversationId, assetId, userId, mcpServers })`.
4. On `ok: true`: yield `{ type: 'tool_result', toolName: 'fill_report', success: true }`, then `{ type: 'artifact', artifactId, artifactType: 'html', title, content: html }`, then `{ type: 'done' }`.
5. On `ok: false`: yield `{ type: 'render_blocked', reason: blockedMessage }` then `{ type: 'error', message: blockedMessage }`. (Fixture data should never trip a gate, but fail visibly, not silently.)

- [ ] **Step 1: Write the failing test**

```ts
// soapbox-platform/apps/api/src/services/__tests__/demo-replay.stream.test.ts
import { describe, it, expect, vi } from 'vitest'
import { replayDemoFixture, type DemoFixture } from '../demo-replay.js'
import type { RuntimeEvent } from '../../lib/types.js'

const fixture: DemoFixture = {
  workflow: 'rsra', version: 1, targetDurationMs: 40, recordedTotalMs: 80,
  events: [
    { t: 0, event: { type: 'model_start' } },
    { t: 40, event: { type: 'text_delta', delta: 'Reading the OM…' } },
    { t: 80, event: { type: 'tool_call', toolName: 'fill_report', input: { template: 'rsra' } } },
  ],
  render: { template: 'rsra', title: 'X — RSRA', data: { property: { name: 'X' } } },
}

const ctx = { conversationId: 'c1', assetId: 'a1', userId: 'u1', portfolioId: 'p1' }

async function collect(fx: DemoFixture, render: any) {
  const sleeps: number[] = []
  const sleep = (ms: number) => { sleeps.push(ms); return Promise.resolve() }
  const out: RuntimeEvent[] = []
  for await (const ev of replayDemoFixture(fx, ctx, { sleep, render })) out.push(ev)
  return { out, sleeps }
}

describe('replayDemoFixture', () => {
  it('yields recorded events then a rendered artifact and done', async () => {
    const render = vi.fn().mockResolvedValue({ ok: true, artifactId: 'art-1', html: '<html>ok</html>', fileSaved: null })
    const { out } = await collect(fixture, render)
    expect(out.map(e => e.type)).toEqual(['model_start', 'text_delta', 'tool_call', 'tool_result', 'artifact', 'done'])
    const artifact = out.find(e => e.type === 'artifact') as Extract<RuntimeEvent, { type: 'artifact' }>
    expect(artifact.artifactId).toBe('art-1')
    expect(artifact.content).toBe('<html>ok</html>')
    expect(render).toHaveBeenCalledWith(expect.objectContaining({ template: 'rsra', assetId: 'a1', conversationId: 'c1', userId: 'u1' }))
  })

  it('scales sleeps to the target duration (half of recorded here)', async () => {
    const render = vi.fn().mockResolvedValue({ ok: true, artifactId: 'a', html: '<x/>', fileSaved: null })
    const { sleeps } = await collect(fixture, render)
    // recorded gaps 0,40,40 -> scaled by 40/80=0.5 -> 0,20,20
    expect(sleeps).toEqual([0, 20, 20])
  })

  it('emits render_blocked + error when the gate rejects the payload', async () => {
    const render = vi.fn().mockResolvedValue({ ok: false, blockedMessage: 'gate: bad curve' })
    const { out } = await collect(fixture, render)
    expect(out.map(e => e.type)).toEqual(['model_start', 'text_delta', 'tool_call', 'render_blocked', 'error'])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/demo-replay.stream.test.ts`
Expected: FAIL — `replayDemoFixture` is not exported.

- [ ] **Step 3: Write minimal implementation** (append to `demo-replay.ts`)

```ts
import { randomUUID } from 'node:crypto'
import { renderReport } from './render-report.js'

export type ReplayCtx = {
  conversationId: string
  assetId: string
  userId: string
  portfolioId: string
  mcpServers?: Array<{ name: string; url: string }>
}

type ReplayDeps = { sleep?: (ms: number) => Promise<void>; render?: typeof renderReport }

const defaultSleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

export async function* replayDemoFixture(
  fixture: DemoFixture,
  ctx: ReplayCtx,
  deps: ReplayDeps = {},
): AsyncGenerator<RuntimeEvent> {
  const sleep = deps.sleep ?? defaultSleep
  const render = deps.render ?? renderReport
  const factor = fixture.targetDurationMs / fixture.recordedTotalMs

  let lastScaled = 0
  for (const { t, event } of fixture.events) {
    const scaled = Math.round(t * factor)
    await sleep(Math.max(0, scaled - lastScaled))
    lastScaled = scaled
    yield event
  }

  const result = await render({
    data: fixture.render.data,
    template: fixture.render.template,
    title: fixture.render.title,
    artifactId: randomUUID(),
    conversationId: ctx.conversationId,
    assetId: ctx.assetId,
    userId: ctx.userId,
    mcpServers: ctx.mcpServers,
    logTag: `demo-replay:${fixture.workflow}`,
  })

  if (result.ok) {
    yield { type: 'tool_result', toolName: 'fill_report', success: true }
    yield {
      type: 'artifact',
      artifactId: result.artifactId,
      artifactType: 'html',
      title: fixture.render.title ?? `${fixture.render.template.toUpperCase()} Report`,
      content: result.html,
    }
    yield { type: 'done' }
  } else {
    yield { type: 'render_blocked', reason: result.blockedMessage }
    yield { type: 'error', message: result.blockedMessage }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/demo-replay.stream.test.ts`
Expected: PASS (3 cases).

- [ ] **Step 5: Commit**

```bash
cd soapbox-platform && git add apps/api/src/services/demo-replay.ts apps/api/src/services/__tests__/demo-replay.stream.test.ts
git commit -m "feat(demo): timed replay generator that re-renders via renderReport"
```

---

### Task 4: Wire the short-circuit into `sendMessage`

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/managed-agents-runtime.ts` (top of `sendMessage`, ~line 387–392)
- Test: `soapbox-platform/apps/api/src/services/__tests__/managed-agents-runtime.demo-branch.test.ts`

**Interfaces:**
- Consumes: `isDemoOrg`, `classifyDemoWorkflow` from `../lib/demo.js`; `loadDemoFixture`, `replayDemoFixture` from `./demo-replay.js`.
- Produces: no new exports; adds a private helper `resolveOrgId(portfolioId: string): Promise<string | null>` (via `supabase.from('portfolios').select('organization_id').eq('id', portfolioId).single()`) and the branch.

The branch runs at the very top of `sendMessage`, before the `user.message` is sent (line 392) and before `resilientEventStream()` opens (line 493). Guard order: `params.assetId` non-null → org is demo → prompt classifies → fixture exists. If all true, delegate to `replayDemoFixture` and `return`. Otherwise proceed to the existing live path unchanged.

- [ ] **Step 1: Write the failing test**

```ts
// soapbox-platform/apps/api/src/services/__tests__/managed-agents-runtime.demo-branch.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const { supabaseFromSpy, replaySpy, loadSpy } = vi.hoisted(() => ({
  supabaseFromSpy: vi.fn(),
  replaySpy: vi.fn(),
  loadSpy: vi.fn(),
}))

vi.mock('../../lib/supabase.js', () => ({ supabase: { from: supabaseFromSpy } }))
vi.mock('../demo-replay.js', () => ({
  loadDemoFixture: loadSpy,
  replayDemoFixture: replaySpy,
}))
// Anthropic client must never be touched on the demo branch:
vi.mock('../../lib/anthropic.js', () => ({ anthropic: { beta: { messages: {} } } }))

function mockOrg(orgId: string) {
  supabaseFromSpy.mockReturnValue({
    select: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    single: vi.fn().mockResolvedValue({ data: { organization_id: orgId }, error: null }),
  })
}

const DEMO = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'

describe('sendMessage demo short-circuit', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('replays the fixture and never opens a live session for a demo-org RSRA prompt', async () => {
    mockOrg(DEMO)
    loadSpy.mockReturnValue({ workflow: 'rsra' }) // opaque fixture; replay is mocked
    replaySpy.mockImplementation(async function* () {
      yield { type: 'model_start' }
      yield { type: 'done' }
    })
    const { ManagedAgentsRuntime } = await import('../managed-agents-runtime.js')
    const rt = new ManagedAgentsRuntime()
    const events: any[] = []
    for await (const e of rt.sendMessage('ext-session', {
      content: 'Run a rapid sustainability risk assessment.',
      assetId: 'asset-1', portfolioId: 'pf-1', conversationId: 'conv-1', userId: 'u-1',
    })) events.push(e)
    expect(loadSpy).toHaveBeenCalledWith('rsra')
    expect(replaySpy).toHaveBeenCalledTimes(1)
    expect(events.map(e => e.type)).toContain('done')
  })

  it('does NOT replay for a non-demo org', async () => {
    mockOrg('99999999-9999-9999-9999-999999999999')
    const { ManagedAgentsRuntime } = await import('../managed-agents-runtime.js')
    const rt = new ManagedAgentsRuntime()
    // Live path will try to use anthropic and throw; we only assert replay was not chosen.
    const gen = rt.sendMessage('ext', { content: 'Run a rapid sustainability risk assessment.', assetId: 'a', portfolioId: 'pf', conversationId: 'c', userId: 'u' })
    await gen.next().catch(() => {})
    expect(replaySpy).not.toHaveBeenCalled()
  })

  it('does NOT replay when assetId is null (portfolio-scope thread)', async () => {
    mockOrg(DEMO)
    loadSpy.mockReturnValue({ workflow: 'rsra' })
    const { ManagedAgentsRuntime } = await import('../managed-agents-runtime.js')
    const rt = new ManagedAgentsRuntime()
    const gen = rt.sendMessage('ext', { content: 'Run a rapid sustainability risk assessment.', assetId: null, portfolioId: 'pf', conversationId: 'c', userId: 'u' })
    await gen.next().catch(() => {})
    expect(replaySpy).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/managed-agents-runtime.demo-branch.test.ts`
Expected: FAIL — the demo branch does not exist; `replaySpy` not called (first test fails).

- [ ] **Step 3: Add imports at the top of `managed-agents-runtime.ts`**

```ts
import { isDemoOrg, classifyDemoWorkflow } from '../lib/demo.js'
import { loadDemoFixture, replayDemoFixture } from './demo-replay.js'
```

- [ ] **Step 4: Add the branch at the start of `sendMessage`** (immediately after the method signature at line 387, before the existing body that begins around line 392)

```ts
  async *sendMessage(externalSessionId: string, params: SendMessageParams): AsyncGenerator<RuntimeEvent> {
    // ── Demo-org scripted replay (stage demos) ──────────────────────────────
    // Gated to the Demo org; renders onto the live asset via the real renderReport.
    if (params.assetId) {
      const orgId = await this.resolveOrgId(params.portfolioId)
      if (isDemoOrg(orgId)) {
        const workflow = classifyDemoWorkflow(params.content)
        const fixture = workflow ? loadDemoFixture(workflow) : null
        if (fixture) {
          yield* replayDemoFixture(fixture, {
            conversationId: params.conversationId,
            assetId: params.assetId,
            userId: params.userId,
            portfolioId: params.portfolioId,
            mcpServers: params.mcpServers,
          })
          return
        }
      }
    }
    // ── Live path (unchanged) ───────────────────────────────────────────────
    // ...existing body continues here...
```

- [ ] **Step 5: Add the `resolveOrgId` private helper** (near the other private methods in the class; uses the module's existing `supabase` import)

```ts
  private async resolveOrgId(portfolioId: string): Promise<string | null> {
    const { data } = await supabase
      .from('portfolios')
      .select('organization_id')
      .eq('id', portfolioId)
      .single()
    return (data as { organization_id?: string } | null)?.organization_id ?? null
  }
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd soapbox-platform/apps/api && npx vitest run src/services/__tests__/managed-agents-runtime.demo-branch.test.ts`
Expected: PASS (3 cases).

- [ ] **Step 7: Run the full API test suite + typecheck to confirm no live-path regressions**

Run: `cd soapbox-platform/apps/api && npx vitest run && npx tsc --noEmit`
Expected: PASS / no type errors. (Confirms the live path is byte-for-byte unchanged for non-demo orgs.)

- [ ] **Step 8: Commit**

```bash
cd soapbox-platform && git add apps/api/src/services/managed-agents-runtime.ts apps/api/src/services/__tests__/managed-agents-runtime.demo-branch.test.ts
git commit -m "feat(demo): demo-org replay short-circuit at top of sendMessage"
```

---

### Task 5: Fixture recorder script (ops tooling in demo-staging)

**Files:**
- Create: `soapbox-agent/demo-staging/record-fixture.mjs`
- Create: `soapbox-agent/demo-staging/README-fixtures.md` (how to record/freeze/scrub)

**Interfaces:**
- Consumes: `.demo.env` (`SOAPBOX_AGENT_EMAIL`, `SOAPBOX_AGENT_PASSWORD`), the stage app host, the Demo org id.
- Produces: a fixture JSON printed to stdout / written to `--out`, in the exact `DemoFixture` shape validated by Task 2.

The recorder authenticates as the service account (Supabase auth → access token), opens a new conversation on the given Demo-org asset, POSTs the prompt to `POST {apiHost}/api/conversations/{convId}/messages` with `x-organization-id: <DEMO_ORG_ID>`, reads the SSE stream, and records every `data:` event with a monotonic `t` (ms since first byte). It extracts the `fill_report` `tool_call` event's `input` as `render` ({template, title, data}) and strips the bulky `data` from the retained in-stream `tool_call` marker (keeping `{template}`) so the narration stream stays light and the render payload lives once under `render`.

**Important:** this recorder runs a REAL agent run against the shared prod+stage DB. It MUST target only the Demo-org asset. It creates a throwaway conversation (record its id in output for later cleanup per the cleanup-test-data standard).

- [ ] **Step 1: Write the recorder**

```js
// soapbox-agent/demo-staging/record-fixture.mjs
// Usage: node record-fixture.mjs --workflow rsra --asset 062cbda3-... --prompt "Run a rapid sustainability risk assessment." --target-ms 75000 --out fixtures/rsra.json
import { writeFileSync } from 'node:fs'
import { createClient } from '@supabase/supabase-js'

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1]]); return a
}, []))

const DEMO_ORG_ID = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'
const API = process.env.DEMO_API_HOST // e.g. stage app API host
const SB_URL = process.env.SUPABASE_URL
const SB_ANON = process.env.SUPABASE_ANON_KEY

const sb = createClient(SB_URL, SB_ANON)
const { data: auth, error } = await sb.auth.signInWithPassword({
  email: process.env.SOAPBOX_AGENT_EMAIL, password: process.env.SOAPBOX_AGENT_PASSWORD,
})
if (error) { console.error('auth failed', error.message); process.exit(1) }
const token = auth.session.access_token
const H = { Authorization: `Bearer ${token}`, 'x-organization-id': DEMO_ORG_ID, 'Content-Type': 'application/json' }

// 1. New conversation on the demo asset
const convRes = await fetch(`${API}/api/assets/${args.asset}/conversations`, {
  method: 'POST', headers: H, body: JSON.stringify({ title: `fixture-record-${args.workflow}` }),
})
const conv = await convRes.json()
console.error('conversation:', conv.id, '(clean up after)')

// 2. Send the prompt, read the SSE stream
const t0 = Date.now()
const events = []
let render = null
const res = await fetch(`${API}/api/conversations/${conv.id}/messages`, {
  method: 'POST', headers: H, body: JSON.stringify({ content: args.prompt }),
})
const reader = res.body.getReader()
const dec = new TextDecoder()
let buf = ''
for (;;) {
  const { done, value } = await reader.read()
  if (done) break
  buf += dec.decode(value, { stream: true })
  const lines = buf.split('\n'); buf = lines.pop() ?? ''
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    let ev; try { ev = JSON.parse(line.slice(6)) } catch { continue }
    if (ev.type === 'ping') continue
    const t = Date.now() - t0
    if (ev.type === 'tool_call' && ev.toolName === 'fill_report') {
      render = { template: ev.input?.template ?? args.workflow, title: ev.input?.title, data: ev.input?.data ?? {} }
      events.push({ t, event: { type: 'tool_call', toolName: 'fill_report', input: { template: render.template } } })
    } else if (ev.type === 'artifact' || ev.type === 'done') {
      // artifact is re-produced by replay; stop capturing at first artifact/done
      break
    } else {
      events.push({ t, event: ev })
    }
  }
  if (render && events.at(-1)?.event?.toolName === 'fill_report') break
}

if (!render) { console.error('no fill_report captured — run did not render'); process.exit(2) }
const recordedTotalMs = events.at(-1).t
const fixture = {
  workflow: args.workflow, version: 1,
  targetDurationMs: Number(args['target-ms'] ?? 75000), recordedTotalMs,
  events, render,
}
const out = args.out ?? `fixtures/${args.workflow}.json`
writeFileSync(out, JSON.stringify(fixture, null, 2))
console.error(`wrote ${out} (${events.length} events, recorded ${recordedTotalMs}ms)`)
```

- [ ] **Step 2: Smoke-run against the Demo org (RSRA)** — requires the clean render to exist (see Task 6 gate).

Run (from `demo-staging`, with `.demo.env` sourced and `DEMO_API_HOST`/`SUPABASE_URL`/`SUPABASE_ANON_KEY` set):
```bash
node record-fixture.mjs --workflow rsra --asset 062cbda3-... --prompt "Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder." --target-ms 75000 --out /tmp/rsra-fixture.json
```
Expected: writes a fixture JSON; stderr prints the throwaway conversation id and event count.

- [ ] **Step 3: Document + commit the recorder**

Write `README-fixtures.md` covering: env vars, the record → scrub → validate → commit-into-API flow, and the cleanup step (delete throwaway conversations via Supabase MCP, Demo-org filtered).

```bash
cd soapbox-agent && git add demo-staging/record-fixture.mjs demo-staging/README-fixtures.md
git commit -m "feat(demo): golden-run fixture recorder + docs"
```

---

### Task 6: Capture, scrub, and freeze the RSRA fixture — **GATED**

> **GATE:** Do not start until one RSRA run on asset `062cbda3` (4400 Prairie Crossing) renders CLEAN against the Phase 9.9 checks (separated VaR block; stepped/distinct `decarb_sensitivity`; Cambium grid factor present; sane measure sizing). This is the "if this one works" gate. The current run must be confirmed first.

**Files:**
- Create: `soapbox-platform/apps/api/src/services/demo-fixtures/rsra.json`

- [ ] **Step 1: Confirm a clean RSRA render.** Inspect the latest verified run's artifact for the four checks above. If it fails any, fix upstream (template/skill) and re-run before proceeding.

- [ ] **Step 2: Record the fixture** from that clean run:
```bash
cd soapbox-agent/demo-staging && node record-fixture.mjs --workflow rsra --asset 062cbda3-... --prompt "Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder." --target-ms 75000 --out /tmp/rsra.json
```

- [ ] **Step 3: Scrub-gate the fixture narration.** Extract narration text and run the fail-closed gate:
```bash
cd soapbox-agent && node -e "const f=require('./demo-staging/../tmp/rsra.json');process.stdout.write(f.events.map(e=>e.event.delta||e.event.text||'').join('\n')+'\n'+JSON.stringify(f.render.data))" > /tmp/rsra-narration.txt
python3 demo-staging/scrub-check.py /tmp/rsra-narration.txt
```
Expected: `SCRUB CLEAN`. If not, the run leaked a real name — re-check pseudonymization and re-record.

- [ ] **Step 4: Validate against the loader** (catches shape drift before commit):
```bash
cd soapbox-platform/apps/api && node -e "import('./src/services/demo-replay.js').then(m=>{const fx=m.validateFixture(require('/tmp/rsra.json'));console.log('valid:',fx.workflow,fx.events.length,'events')})"
```
Expected: `valid: rsra <N> events`.

- [ ] **Step 5: Commit the fixture into the API repo:**
```bash
cp /tmp/rsra.json soapbox-platform/apps/api/src/services/demo-fixtures/rsra.json
cd soapbox-platform && git add apps/api/src/services/demo-fixtures/rsra.json
git commit -m "feat(demo): freeze verified RSRA golden-run fixture"
```

- [ ] **Step 6: End-to-end rehearsal** on a FRESH Demo-org asset (full add-asset → OM → map → footprints → Audette → thread → prompt). Confirm: replay streams narration, artifact renders within the target window, artifact reflects the clean output. Delete the throwaway conversation afterward (Supabase MCP, Demo-org filtered).

---

### Task 7: ESG fixture — **GATED on re-record**

> **GATE:** ESG currently depends on live crrem/physrisk. Record the fixture from a clean ESG run so those gap-fills are baked into the narration (neither needs to be live on stage). Confirm crrem availability during the recording run only (per `00-env.md`, crrem may need attaching to the Demo portfolio for the recording run; it is NOT needed at replay time).

**Files:**
- Create: `soapbox-platform/apps/api/src/services/demo-fixtures/esg.json`

- [ ] **Step 1: Record** on asset `cece8ad8` (Madison):
```bash
cd soapbox-agent/demo-staging && node record-fixture.mjs --workflow esg --asset cece8ad8-... --prompt "Run the ESG Profile assessment for the Madison sponsor. Inputs are in the asset files. Produce the sponsor ESG profile report." --target-ms 85000 --out /tmp/esg.json
```

- [ ] **Step 2: Scrub-gate** (same procedure as Task 6 Step 3, on `/tmp/esg.json`). Expected: `SCRUB CLEAN`.

- [ ] **Step 3: Validate** (Task 6 Step 4 procedure). Expected: `valid: esg <N> events`.

- [ ] **Step 4: Commit:**
```bash
cp /tmp/esg.json soapbox-platform/apps/api/src/services/demo-fixtures/esg.json
cd soapbox-platform && git add apps/api/src/services/demo-fixtures/esg.json
git commit -m "feat(demo): freeze verified ESG golden-run fixture"
```

- [ ] **Step 5: E2E rehearsal** on the Madison asset (new thread → prompt). Confirm artifact renders in-window; delete throwaway conversation.

---

### Task 8: Decarb fixture — **GATED on Christopher's engagement run**

> **GATE:** Requires Christopher's one real decarb engagement on 4th & Madison (`f6e043dd`) to complete, producing the completed state + rendered plan in Files. The demo prompt is "walk me through the plan" — a SHORT narration timeline surfacing the ideated measures, ending in the re-rendered decarb plan.

**Files:**
- Create: `soapbox-platform/apps/api/src/services/demo-fixtures/decarb.json`

- [ ] **Step 1:** After the engagement completes, record on asset `f6e043dd` with the walkthrough prompt:
```bash
cd soapbox-agent/demo-staging && node record-fixture.mjs --workflow decarb --asset f6e043dd-... --prompt "Show me the decarbonization plan for 4th & Madison — walk me through the measures." --target-ms 70000 --out /tmp/decarb.json
```
Note: the decarb template is verifier-gated — the recording run's `fill_report` must pass the gate (curve/fine/economics validators in `render-report.ts:43-48`), which it will if the engagement's data is complete. The replay re-runs those same validators.

- [ ] **Step 2: Scrub-gate** (Task 6 Step 3 procedure). Expected: `SCRUB CLEAN`.

- [ ] **Step 3: Validate** (Task 6 Step 4 procedure). Expected: `valid: decarb <N> events`.

- [ ] **Step 4: Commit:**
```bash
cp /tmp/decarb.json soapbox-platform/apps/api/src/services/demo-fixtures/decarb.json
cd soapbox-platform && git add apps/api/src/services/demo-fixtures/decarb.json
git commit -m "feat(demo): freeze verified decarb golden-run fixture"
```

- [ ] **Step 5: E2E rehearsal** on 4th & Madison; confirm in-window render; delete throwaway conversation.

---

### Task 9: Runbook + README updates and pre-demo checklist

**Files:**
- Modify: `soapbox-agent/demo-staging/README.md`
- Modify: `soapbox-agent/demo-staging/runbook-rsra.md`, `runbook-esg.md`, `runbook-decarb.md`

- [ ] **Step 1:** Update each runbook's "Expected beats" and "Hero live calls" sections to reflect scripted replay: the analysis phase is a deterministic ~60–90s replay of a recorded verified run; the ONLY live steps are upstream (add-asset/OM/map/footprints/Audette) plus the final `fill_report` re-render. Remove the "live physrisk hero" / "live crrem" beats and add a one-line note that they were deliberately dropped for stage reliability (recorded in the design decisions).

- [ ] **Step 2:** Update `README.md`: replace the "Timing observed (rehearsals)" section — the analysis phase is now fixed (~target-ms), not ~168s/~314s. Add a "Fixture currency" line: fixtures live at `soapbox-platform/apps/api/src/services/demo-fixtures/<workflow>.json`; re-record whenever the report template/skill output changes materially.

- [ ] **Step 3:** Add a pre-demo checklist item: "Fixtures committed + API deployed" and "one E2E rehearsal per workflow on a fresh thread the day before."

- [ ] **Step 4: Commit:**
```bash
cd soapbox-agent && git add demo-staging/README.md demo-staging/runbook-rsra.md demo-staging/runbook-esg.md demo-staging/runbook-decarb.md
git commit -m "docs(demo): runbooks reflect scripted replay + fixture currency"
```

---

## Self-Review

**Spec coverage:**
- Unit A (org-scoped demo mode) → Task 1 (`isDemoOrg`/classifier) + Task 4 (org resolution + branch). Client-side already exists (map override + auto-prompt), so no client task — noted in the plan header.
- Unit B (recorded fixtures + scrub gate) → Task 2 (format), Task 5 (recorder), Tasks 6/7/8 (capture + scrub + freeze, each gated).
- Unit C (timed replay branch) → Task 3 (generator) + Task 4 (wiring). Re-render via real `renderReport` → covered (Task 3 Step 3). `artifacts.asset_id NOT NULL` → Global Constraint + Task 4 null-asset guard + test.
- Unit D (upstream beats verify-only) → Task 6 Step 6 / Task 7 Step 5 / Task 8 Step 5 E2E rehearsals.
- Explicit decisions (full replay, all three, drop live beats, thread-stream not RsraPanel, org-scoped, bespoke server-side) → reflected; RsraPanel untouched (out of scope, confirmed orphaned).
- Shared prod+stage DB safety → Global Constraint + recorder targets Demo-org asset only + cleanup steps.
- Sequencing (RSRA first) → Tasks 6→7→8 ordered, each independently gated.

**Placeholder scan:** No TBD/TODO. Every code step shows full code. Fixture-capture steps are ops (real commands with expected output); their "content" is produced by the recorder, not hand-authored.

**Type consistency:** `DemoFixture`/`DemoRender`/`DemoFixtureEvent`/`ReplayCtx` defined in Task 2/3 and consumed unchanged in Task 4. `renderReport` params match `RenderReportParams` (`data, template, title?, artifactId, conversationId?, assetId?, userId, mcpServers?, logTag?`) verified against `render-report.ts:13-22`. `RuntimeEvent` variants (`model_start`, `text_delta`, `tool_call`, `tool_result`, `artifact`, `render_blocked`, `error`, `done`) match `types.ts:23-37`. `classifyDemoWorkflow` returns `DemoWorkflow | null` consistently.

## Open decision resolved during planning
Fixture storage = **committed JSON in the API repo** (`apps/api/src/services/demo-fixtures/`), authored by the demo-staging recorder. Chosen over live-fetch-from-GitHub (network dependency on stage = reliability risk) and a DB table (harder to review/diff; the demo must be deterministic and offline).
