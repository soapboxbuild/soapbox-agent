# Consumption Monitoring v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** True per-model credit metering (incl. cache + all system LLM calls), per-portfolio markup set by a super owner, and portfolio/asset consumption views with per-thread cost drill-in.

**Architecture:** Persist `credits_usd` per usage event at write time from a versioned rate table (billing worker computes it); markup applied at read time from `portfolios.markup_factor`. One `recordLlmUsage()` helper meters every non-thread Anthropic call as `category='system'`. New `platform_admins` table gates the markup knob.

**Tech Stack:** Hono + Supabase (apps/api on soapbox-platform `main`, auto-deploys to Railway), BullMQ billing queue, Next.js (platform-web, Vercel), Vitest.

**Spec:** `soapbox-agent/docs/superpowers/specs/2026-07-03-consumption-monitoring-design.md`

## Global Constraints

- soapbox-platform `main` auto-deploys — every commit ships. Keep each commit green (`npx tsc --noEmit` in apps/api before committing).
- NEVER `git add -A` or `git add .` — stage named files only.
- Vitest on this VM: run with `--pool=forks --poolOptions.forks.singleFork=true` (thread ulimit). Full command: `cd /home/claude/soapbox-platform/apps/api && npx vitest run <file> --pool=forks --poolOptions.forks.singleFork=true`.
- Migrations: apply via Supabase MCP `apply_migration` (project `fplbvanvwvnviczozwhz`) AND commit the same SQL to `soapbox-platform/supabase/migrations/` so the repo stays canonical.
- Markup semantics: `credits` = raw Anthropic USD; `cost` = credits × `markup_factor` (default 20). Rates per MTok: opus 5/25 (cache write 6.25, read 0.5), sonnet 3/15 (3.75/0.30), haiku 1/5 (1.25/0.10). Unknown model → opus rates + `console.error`.
- Metering must be fire-and-forget: a metering failure NEVER breaks the user-facing operation, but is always logged loudly (never-fail-silently).
- Frontend work requires the soapbox-e2e skill pass before completion; bulk-delete any test records (threads, usage rows on test assets) created during verification.
- Platform admin seed user ids: `f243660a-6991-4f7a-97f4-fefce9e24873` (christopher@soapbox.build), `e0f8179b-147b-48ea-8dad-cbc7d6c493b3` (christopher@audette.io).

---

### Task 1: Migrations (4 additive changes + backfill)

**Files:**
- Create: `soapbox-platform/supabase/migrations/20260703000001_token_usage_credits.sql`
- Create: `soapbox-platform/supabase/migrations/20260703000002_portfolio_markup.sql`
- Create: `soapbox-platform/supabase/migrations/20260703000003_platform_admins.sql`
- Create: `soapbox-platform/supabase/migrations/20260703000004_conversation_output_type.sql`

**Interfaces:**
- Produces: columns `token_usage_events.{cache_read_tokens,cache_write_tokens,credits_usd,category,source}`, `portfolios.markup_factor`, table `platform_admins(user_id)`, `conversations.output_type` — all later tasks depend on these existing in prod.

- [ ] **Step 1: Write migration 1 — token_usage_events columns + backfill**

`20260703000001_token_usage_credits.sql`:
```sql
alter table token_usage_events
  add column if not exists cache_read_tokens int not null default 0,
  add column if not exists cache_write_tokens int not null default 0,
  add column if not exists credits_usd numeric(12,6),
  add column if not exists category text not null default 'thread' check (category in ('thread','system')),
  add column if not exists source text;

-- Backfill credits_usd for historical rows at true per-model rates (cache unknown = 0).
-- Rates per 1M tokens: opus 5/25, sonnet 3/15, haiku 1/5.
update token_usage_events set credits_usd = round((
  input_tokens::numeric * (case
    when model ilike '%opus%'   then 5
    when model ilike '%sonnet%' then 3
    when model ilike '%haiku%'  then 1
    else 5 end)
  + output_tokens::numeric * (case
    when model ilike '%opus%'   then 25
    when model ilike '%sonnet%' then 15
    when model ilike '%haiku%'  then 5
    else 25 end)
) / 1000000, 6)
where credits_usd is null;
```

- [ ] **Step 2: Write migration 2 — portfolio markup**

`20260703000002_portfolio_markup.sql`:
```sql
alter table portfolios
  add column if not exists markup_factor numeric(6,2) not null default 20;
```

- [ ] **Step 3: Write migration 3 — platform_admins**

`20260703000003_platform_admins.sql`:
```sql
create table if not exists platform_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);
alter table platform_admins enable row level security;
-- Readable only by the admin themselves; writes are service-role only (no policy).
create policy "platform_admins_read_self" on platform_admins
  for select using (auth.uid() = user_id);

insert into platform_admins (user_id) values
  ('f243660a-6991-4f7a-97f4-fefce9e24873'),
  ('e0f8179b-147b-48ea-8dad-cbc7d6c493b3')
on conflict (user_id) do nothing;
```

- [ ] **Step 4: Write migration 4 — conversation output_type**

`20260703000004_conversation_output_type.sql`:
```sql
alter table conversations
  add column if not exists output_type text not null default 'general_query'
  check (output_type in ('general_query','report','analysis','data_update','plan'));
```

- [ ] **Step 5: Apply all four via Supabase MCP**

Call `mcp__plugin_supabase_supabase__apply_migration` four times (project_id `fplbvanvwvnviczozwhz`, name = filename stem, query = file content), in order.

- [ ] **Step 6: Verify**

Run via `execute_sql`:
```sql
select count(*) as null_credits from token_usage_events where credits_usd is null;
select markup_factor from portfolios limit 1;
select count(*) from platform_admins;
select output_type from conversations limit 1;
```
Expected: `null_credits = 0`, `markup_factor = 20.00`, `platform_admins count = 2`, output_type `general_query`.

- [ ] **Step 7: Commit**

```bash
cd /home/claude/soapbox-platform
git add supabase/migrations/20260703000001_token_usage_credits.sql supabase/migrations/20260703000002_portfolio_markup.sql supabase/migrations/20260703000003_platform_admins.sql supabase/migrations/20260703000004_conversation_output_type.sql
git commit -m "feat(consumption): usage credit columns, portfolio markup, platform_admins, output_type"
git push
```

---

### Task 2: Model pricing module

**Files:**
- Create: `soapbox-platform/apps/api/src/lib/model-pricing.ts`
- Test: `soapbox-platform/apps/api/test/lib/model-pricing.test.ts`

**Interfaces:**
- Produces: `ratesForModel(model: string): ModelRates` and `computeCreditsUsd(u: { model: string; inputTokens: number; outputTokens: number; cacheReadTokens?: number; cacheWriteTokens?: number }): number` (USD, rounded to 6 dp). Task 3 (billing worker) and Task 6 (consumption read fallback) consume `computeCreditsUsd`.

- [ ] **Step 1: Write the failing tests**

`test/lib/model-pricing.test.ts`:
```ts
import { describe, it, expect, vi } from 'vitest'
import { computeCreditsUsd, ratesForModel } from '../../src/lib/model-pricing.js'

describe('model-pricing', () => {
  it('prices opus input/output per MTok', () => {
    expect(computeCreditsUsd({ model: 'claude-opus-4-8', inputTokens: 1_000_000, outputTokens: 1_000_000 })).toBe(30)
  })
  it('prices sonnet and haiku', () => {
    expect(computeCreditsUsd({ model: 'claude-sonnet-4-6', inputTokens: 1_000_000, outputTokens: 0 })).toBe(3)
    expect(computeCreditsUsd({ model: 'claude-haiku-4-5-20251001', inputTokens: 0, outputTokens: 1_000_000 })).toBe(5)
  })
  it('prices cache read at 0.1x and cache write at 1.25x input', () => {
    expect(computeCreditsUsd({ model: 'claude-opus-4-8', inputTokens: 0, outputTokens: 0, cacheReadTokens: 1_000_000 })).toBe(0.5)
    expect(computeCreditsUsd({ model: 'claude-opus-4-8', inputTokens: 0, outputTokens: 0, cacheWriteTokens: 1_000_000 })).toBe(6.25)
  })
  it('falls back to opus rates for unknown models and logs an error', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(ratesForModel('gpt-5')).toEqual({ input: 5, output: 25, cacheWrite: 6.25, cacheRead: 0.5 })
    expect(spy).toHaveBeenCalled()
    spy.mockRestore()
  })
  it('rounds to 6 decimal places', () => {
    expect(computeCreditsUsd({ model: 'claude-haiku-4-5', inputTokens: 1, outputTokens: 1 })).toBe(0.000006)
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /home/claude/soapbox-platform/apps/api && npx vitest run test/lib/model-pricing.test.ts --pool=forks --poolOptions.forks.singleFork=true`
Expected: FAIL (module not found).

- [ ] **Step 3: Implement**

`src/lib/model-pricing.ts`:
```ts
// Anthropic list pricing, USD per 1M tokens. Verified 2026-07-03.
// Cache write = 1.25x input (5m TTL); cache read = 0.1x input.
export type ModelRates = { input: number; output: number; cacheWrite: number; cacheRead: number }

const OPUS: ModelRates = { input: 5, output: 25, cacheWrite: 6.25, cacheRead: 0.5 }
const SONNET: ModelRates = { input: 3, output: 15, cacheWrite: 3.75, cacheRead: 0.3 }
const HAIKU: ModelRates = { input: 1, output: 5, cacheWrite: 1.25, cacheRead: 0.1 }

export function ratesForModel(model: string): ModelRates {
  const m = model.toLowerCase()
  if (m.includes('opus')) return OPUS
  if (m.includes('sonnet')) return SONNET
  if (m.includes('haiku')) return HAIKU
  console.error(`[model-pricing] Unknown model "${model}" — using Opus rates (conservative)`)
  return OPUS
}

export function computeCreditsUsd(u: {
  model: string
  inputTokens: number
  outputTokens: number
  cacheReadTokens?: number
  cacheWriteTokens?: number
}): number {
  const r = ratesForModel(u.model)
  const usd =
    (u.inputTokens * r.input +
      u.outputTokens * r.output +
      (u.cacheReadTokens ?? 0) * r.cacheRead +
      (u.cacheWriteTokens ?? 0) * r.cacheWrite) /
    1_000_000
  return Math.round(usd * 1e6) / 1e6
}
```

- [ ] **Step 4: Run tests — expect PASS**

Same command as Step 2. Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/lib/model-pricing.ts apps/api/test/lib/model-pricing.test.ts
git commit -m "feat(consumption): per-model pricing table with cache rates"
git push
```

---

### Task 3: Billing worker — cache tokens, category/source, credits, portfolio resolution

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/billing-worker.ts:11-42`
- Create: `soapbox-platform/apps/api/src/lib/llm-metering.ts`
- Test: `soapbox-platform/apps/api/test/services/billing-worker.test.ts`

**Interfaces:**
- Consumes: `computeCreditsUsd` from Task 2.
- Produces: extended `BillingJobData` `{ assetId?, portfolioId?, model, inputTokens, outputTokens, cacheReadTokens?, cacheWriteTokens?, conversationId?, agentThreadId?, category?: 'thread'|'system', source?: string }`; helper `recordLlmUsage(opts: { model: string; usage: { input_tokens: number; output_tokens: number; cache_read_input_tokens?: number|null; cache_creation_input_tokens?: number|null }; portfolioId?: string; assetId?: string; conversationId?: string; category: 'thread'|'system'; source?: string }): void` (fire-and-forget). Tasks 4–5 call `recordLlmUsage`.

- [ ] **Step 1: Write failing tests**

`test/services/billing-worker.test.ts` (mock supabase/queue following the mocking style used in `test/services/portfolio.test.ts`; the worker processor is exercised by importing `startBillingWorker` with a mocked `Worker` that captures the processor fn, then invoking it directly):
```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const inserted: any[] = []
const fromMock = vi.fn((table: string) => {
  if (table === 'token_usage_events') return { insert: vi.fn(async (row: any) => { inserted.push(row); return { error: null } }) }
  if (table === 'assets') return { select: vi.fn(() => ({ eq: vi.fn(() => ({ single: vi.fn(async () => ({ data: { stripe_customer_id: null, portfolio_id: 'pf-1', portfolios: null } })) })) })) }
  return {} as any
})
vi.mock('../../src/lib/supabase.js', () => ({ supabase: { from: fromMock } }))
vi.mock('../../src/lib/redis.js', () => ({ redisForBullMQ: {} }))
vi.mock('../../src/lib/stripe.js', () => ({ getStripe: () => ({ billing: { meterEvents: { create: vi.fn() } } }) }))
vi.mock('../../src/lib/queue.js', () => ({ indexingQueue: { add: vi.fn() } }))

let processor: (job: any) => Promise<void>
vi.mock('bullmq', () => ({
  Worker: class { constructor(_n: string, fn: any) { processor = fn } on() {} },
}))

import { startBillingWorker } from '../../src/services/billing-worker.js'

describe('billing worker', () => {
  beforeEach(() => { inserted.length = 0; startBillingWorker() })

  it('persists cache tokens, category, source and computed credits_usd', async () => {
    await processor({ data: { portfolioId: 'pf-1', model: 'claude-opus-4-8', inputTokens: 1_000_000, outputTokens: 0, cacheReadTokens: 1_000_000, cacheWriteTokens: 0, category: 'system', source: 'rsra_pipeline' } })
    expect(inserted[0]).toMatchObject({
      portfolio_id: 'pf-1', category: 'system', source: 'rsra_pipeline',
      cache_read_tokens: 1_000_000, cache_write_tokens: 0, credits_usd: 5.5,
    })
  })

  it('defaults category to thread and resolves portfolio_id from asset when missing', async () => {
    await processor({ data: { assetId: 'a-1', model: 'claude-haiku-4-5', inputTokens: 10, outputTokens: 10 } })
    expect(inserted[0]).toMatchObject({ asset_id: 'a-1', portfolio_id: 'pf-1', category: 'thread' })
  })
})
```

- [ ] **Step 2: Run — expect FAIL** (credits_usd/category/source not inserted; no portfolio resolution).

Run: `npx vitest run test/services/billing-worker.test.ts --pool=forks --poolOptions.forks.singleFork=true`

- [ ] **Step 3: Implement worker changes**

In `billing-worker.ts`, replace `BillingJobData` and the processor body's insert section:
```ts
import { computeCreditsUsd } from '../lib/model-pricing.js'

export type BillingJobData = {
  assetId?: string
  portfolioId?: string
  model: string
  inputTokens: number
  outputTokens: number
  cacheReadTokens?: number
  cacheWriteTokens?: number
  conversationId?: string
  agentThreadId?: string
  category?: 'thread' | 'system'
  source?: string
}
```
Processor (replace lines 31–54; the asset lookup now also selects `portfolio_id` and doubles as portfolio resolution — keep the Stripe meter block unchanged after it):
```ts
const { assetId, portfolioId, conversationId, model, inputTokens, outputTokens, agentThreadId,
        cacheReadTokens = 0, cacheWriteTokens = 0, category = 'thread', source } = job.data
const totalTokens = inputTokens + outputTokens

// Resolve customer + portfolio from the asset in one query (asset may be absent for
// portfolio-only system calls).
const { data: asset } = assetId
  ? await supabase
      .from('assets')
      .select('stripe_customer_id, portfolio_id, portfolios(stripe_customer_id)')
      .eq('id', assetId)
      .single()
  : { data: null }

const resolvedPortfolioId = portfolioId ?? (asset as any)?.portfolio_id ?? null
if (!resolvedPortfolioId) {
  console.error(`[billing] usage event has no resolvable portfolio (asset=${assetId}, source=${source ?? 'thread'}) — inserting without portfolio_id`)
}

const credits = computeCreditsUsd({ model, inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens })

const { error: insertError } = await supabase.from('token_usage_events').insert({
  asset_id: assetId,
  portfolio_id: resolvedPortfolioId,
  model,
  input_tokens: inputTokens,
  output_tokens: outputTokens,
  cache_read_tokens: cacheReadTokens,
  cache_write_tokens: cacheWriteTokens,
  credits_usd: credits,
  category,
  source,
  conversation_id: conversationId,
  agent_thread_id: agentThreadId,
})
if (insertError) console.error('[billing] token_usage_events insert failed:', insertError.message)

const customerId = asset?.stripe_customer_id ??
  (asset?.portfolios as any)?.stripe_customer_id
```
(Then the existing `getMeterName`/Stripe block continues unchanged from `const meterId = ...`.)

- [ ] **Step 4: Implement `recordLlmUsage` helper**

`src/lib/llm-metering.ts`:
```ts
import { billingQueue } from './queue.js'
import type { BillingJobData } from '../services/billing-worker.js'

/**
 * Fire-and-forget metering for any Anthropic call. A metering failure must
 * never break the caller — it is logged loudly instead.
 */
export function recordLlmUsage(opts: {
  model: string
  usage: {
    input_tokens: number
    output_tokens: number
    cache_read_input_tokens?: number | null
    cache_creation_input_tokens?: number | null
  }
  portfolioId?: string
  assetId?: string
  conversationId?: string
  category: 'thread' | 'system'
  source?: string
}): void {
  const job: BillingJobData = {
    assetId: opts.assetId,
    portfolioId: opts.portfolioId,
    conversationId: opts.conversationId,
    model: opts.model,
    inputTokens: opts.usage.input_tokens ?? 0,
    outputTokens: opts.usage.output_tokens ?? 0,
    cacheReadTokens: opts.usage.cache_read_input_tokens ?? 0,
    cacheWriteTokens: opts.usage.cache_creation_input_tokens ?? 0,
    category: opts.category,
    source: opts.source,
  }
  void billingQueue.add('token-billing', job).catch((err) => {
    console.error(`[llm-metering] FAILED to record usage (source=${opts.source ?? 'thread'}, model=${opts.model}):`, err)
  })
}
```

- [ ] **Step 5: Run tests — expect PASS**, then `npx tsc --noEmit`.

- [ ] **Step 6: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/services/billing-worker.ts apps/api/src/lib/llm-metering.ts apps/api/test/services/billing-worker.test.ts
git commit -m "feat(consumption): billing worker persists cache tokens, credits_usd, category/source; recordLlmUsage helper"
git push
```

---

### Task 4: Thread path — stop dropping cache tokens; meter title/tag/suggest calls; output_type tagging

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/messages.ts` (lines ~13–82 tagger/title, ~465–474 enqueue, ~496–509 finally-block callers, ~540–586 suggest)
- Test: `soapbox-platform/apps/api/test/routes/messages.test.ts` (extend existing)

**Interfaces:**
- Consumes: `recordLlmUsage` (Task 3).
- Produces: `classifyThreadFromHistory(convId, isPortfolio, ids?: { assetId?: string|null; portfolioId?: string })` now also writes `conversations.output_type`; all three Haiku calls metered as `category='system'` with sources `tag_gen`, `title_gen`, `suggest`.

- [ ] **Step 1: Pass cache tokens through the SSE billing enqueue**

At messages.ts lines 465–474, extend the payload:
```ts
if (event.type === 'token_usage') {
  await billingQueue.add('token-billing', {
    assetId: verifiedAssetId,
    portfolioId: billingPortfolioId,
    conversationId: convId,
    model: event.model,
    inputTokens: event.inputTokens,
    outputTokens: event.outputTokens,
    cacheReadTokens: event.cacheReadTokens,
    cacheWriteTokens: event.cacheWriteTokens,
    category: 'thread',
  })
}
```

- [ ] **Step 2: Meter + extend the auto-tagger**

Add import `import { recordLlmUsage } from '../lib/llm-metering.js'`. Change `classifyThreadFromHistory` signature to `(convId: string, isPortfolio: boolean, ids?: { assetId?: string | null; portfolioId?: string })` and replace the create call + parsing (lines 44–64):
```ts
const resp = await anthropic.messages.create({
  model: 'claude-haiku-4-5-20251001',
  max_tokens: 40,
  messages: [{
    role: 'user',
    content: `Analyze this CRE conversation. Reply with exactly three lines:\nLine 1: one of these types: due_diligence | capital_plan | compliance | financial_analysis | lease_review | document_review | general\nLine 2: a 3-6 word activity tag describing what this thread is actually about (e.g. "1031 exchange analysis", "quarterly local law 97 audit", "tenant estoppel certificate review", "acquisition underwriting 123 main st")\nLine 3: what the thread PRODUCED, one of: general_query | report | analysis | data_update | plan\n\nConversation:\n${excerpt}`,
  }],
})
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: resp.usage, category: 'system', source: 'tag_gen', conversationId: convId, assetId: ids?.assetId ?? undefined, portfolioId: ids?.portfolioId })

const lines = ((resp.content[0] as any).text ?? '').trim().split('\n').map((l: string) => l.trim())
const rawType = (lines[0] ?? '').toLowerCase().replace(/[^a-z_]/g, '')
const valid = ['due_diligence','capital_plan','compliance','financial_analysis','lease_review','document_review','general']
const type = valid.includes(rawType) ? rawType : 'general'
const activityTag = (lines[1] ?? '').slice(0, 80) || null
const rawOutput = (lines[2] ?? '').toLowerCase().replace(/[^a-z_]/g, '')
const validOutputs = ['general_query','report','analysis','data_update','plan']
const outputType = validOutputs.includes(rawOutput) ? rawOutput : 'general_query'

await supabase.from('conversations').update({
  thread_type: type,
  activity_tag: activityTag,
  output_type: outputType,
  last_classified_at: new Date().toISOString(),
  taxonomy_version: 1,
}).eq('id', convId)
```
Update the two call sites in the finally block (lines ~501–509) to pass `{ assetId: verifiedAssetId, portfolioId: billingPortfolioId }` as the third argument.

- [ ] **Step 3: Meter `generateTitle`**

Change signature to `generateTitle(userMessage, assistantReply, ids?: { assetId?: string | null; portfolioId?: string; conversationId?: string })` and after the create call add:
```ts
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: resp.usage, category: 'system', source: 'title_gen', assetId: ids?.assetId ?? undefined, portfolioId: ids?.portfolioId, conversationId: ids?.conversationId })
```
Update its call site (line ~496) to pass `{ assetId: verifiedAssetId, portfolioId: billingPortfolioId, conversationId: convId }`.

- [ ] **Step 4: Meter `/suggest`**

At line 544, capture the ownership result instead of discarding it:
```ts
const ownership = await assertConvBelongsTenant(convId, portfolioId)
if (!ownership) {
  return c.json({ error: 'Not found' }, 404)
}
```
After the create call at line 566:
```ts
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: resp.usage, category: 'system', source: 'suggest', assetId: ownership.assetId ?? undefined, portfolioId: ownership.portfolioId, conversationId: convId })
```

- [ ] **Step 5: Extend tests**

Add to `test/routes/messages.test.ts` (follow the file's existing mocking of `anthropic` and `billingQueue`; ensure the anthropic mock's create result includes `usage: { input_tokens: 10, output_tokens: 5 }`):
```ts
it('meters the suggest call as a system usage event', async () => {
  // invoke POST /suggest through the existing test harness for this route
  // then:
  expect(billingQueueAddMock).toHaveBeenCalledWith('token-billing', expect.objectContaining({
    category: 'system', source: 'suggest', model: 'claude-haiku-4-5-20251001',
  }))
})

it('forwards cache tokens on thread token_usage events', async () => {
  // drive the SSE send flow with a runtime mock emitting
  // { type: 'token_usage', inputTokens: 1, outputTokens: 2, cacheReadTokens: 3, cacheWriteTokens: 4, model: 'claude-opus-4-8' }
  expect(billingQueueAddMock).toHaveBeenCalledWith('token-billing', expect.objectContaining({
    cacheReadTokens: 3, cacheWriteTokens: 4, category: 'thread',
  }))
})
```
Adapt harness details to the file's existing patterns (it already tests the send flow and mocks the runtime).

- [ ] **Step 6: Run tests + typecheck**

Run: `npx vitest run test/routes/messages.test.ts --pool=forks --poolOptions.forks.singleFork=true` → PASS. `npx tsc --noEmit` → clean.

- [ ] **Step 7: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/routes/messages.ts apps/api/test/routes/messages.test.ts
git commit -m "feat(consumption): meter title/tag/suggest calls, forward cache tokens, output_type auto-tagging"
git push
```

---

### Task 5: Meter remaining system call sites (extract-address, detect-buildings, bulk-extract, RSRA) + deliverable output_type stamping

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/extract-address.ts` (4 create calls, lines ~81, 89, 103, 123)
- Modify: `soapbox-platform/apps/api/src/routes/detect-buildings.ts` (line ~116)
- Modify: `soapbox-platform/apps/api/src/routes/bulk-extract.ts` (helpers at lines ~179, ~218 + handler at ~327)
- Modify: `soapbox-platform/apps/api/src/lib/rsra-pipeline.ts` (`runStageC`, line ~455)
- Modify: `soapbox-platform/apps/api/src/services/managed-agents-runtime.ts` (artifact insert ~line 621, fill_report upsert ~line 723)
- Test: extend `soapbox-platform/apps/api/test/routes/extract-address.test.ts` and `soapbox-platform/apps/api/src/routes/__tests__/bulk-extract.test.ts`

**Interfaces:**
- Consumes: `recordLlmUsage` (Task 3).
- Produces: every remaining `anthropic.messages.create` in apps/api metered with `category='system'` and sources `address_extract`, `building_detect`, `bulk_extract`, `rsra_pipeline`; conversations that produce artifacts get `output_type` stamped.

- [ ] **Step 1: extract-address.ts**

Add imports; in the handler read tenant once at the top:
```ts
import { recordLlmUsage } from '../lib/llm-metering.js'
// inside the POST handler, first line:
const { portfolioId } = c.get('tenant')
```
After EACH of the four `message = await anthropic.messages.create({...})` calls add:
```ts
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: message.usage, category: 'system', source: 'address_extract', portfolioId })
```

- [ ] **Step 2: detect-buildings.ts**

Same pattern — read `const { portfolioId } = c.get('tenant')` at the top of the handler, and after the create at ~116:
```ts
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: msg.usage, category: 'system', source: 'building_detect', portfolioId })
```

- [ ] **Step 3: bulk-extract.ts**

Thread `portfolioId` into both helpers: change signatures to `extractFromOfficeFile(filename, bytes, propertyHint?, portfolioId?)` and `extractFromPdf(filename, bytes, propertyHint?, portfolioId?)`; after each create:
```ts
recordLlmUsage({ model: 'claude-haiku-4-5-20251001', usage: msg.usage, category: 'system', source: 'bulk_extract', portfolioId })
```
Update all call sites in the handler to pass the `portfolioId` from `c.get('tenant')` (line 328).

- [ ] **Step 4: rsra-pipeline.ts**

In `runStageC`, after the successful create inside the retry (the `msg` variable, line ~455) — record inside the retry callback right after `const msg = await anthropic.messages.create(...)`:
```ts
recordLlmUsage({ model: 'claude-sonnet-4-6', usage: msg.usage, category: 'system', source: 'rsra_pipeline', assetId })
```
(`assetId` is a `runStageC` param; portfolio resolves in the billing worker via the asset. Import `recordLlmUsage` at top of file.)

- [ ] **Step 5: Deliverable output_type stamping in managed-agents-runtime.ts**

After the `create_artifact` insert (~line 629, after the `await supabase.from('artifacts').insert({...})`):
```ts
if (params.conversationId) {
  const stamp = (input.type === 'html' || input.type === 'markdown') ? 'report' : 'analysis'
  void supabase.from('conversations').update({ output_type: stamp }).eq('id', params.conversationId)
    .then(({ error }) => { if (error) console.error('[output-type] stamp failed:', error.message) })
}
```
After the `fill_report` upsert (~line 723):
```ts
if (params.conversationId) {
  void supabase.from('conversations').update({ output_type: 'report' }).eq('id', params.conversationId)
    .then(({ error }) => { if (error) console.error('[output-type] stamp failed:', error.message) })
}
```

- [ ] **Step 6: Tests**

Extend `test/routes/extract-address.test.ts`: mock `../../src/lib/llm-metering.js` (`recordLlmUsage: vi.fn()`), ensure the existing anthropic mock returns `usage: { input_tokens: 100, output_tokens: 10 }`, drive one extraction, assert:
```ts
expect(recordLlmUsageMock).toHaveBeenCalledWith(expect.objectContaining({ category: 'system', source: 'address_extract' }))
```
Extend `src/routes/__tests__/bulk-extract.test.ts` equivalently with `source: 'bulk_extract'`.

- [ ] **Step 7: Run tests + typecheck**

Run: `npx vitest run test/routes/extract-address.test.ts src/routes/__tests__/bulk-extract.test.ts --pool=forks --poolOptions.forks.singleFork=true` → PASS. `npx tsc --noEmit` → clean.

- [ ] **Step 8: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/routes/extract-address.ts apps/api/src/routes/detect-buildings.ts apps/api/src/routes/bulk-extract.ts apps/api/src/lib/rsra-pipeline.ts apps/api/src/services/managed-agents-runtime.ts apps/api/test/routes/extract-address.test.ts apps/api/src/routes/__tests__/bulk-extract.test.ts
git commit -m "feat(consumption): meter all system LLM calls; stamp output_type on artifact/report creation"
git push
```

---

### Task 6: Super owner — tenant `isSuper` + markup PATCH endpoint

**Files:**
- Modify: `soapbox-platform/apps/api/src/lib/types.ts` (TenantContext)
- Modify: `soapbox-platform/apps/api/src/middleware/tenant.ts:62`
- Modify: `soapbox-platform/apps/api/src/routes/portfolios.ts` (new PATCH route near the other portfolio-settings routes)
- Test: extend `soapbox-platform/apps/api/test/middleware/tenant.test.ts`; extend `soapbox-platform/apps/api/test/routes/portfolios.test.ts`

**Interfaces:**
- Produces: `TenantContext` gains `isSuper: boolean`; `PATCH /api/portfolios/markup` body `{ markup_factor: number }` → 200 `{ markup_factor }` for super owners, 403 otherwise. Task 7's consumption endpoints read `isSuper` to decide whether to include `markup_factor` in the payload.

- [ ] **Step 1: Failing tests**

In `test/middleware/tenant.test.ts` add (reusing the file's existing supabase mock helper — add a `platform_admins` branch to the table switch returning `{ data: { user_id: 'u-1' } }` for the super case and `{ data: null }` otherwise):
```ts
it('sets isSuper true when the user is a platform admin', async () => {
  // arrange mock: platform_admins select -> row
  // run middleware, then:
  expect(setTenant).toHaveBeenCalledWith('tenant', expect.objectContaining({ isSuper: true }))
})
it('sets isSuper false otherwise', async () => {
  expect(setTenant).toHaveBeenCalledWith('tenant', expect.objectContaining({ isSuper: false }))
})
```
In `test/routes/portfolios.test.ts` add:
```ts
it('PATCH /markup returns 403 for non-super admins', async () => {
  // tenant mock: { role: 'admin', isSuper: false }
  const res = await app.request('/api/portfolios/markup', { method: 'PATCH', body: JSON.stringify({ markup_factor: 25 }), headers: { 'content-type': 'application/json' } })
  expect(res.status).toBe(403)
})
it('PATCH /markup updates markup for super owner and validates range', async () => {
  // tenant mock: { role: 'admin', isSuper: true }
  const ok = await app.request('/api/portfolios/markup', { method: 'PATCH', body: JSON.stringify({ markup_factor: 25 }), headers: { 'content-type': 'application/json' } })
  expect(ok.status).toBe(200)
  const bad = await app.request('/api/portfolios/markup', { method: 'PATCH', body: JSON.stringify({ markup_factor: 0 }), headers: { 'content-type': 'application/json' } })
  expect(bad.status).toBe(400)
})
```
(Adapt request-harness details to how the file already builds the Hono app + mock middleware.)

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`types.ts` — extend TenantContext:
```ts
export type TenantContext = {
  portfolioId: string
  role: 'admin' | 'member'
  userId: string
  isSuper: boolean
}
```
`tenant.ts` — before `c.set('tenant', ...)` (line 62):
```ts
const { data: superRow } = await supabase
  .from('platform_admins')
  .select('user_id')
  .eq('user_id', user.id)
  .maybeSingle()

c.set('tenant', { portfolioId, role, userId: user.id, isSuper: !!superRow })
```
`portfolios.ts` — add route:
```ts
// PATCH /api/portfolios/markup — super owner only: set the credit->cost markup factor
portfolios.patch('/markup', async (c) => {
  const { portfolioId, isSuper } = c.get('tenant')
  if (!isSuper) return c.json({ error: 'Forbidden' }, 403)

  const body = await c.req.json().catch(() => ({}))
  const factor = Number(body.markup_factor)
  if (!Number.isFinite(factor) || factor < 1 || factor > 1000) {
    return c.json({ error: 'markup_factor must be between 1 and 1000' }, 400)
  }

  const { error } = await supabase
    .from('portfolios')
    .update({ markup_factor: factor })
    .eq('id', portfolioId)
  if (error) return c.json({ error: error.message }, 500)
  return c.json({ markup_factor: factor })
})
```
Fix any other `c.set('tenant', ...)` sites and test fixtures that construct TenantContext (grep `set('tenant'` and `isSuper` compile errors from `npx tsc --noEmit`).

- [ ] **Step 4: Run tests + typecheck — expect PASS/clean.**

- [ ] **Step 5: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/lib/types.ts apps/api/src/middleware/tenant.ts apps/api/src/routes/portfolios.ts apps/api/test/middleware/tenant.test.ts apps/api/test/routes/portfolios.test.ts
git commit -m "feat(consumption): platform_admins isSuper on tenant + super-owner markup PATCH"
git push
```

---

### Task 7: Consumption endpoints — portfolio reshape + asset drill-in

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/portfolios.ts:961-1071` (pricing constants + `GET /consumption`)
- Modify: `soapbox-platform/apps/api/src/routes/assets.ts` (new `GET /:id/consumption`)
- Test: extend `soapbox-platform/apps/api/test/routes/portfolios.test.ts` and `test/routes/assets.test.ts`

**Interfaces:**
- Consumes: `computeCreditsUsd` (Task 2), `isSuper` (Task 6), event columns (Task 1).
- Produces the payload the frontend (Tasks 8–9) renders:

```ts
// GET /api/portfolios/consumption?period=7d|30d|90d|all  (admin-gated)
type PortfolioConsumption = {
  period: string
  markup_factor?: number            // present ONLY when isSuper
  total_tokens: number
  total_credits: number             // raw Anthropic $
  total_cost: number                // credits * markup
  total_queries: number
  total_threads: number
  portfolio_threads: ThreadRow[]    // conversations with asset_id null
  assets: { asset_id: string; name: string; tokens: number; credits: number; cost: number; thread_count: number }[]
  system: { source: string; tokens: number; credits: number; cost: number; events: number }[]
  by_type: { type: string; label: string; tokens: number; queries: number; credits: number; cost: number; pct: number }[]
  by_output_type: { type: string; tokens: number; credits: number; cost: number; threads: number }[]
  by_day: { date: string; tokens: number; credits: number; cost: number }[]
}
type ThreadRow = {
  conversation_id: string; title: string | null
  thread_type: string; output_type: string; activity_tag: string | null
  tokens: number; credits: number; cost: number; queries: number; last_activity: string
}

// GET /api/assets/:id/consumption?period=...  (portfolio admin-gated, asset membership checked)
type AssetConsumption = {
  period: string
  asset_id: string
  total_tokens: number; total_credits: number; total_cost: number; total_threads: number
  threads: ThreadRow[]
  system: { source: string; tokens: number; credits: number; cost: number; events: number }[]
}
```

- [ ] **Step 1: Failing tests**

Extend `test/routes/portfolios.test.ts` (mock `token_usage_events` select to return two events: one thread event on a portfolio conversation with `credits_usd: 1`, one system event `source: 'rsra_pipeline', credits_usd: 0.5`; mock `portfolios` select returning `markup_factor: 20`):
```ts
it('GET /consumption returns credits raw and cost = credits x markup, with system row', async () => {
  const res = await app.request('/api/portfolios/consumption')
  const j = await res.json()
  expect(j.total_credits).toBeCloseTo(1.5)
  expect(j.total_cost).toBeCloseTo(30)
  expect(j.system[0]).toMatchObject({ source: 'rsra_pipeline' })
})
it('includes markup_factor only for super owners', async () => {
  // non-super tenant -> expect(j.markup_factor).toBeUndefined()
  // super tenant -> expect(j.markup_factor).toBe(20)
})
it('is admin-only', async () => {
  // tenant role 'member' -> expect 403
})
```
Extend `test/routes/assets.test.ts`:
```ts
it('GET /:id/consumption 404s for assets outside the portfolio and returns per-thread rows otherwise', async () => { /* mirror the rsra-stream membership-test pattern */ })
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement portfolio endpoint**

Replace the pricing-constants block and `GET /consumption` handler (portfolios.ts 961–1071) with:
```ts
import { computeCreditsUsd } from '../lib/model-pricing.js'  // add to top-of-file imports

const daysMap: Record<string, number> = { '7d': 7, '30d': 30, '90d': 90, 'all': 36500 }

type UsageEvent = {
  input_tokens: number | null; output_tokens: number | null
  cache_read_tokens: number | null; cache_write_tokens: number | null
  credits_usd: number | null; category: string | null; source: string | null
  model: string; asset_id: string | null; conversation_id: string | null; created_at: string
  conversations: { title: string | null; thread_type: string | null; activity_tag: string | null; output_type: string | null; asset_id: string | null } | null
}

function eventCredits(e: UsageEvent): number {
  if (e.credits_usd != null) return Number(e.credits_usd)
  // fallback for any legacy row missed by the backfill
  return computeCreditsUsd({
    model: e.model, inputTokens: e.input_tokens ?? 0, outputTokens: e.output_tokens ?? 0,
    cacheReadTokens: e.cache_read_tokens ?? 0, cacheWriteTokens: e.cache_write_tokens ?? 0,
  })
}
const eventTokens = (e: UsageEvent) => (e.input_tokens ?? 0) + (e.output_tokens ?? 0)
const round2 = (n: number) => Math.round(n * 100) / 100
const round4 = (n: number) => Math.round(n * 10000) / 10000

// GET /api/portfolios/consumption — credit/cost stats for the current portfolio (admin only)
portfolios.get('/consumption', async (c) => {
  const { portfolioId, role, isSuper } = c.get('tenant')
  if (role !== 'admin') return c.json({ error: 'Admin only' }, 403)
  const period = c.req.query('period') ?? '30d'
  const days = daysMap[period] ?? 30
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()

  const [{ data: pf }, { data: events }] = await Promise.all([
    supabase.from('portfolios').select('markup_factor').eq('id', portfolioId).single(),
    supabase
      .from('token_usage_events')
      .select('input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, credits_usd, category, source, model, asset_id, conversation_id, created_at, conversations(title, thread_type, activity_tag, output_type, asset_id)')
      .eq('portfolio_id', portfolioId)
      .gte('created_at', since),
  ])
  const markup = Number(pf?.markup_factor ?? 20)
  const evts = (events ?? []) as unknown as UsageEvent[]

  const totals = { tokens: 0, credits: 0, queries: 0 }
  const threadAgg: Record<string, { title: string | null; thread_type: string; output_type: string; activity_tag: string | null; asset_id: string | null; tokens: number; credits: number; queries: number; last: string }> = {}
  const assetAgg: Record<string, { tokens: number; credits: number; threads: Set<string> }> = {}
  const systemAgg: Record<string, { tokens: number; credits: number; events: number }> = {}
  const typeAgg: Record<string, { tokens: number; credits: number; queries: number }> = {}
  const outputAgg: Record<string, { tokens: number; credits: number; threads: Set<string> }> = {}
  const dayAgg: Record<string, { tokens: number; credits: number }> = {}

  for (const e of evts) {
    const tokens = eventTokens(e)
    const credits = eventCredits(e)
    totals.tokens += tokens; totals.credits += credits; totals.queries += 1

    const day = e.created_at.slice(0, 10)
    dayAgg[day] = dayAgg[day] ?? { tokens: 0, credits: 0 }
    dayAgg[day].tokens += tokens; dayAgg[day].credits += credits

    if (e.category === 'system') {
      const src = e.source ?? 'other'
      systemAgg[src] = systemAgg[src] ?? { tokens: 0, credits: 0, events: 0 }
      systemAgg[src].tokens += tokens; systemAgg[src].credits += credits; systemAgg[src].events += 1
      continue
    }

    const conv = e.conversations
    if (e.conversation_id) {
      const t = threadAgg[e.conversation_id] ?? {
        title: conv?.title ?? null, thread_type: conv?.thread_type ?? 'general',
        output_type: conv?.output_type ?? 'general_query', activity_tag: conv?.activity_tag ?? null,
        asset_id: conv?.asset_id ?? e.asset_id, tokens: 0, credits: 0, queries: 0, last: e.created_at,
      }
      t.tokens += tokens; t.credits += credits; t.queries += 1
      if (e.created_at > t.last) t.last = e.created_at
      threadAgg[e.conversation_id] = t

      const ty = conv?.thread_type ?? 'general'
      typeAgg[ty] = typeAgg[ty] ?? { tokens: 0, credits: 0, queries: 0 }
      typeAgg[ty].tokens += tokens; typeAgg[ty].credits += credits; typeAgg[ty].queries += 1

      const ot = conv?.output_type ?? 'general_query'
      outputAgg[ot] = outputAgg[ot] ?? { tokens: 0, credits: 0, threads: new Set() }
      outputAgg[ot].tokens += tokens; outputAgg[ot].credits += credits; outputAgg[ot].threads.add(e.conversation_id)
    }
    const aId = conv?.asset_id ?? e.asset_id
    if (aId) {
      assetAgg[aId] = assetAgg[aId] ?? { tokens: 0, credits: 0, threads: new Set() }
      assetAgg[aId].tokens += tokens; assetAgg[aId].credits += credits
      if (e.conversation_id) assetAgg[aId].threads.add(e.conversation_id)
    }
  }

  // Resolve asset names for the aggregate rows
  const assetIds = Object.keys(assetAgg)
  const nameById: Record<string, string> = {}
  if (assetIds.length) {
    const { data: assetRows } = await supabase.from('assets').select('id, name').in('id', assetIds)
    for (const a of assetRows ?? []) nameById[a.id] = a.name
  }

  const TYPE_LABELS: Record<string, string> = {
    portfolio: 'Portfolio', due_diligence: 'Due Diligence', capital_plan: 'Capital Planning',
    compliance: 'Compliance', financial_analysis: 'Financial Analysis', lease_review: 'Lease Review',
    document_review: 'Document Review', general: 'General',
  }

  const threadRow = ([id, t]: [string, typeof threadAgg[string]]) => ({
    conversation_id: id, title: t.title, thread_type: t.thread_type, output_type: t.output_type,
    activity_tag: t.activity_tag, tokens: t.tokens, credits: round4(t.credits),
    cost: round2(t.credits * markup), queries: t.queries, last_activity: t.last,
  })

  return c.json({
    period,
    ...(isSuper ? { markup_factor: markup } : {}),
    total_tokens: totals.tokens,
    total_credits: round4(totals.credits),
    total_cost: round2(totals.credits * markup),
    total_queries: totals.queries,
    total_threads: Object.keys(threadAgg).length,
    portfolio_threads: Object.entries(threadAgg).filter(([, t]) => !t.asset_id).map(threadRow)
      .sort((a, b) => b.credits - a.credits),
    assets: Object.entries(assetAgg).map(([id, a]) => ({
      asset_id: id, name: nameById[id] ?? 'Unknown asset', tokens: a.tokens,
      credits: round4(a.credits), cost: round2(a.credits * markup), thread_count: a.threads.size,
    })).sort((a, b) => b.credits - a.credits),
    system: Object.entries(systemAgg).map(([source, s]) => ({
      source, tokens: s.tokens, credits: round4(s.credits), cost: round2(s.credits * markup), events: s.events,
    })).sort((a, b) => b.credits - a.credits),
    by_type: Object.entries(typeAgg).map(([type, d]) => ({
      type, label: TYPE_LABELS[type] ?? type, tokens: d.tokens, queries: d.queries,
      credits: round4(d.credits), cost: round2(d.credits * markup),
      pct: totals.tokens > 0 ? Math.round((d.tokens / totals.tokens) * 100) : 0,
    })).sort((a, b) => b.tokens - a.tokens),
    by_output_type: Object.entries(outputAgg).map(([type, d]) => ({
      type, tokens: d.tokens, credits: round4(d.credits), cost: round2(d.credits * markup), threads: d.threads.size,
    })).sort((a, b) => b.tokens - a.tokens),
    by_day: Object.entries(dayAgg).sort(([a], [b]) => a.localeCompare(b)).map(([date, d]) => ({
      date, tokens: d.tokens, credits: round4(d.credits), cost: round2(d.credits * markup),
    })),
  })
})
```
Keep the existing `GET /consumption/tags` endpoint below unchanged. Delete the old `COST_INPUT_PER_TOKEN`/`MARKUP`/`tokenCost` constants. **Note:** `test/routes/admin.test.ts` and `AdminUsageView` use `/api/admin/usage`, which is untouched.

- [ ] **Step 4: Implement asset endpoint**

In `assets.ts`, add (import `computeCreditsUsd` and reuse the same shapes — extract `eventCredits`/`eventTokens`/`round2`/`round4`/`daysMap` into `src/lib/consumption-utils.ts` and import from both routers to stay DRY):
```ts
// GET /api/assets/:id/consumption — per-thread credit/cost breakdown (portfolio admin only)
assets.get('/:id/consumption', async (c) => {
  const assetId = c.req.param('id')
  const { portfolioId, role } = c.get('tenant')
  if (role !== 'admin') return c.json({ error: 'Admin only' }, 403)

  const { data: asset } = await supabase
    .from('assets').select('id').eq('id', assetId).eq('portfolio_id', portfolioId).single()
  if (!asset) return c.json({ error: 'Asset not found' }, 404)

  const period = c.req.query('period') ?? '30d'
  const days = daysMap[period] ?? 30
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()

  const [{ data: pf }, { data: events }] = await Promise.all([
    supabase.from('portfolios').select('markup_factor').eq('id', portfolioId).single(),
    supabase
      .from('token_usage_events')
      .select('input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, credits_usd, category, source, model, asset_id, conversation_id, created_at, conversations(title, thread_type, activity_tag, output_type, asset_id)')
      .eq('asset_id', assetId)
      .gte('created_at', since),
  ])
  const markup = Number(pf?.markup_factor ?? 20)
  // aggregate per conversation + system rows exactly as in the portfolio endpoint
  // (same threadAgg/systemAgg loop over (events ?? []) as UsageEvent[]),
  // then return:
  return c.json({
    period, asset_id: assetId,
    total_tokens, total_credits: round4(totalCredits), total_cost: round2(totalCredits * markup),
    total_threads: Object.keys(threadAgg).length,
    threads: Object.entries(threadAgg).map(threadRow).sort((a, b) => b.credits - a.credits),
    system: systemRows,
  })
})
```
(The aggregation loop is the same shape as Task 7 Step 3's — reuse via `consumption-utils.ts`: export `aggregateUsage(events: UsageEvent[])` returning `{ totals, threadAgg, systemAgg, typeAgg, outputAgg, dayAgg }` and use it in BOTH endpoints so the logic exists once.)

- [ ] **Step 5: Run tests + typecheck — expect PASS/clean.**

Run: `npx vitest run test/routes/portfolios.test.ts test/routes/assets.test.ts --pool=forks --poolOptions.forks.singleFork=true`

- [ ] **Step 6: Commit**

```bash
cd /home/claude/soapbox-platform
git add apps/api/src/routes/portfolios.ts apps/api/src/routes/assets.ts apps/api/src/lib/consumption-utils.ts apps/api/test/routes/portfolios.test.ts apps/api/test/routes/assets.test.ts
git commit -m "feat(consumption): portfolio consumption reshape (credits/cost/assets/system) + asset drill-in endpoint"
git push
```

---

### Task 8: Frontend — portfolio consumption page rebuild + markup editor

**Files:**
- Modify: `platform-web/src/components/app/settings/ConsumptionView.tsx` (rewrite)
- Create: `platform-web/src/components/app/settings/MarkupEditor.tsx`
- Modify: `platform-web/src/app/(app)/settings/consumption/page.tsx`
- Test: `platform-web/src/components/app/settings/__tests__/ConsumptionView.test.tsx` (update)

**Interfaces:**
- Consumes: `PortfolioConsumption` payload (Task 7), `apiFetch` from `src/lib/api-client.ts`, `getSettingsContext()`.
- Produces: rendered portfolio consumption page; asset rows link to `/assets/{asset_id}/settings#consumption`.

- [ ] **Step 1: Update `ConsumptionStats` type + rewrite `ConsumptionView`**

Replace the type with the Task 7 payload (`total_cost`, `total_credits`, `portfolio_threads`, `assets`, `system`, `by_type` w/ `cost`, `by_output_type`, `by_day` w/ `credits`+`cost`, optional `markup_factor`). Rewrite the component keeping the existing visual language (`SettingsCard`, `StatCard`, inline styles with CSS vars):
1. Four `StatCard`s: **Cost** (`fmtCredits(total_cost)`), **Credits (Anthropic $)** (`fmtCredits(total_credits)`), **Threads** (`total_threads`), **Tokens** (`fmt(total_tokens)`).
2. **Portfolio threads** table (`portfolio_threads`): Title · Type · Output · Credits · Cost — plain rows, empty-state text "No portfolio-level threads in this period."
3. **Assets** table (`assets`): each row is a Next `<Link href={`/assets/${a.asset_id}/settings#consumption`}>` — Name · Threads · Credits · Cost.
4. **System usage** table (`system`): Source (humanize: `rsra_pipeline` → "RSRA pipeline", `title_gen` → "Thread titles", `tag_gen` → "Thread tagging", `suggest` → "Suggestions", `address_extract` → "Address extraction", `building_detect` → "Building detection", `bulk_extract` → "Bulk extraction") · Events · Credits · Cost.
5. Keep the existing **By activity type** bar list (now also showing `cost`) and **Daily usage** sparkline (bars by `cost`).
Number formatting: reuse `fmt`/`fmtCredits`.

- [ ] **Step 2: Create `MarkupEditor.tsx`**

```tsx
"use client";
import { useState } from "react";
import { SettingsCard } from "@/components/app/settings/SettingsCard";
import { apiFetch, apiError, type ApiAuth } from "@/lib/api-client";

export function MarkupEditor({ auth, initial }: { auth: ApiAuth; initial: number }) {
  const [value, setValue] = useState(String(initial));
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setSaving(true); setMsg(null);
    const res = await apiFetch(auth, "/api/portfolios/markup", {
      method: "PATCH", body: { markup_factor: Number(value) },
    });
    setSaving(false);
    setMsg(res.ok ? "Saved" : await apiError(res));
  }

  return (
    <SettingsCard>
      <p style={{ margin: "0 0 4px", fontWeight: 600 }}>Markup factor</p>
      <p style={{ margin: "0 0 12px", fontSize: "var(--text-xs)", color: "var(--muted-foreground)" }}>
        Cost shown to this portfolio = Anthropic credits × this factor. Visible to platform admins only.
      </p>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="number" min={1} max={1000} step={0.5} value={value}
          onChange={(e) => setValue(e.target.value)}
          style={{ width: 100, padding: "6px 8px", border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--background)", color: "var(--foreground)" }} />
        <button onClick={save} disabled={saving}
          style={{ padding: "6px 14px", border: "1px solid var(--border)", borderRadius: "var(--radius)", background: "var(--foreground)", color: "var(--background)", cursor: "pointer" }}>
          {saving ? "Saving…" : "Save"}
        </button>
        {msg && <span style={{ fontSize: "var(--text-xs)", color: "var(--muted-foreground)" }}>{msg}</span>}
      </div>
    </SettingsCard>
  );
}
```

- [ ] **Step 3: Wire the page**

In `settings/consumption/page.tsx`, after fetching `stats`, render the editor only when the payload carries `markup_factor` (i.e. super owner):
```tsx
{stats?.markup_factor !== undefined && accessToken && (
  <div style={{ marginBottom: 16 }}>
    <MarkupEditor auth={{ apiUrl, accessToken, orgId }} initial={stats.markup_factor} />
  </div>
)}
```

- [ ] **Step 4: Update `ConsumptionView.test.tsx`** to the new payload shape (build a fixture matching `PortfolioConsumption`, assert cost/credits stat cards render, asset row links to `/assets/<id>/settings#consumption`, and the System table shows the humanized source). Run the platform-web test command used by the existing suite (check `package.json` scripts; run only this file).

- [ ] **Step 5: Typecheck + commit + deploy**

```bash
cd /home/claude/platform-web && npx tsc --noEmit
git add src/components/app/settings/ConsumptionView.tsx src/components/app/settings/MarkupEditor.tsx src/app/(app)/settings/consumption/page.tsx src/components/app/settings/__tests__/ConsumptionView.test.tsx
git commit -m "feat(consumption): portfolio consumption rebuild — cost/credits, asset drill-in links, system row, markup editor"
git push
```
(platform-web deploys per its existing flow — push to the repo's deploy branch; check memory `platform-web-react-rewrite` conventions.)

---

### Task 9: Frontend — asset consumption section

**Files:**
- Create: `platform-web/src/components/app/settings/AssetConsumptionSection.tsx`
- Modify: `platform-web/src/app/(app)/assets/[id]/settings/page.tsx`

**Interfaces:**
- Consumes: `AssetConsumption` payload (Task 7).
- Produces: per-thread credits/cost table on the asset settings page, anchor `#consumption` (target of the portfolio page's asset links).

- [ ] **Step 1: Create the section component** (server-renderable, pure props — mirror ConsumptionView's table styling):

```tsx
import { SettingsCard } from "@/components/app/settings/SettingsCard";

export type AssetConsumption = {
  period: string; asset_id: string;
  total_tokens: number; total_credits: number; total_cost: number; total_threads: number;
  threads: { conversation_id: string; title: string | null; thread_type: string; output_type: string; activity_tag: string | null; tokens: number; credits: number; cost: number; queries: number; last_activity: string }[];
  system: { source: string; tokens: number; credits: number; cost: number; events: number }[];
};

function fmtMoney(n: number) { return n >= 1 ? "$" + n.toFixed(2) : (n * 100).toFixed(1) + "¢"; }

export function AssetConsumptionSection({ stats }: { stats: AssetConsumption | null }) {
  return (
    <div id="consumption" style={{ maxWidth: 720, margin: "24px auto", padding: "0 16px 32px" }}>
      <h2 style={{ fontSize: "var(--text-lg)", fontWeight: 600, margin: "0 0 12px" }}>Consumption (30d)</h2>
      {!stats || stats.total_threads === 0 ? (
        <SettingsCard><p style={{ margin: 0, color: "var(--muted-foreground)" }}>No usage data for this period.</p></SettingsCard>
      ) : (
        <SettingsCard>
          <p style={{ margin: "0 0 12px", fontSize: "var(--text-sm)", color: "var(--muted-foreground)" }}>
            {fmtMoney(stats.total_cost)} cost · {fmtMoney(stats.total_credits)} credits · {stats.total_threads} threads
          </p>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}>
            <thead><tr style={{ textAlign: "left", color: "var(--muted-foreground)" }}>
              <th style={{ padding: "6px 8px" }}>Thread</th><th>Type</th><th>Output</th>
              <th style={{ textAlign: "right" }}>Credits</th><th style={{ textAlign: "right", padding: "6px 8px" }}>Cost</th>
            </tr></thead>
            <tbody>
              {stats.threads.map((t) => (
                <tr key={t.conversation_id} style={{ borderTop: "1px solid var(--border)" }}>
                  <td style={{ padding: "6px 8px" }}>{t.title ?? "Untitled"}</td>
                  <td>{t.thread_type}</td><td>{t.output_type}</td>
                  <td style={{ textAlign: "right" }}>{fmtMoney(t.credits)}</td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>{fmtMoney(t.cost)}</td>
                </tr>
              ))}
              {stats.system.map((s) => (
                <tr key={s.source} style={{ borderTop: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
                  <td style={{ padding: "6px 8px" }}>System · {s.source}</td><td>—</td><td>—</td>
                  <td style={{ textAlign: "right" }}>{fmtMoney(s.credits)}</td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>{fmtMoney(s.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </SettingsCard>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Fetch + render in the asset settings page**

In `assets/[id]/settings/page.tsx`, after the existing `Promise.all`, fetch the consumption payload server-side (only when a session exists) and render the section below `<SettingsView>` inside the scroll container:
```tsx
let consumption: AssetConsumption | null = null;
if (session?.access_token) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/assets/${id}/consumption?period=30d`, {
      headers: { Authorization: `Bearer ${session.access_token}`, ...(orgId ? { "x-organization-id": orgId } : {}) },
      cache: "no-store",
    });
    if (res.ok) consumption = (await res.json()) as AssetConsumption;
  } catch { /* degrade gracefully */ }
}
// in JSX, inside the scrolling div, after <SettingsView ... />:
<AssetConsumptionSection stats={consumption} />
```
Note: the endpoint is admin-gated — a 403 leaves `consumption` null and the section renders the empty state; that is acceptable for members.

- [ ] **Step 3: Typecheck + commit + deploy**

```bash
cd /home/claude/platform-web && npx tsc --noEmit
git add src/components/app/settings/AssetConsumptionSection.tsx "src/app/(app)/assets/[id]/settings/page.tsx"
git commit -m "feat(consumption): asset settings consumption section with per-thread cost"
git push
```

---

### Task 10: E2E + production pilot verification

**Files:**
- Modify: `soapbox-agent` (nothing — verification only; record results in SDD ledger)

**Interfaces:**
- Consumes: everything above, deployed to prod (Railway auto-deploy for api; Vercel for web).

- [ ] **Step 1: Wait for deploys** — confirm the soapbox-api Railway deploy for the last apps/api commit succeeded (use the deploy-log recipe from memory if needed) and the Vercel deploy for platform-web is live.

- [ ] **Step 2: Run the soapbox-e2e skill** covering: portfolio Settings → Consumption renders totals + asset rows + System row; clicking an asset row lands on the asset settings consumption section; markup editor visible when logged in as christopher@soapbox.build and ABSENT for the e2e service account; markup PATCH via API as service account returns 403.

- [ ] **Step 3: Live metering check** — as the service account, send one thread message on a Cortland test asset; verify via Supabase:
```sql
select model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, credits_usd, category
from token_usage_events order by created_at desc limit 5;
```
Expected: a `thread` row with non-zero cache tokens and `credits_usd` consistent with opus rates; plus `system`/`title_gen` + `tag_gen` rows after the title/classification fire.

- [ ] **Step 4: System-call check** — hit `/api/extract-address` with a small test PDF (service account); verify an `address_extract` system row lands with `portfolio_id` set.

- [ ] **Step 5: Cleanup** — bulk-delete the test thread + its `token_usage_events` rows via Supabase MCP (standing cleanup rule).

- [ ] **Step 6: Record results** in `soapbox-agent/.superpowers/sdd/progress.md` and commit.

---

## Self-Review Notes

- Spec coverage: rate table (T2), write-time credits + backfill (T1/T3), capture-all incl. cache (T3–T5), markup + super owner (T1/T6), consumption views (T7–T9), output_type incl. deliverable stamping (T1/T4/T5), e2e/pilot (T10). `by_output_type` grouping included (T7).
- Spec deviation (intentional): spec's "RSRA re-stamps a conversation" is impossible — RSRA runs are asset-scoped, not conversation-scoped; deliverable stamping instead hooks `create_artifact`/`fill_report` in managed-agents-runtime, which IS where conversation deliverables are produced.
- Old `tokenCost`/`MARKUP` constants deleted in T7; `/api/admin/usage` untouched.
- `platform-web` test-runner command intentionally left as "use the repo's existing script" — verify in `package.json` at execution time.
