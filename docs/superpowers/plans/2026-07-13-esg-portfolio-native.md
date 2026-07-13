# Portfolio-Native ESG (2a) — Implementation Plan

> Execute with subagent-driven-development. Steps use `- [ ]`.

**Goal:** Make ESG a true portfolio-thread workflow — the fund-level ESG profile runs at a portfolio thread (`asset_id` null), renders + stores an artifact at portfolio scope, and the scripted replay fires on portfolio threads.

**Architecture:** Relax the asset-only artifact model (nullable `artifacts.asset_id` + RLS portfolio fallback), let `renderReport`/runtime handle portfolio scope, stage the ESG fund inputs at portfolio scope, teach esg-profile to run+render at portfolio scope, ensure the portfolio-thread UI shows the artifact, then live-run → record → freeze.

## Global Constraints
- Shared prod+stage DB (`fplbvanvwvnviczozwhz`) — migration is careful, reversible, Demo-safe; RLS must not widen visibility beyond the artifact's conversation's portfolio.
- Branches: soapbox-platform `feat/esg-portfolio-native`; soapbox-agent `feat/esg-portfolio-native`. Build+commit; deploy only at Task 7.
- RLS invariant: an `asset_id`-null artifact is visible iff the user can see its conversation's `portfolio_id`. Never broaden.
- Reuse the working MCP endpoints (firststreet/fabric service domains) + the Railway API token pattern already in memory.

---

### Task 1: Migration — nullable `artifacts.asset_id` + RLS portfolio fallback
**Files:** `soapbox-platform/supabase/migrations/20260713_artifacts_portfolio_scope.sql` (create); apply via Supabase.
- [ ] Read the current artifacts RLS (`20260612000004_artifacts.sql` select/insert + `20260621000001_rls_write_policies.sql`) and confirm a portfolio-visibility helper exists (`can_see_portfolio` or portfolio_members lookup). Report what's there.
- [ ] Write migration: `alter table artifacts alter column asset_id drop not null;` + drop/recreate the artifacts SELECT and INSERT policies to: `can_see_asset(asset_id)` **OR** `(asset_id is null and exists (select 1 from conversations c where c.id = artifacts.conversation_id and can_see_portfolio(c.portfolio_id)))`. Use the exact portfolio-visibility predicate the codebase already uses.
- [ ] Apply to the DB (Supabase apply_migration). Verify: an asset-null artifact on a Demo conversation is selectable by a Demo member and NOT by a non-member (test with a scoped query).
- [ ] Commit the migration file.

### Task 2: `renderReport` — allow null assetId + skip Files copy when null
**Files:** `soapbox-platform/apps/api/src/services/render-report.ts`; Test: `__tests__/render-report.portfolio.test.ts`
- [ ] Failing test: `renderReport({assetId: undefined/null, conversationId, template:'esg-profile', data, userId})` returns `ok:true`, upserts an artifact with `asset_id null`, and does NOT attempt the Files-store save.
- [ ] Implement: guard the Files-store block (currently `const assetId = p.assetId ?? ''` … uploadFile) with `if (p.assetId) { …files save… }`; the artifacts upsert already passes `asset_id: p.assetId` (null now allowed). Keep verifier-gate logic unchanged.
- [ ] Test passes; `tsc` clean; full suite delta = none new.
- [ ] Commit.

### Task 3: Runtime replay — fire on portfolio threads (assetId null)
**Files:** `soapbox-platform/apps/api/src/services/managed-agents-runtime.ts` (the `sendMessage` short-circuit); Test: `__tests__/managed-agents-runtime.demo-branch.test.ts` (extend)
- [ ] Failing test: a Demo-org **portfolio** message (`assetId: null`) with an esg prompt + esg fixture → `replayDemoFixture` is called (currently blocked by the `if (params.assetId)` guard).
- [ ] Implement: relax the guard so the branch runs when a workflow classifies + a fixture loads, regardless of `assetId` (keep: classify-before-org-lookup ordering; real-org live path untouched). `replayDemoFixture` passes `ctx.assetId` (may be null → renderReport now allows it).
- [ ] Tests pass (incl. existing null-asset test now inverted for esg); tsc clean.
- [ ] Commit.

### Task 4: Stage ESG fund inputs as Demo-portfolio files
**Files:** ops (Files store); optionally `soapbox-agent/demo-staging/stage-esg-portfolio.sh`
- [ ] Upload `fund-peers.json`, the sponsor `extract.xlsx`, `notes_scrubbed.docx`, `materiality.json`, `bps_cache.json` (from `skills/esg-profile/demo/madison/` + `reference/`) to the **Demo portfolio** Files store (portfolio-scoped) via the service-account app API. Idempotent.
- [ ] Verify they appear in `list_portfolio_files` for the Demo portfolio.

### Task 5: esg-profile SKILL.md — portfolio-scope run + render
**Files:** `soapbox-agent/skills/esg-profile/SKILL.md`
- [ ] Add explicit guidance: for `scope: fund` at a portfolio thread, read the fund inputs from **portfolio files** (list/read_portfolio_file), assemble `fund_overview` (from fund-peers) + the sponsor deep-dive, and render via `fill_report(esg-profile)` at portfolio scope (no asset). Keep the connector calls (firststreet/fabric/etc.).
- [ ] Re-sync gate: null `anthropic_skill_id` on the Demo portfolio soapbox-agent row (done at Task 7 deploy).
- [ ] Commit.

### Task 6: Portfolio-thread UI shows the artifact
**Files:** `platform-web` portfolio-thread page/components
- [ ] Confirm the portfolio-thread chat page renders artifacts from the SSE `artifact` event / the conversation's artifacts (same as asset chat). If it doesn't (asset-only assumption), make the minimal fix so a portfolio-thread artifact displays.
- [ ] If already handled, note it (no change).

### Task 7: Deploy + live portfolio-thread run → verify
- [ ] Merge soapbox-platform `feat/esg-portfolio-native` → main + deploy soapbox-api (migration already applied). Null the Demo soapbox-agent `anthropic_skill_id`; restart clears cache + re-syncs the skill.
- [ ] Run the fund-scope ESG at a Demo **portfolio thread** (service account). Verify: agent calls firststreet/fabric (+ crrem/espm), reconciles, and renders an artifact with `meta` + `sponsor` + populated `fund_overview`, stored with `asset_id null`.
- [ ] Confirm the artifact displays in the portfolio-thread UI.

### Task 8: Record → freeze `esg.json` → verify replay on portfolio thread
- [ ] `build-fixture-from-run.mjs` from the live artifact → new `esg.json` (fund+sponsor); scrub-clean; loader-valid.
- [ ] Freeze at `apps/api/src/services/demo-fixtures/esg.json`; commit; deploy.
- [ ] Verify the replay now fires on a fresh Demo **portfolio thread** with an esg prompt and renders the fund+sponsor profile. Clean up test conversations.

## Self-Review
- Covers 2a design points: nullable asset_id + RLS fallback (T1), renderReport null-asset (T2), replay portfolio-fire (T3), inputs at portfolio scope (T4), skill portfolio pipeline (T5), UI (T6), live run (T7), record/freeze/verify (T8).
- RLS is the security-critical task (T1) — gets careful review + a visibility test.
- No placeholder RLS: T1 reads the exact existing predicate and reuses it.
