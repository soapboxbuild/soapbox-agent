# Rigorous Measure Ideation via retrofit-advisor — Design

**Date:** 2026-07-11
**Goal:** Make measure ideation a first-class, rigorous capability that runs **standalone** *and* **inside decarb-plan (P3)**, with **equal rigor** in both paths. The Retrofit MCP **measure register** is the handoff between them.

---

## 1. Problem

- decarb-plan P3 has the rigor (propose_candidates → measure-universe cross-walk → audit/PCA source cross-walk → screen → evaluate → persist to the Retrofit MCP register with provenance), but it's **inlined** in decarb-plan and not runnable on its own.
- The installed `retrofit-advisor` plugin (repo `soapboxbuild/retrofit-advisor-skill`) is **generic/portable**: pure LLM heuristics, **no Retrofit MCP, no register, no audit grounding** — the wrong vehicle for rigor, and it doesn't feed decarb-plan.

## 2. Decisions (locked with Christopher)

- **Equal rigor = identical method + provenance discipline**, not a required Gate-1 baseline. Sparse data is handled **best-effort with a per-measure grounding-confidence label** (`audit-backed` / `modeled` / `extrapolated — feasibility study required`), never by lowering the method or fabricating.
- **Standalone output:** writes the register **+ a concise in-chat table** (ranked, confidence + source + $/tCO₂e). **No branded artifact.**
- **Keep the name "retrofit-advisor"**; replace the generic skill with the rigorous one.
- **Bundle the MCP with the skill** (cohesive plugin), following the **`crrem-skills` precedent** (one plugin registering both `mcp_url` and `skills_repo`).

## 3. Architecture

**One cohesive core plugin = Retrofit MCP + rigorous ideation skill.**

- Reuse the **existing core `retrofit` plugin** (today MCP-only, `plugin_id: 'retrofit'`, display "Retrofit Specialist"). **Add `skills_repo: 'soapboxbuild/retrofit-advisor-skill'`** and change **display name → "Retrofit Advisor"**.
  - **`plugin_id` stays `retrofit`** so the MCP tool prefix stays **`retrofit__*`** — decarb-plan, portfolio-analysis, and `references/measure-universe.md` all call `retrofit__propose_candidates` etc. Renaming the id would rename the tools and break every caller. (Confirmed: tool prefix derives from connector identity.)
- **Cross-plugin invocation is reliable:** the managed runtime attaches every enabled plugin's skill to the one agent as peer Anthropic skills (`agent-config.ts`: `enabledPlugins.map(anthropic_skill_id) → skills:[{type:'custom',skill_id}]`). So decarb-plan (in soapbox-agent) invokes the retrofit-advisor skill (in the `retrofit` plugin) **by name** — no `cat` file path across plugins.
- **The generic `soapboxbuild/retrofit-advisor-skill` repo is rewritten** into the rigorous skill (same repo, so the `retrofit` plugin's `skills_repo` points at it). The **separate installed `retrofit-advisor` plugin** (row `31e542c1`, created earlier on Demo) is **uninstalled** — the rigorous skill now arrives via the `retrofit` core plugin.

### Data flow
```
standalone run  ─┐
                 ├─► retrofit-advisor skill (rigorous) ──► retrofit__* (register) ──┐
decarb-plan P3 ──┘                                                                  │
                                                                register (system of record)
decarb-plan P3 reads register (retrofit__get_measure_state) ◄───────────────────────┘
      → builds Gate-2 roster / roadmap / economics
```

## 4. Components

### 4.1 Rigorous retrofit-advisor skill (`soapboxbuild/retrofit-advisor-skill`, rewritten)
`SKILL.md` (name: `retrofit-advisor`) — the ideation core, identical for both callers:
1. **Read register first** (`retrofit__get_measure_state`) — refine, don't duplicate.
2. **Gather grounding (best-effort):** Audette model/baseline if calibrated; audit/PCA docs (`state.documents` when called from decarb, else asset Files via `search_files`); OM/web fallback.
3. **Method:** `retrofit__propose_candidates` → cross-walk vs `references/measure-universe.md` (full universe; nothing silently dropped) → source-audit cross-walk vs available docs → `retrofit__screen_measures` → `retrofit__evaluate_measure` → **persist** via `retrofit__update_measure_state`.
4. **Provenance + confidence per measure:** each cites its source line OR is labeled `extrapolated — feasibility study required`; each carries a grounding-confidence label. Never fabricate.
5. **Output:** register populated (`register_ids`) + **concise in-chat markdown table** (measure, tier, $/tCO₂e, payback, confidence, source). Numbers obey analytics standards (kWh + kWh/m², ≤2 sig figs, peer benchmarks).
6. **Triggers:** standalone ("ideate measures", "measure ideation", retrofit recommendations) + invoked by decarb-plan. Slash commands retained (`/recommend`, `/electrification`, `/capex-plan`) but re-pointed at the rigorous method.
- **`measure-universe.md` ownership:** it currently lives at `decarb-plan/references/measure-universe.md`. Since ideation now belongs to retrofit-advisor, the **canonical copy moves into the retrofit-advisor-skill repo** (`references/measure-universe.md`) and the rigorous skill reads it there. decarb-plan no longer references it directly (it delegates ideation), so no cross-plugin file read is needed. If any decarb-plan prose still cites it, replace with "the retrofit-advisor skill performs the measure-universe cross-walk."

### 4.2 decarb-plan P3 refactor (`soapbox-agent/skills/decarb-plan/SKILL.md`, lines ~672–756)
- Replace the inlined ideation core with: *"Invoke the **retrofit-advisor** skill to ideate + evaluate measures for this asset (it reads the Gate-1 baseline in `state.baseline` and audit docs in `state.documents`, and persists to the register). Then continue below with the register."*
- **Keep** the decarb-specific parts: Gate-2 roster assembly, roadmap phasing, economics linkage, `state.measures.register_ids` / `roadmap_phases` mapping, the render/verifier gate.
- The audit source-audit cross-walk + anti-fabrication guardrails move **into** the retrofit-advisor skill (so both paths enforce them); decarb-plan keeps a one-line assertion that P3 must have run it.

### 4.3 Core seed (`soapbox-platform/apps/api/src/services/portfolio.ts`)
- The `corePlugins` `retrofit` entry: add `skills_repo: 'soapboxbuild/retrofit-advisor-skill'`, `name: 'Retrofit Advisor'` (display), `prompt_addition` if needed. Keep `plugin_id: 'retrofit'`, `mcp_url: 'https://retrofit-mcp-production.up.railway.app/mcp'`.
- New portfolios auto-provision the merged plugin. Existing portfolios need a **re-sync** to pick up the added skill (registers `anthropic_skill_id` on the `retrofit` row).

### 4.4 portfolio-analysis (out of scope, note only)
portfolio-analysis also calls `retrofit__evaluate_measure` directly. It keeps working unchanged (same MCP, same prefix). Optionally delegating its ideation to the retrofit-advisor skill is a **follow-up**, not this change.

## 5. Rollout

1. Rewrite `soapboxbuild/retrofit-advisor-skill` → rigorous skill (+ shared measure-universe).
2. Update `portfolio.ts` core seed (`retrofit` gets `skills_repo` + display name).
3. Refactor decarb-plan P3 to delegate by name.
4. Re-sync the `retrofit` plugin to existing portfolios (register `anthropic_skill_id`); **Demo first**.
5. **Uninstall** the separate generic `retrofit-advisor` plugin from Demo (row `31e542c1`).
6. Verify (below).

## 6. Verification

- **Standalone:** new thread on an asset → "ideate measures" → retrofit-advisor runs → register populated (`retrofit__get_measure_state` shows measures) + in-chat table with confidence + provenance.
- **decarb-plan P3:** a decarb run reaches P3 → invokes retrofit-advisor → same register entries → Gate-2 roster built from them.
- **Handoff:** run standalone first, then decarb-plan on the same asset → P3 picks up the standalone measures (no re-ideation from scratch).
- **Prefix intact:** `retrofit__*` tool calls still resolve (decarb-plan + portfolio-analysis unaffected).
- **Cross-plugin invocation:** confirm decarb-plan actually loads the retrofit-advisor skill in a managed session.

## 7. Out of scope
- portfolio-analysis ideation refactor (follow-up).
- A public/generic retrofit-advisor variant (the repo becomes Soapbox-rigorous; a portable fork is a separate concern).
- Branded standalone artifact (explicitly deferred — in-chat table only).
