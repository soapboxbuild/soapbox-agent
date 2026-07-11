# Building-Setup Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reusable `building-setup` skill (soapbox-agent) that creates Audette building(s) for an asset — single or multi — after gathering all evidence (documents + lease listings + general web), with footprint detection and verified/persisted `audette_property_id` linkage; plus the platform wiring (a thin agent-config pointer + the `update_asset_fields` allowlist).

**Architecture:** The workflow lives as a skill in `soapbox-agent` (source of truth, reaches portfolios on bundle re-sync). `soapbox-platform` gets two small changes: `audette_property_id` added to the `update_asset_fields` allowlist (so Step 5 can persist), and the inline "Multi-Building Site Protocol" in `agent-config.ts` replaced by a thin pointer to the skill (live immediately). Design: `docs/superpowers/specs/2026-07-11-building-setup-workflow-design.md`.

**Tech Stack:** Markdown skill + `node scripts/lint-skill-*.mjs` (soapbox-agent). TypeScript (soapbox-platform apps/api). Existing agent tools: `search_documents`, brave-search connector, `overture__nearby_buildings`, `save_building`, `audette__switch_customer_account`, Audette building-creation tools, `get_asset_record`, `update_asset_fields`.

## Global Constraints

- **No new MCP** — the skill drives existing agent tools only.
- **No fabrication.** Every building-profile attribute traces to a document, listing, record, or Audette; unknowns stay unknown and are flagged.
- **Provenance on every field** (source = document filename / listing URL / web URL + retrieval date). Source authority ranking: **documents > listings/records > general web**. Conflicts are surfaced, not silently overwritten.
- **Footprints before creation** (Step 3 always precedes Step 4).
- **Linkage integrity** — never trust a stored `audette_property_id` that doesn't resolve on the account; Step 5 writes back the correct UID.
- Scope is **building creation only** — NOT energy-data compilation, equipment survey, or reporting.
- soapbox-agent skill authoring mirrors the existing `skills/*/SKILL.md` + `scripts/lint-skill-*.mjs` convention.

---

### Task 1: `building-setup` skill (soapbox-agent)

**Files:**
- Create: `skills/building-setup/SKILL.md`
- Create: `skills/building-setup/references/evidence-gathering.md`
- Create: `scripts/lint-skill-building-setup.mjs`

**Interfaces:**
- Produces: a skill the agent follows for building creation; consumed at runtime by managed agents (and referenced by the agent-config pointer in Task 3).

- [ ] **Step 1: Write the lint (failing target)** — `scripts/lint-skill-building-setup.mjs` reads `skills/building-setup/SKILL.md` and throws listing any missing substring; print `building-setup skill lint OK`. Required substrings:
```
'switch_customer_account', 'account context', 'audette_property_id',
'search_documents', 'documents', 'lease', 'general web', 'provenance', 'retrieval date',
'documents > listings', 'conflicts', 'overture__nearby_buildings', 'save_building',
'is_primary', 'single', 'multi', 'update_asset_fields', 'verify', 'never invent'
```

- [ ] **Step 2: Run → FAIL** (`cd ~/soapbox-agent && node scripts/lint-skill-building-setup.mjs` — file missing).

- [ ] **Step 3: Write `skills/building-setup/SKILL.md`** — frontmatter (name `building-setup`; description triggering on "create a building", "set up the building", "onboard this building in Audette", "create Audette building", "multi-building site"; version 0.1.0). Body = the 5-step method from the spec:
  1. **Resolve account context** — `switch_customer_account` to the portfolio's Audette account; if the asset already has an `audette_property_id`, verify it resolves on that account, else surface the mismatch and treat linkage as unverified.
  2. **Evidence gathering** — pointer to `references/evidence-gathering.md`; consolidate one cited building profile (documents + lease + general web), provenance on every field, ranking `documents > listings/records > general web`, conflicts surfaced not overwritten, never invent.
  3. **Footprint detection** — `list_buildings` → else `overture__nearby_buildings(lat,lon,radius_m=120)` → `save_building` per footprint (largest `is_primary`); single point-footprint fallback.
  4. **Create Audette building(s)** — single → one building (asset name); multi → one per footprint ("<asset> — Bldg N"), passing height/floors/class + profile specs.
  5. **Verify + persist linkage** — confirm each created UID resolves; write the correct `audette_property_id` back via `update_asset_fields` (multi → primary UID, note others).
  Include the guardrails + degraded-mode notes (Audette expired → stop + tell user to reconnect; Overture empty → point fallback; `update_asset_fields` can't persist → report UID + flag).

- [ ] **Step 4: Write `skills/building-setup/references/evidence-gathering.md`** — the detailed evidence recipes: (a) documents via `search_documents` + file reads (extract GFA, floors, year built, class, systems/equipment, tenancy, address); (b) lease listings via brave-search on CRE sites (specs, tenancy/lease structure incl. NNN vs gross + WALT, asking rent/sale comps); (c) general web via brave-search (assessor/property records, owner/property sites, permits, news). The reconciliation + provenance + ranking rules.

- [ ] **Step 5: Run → `building-setup skill lint OK`.** If an assertion fails only on wording, adjust the assertion to match the prose (don't weaken the concept).

- [ ] **Step 6: Commit** `skills/building-setup/SKILL.md skills/building-setup/references/evidence-gathering.md scripts/lint-skill-building-setup.mjs`, msg `feat(building-setup): building-creation workflow skill (evidence gathering + footprints + verify/persist linkage)`.

---

### Task 2: Allow `audette_property_id` in `update_asset_fields` (soapbox-platform)

**Files:**
- Modify: `apps/api/src/mcp/asset-db-server.ts` (the `ALLOWED_ASSET_UPDATE_KEYS` set + the `update_asset_fields` `describe(...)` allowed-fields list)
- Modify: `apps/api/src/mcp/portfolio-db-server.ts` (same set + description)

**Interfaces:**
- Produces: `update_asset_fields` can persist `audette_property_id` (Step 5 of the skill depends on this).

- [ ] **Step 1:** Locate `ALLOWED_ASSET_UPDATE_KEYS` in `apps/api/src/mcp/asset-db-server.ts`. Add `'audette_property_id'` to the set.
- [ ] **Step 2:** Update that file's `update_asset_fields` tool `describe(...)` string to include `audette_property_id` in the "Allowed:" list.
- [ ] **Step 3:** Repeat Steps 1–2 in `apps/api/src/mcp/portfolio-db-server.ts` (its `ALLOWED_ASSET_UPDATE_KEYS` + description).
- [ ] **Step 4: Build check** — `cd ~/soapbox-platform && npx tsc -p apps/api --noEmit` (or the repo's typecheck) passes.
- [ ] **Step 5: Grep verification** — `grep -n "audette_property_id" apps/api/src/mcp/asset-db-server.ts apps/api/src/mcp/portfolio-db-server.ts` shows it in both allowlists.
- [ ] **Step 6: Commit** those two files, msg `feat(agent-tools): allow update_asset_fields to persist audette_property_id`.

---

### Task 3: Thin agent-config pointer replacing the inline protocol (soapbox-platform)

**Files:**
- Modify: `apps/api/src/services/agent-config.ts` (the inline "Multi-Building Site Protocol" in the `no audette_property_id` branch, ~line 427)

**Interfaces:**
- Consumes: the `building-setup` skill (Task 1) by name.
- Produces: agents are told to follow the `building-setup` skill for building creation instead of the inline steps.

- [ ] **Step 1: Read** `apps/api/src/services/agent-config.ts` around the `audetteBuildingSection` (~427) — the `: \`...Multi-Building Site Protocol...\`` template-literal branch used when the asset has no `audette_property_id`.
- [ ] **Step 2: Replace** the inline "## Multi-Building Site Protocol (REQUIRED …)" block (Steps 1–3 of the old protocol) with a thin pointer, preserving the surrounding account-UID lines and the "no Audette building yet" framing:
  ```
  \n\n## Building setup\nTo create or set up Audette building(s) for this asset, follow the **building-setup** skill — it gathers evidence from the asset's documents, lease listings, and general web research; detects footprints (Overture) before creating; handles single and multi-building sites; and verifies + persists the correct audette_property_id linkage. Do not create buildings ad hoc; use the skill.
  ```
  Keep the account UID (`${audetteAccountId ?? 'unknown'}`) line and the "no config files / proceed with the UID" platform rules intact. Do NOT change the `audette_property_id`-present branch.
- [ ] **Step 3:** Bump `TOOLS_VERSION` in `agent-config.ts` (e.g. append `; v13: building-setup skill pointer replaces inline multi-building protocol`) so cached agents refresh.
- [ ] **Step 4: Build check** — typecheck passes.
- [ ] **Step 5:** Grep — the old "Multi-Building Site Protocol" string is gone and "building-setup" is referenced.
- [ ] **Step 6: Commit** `apps/api/src/services/agent-config.ts`, msg `feat(agent-config): point building setup at the building-setup skill; bump TOOLS_VERSION`.

---

### Task 4: Deploy + validate ⚠️ OUTWARD-FACING (soapbox-api deploy affects all orgs)

**Files:** none (deploy + live validation).

> Controller pauses for human go-ahead before the soapbox-api deploy.

- [ ] **Step 1:** Merge the soapbox-platform changes (Tasks 2–3) via the branch/PR the repo uses, and deploy soapbox-api (it tracks `main`). Wait for Online + `/health`.
- [ ] **Step 2:** Commit/push the soapbox-agent skill (Task 1). Note: it reaches a managed portfolio only on that portfolio's next `soapbox-agent` bundle re-sync; the agent-config pointer is live immediately.
- [ ] **Step 3: Live validation** — on a test asset with documents + a known address, start a fresh thread and ask to "set up the building." Confirm: the agent extracts from documents, cites lease/web findings, detects footprints, creates the Audette building(s), and writes back a resolving `audette_property_id` (re-query the asset row to confirm the UID persisted). Record outputs.

---

## Self-Review

- **Spec coverage:** Task 1 = the skill (all 5 steps + evidence gathering + guardrails); Task 2 = the `update_asset_fields` persist path (spec verify-at-build); Task 3 = the thin agent-config pointer; Task 4 = deploy + the live-validation acceptance test. All spec sections mapped.
- **Placeholder scan:** none — lint substrings, exact files, and the pointer copy are concrete. The two "adjust assertion to match prose" notes are the established lint-reconciliation convention, not placeholders.
- **Type/name consistency:** skill name `building-setup` and field `audette_property_id` are used identically across Tasks 1–4; `ALLOWED_ASSET_UPDATE_KEYS` is the real set name in both db-server files.
- **Blast radius:** Task 1 is soapbox-agent content (safe, re-sync-gated). Tasks 2–3 are small platform-core edits behind the Task 4 deploy checkpoint; `TOOLS_VERSION` bump busts cached agents so the pointer takes effect.
