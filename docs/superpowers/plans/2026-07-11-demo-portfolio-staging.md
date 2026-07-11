# Demo Portfolio Staging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stage the "Demo" org so three sustainability workflows (RSRA, ESG Profile, Decarb+Measure Ideation) run reliably with ~30–60 s turns as *real* managed-agent workflows on stage.

**Architecture:** One asset per workflow in the existing "Demo" portfolio, each with a minimal tool allowlist. Speed comes from pre-staged **state + helper files + cached tool results** that the *already-installed, unmodified* skills read — never from skill code edits or gate-gaming. Reports still render live through `fill_report`; only the slow compute upstream is pre-computed. All names pseudonymized via freshly authored fixtures.

**Tech Stack:** Supabase (Postgres) via MCP on project `fplbvanvwvnviczozwhz`; the Soapbox managed-agent runtime; MCP servers (audette, verifier, physrisk, crrem, costing, soapbox-agent/templates, memory); Node/Python fixture + scrub scripts; service-account app API for thread creation.

## Global Constraints

- **Scope: Demo org ONLY** — org `8ebc72a7-dca1-4cb1-be02-eed12f38340f`, portfolio "Demo" `3b683c32-ea8e-4851-b350-fd7b85a60e2e`. Never write to any other org/portfolio.
- **No skill code edits, no new skills, no new MCP servers.** Managed-agent bundles are frozen at install; re-sync the *current* bundle only.
- **No gate-gaming.** The decarb render gate is hard/fails-closed. Satisfy it only by staging genuinely-completed analysis (real reconciled baseline/measures/economics + resolved verifier findings + verifier connector row). Never record-and-confirm a token finding; never `save_file`-bypass a blocked render.
- **Reports render ONLY via `fill_report`.** Do not author or stage report HTML as the deliverable. Stage the *data/inputs*; the live run calls `fill_report`.
- **Pseudonymize everything.** Author fresh pseudonymous fixtures. Real inbox sources (`~/inbox/Prose Frontier OM.pdf`, ESG DD PDFs, `4th and Madison.zip`) are reference-only and are NEVER parsed live on stage. A fail-closed scrub gate must pass before any fixture is staged.
- **Idempotent staging.** Every seed script is check-first / upsert and re-runnable before each demo.
- **Turn budget:** ~30–60 s per turn; each workflow's slow lookups must resolve from cache, leaving only 2–3 hero live calls.
- **Analytics standards** (any number shown): kWh + kWh/m² only, ≤2 sig figs, BPD peer benchmarks (not national median), IRR = incremental cost + landlord-share savings + conditional exit value.

**Staging artifact locations:**
- Seed scripts + runbooks: `~/soapbox-agent/demo-staging/` (new).
- Per-skill fixtures: `~/soapbox-agent/skills/<skill>/demo/` (esg-profile/demo exists; create rsra/demo, decarb-plan/demo).
- Scrub denylist (untracked): `~/soapbox-agent/demo-staging/.scrub-denylist.json`.

---

## Phase 0 — Environment & mechanism spike (blocking)

### Task 0.1: Confirm the write target and service-account path

**Files:** Create `demo-staging/00-env.md`

- [ ] **Step 1: Confirm stage serves from `fplbvanvwvnviczozwhz` (not a hidden branch).**
Run (Supabase MCP `execute_sql`, project `fplbvanvwvnviczozwhz`):
```sql
select current_database(), (select count(*) from organizations where id='8ebc72a7-dca1-4cb1-be02-eed12f38340f') as demo_org_present;
```
Expected: `demo_org_present = 1`. Then open `stage.soapbox.build` in Playwright, confirm the Demo org + "4400 PRAIRIE CROSSING" asset are visible → the app reads this DB.

- [ ] **Step 2: Confirm service-account thread-creation path.**
Retrieve the claude@agents service-account creds (per `drive-soapbox-app-own-login` memory: Supabase auth → API POST conversations+messages with `x-organization-id`). Record the base URL for stage and the org header value in `00-env.md`.

- [ ] **Step 3: Commit.**
```bash
cd ~/soapbox-agent && git add demo-staging/00-env.md && git commit -m "docs(demo): confirm stage DB + service-account write path"
```

### Task 0.2: Verify the installed skill bundle contains the three skills

**Files:** Append to `demo-staging/00-env.md`

- [ ] **Step 1: List the skills actually installed on the Demo portfolio's soapbox-agent row.**
```sql
select jsonb_agg(s->>'name' order by s->>'name') skill_names, count(*) n
from installed_plugins ip, jsonb_array_elements(ip.skills) s
where ip.portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and ip.plugin_id='soapbox-agent';
```
Expected: a list of ~14 skill names. **Record whether `rsra`, `esg-profile`, `decarb-plan` are present.**

- [ ] **Step 2: Compare to local repo skills.**
Run: `ls ~/soapbox-agent/skills/` — note any of the three missing from Step 1 (esg-profile is the likely gap since installed n_skills=14 < local dir count).

- [ ] **Step 3: Record the re-sync requirement** in `00-env.md`: which skills are missing, and that `skills_synced_sha` is NULL (needs re-register). Commit.

### Task 0.3: Spike — the per-skill "pickup contract" (THE crux)

**Files:** Create `demo-staging/pickup-contract.md`

This task determines *exactly* how each skill reads staged state so its slow phases short-circuit. Its output drives all of Phase 4. Do NOT write Phase 4 seed SQL until this is filled in with verified answers.

- [ ] **Step 1: RSRA input pickup.** Read `skills/rsra/SKILL.md` phases 1–9. Answer in `pickup-contract.md`:
  - How does RSRA discover the OM? (`search_files("offering memorandum")` → the `files` table.)
  - Which lookups are slow and cacheable (physrisk hazard, BPS, benchmark, incentives) and does the skill read a memory/file cache before calling the MCP? Record the exact memory `key`/file name each phase reads, or note "no cache hook — must rely on connector stubbing."
  - Confirm the render is `fill_report(template:'rsra', data)` and list the required data fields.

- [ ] **Step 2: Decarb state persistence.** Read `skills/decarb-plan/SKILL.md` (state handling) + `state-schema.json`. Answer:
  - Where is the engagement `state` object (phase/baseline/measures/targets/audette/citations/report) persisted and read? Check candidates in order: memory MCP (`agent-memory.soapbox.build`, list memories for the asset), conversation `files`, `assets.metadata`. Run for a real completed decarb asset (e.g. a Cortland asset in portfolio `8cea3d4f-2387-4f89-beb2-60937dc761e1`):
```sql
select scope, key, left(value,120) from memories where asset_id in
 (select id from assets where portfolio_id='8cea3d4f-2387-4f89-beb2-60937dc761e1') order by updated_at desc limit 30;
```
  - Record the exact store + key convention decarb uses for `state`.

- [ ] **Step 3: Verifier gate satisfaction.** Read the render-gate rules in decarb SKILL + confirm via the verifier MCP. Answer:
  - Does `verifier__verification_status({asset_id})` need zero open-high findings, or resolved findings? What `asset_connectors` row must exist (per `verifier-connector-row-gap`: `plugin_id='plugin_verifier'` scoped to portfolio/asset with the proxy for the trusted header)?
  - Record the exact `verifier__record_finding` / resolve calls needed to reach a passing status.

- [ ] **Step 4: Commit** the completed contract.
```bash
cd ~/soapbox-agent && git add demo-staging/pickup-contract.md && git commit -m "docs(demo): per-skill staged-state pickup contract"
```

---

## Phase 1 — Bundle & per-asset tooling

### Task 1.1: Re-sync the current skill bundle to the Demo portfolio

**Files:** Create `demo-staging/10-resync-bundle.sh`

- [ ] **Step 1: Write the verification query (expect current/missing).**
```sql
select plugin_id, skills_synced_sha, jsonb_array_length(skills) n
from installed_plugins where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and plugin_id='soapbox-agent';
```
Record current `n` and `skills_synced_sha` (expected NULL).

- [ ] **Step 2: Trigger re-register/sync** using the documented mechanism (per `building-setup-workflow` memory: repo re-register on cold build; restart soapbox-api to clear the 30-min warm cache). Write the exact command sequence used into `10-resync-bundle.sh` (skill upload to Anthropic Skills API → update `installed_plugins.skills` + `skills_synced_sha` for the Demo portfolio row → restart soapbox-api).

- [ ] **Step 3: Verify** the three skills are present post-sync and `skills_synced_sha` is non-null:
```sql
select bool_or(s->>'name'='rsra') has_rsra, bool_or(s->>'name'='esg-profile') has_esg,
       bool_or(s->>'name'='decarb-plan') has_decarb
from installed_plugins ip, jsonb_array_elements(ip.skills) s
where ip.portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and ip.plugin_id='soapbox-agent';
```
Expected: all three `true`.

- [ ] **Step 4: Commit** `10-resync-bundle.sh`.

### Task 1.2: Per-asset minimal tool allowlist

**Files:** Create `demo-staging/11-tool-allowlist.sql`

Installed plugins are portfolio-scoped (shared by all three assets). To limit tools *per workflow* without disabling them portfolio-wide, scope the allowlist through each asset's `system_prompt` (a hard instruction naming the only MCP tools that workflow may call), NOT by toggling `installed_plugins.enabled` (which is portfolio-wide and would break the other assets).

- [ ] **Step 1:** Define the allowed-tool set per workflow in `11-tool-allowlist.sql` as a comment block:
  - RSRA (4400 Prairie Crossing): `soapbox-agent__fill_report`, `search_files`, `physrisk__*` (hero) — everything else served from cache.
  - ESG (Madison): `soapbox-agent__fill_report`, `crrem__get_pathway`, `physrisk__get_hazard_exposure` (hero) — rest static.
  - Decarb (4th & Madison): `soapbox-agent__fill_report`, `verifier__list_findings`, `verifier__verification_status`, `audette__*` (read only) — economics/costing served from cache.

- [ ] **Step 2:** Write the per-asset `system_prompt` update (upsert) that appends the allowlist directive. Example for one asset:
```sql
update assets set system_prompt = coalesce(system_prompt,'') ||
  E'\n\n[DEMO MODE] Only call these MCP tools: soapbox-agent__fill_report, search_files, physrisk__*. For all benchmark/BPS/incentive/Audette data, read the pre-staged values from asset memory/files; do NOT call other MCPs.'
where id = :rsra_asset_id;
```
(Repeat per asset with its allowlist; use the asset IDs resolved in Phase 3.)

- [ ] **Step 3: Verify** each asset's `system_prompt` contains its `[DEMO MODE]` directive:
```sql
select name, (system_prompt ilike '%[DEMO MODE]%') has_directive from assets
where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e';
```
Expected: `has_directive=true` for all three.

- [ ] **Step 4: Commit.**

---

## Phase 2 — Pseudonymous fixtures + scrub gate

### Task 2.1: RSRA pseudonymous OM + computed-data cache

**Files:** Create `skills/rsra/demo/` — `om_4400_prairie_crossing.pdf`, `rsra_data.json`, `physrisk_cache.json`, `bps_cache.json`, `README.md`

- [ ] **Step 1:** Read `~/inbox/Prose Frontier OM.pdf` (reference only) to learn realistic structure/figures. Author a **compact (~6-page) pseudonymous OM** for "4400 Prairie Crossing" (fictional sponsor "Stonebridge Capital", generic address in a real BPS jurisdiction so BPS lookups make sense). Save as `demo/om_4400_prairie_crossing.pdf`.

- [ ] **Step 2:** Author `demo/rsra_data.json` — the complete `fill_report(template:'rsra')` data object (all required fields from the pickup contract): sustainability CapEx line items, NOI impact, incentives (IRA/Green Rewards), regulatory flags, seller questions, recommendation. Numbers must obey the analytics standards.

- [ ] **Step 3:** Author `demo/physrisk_cache.json` and `demo/bps_cache.json` matching the shapes RSRA reads (from the pickup contract), so those lookups resolve instantly.

- [ ] **Step 4: Verify** `rsra_data.json` validates against the rsra template schema:
```bash
node ~/soapbox-agent/scripts/validate-*.mjs 2>/dev/null || node -e "JSON.parse(require('fs').readFileSync('skills/rsra/demo/rsra_data.json'))" && echo VALID
```
Expected: `VALID` (and schema-valid if a validator exists).

- [ ] **Step 5: Commit.**

### Task 2.2: ESG Madison fixtures (reuse esg-profile/demo pattern)

**Files:** Create `skills/esg-profile/demo/madison/` — `extract.xlsx`, `notes_scrubbed.docx`, `bps_cache.json`, `example-sponsor.json`

- [ ] **Step 1:** Using `~/inbox/*ESG_DD_Report*` + `20251119 Madison - Watermark at Talbot Park.xlsx` as reference, author a pseudonymous sponsor "Madison" set following the existing `esg-profile/demo/README.md` schema (sheet `30_input_qualitative`, peer benchmarks, governance, market regulation). Keep `crrem` + `physrisk` as LIVE bindings (the visible gap-fillers).

- [ ] **Step 2: Verify** with the existing ESG smoke:
```bash
cd ~/soapbox-agent && node scripts/smoke-esg-profile.mjs && node scripts/validate-esg-profile.mjs
```
Expected: both pass (inject + render both layouts).

- [ ] **Step 3: Commit.**

### Task 2.3: Decarb 4th & Madison fixtures

**Files:** Create `skills/decarb-plan/demo/` — `building_setup.json`, `baseline.json`, `measures.json`, `economics.json`, `costing_cache.json`, `citations.json`, `README.md`

- [ ] **Step 1:** Using `~/inbox/4th and Madison.zip` (reference only) author pseudonymous "4th & Madison" (fictional owner "JP Metro Asset Management"). Build `building_setup.json` conforming to the equipment-survey schema (all 10 groups + DHW sub-keys, null-not-zero, hydronic furnaces as native `central_plant_heater_type=hydronic_furnace`).

- [ ] **Step 2:** Author `baseline.json` (calibrated energy, kWh + kWh/m²), `measures.json` (ideated measure set — the hero content), `economics.json` (gross + landlord-share capture, solar VNM 0.80, IRR per standards), `costing_cache.json` (Costing MCP results), `citations.json`. All numbers reconciled so the headline % equals the measure-reconciled figure (gate requirement).

- [ ] **Step 3: Verify** internal reconciliation with a check script:
```bash
node -e "const e=require('./skills/decarb-plan/demo/economics.json'); if(Math.abs(e.headline_pct - e.measure_reconciled_pct)>0.5) throw 'HEADLINE MISMATCH'; console.log('RECONCILED')"
```
Expected: `RECONCILED`.

- [ ] **Step 4: Commit.**

### Task 2.4: Fail-closed scrub gate across all fixtures

**Files:** Create `demo-staging/scrub-check.mjs`; untracked `demo-staging/.scrub-denylist.json`

- [ ] **Step 1:** Populate `.scrub-denylist.json` with the real names to catch (Stoneweg, JPMAM, Prose Frontier, Watermark at Talbot Park, real addresses, real people from the DD reports). This file is untracked (in `.gitignore`).

- [ ] **Step 2:** Write `scrub-check.mjs` that scans all files under `skills/rsra/demo`, `skills/esg-profile/demo/madison`, `skills/decarb-plan/demo` (including text extracted from the PDF/xlsx/docx) for any denylist term (case-insensitive) and **exits non-zero** on any hit.

- [ ] **Step 3: Verify** it fails on a planted term then passes clean:
```bash
node demo-staging/scrub-check.mjs && echo "SCRUB CLEAN"
```
Expected: `SCRUB CLEAN` (exit 0). Manually plant "Stoneweg" in a temp copy first to confirm it exits non-zero, then remove.

- [ ] **Step 4: Commit** the script (NOT the denylist).

---

## Phase 3 — Asset seeding

### Task 3.1: Seed the Madison ESG asset

**Files:** Create `demo-staging/30-seed-assets.sql`

- [ ] **Step 1: Write verification (expect absent).**
```sql
select count(*) from assets where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and name='Madison';
```
Expected: 0.

- [ ] **Step 2: Upsert** the Madison asset (property_type residential/BTR, EU/EPC energy context per the ESG demo, address in a real market for regulation lookups). Idempotent on (portfolio_id, name).

- [ ] **Step 3: Verify** it exists and capture its `id` into `30-seed-assets.sql` as a comment. Commit.

### Task 3.2: Seed the 4th & Madison decarb asset with building-setup metadata

- [ ] **Step 1: Write verification (expect absent).** Same query for name `'4th & Madison'`.

- [ ] **Step 2: Upsert** the asset with `audette_pipeline_state='ready'` (or the value the pickup contract says a completed setup uses), and `metadata` carrying the building-setup keys observed on real assets: `setup_complete=true, equipment_survey, energy, archetype, num_buildings, ingestion_source='demo', regulatory_driver, audette_building_uids`. Populate from `decarb-plan/demo/building_setup.json`.

- [ ] **Step 3: Verify** `metadata->>'setup_complete' = 'true'` and capture the asset `id`. Commit.

### Task 3.3: Enrich the existing 4400 Prairie Crossing (RSRA) asset

- [ ] **Step 1:** Update the Demo-portfolio 4400 Prairie Crossing asset with realistic `street_address`, `city`, `state_province`, `gross_floor_area_m2`, `year_built`, `property_type` matching the pseudonymous OM.

- [ ] **Step 2: Verify** the fields are set; capture the asset `id`. Commit.

---

## Phase 4 — State staging per workflow (driven by pickup-contract.md)

### Task 4.1: RSRA — stage cached lookups + computed data

**Files:** Create `demo-staging/40-stage-rsra.sql` (+ file uploads)

- [ ] **Step 1:** Upload `demo/om_4400_prairie_crossing.pdf` into the RSRA asset's document library (`files` table / the app upload path) so `search_files("offering memorandum")` finds it.

- [ ] **Step 2:** Per the pickup contract, write the cached lookups + computed data object into the store RSRA reads (memory `key`s or files): `physrisk_cache.json`, `bps_cache.json`, and the `rsra_data.json` object. Idempotent upserts keyed by asset_id.

- [ ] **Step 3: Verify** via a dry rehearsal query that the memory/file rows exist for the RSRA asset. Commit.

### Task 4.2: ESG — stage static inputs + connector bindings

**Files:** Create `demo-staging/41-stage-esg.sql`

- [ ] **Step 1:** Stage the Madison static inputs (extract/notes/bps) where the esg-profile skill reads them (per its `demo/README.md` connector registry) and set the run-config connector bindings: `crrem`+`physrisk` = LIVE, the rest = static.

- [ ] **Step 2: Verify** the static inputs resolve and the two live bindings are configured. Commit.

### Task 4.3: Decarb — stage completed engagement to a gate-satisfied state

**Files:** Create `demo-staging/42-stage-decarb.sql` + `demo-staging/42-stage-verifier.md`

- [ ] **Step 1:** Write the decarb `state` object (baseline/measures/targets/economics/audette/citations/report-inputs from the demo fixtures) into the store + key the pickup contract identified (memory MCP or files), keyed to the 4th & Madison asset.

- [ ] **Step 2:** Ensure the `asset_connectors` verifier row exists for this asset/portfolio (per `verifier-connector-row-gap`):
```sql
insert into asset_connectors (id, asset_id, portfolio_id, plugin_id, name, scope, enabled, url)
select gen_random_uuid(), :decarb_asset_id, '3b683c32-ea8e-4851-b350-fd7b85a60e2e', 'plugin_verifier', 'Verifier', 'asset', true, 'https://verifier-mcp-production.up.railway.app/mcp'
where not exists (select 1 from asset_connectors where asset_id=:decarb_asset_id and plugin_id='plugin_verifier');
```

- [ ] **Step 3:** Via the **verifier MCP** (not SQL), record the genuine findings for the staged analysis and resolve them so `verifier__verification_status({asset_id})` returns PASS with no open-high findings. Document the exact calls in `42-stage-verifier.md`. **Do not** record a token finding just to clear the gate.

- [ ] **Step 4: Verify** the gate is genuinely satisfied:
call `verifier__verification_status({asset_id: <decarb>})` → expect a passing status with zero open-high findings.

- [ ] **Step 5: Commit.**

---

## Phase 5 — Rehearsal & fallback

### Task 5.1: Rehearse RSRA end-to-end on stage

- [ ] **Step 1:** In the Demo org on `stage.soapbox.build` (Playwright), open the 4400 Prairie Crossing asset, start a thread, drop `om_4400_prairie_crossing.pdf`, and run RSRA.
- [ ] **Step 2: Measure** wall-clock to the rendered artifact. Expected: render appears, turns ≤~60 s. Record timing in `demo-staging/rehearsal-log.md`.
- [ ] **Step 3:** Save the rendered artifact (`artifacts` row) as the **fallback**; note its id in the runbook.
- [ ] **Step 4: Commit** the rehearsal log.

### Task 5.2: Rehearse ESG (Madison)
- [ ] **Step 1:** Run the esg-profile Sponsor Profile flow; confirm `crrem`+`physrisk` fire live and the branded artifact renders (~60 s). Record timing + fallback artifact id. Commit.

### Task 5.3: Rehearse Decarb (4th & Madison)
- [ ] **Step 1:** Run the decarb+measure-ideation flow. Confirm: (a) gates pass hands-off, (b) Measure Ideation is **visibly surfaced** before render, (c) `fill_report(template:'decarb')` renders. Record timing + fallback artifact id.
- [ ] **Step 2:** If any gate blocks, do NOT bypass — return to Task 4.3 and stage the missing genuine analysis. Commit when green.

### Task 5.4: Cleanup rehearsal residue
- [ ] **Step 1:** Bulk-delete rehearsal threads/conversations/messages created by the service account (standing practice), keeping only the fallback artifacts referenced by the runbooks.
```sql
-- review first, then delete rehearsal conversations older than the final staged set
select id, title, created_at from conversations where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' order by created_at desc;
```
- [ ] **Step 2: Commit** any cleanup script.

---

## Phase 6 — Runbooks

### Task 6.1: Per-workflow demo runbooks

**Files:** Create `demo-staging/runbook-rsra.md`, `runbook-esg.md`, `runbook-decarb.md`

- [ ] **Step 1:** For each workflow write a runbook (ESG `README.md` shape): exact prompt to type, the OM/file to drop, the expected on-screen beats and their order, the ~timing per beat, the 2–3 live hero calls, and the **fallback** (artifact id to show if a live render stalls).
- [ ] **Step 2:** Add a top-level `demo-staging/README.md` indexing the three runbooks + the pre-demo re-stage checklist (run seed scripts, run scrub gate, confirm bundle sha, one smoke of each).
- [ ] **Step 3: Commit.**

---

## Self-Review

- **Spec coverage:** §1 env → Task 0.1; §3.1 RSRA → 2.1/3.3/4.1/5.1; §3.2 ESG → 2.2/3.1/4.2/5.2; §3.3 decarb → 2.3/3.2/4.3/5.3; §4 mechanisms (bundle re-sync → 1.1, allowlist → 1.2, helper cache → 4.x, scrub → 2.4, runbooks → 6.1); §5 honesty → Global Constraints + 4.3; §6 rails → 5.x + 6.1. Covered.
- **Placeholder scan:** the `:asset_id` tokens are bind-parameters resolved in Phase 3 (IDs captured as comments), not TODO placeholders. Phase 0.3 is a genuine spike with concrete investigation steps + a decision artifact, not a deferred blank.
- **Type consistency:** asset IDs flow Phase 3 → Phase 4 via captured comments; verifier connector `plugin_id='plugin_verifier'` used consistently; `fill_report` template names (`rsra`/`esg-profile`/`decarb`) consistent.
- **Adaptation note:** this is data-staging/infra, so "TDD" is applied as verification-first (a query/rehearsal that must return the expected result after each task) rather than unit tests.
