# Rigorous Measure Ideation via retrofit-advisor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make measure ideation a rigorous, register-backed capability that runs standalone AND inside decarb-plan P3, by rewriting the `retrofit-advisor` skill and bundling it with the Retrofit MCP in the core `retrofit` plugin.

**Architecture:** The core `retrofit` plugin gains `skills_repo` → it ships the Retrofit MCP (tools stay `retrofit__*`) **plus** the rigorous retrofit-advisor skill. Both a standalone run and decarb-plan P3 (which delegates by name) run the identical method and persist to the shared Retrofit MCP measure register (the handoff).

**Tech Stack:** Markdown skills (Anthropic Skills API via managed-agent runtime), soapbox-agent repo, soapboxbuild/retrofit-advisor-skill repo, soapbox-platform (Hono API, `portfolio.ts` seed), platform-web (`plugin-registry.ts`), Supabase.

## Global Constraints

- **Keep `plugin_id: 'retrofit'` and connector `name: 'plugin_retrofit'`** — the `retrofit__*` tool prefix derives from connector identity; decarb-plan, portfolio-analysis, and `measure-universe.md` all call `retrofit__*`. Renaming breaks every caller. Display name changes live in platform-web `plugin-registry.ts` only.
- **Equal rigor = identical method + provenance discipline.** Never fabricate; every measure cites a source line or is labeled `extrapolated — feasibility study required`; sparse data → per-measure grounding-confidence label (`audit-backed` / `modeled` / `extrapolated`), method unchanged.
- **Standalone output = register + concise in-chat markdown table only.** No branded artifact.
- **decarb-plan P3 delegates to retrofit-advisor by NAME** (cross-plugin skill invocation via the Anthropic Skills API), never `cat skills/…` across plugins.
- **Register is the handoff:** `retrofit__update_measure_state` (write), `retrofit__get_measure_state` (read); measures tracked in decarb `state.measures.register_ids`.
- Analytics: kWh + kWh/m², ≤2 sig figs, BPD peer benchmarks (not national median).
- **Demo-org scope for the live re-sync/verify:** portfolio `3b683c32-ea8e-4851-b350-fd7b85a60e2e`.

## File / resource map
- `~/retrofit-advisor-skill/skills/retrofit-advisor/SKILL.md` — rewritten to the rigorous method.
- `~/retrofit-advisor-skill/references/measure-universe.md` — canonical copy (moved from decarb-plan).
- `~/retrofit-advisor-skill/commands/{recommend,electrification,capex-plan}.md` — re-pointed at the rigorous method.
- `~/retrofit-advisor-skill/.claude-plugin/plugin.json`, `README.md` — updated description.
- `~/soapbox-agent/skills/decarb-plan/SKILL.md` (P3, lines ~672–756) — delegate ideation to retrofit-advisor.
- `~/soapbox-agent/skills/decarb-plan/references/measure-universe.md` — removed (moved).
- `~/soapbox-platform/apps/api/src/services/portfolio.ts` (line 79) — add `skills_repo` to the `retrofit` seed entry.
- `~/platform-web/src/lib/plugin-registry.ts` (`id: 'retrofit'`) — display name "Retrofit Advisor" + `skills_repo`.
- Supabase `installed_plugins` — Demo `retrofit` row gets `skills_repo`; generic `retrofit-advisor` row `31e542c1` deleted.

---

## Phase 1 — Rewrite the retrofit-advisor skill (repo `soapboxbuild/retrofit-advisor-skill`)

### Task 1: Move measure-universe.md into the retrofit-advisor repo

**Files:** Create `~/retrofit-advisor-skill/references/measure-universe.md`; later remove `~/soapbox-agent/skills/decarb-plan/references/measure-universe.md` (Task 6).

- [ ] **Step 1:** Copy the canonical file:
```bash
mkdir -p ~/retrofit-advisor-skill/references
cp ~/soapbox-agent/skills/decarb-plan/references/measure-universe.md ~/retrofit-advisor-skill/references/measure-universe.md
```
- [ ] **Step 2: Verify** it's non-empty and carries the full universe categories:
```bash
grep -ciE "envelope|hvac|controls|dhw|lighting|solar|ev|procurement" ~/retrofit-advisor-skill/references/measure-universe.md
```
Expected: ≥6.
- [ ] **Step 3: Commit** (in the retrofit-advisor-skill repo):
```bash
cd ~/retrofit-advisor-skill && git add references/measure-universe.md && git commit -m "feat: bring measure-universe.md into retrofit-advisor (canonical home for ideation)"
```

### Task 2: Rewrite SKILL.md to the rigorous, register-backed method

**Files:** Modify `~/retrofit-advisor-skill/skills/retrofit-advisor/SKILL.md` (currently 116 lines, generic heuristics).

**Interfaces produced:** a skill named `retrofit-advisor` that, given an asset context, reads/writes the Retrofit MCP register and prints an in-chat measures table. Consumed by decarb-plan P3 (Task 6) by name.

- [ ] **Step 1:** Read the rigor source to port: `~/soapbox-agent/skills/decarb-plan/SKILL.md` lines 672–756 (P3), plus the tool list (`retrofit__propose_candidates`, `retrofit__screen_measures`, `retrofit__evaluate_measure`, `retrofit__get_measure_state`, `retrofit__update_measure_state`, `retrofit__get_retrofit_playbook`, `retrofit__search_reference_library`).
- [ ] **Step 2:** Replace SKILL.md body with the rigorous method. The frontmatter `name: retrofit-advisor`; description covering standalone + decarb use. Required sections, in order:
  1. **Trigger** — "ideate measures", "measure ideation", "retrofit recommendations", "what should we do to this building", and *invoked by decarb-plan P3*.
  2. **Step 0 — Read the register first:** `retrofit__get_measure_state({asset_id})`; if measures exist, refine/extend rather than regenerate.
  3. **Step 1 — Gather grounding (best-effort):** Audette model/baseline if present; audit/PCA docs (from decarb `state.documents` when invoked there, else `search_files` on the asset); OM/web as labeled fallback. Record what grounding was found.
  4. **Step 2 — Propose:** `retrofit__propose_candidates` with the best available asset attributes.
  5. **Step 3 — Completeness cross-walk:** read `references/measure-universe.md`; confirm EVERY category considered (envelope, HVAC plant + distribution, controls/retro-cx, DHW, lighting + controls, plug/appliance, common-area/amenity, on-site generation/storage, EV, procurement); mark each evaluated / screened-out-with-reason / N/A. Screening DOWN from the universe, not UP from the optimizer.
  6. **Step 4 — Source-audit cross-walk:** every audit/PCA-recommended measure appears or is explicitly screened out; every roster measure cites its source line; a measure in no source is labeled `extrapolated — feasibility study required`; sizing traces to documents. NEVER fabricate.
  7. **Step 5 — Screen + evaluate:** `retrofit__screen_measures`, then `retrofit__evaluate_measure` for economics/carbon.
  8. **Step 6 — Persist:** `retrofit__update_measure_state` (the register is the system of record — never persist by editing state alone).
  9. **Step 7 — Confidence label** per measure: `audit-backed` / `modeled` / `extrapolated`.
  10. **Step 8 — Output:** a concise in-chat markdown table: `Measure | Tier | CapEx | Annual saving | $/tCO₂e | Payback | Confidence | Source`. Analytics standards enforced. **No artifact/fill_report.**
  11. **Guardrail:** when invoked by decarb-plan, do NOT build the Gate-2 roster/roadmap or economics rollup — that stays in decarb-plan; this skill's job ends at a populated register + table.
- [ ] **Step 3: Verify** structure:
```bash
grep -cE "retrofit__(get_measure_state|propose_candidates|screen_measures|evaluate_measure|update_measure_state)" ~/retrofit-advisor-skill/skills/retrofit-advisor/SKILL.md
grep -ciE "measure-universe|extrapolated — feasibility|confidence|register" ~/retrofit-advisor-skill/skills/retrofit-advisor/SKILL.md
```
Expected: first ≥5 (all core tools referenced), second ≥4.
- [ ] **Step 4: Commit:**
```bash
cd ~/retrofit-advisor-skill && git add skills/retrofit-advisor/SKILL.md && git commit -m "feat: rewrite retrofit-advisor as rigorous register-backed measure ideation"
```

### Task 3: Re-point commands + update plugin metadata

**Files:** Modify `~/retrofit-advisor-skill/commands/{recommend,electrification,capex-plan}.md`, `~/retrofit-advisor-skill/.claude-plugin/plugin.json`, `~/retrofit-advisor-skill/README.md`.

- [ ] **Step 1:** Update each command to invoke the rigorous skill (they should trigger the SKILL.md method, not the old generic heuristics). `recommend` = full ideation; `electrification` = ideation scoped to electrification measures; `capex-plan` = ideation → phased register view. Each must state it uses `retrofit__*` and writes the register.
- [ ] **Step 2:** Update `plugin.json` description + `README.md` to "rigorous, register-backed measure ideation (uses the Retrofit MCP)". Note it requires the Retrofit MCP connector.
- [ ] **Step 3: Verify** no stale generic-only framing remains:
```bash
grep -riL "retrofit__\|register" ~/retrofit-advisor-skill/commands/ || echo "all commands reference the engine"
```
- [ ] **Step 4: Commit + push** (this is what the plugin syncs from):
```bash
cd ~/retrofit-advisor-skill && git add -A && git commit -m "feat: re-point commands + metadata at rigorous ideation" && git push origin main
```

---

## Phase 2 — Platform config

### Task 4: Add skills_repo to the core `retrofit` seed (soapbox-platform)

**Files:** Modify `~/soapbox-platform/apps/api/src/services/portfolio.ts:79`.

- [ ] **Step 1:** Edit the `retrofit` corePlugins entry to add `skills_repo` (mirroring `crrem-skills`). New line:
```ts
    { plugin_id: 'retrofit',      name: 'plugin_retrofit',      description: 'Retrofit Advisor: rigorous register-backed measure ideation — playbooks, provenance-enforced evaluation, measure register, reference library.', mcp_url: 'https://retrofit-mcp-production.up.railway.app/mcp', skills_repo: 'soapboxbuild/retrofit-advisor-skill' },
```
(Keep `plugin_id`/`name` unchanged — tool prefix stays `retrofit__`.)
- [ ] **Step 2: Verify** it typechecks:
```bash
cd ~/soapbox-platform/apps/api && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -i "portfolio.ts" || echo "no portfolio.ts type errors"
```
- [ ] **Step 3: Commit + push** (Railway deploy):
```bash
cd ~/soapbox-platform && git add apps/api/src/services/portfolio.ts && git commit -m "feat(seed): retrofit core plugin ships the retrofit-advisor skill (skills_repo)" && git push origin main
```

### Task 5: Rename display + add skills_repo in platform-web registry

**Files:** Modify `~/platform-web/src/lib/plugin-registry.ts` (`id: 'retrofit'`, ~line 85).

- [ ] **Step 1:** Update the `retrofit` entry: `name: 'Retrofit Advisor'`, description to match (rigorous measure ideation), add `skills_repo: 'soapboxbuild/retrofit-advisor-skill'`, and `iconUrl: '/icons/soapbox-app-icon.svg'` (it's a Soapbox plugin). Keep `id: 'retrofit'`.
- [ ] **Step 2: Verify:**
```bash
cd ~/platform-web && grep -A6 "id: 'retrofit'" src/lib/plugin-registry.ts | grep -E "Retrofit Advisor|skills_repo|soapbox-app-icon"
```
Expected: all three present.
- [ ] **Step 3: Commit + push** (Vercel deploy):
```bash
cd ~/platform-web && git add src/lib/plugin-registry.ts && git commit -m "feat(marketplace): retrofit → 'Retrofit Advisor' display + skill + icon" && git push origin main
```

---

## Phase 3 — decarb-plan P3 delegates by name

### Task 6: Refactor decarb-plan P3 + drop the moved reference

**Files:** Modify `~/soapbox-agent/skills/decarb-plan/SKILL.md` (P3, ~672–756); delete `~/soapbox-agent/skills/decarb-plan/references/measure-universe.md`.

**Interfaces consumed:** the `retrofit-advisor` skill (Task 2), invoked by name; the register via `retrofit__get_measure_state`.

- [ ] **Step 1:** In P3, replace the inlined ideation core (the `propose_candidates` → measure-universe cross-walk → source-audit cross-walk → screen → evaluate sub-steps) with a delegation block:
> "**Ideation is delegated.** Invoke the **retrofit-advisor** skill for this asset — it reads the Gate-1-adjudicated `state.baseline` and audit docs in `state.documents`, runs the full measure-universe + source-audit cross-walk with provenance + confidence, and persists to the Retrofit register. Do not re-derive measures here. When it returns, load the register with `retrofit__get_measure_state({asset_id})` and continue."
- [ ] **Step 2:** KEEP everything downstream: Gate-2 roster assembly, roadmap phasing, economics linkage, `state.measures.register_ids` / `roadmap_phases` mapping, render/verifier gate. Keep a one-line assertion: "P3 must have run the retrofit-advisor ideation (register non-empty) before building the roster."
- [ ] **Step 3:** Remove the now-moved reference and any `cat .../measure-universe.md` line in decarb-plan (the cross-walk lives in retrofit-advisor now):
```bash
git rm ~/soapbox-agent/skills/decarb-plan/references/measure-universe.md
grep -n "measure-universe" ~/soapbox-agent/skills/decarb-plan/SKILL.md   # expect: none, or replaced with the delegation note
```
- [ ] **Step 4: Verify** P3 now delegates and keeps the roster:
```bash
grep -niE "retrofit-advisor|delegat|get_measure_state" ~/soapbox-agent/skills/decarb-plan/SKILL.md | head
grep -ciE "roster|roadmap|register_ids" ~/soapbox-agent/skills/decarb-plan/SKILL.md   # expect >0 (kept)
```
- [ ] **Step 5: Commit + push:**
```bash
cd ~/soapbox-agent && git add -A && git commit -m "refactor(decarb-plan): P3 delegates measure ideation to retrofit-advisor by name" && git push origin main
```

---

## Phase 4 — Provision on Demo + cleanup

### Task 7: Attach the rigorous skill to the Demo `retrofit` plugin

The core-seed change (Task 4) only affects NEW portfolios. Demo's existing `retrofit` row is MCP-only (`skills_repo` null, `anthropic_skill_id` null). Setting `skills_repo` triggers the runtime's lazy skill-registration on the next session (`agent-config.ts`: rows with `skills_repo` and null `anthropic_skill_id` are registered to Anthropic and the id is written back).

**Files:** none (Supabase MCP op) — record in `demo-staging/` notes.

- [ ] **Step 1: Verify current state:**
```sql
select plugin_id, skills_repo, anthropic_skill_id, jsonb_array_length(coalesce(skills,'[]'::jsonb)) n
from installed_plugins where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and plugin_id='retrofit';
```
Expected: `skills_repo` null.
- [ ] **Step 2:** Set `skills_repo` on the Demo `retrofit` row (forces lazy re-register):
```sql
update installed_plugins set skills_repo='soapboxbuild/retrofit-advisor-skill', anthropic_skill_id=null
where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and plugin_id='retrofit';
```
- [ ] **Step 3:** Trigger registration by starting a fresh thread on any Demo asset as the service account (per `demo-staging/run-one.sh`), then verify the id was written back:
```sql
select plugin_id, (anthropic_skill_id is not null) has_skill_id, jsonb_array_length(coalesce(skills,'[]'::jsonb)) n
from installed_plugins where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and plugin_id='retrofit';
```
Expected: `has_skill_id=true`, `n≥1`. (If it stays null, restart soapbox-api to clear the warm agent-config cache, per the building-setup re-sync gotcha.)

### Task 8: Uninstall the generic retrofit-advisor plugin from Demo

**Files:** none (API call).

- [ ] **Step 1:** Delete via the installed-plugins DELETE endpoint (also unregisters its Anthropic skill), as the service-account owner:
```bash
# auth as service account (demo-staging/.demo.env), then:
curl -s -X DELETE "https://soapbox-api-production.up.railway.app/api/portfolios/3b683c32-ea8e-4851-b350-fd7b85a60e2e/installed-plugins/31e542c1-6717-4434-9f52-fc195bc9c2ca" \
  -H "Authorization: Bearer $TOKEN" -H "x-organization-id: 8ebc72a7-dca1-4cb1-be02-eed12f38340f" -w "\nHTTP %{http_code}\n"
```
Expected: HTTP 200/204.
- [ ] **Step 2: Verify** it's gone and only the merged `retrofit` remains:
```sql
select plugin_id, name from installed_plugins
where portfolio_id='3b683c32-ea8e-4851-b350-fd7b85a60e2e' and plugin_id in ('retrofit','retrofit-advisor');
```
Expected: only `retrofit`.

---

## Phase 5 — Verify

### Task 9: Standalone ideation run

- [ ] **Step 1:** New thread on the Demo decarb asset (`4th & Madison`, `f6e043dd`), service account: *"Ideate decarbonization measures for this building."*
- [ ] **Step 2: Verify** the register populated + in-chat table:
```sql
-- measures should be readable via the register; check the thread produced a table (assistant message), no artifact
select (select count(*) from messages where conversation_id=:conv and role='assistant') asst,
       (select count(*) from artifacts where conversation_id=:conv) arts;
```
Expected: `asst≥1`, `arts=0` (in-chat table, no artifact). Confirm the assistant message contains a measures table with a Confidence + Source column.

### Task 10: decarb-plan P3 delegation + handoff

- [ ] **Step 1:** In a decarb-plan run that reaches P3 (or a fresh decarb run on a set-up asset), confirm the agent invokes the retrofit-advisor skill (SSE/log shows the skill load + `retrofit__propose_candidates`/`update_measure_state`), then builds the Gate-2 roster from the register.
- [ ] **Step 2 — Handoff:** on an asset where a standalone run (Task 9) already populated the register, start decarb-plan → confirm P3 loads existing measures (`retrofit__get_measure_state`) and does NOT re-ideate from scratch.
- [ ] **Step 3:** Confirm `retrofit__*` tools still resolve in both decarb-plan and portfolio-analysis (prefix intact).

---

## Self-Review

- **Spec coverage:** §3 architecture → Tasks 4,5,7; rigorous skill (§4.1) → Tasks 1,2,3; decarb P3 (§4.2) → Task 6; core seed (§4.3) → Task 4; measure-universe move → Tasks 1,6; rollout (§5) → Tasks 4–8; verification (§6) → Tasks 9,10; generic-plugin uninstall → Task 8. Covered. portfolio-analysis explicitly out of scope (§7).
- **Placeholder scan:** `:conv` and `:asset_id` are bind-parameters resolved at run time, not TODOs. The SKILL.md rewrite (Task 2) specifies exact required sections + tool sequence rather than inlining 100+ lines of prose — appropriate for a prose-skill deliverable; the source to port (decarb-plan P3) is named with line numbers.
- **Type/name consistency:** `plugin_id: 'retrofit'` + connector `name: 'plugin_retrofit'` preserved everywhere (prefix `retrofit__*`); display "Retrofit Advisor" only in platform-web; `skills_repo: 'soapboxbuild/retrofit-advisor-skill'` consistent across seed, registry, and the Demo row.
- **Adaptation note:** data-staging/prose tasks use verification-first (grep/SQL/live-run checks) in place of unit tests.
