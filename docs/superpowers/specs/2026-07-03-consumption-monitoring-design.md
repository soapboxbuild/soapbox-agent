# Consumption Monitoring v2 — Design Spec

**Date:** 2026-07-03
**Status:** Approved by Christopher (brainstorm session)
**Repos:** soapbox-platform (apps/api, main = auto-deploy), platform-web (Vercel)

---

## Problem

The platform already meters thread token usage (`token_usage_events`, portfolio
`/consumption` endpoint, ConsumptionView UI), but the numbers are wrong and
incomplete, and the views don't answer the questions an operator has:

1. Pricing is a flat $1/$5 per MTok "Haiku blended" for every model, while
   threads default to Opus 4.8 ($5/$25). Reported cost is fiction.
2. Cache read/write tokens are captured by the agent runtime but dropped
   before billing; six non-thread LLM call sites (RSRA pipeline, thread
   title/tag generation, address extraction, building detection, bulk
   extraction ×2) bill nothing at all.
3. Markup is hardcoded at 10× in code — not per-portfolio, not settable.
4. There is no per-thread cost view, no asset-level consumption view, and no
   portfolio view splitting portfolio threads vs per-asset aggregates.
5. No platform-level "super owner" role exists to own the markup knob.

## Approved decisions

- **Semantics:** `credits` = raw Anthropic commercial $ consumed (true
  per-model pricing incl. cache). `cost` = credits × per-portfolio
  `markup_factor` (default **20×**), applied at read time.
- **Super owner:** new `platform_admins` table (seeded with Christopher's
  user id); `is_super` exposed on the tenant context. Only super owners see
  and edit `markup_factor` (and the raw-vs-marked-up split).
- **Visibility:** portfolio/asset **admins** see credits + cost per thread.
  Members see nothing new. Markup value/editor is super-owner-only.
- **Capture all credits:** every LLM call is metered. Non-thread calls are
  recorded with `category='system'` + a `source` tag and **billed to the
  portfolio** (System row in the UI).
- **Thread tagging:** keep `thread_type` + `activity_tag`; add an
  **`output_type`** dimension for what the thread PRODUCED
  (`general_query | report | analysis | data_update | plan`), auto-tagged by
  the existing Haiku tagger and re-stamped when a deliverable is actually
  generated (report render, RSRA run).
- **Views:** portfolio consumption = totals + portfolio-thread rows + one
  aggregate row per asset (+ System row); drill into an asset for per-thread
  credits/cost. Asset settings gets its own Consumption tab.
- **Architecture (Approach A):** persist `credits_usd` per event at write
  time from a versioned per-model rate table; markup applied at read time.

## Architecture

### Rate table (new module `apps/api/src/lib/model-pricing.ts`)

Per-MTok USD rates, verified against Anthropic pricing 2026-07-03:

| Model | Input | Output | Cache write (1.25×) | Cache read (0.1×) |
|---|---|---|---|---|
| claude-opus-4-8 / 4-7 / 4-6 | 5.00 | 25.00 | 6.25 | 0.50 |
| claude-sonnet-4-6 / 4-5 | 3.00 | 15.00 | 3.75 | 0.30 |
| claude-haiku-4-5(-20251001) | 1.00 | 5.00 | 1.25 | 0.10 |

- `PRICING_VERSION` constant stamped conceptually via write-time persistence
  (an event's `credits_usd` never changes after write).
- Unknown model → Opus rates (conservative) + `console.error` warning
  (never-fail-silently).
- Exported `computeCreditsUsd({model, inputTokens, outputTokens,
  cacheReadTokens, cacheWriteTokens}): number`.

### Data model (4 additive migrations)

1. `token_usage_events` + `cache_read_tokens int default 0`,
   `cache_write_tokens int default 0`, `credits_usd numeric(12,6)`,
   `category text not null default 'thread' check in ('thread','system')`,
   `source text` (e.g. `rsra_pipeline`, `title_gen`, `tag_gen`,
   `address_extract`, `building_detect`, `bulk_extract`).
   **Backfill:** one UPDATE computing `credits_usd` from existing
   `model` + token counts (cache = 0) using the rate table values inlined in
   SQL.
2. `portfolios` + `markup_factor numeric(6,2) not null default 20`.
3. `platform_admins (user_id uuid primary key references auth.users,
   created_at)` — seeded with Christopher's user id; RLS: readable by self,
   writable by service role only.
4. `conversations` + `output_type text not null default 'general_query'
   check in ('general_query','report','analysis','data_update','plan')`.

### Capture pipeline

- `recordLlmUsage(opts)` helper (in billing-worker or a new
  `lib/llm-metering.ts`): computes `credits_usd` via the rate table and
  enqueues the existing BullMQ `token-billing` job with the extended payload
  (cache tokens, category, source, credits). Fire-and-forget with loud error
  logging — a metering failure never breaks a chat turn or pipeline run.
- `billing-worker.ts`: extended `BillingJobData`; inserts the new columns.
  Stripe meter events unchanged (out of scope).
- `messages.ts` SSE loop: pass `cacheReadTokens`/`cacheWriteTokens` through
  (stop dropping them); category `thread`.
- Wrap the six unmetered call sites with `recordLlmUsage` using the response
  `usage` object, `category='system'`, portfolio/asset attribution from
  their own context, `conversation_id=null`:
  `lib/rsra-pipeline.ts`, `routes/messages.ts` (title gen + tag gen),
  `routes/extract-address.ts`, `routes/detect-buildings.ts`,
  `routes/bulk-extract.ts` (2 sites).

### API

- `GET /api/portfolios/consumption` (admin-gated, per existing pattern)
  reshaped:
  - totals: `total_credits` (raw $), `total_cost` (credits × markup),
    tokens, queries, threads
  - `portfolio_threads[]`: per-thread rows for portfolio-level conversations
    (title, thread_type, output_type, tokens, credits, cost, last_activity)
  - `assets[]`: one aggregate row per asset (name, tokens, credits, cost,
    thread_count) — the drill-in link target
  - `system`: aggregate of `category='system'` events grouped by `source`
  - `by_type` / `by_output_type` / `by_day` groupings (credits + cost)
  - `markup_factor` included **only when** `is_super`
  - Read path prefers stored `credits_usd`; falls back to computing from
    tokens for any row where it is null (belt and suspenders).
- `GET /api/assets/:id/consumption` (asset admin-gated): per-thread rows for
  that asset with credits, cost, tags, query count, last activity; plus the
  asset's System row.
- `PATCH /api/portfolios/markup` `{markup_factor}` — 403 unless `is_super`;
  validates 1 ≤ factor ≤ 1000.
- `middleware/tenant.ts`: look up `platform_admins` for the session user and
  set `is_super` on the tenant context (single indexed PK lookup; cached per
  request).

### Frontend (platform-web)

- Rebuild `settings/consumption/page.tsx` + `ConsumptionView.tsx`:
  summary tiles (credits, cost, tokens, threads) → portfolio-threads table →
  per-asset aggregate table (row click → asset consumption) → System row.
  Reuse `SettingsCard`, `TimePeriodSelector`.
- New asset consumption view at `assets/[id]/settings` (Consumption tab or
  section): per-thread table with credits/cost/output_type.
- Markup editor card renders only when the consumption payload carries
  `markup_factor` (i.e. super owner); PATCH on save.
- Members/admins see credits + cost; nothing displays raw-vs-markup split
  except for super owner.

### Output-type tagging

- Extend the Haiku auto-tagger prompt in `messages.ts` to also emit
  `output_type` (enum-constrained) alongside title/activity_tag.
- Deliverable re-stamping: where the platform knows a deliverable was
  produced (RSRA pipeline completion, report render/export paths), update
  the conversation's `output_type` to `report` (or `analysis`/`plan` as
  appropriate) directly.

## Failure handling

- Metering is fire-and-forget: enqueue/insert failures are logged with
  enough context to re-derive (conversation id, model, tokens) but never
  fail the user-facing operation.
- Rate-table miss → conservative Opus pricing + logged warning.
- Markup PATCH is validated and super-owner-gated; the consumption read
  never 500s on a null markup (coalesce to 20).

## Non-goals (v1)

- Stripe meter/invoicing changes (existing meter events untouched).
- Allowance enforcement, quotas, budgets, alerts.
- Retroactive recovery of historically unmetered system calls.
- Org-level consumption roll-up across portfolios.

## Testing

- Unit: rate table (per-model, cache rates, unknown-model fallback),
  `recordLlmUsage` payload shape, markup math.
- API: consumption endpoint shape (admin vs member vs super owner payload
  differences), asset drill-in, markup PATCH authz (member 403, admin 403,
  super 200).
- Backfill verification query: no null `credits_usd` rows post-migration.
- E2E (soapbox-e2e, REQUIRED): portfolio consumption page renders totals +
  asset rows; drill into an asset shows per-thread costs; markup editor
  visible to Christopher's account and hidden for the service account;
  System row appears after an address-extract call.
- Live production check: send one thread message on a test asset, confirm a
  `token_usage_events` row with cache tokens + credits_usd lands and the UI
  reflects it. Clean up test records per standing rule.

## Open questions for implementation

1. Exact Vitest/test-runner setup in apps/api (respect the fork-pool
   constraint on this VM).
2. Whether asset settings uses a tab component or a section on the existing
   page — follow whatever `assets/[id]/settings/page.tsx` already does.
3. Christopher's auth.users id for the platform_admins seed — resolve from
   Supabase (`christopher@soapbox.build`) at migration-writing time.
