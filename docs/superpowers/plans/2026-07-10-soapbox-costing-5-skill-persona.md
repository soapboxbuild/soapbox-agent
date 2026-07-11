# Soapbox Costing — Plan 5: Costing skill + Costing Specialist persona

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Author the agent-facing layer of the plugin — a `costing` skill that orchestrates the 9 MCP tools into a validated `measure.cost` object per measure, and a provenance-gated **Costing Specialist** persona — so portfolio agents can produce defensible, cited cost estimates.

**Architecture:** Content lives in the `~/soapbox-costing` repo: `skills/costing/SKILL.md` (+ `references/`), `agents/subagents/costing-specialist.md`. No MCP/server code changes; no Railway redeploy (skills ship with the repo/plugin). Verified with `scripts/lint-skill-*.mjs` content-assertion linters mirroring the soapbox-agent convention.

**Tech Stack:** Markdown skill/persona + Node lint scripts (`node scripts/lint-*.mjs`).

## Global Constraints

- The skill's job ends at producing a **`measure.cost` object per the CANONICAL contract in soapbox-agent** (`skills/construction-costing/schema/measure-cost.schema.json`). It does NOT compute NPV/IRR/payback — that stays in `decarb-plan`. Do not duplicate or vendor the schema; describe the shape and point to the canonical file.
- Canonical `measure.cost` shape (produce exactly these keys): `measure_id`, `measure_kind` (`fuel_switch|efficiency|envelope|controls|other`), `cost: { capex{low,base,high}, opex_delta_yr (POSITIVE = OpEx rises), electrical_capacity{demand_increase_kw, service_capacity_known, upgrade_cost{low,high}, flag}, efficiency_alternative{measure, capex, opex_delta_yr} }` plus the additive extension `contingency_pct`, `cost_breakdown{material,labour,equipment}`, `escalation{base_year,index,index_vintage,escalated_to}`.
- **Tool → contract mapping (authoritative):**
  - `get_measure_capex` → `cost.capex`, `cost_breakdown`, `contingency_pct`, `escalation`, and the surfaced `references[]`.
  - `estimate_service_upgrade` → `cost.electrical_capacity` (REQUIRED on any fuel_switch/electrification; UNVERIFIED range, never collapsed).
  - `get_energy_prices` + `get_tariff` → derive `cost.opex_delta_yr` (positive = OpEx rises; use tariff demand charges where present).
  - `get_der_economics` → capex/opex for solar/storage/GHP measures.
  - every fuel_switch also gets a non-switching `efficiency_alternative` (a second `get_measure_capex` call).
- **Ground rules (persona + skill):** never invent numbers (every figure from a tool result or flagged tuned-base); always **surface references** (`get_references` / the `references[]` on capex) — an uncited number is low-confidence; never collapse an UNVERIFIED electrical-capacity range; flag coverage gaps (commercial-electrical, lab/fume-hood) rather than presenting a false point; feed new surveys back via `add_reference`.
- Skill/persona names + descriptions follow the plugin conventions (mirror `crrem-skills`).

---

### Task 1: The `costing` skill

**Files:** Create `skills/costing/SKILL.md`, `skills/costing/references/tool-orchestration.md`; Create `scripts/lint-skill-costing.mjs`.

- [ ] **Step 1: Write the lint (failing target)** — `scripts/lint-skill-costing.mjs` reads `skills/costing/SKILL.md` and asserts the presence of the load-bearing content (throw listing any missing):
```
'measure.cost', 'canonical contract in soapbox-agent', 'get_measure_capex', 'estimate_service_upgrade',
'get_energy_prices', 'get_tariff', 'get_der_economics', 'efficiency_alternative', 'electrical_capacity',
'opex_delta_yr', 'UNVERIFIED', 'never collapse', 'references', 'no invented', 'does not compute IRR'
```
Print `costing skill lint OK` on success.
- [ ] **Step 2: Run → FAIL** (`node scripts/lint-skill-costing.mjs` — file missing).
- [ ] **Step 3: Write `skills/costing/SKILL.md`** — frontmatter (name `costing`, description triggering on "cost this measure/roster", "what's the CapEx", "estimate construction cost", version 0.1.0). Body: the method — (1) read the measure roster + building/Audette context; (2) per measure, call the mapped MCP tools (per Global Constraints); (3) assemble the `measure.cost` object; (4) validate against the canonical soapbox-agent schema; (5) hand off to decarb-plan for economics. Include the tool→contract mapping table, the ground rules, and the "does not compute IRR/NPV — that's decarb-plan" positioning. Put the detailed per-tool call recipes in `references/tool-orchestration.md`.
- [ ] **Step 4: Run → `costing skill lint OK`.**
- [ ] **Step 5: Commit** `skills/costing/SKILL.md skills/costing/references/tool-orchestration.md scripts/lint-skill-costing.mjs`, msg `feat: costing skill orchestrating the MCP tools into measure.cost`.

---

### Task 2: The Costing Specialist persona

**Files:** Create `agents/subagents/costing-specialist.md`; Create `scripts/lint-persona-costing.mjs`; Modify `.claude-plugin/plugin.json` if agents must be declared (check `crrem-skills` — its plugin.json declares only `skills`; agents/ is auto-discovered — so only add an `agents` key if the convention requires it; otherwise leave plugin.json unchanged and note why).

- [ ] **Step 1: Write the lint** — `scripts/lint-persona-costing.mjs` asserts `agents/subagents/costing-specialist.md` contains: `Costing Specialist`, `never invent`, `provenance`, `references`, `UNVERIFIED`, `efficiency alternative`, `coverage gap`, `costing MCP`, `add_reference`. Print `costing persona lint OK`.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Write `agents/subagents/costing-specialist.md`** — mirror `crrem-skills/agents/subagents/stranding-analyst.md` structure (frontmatter name/description; Capabilities; Data Sources = the costing MCP + the `soapbox-costing` hindsight reference bank; Approach = the ground rules verbatim). Provenance-gated: cites references on every estimate, never invents, never collapses UNVERIFIED, always pairs fuel-switch with an efficiency alternative, flags gaps, feeds `add_reference`.
- [ ] **Step 4: Run → `costing persona lint OK`.** Confirm the `crrem-skills` agents-declaration convention and either update `plugin.json` to match or document that agents/ is auto-discovered.
- [ ] **Step 5: Commit** `agents/subagents/costing-specialist.md scripts/lint-persona-costing.mjs` (+ plugin.json if changed), msg `feat: Costing Specialist persona (provenance-gated)`.

---

### Task 3: Wire lints into the repo + push

**Files:** Modify `package.json` (add a `lint` script running both lint-skill-costing + lint-persona-costing).

- [ ] **Step 1:** Add `"lint": "node scripts/lint-skill-costing.mjs && node scripts/lint-persona-costing.mjs"` to `package.json` scripts.
- [ ] **Step 2:** Run `npm run lint` → both print OK.
- [ ] **Step 3:** Run `npm test` → still 40/40 (no code changed).
- [ ] **Step 4:** Commit `package.json`, msg `chore: npm run lint runs skill+persona content linters`. Then `git push origin main` (ships the skill/persona content in the repo; NO Railway redeploy needed — skills are plugin content, not server code).
- [ ] **Step 5:** Note in the report: installing/provisioning the skill+persona to managed portfolios is separate (skill bundles are frozen at install — re-sync per portfolio when ready).

---

## Self-Review

- **Spec coverage:** implements the design's Costing skill + Costing Specialist persona and the tool→`measure.cost` mapping; economics (NPV/IRR) explicitly excluded (decarb-plan owns it, Plan 6).
- **Placeholder scan:** none — lint scripts assert real content; the skill points to the canonical schema rather than vendoring it.
- **Contract fidelity:** the skill produces exactly the canonical `measure.cost` keys + additive extension; Plan 6 maps/validates these into `decarb-plan`/`quality-review`.
- **Blast radius:** repo-only content; no server redeploy, no production decarb change (that's Plan 6). Managed-portfolio install is a separate, deliberate step.
