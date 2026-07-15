# Audette Skills Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `soapboxbuild/audette-skills`' `audette-create-building` skill be the real, current building-creation workflow (content-equivalent to `soapbox-agent/skills/building-setup/`), and get it live on a real portfolio via the plugin's normal skill-bundle mechanism — replacing the stale 296-line version it holds today.

**Architecture:** This is a content migration + operational rollout, not new application code. A lint script (ported from `soapbox-agent`) acts as this plan's "test" — it fails against the current stale skill content and passes once the migrated content lands. Rollout uses the exact, previously-validated re-sync mechanism for this codebase: managed-agent skill bundles are frozen as an Anthropic Skills API upload at plugin-install time (`registerPluginSkillsFromRepo`) and only refresh via an explicit re-sync (`POST /api/portfolios/:pid/installed-plugins/:id/refresh-commands`) followed by a `soapbox-api` restart (30-minute in-memory `warmPortfolioConfigCache` otherwise hides the change) — see `managed-agent-skill-bundle-frozen` in this session's memory for the full mechanism and its "push before resync" gotcha.

**Tech Stack:** Markdown skill files (Claude Skills format), Node.js lint scripts (no framework), Supabase/Postgres (`installed_plugins` table), Railway (`soapbox-api` service).

## Global Constraints

- Repos: `/home/claude/audette-skills` (currently `chmod 555`, must be made writable first), `/home/claude/soapbox-agent` (source of the content being migrated + the pointer removal), `/home/claude/soapbox-platform` (the `agent-config.ts` pointer text).
- `soapboxbuild/audette-skills` is **not** GitHub-archived and has no repo-level deprecation lock — un-deprecating is a local `chmod` + normal PR, nothing to reverse on GitHub.
- Do not change `building-setup`'s Step 3/4 decision logic during migration — copy content, adapt only front-matter/naming to fit `audette-skills`' conventions.
- Keep the skill slug `audette-create-building` (not `building-setup`) — it's the name already published in the plugin's marketplace description (`platform-web/src/lib/plugin-registry.ts:248`).
- Every push to a shared branch/remote in this plan requires explicit user confirmation first (established norm this session) — these are called out per task, not assumed.

---

### Task 1: Un-deprecate `audette-skills` and branch

**Files:**
- Modify (permissions only, no content yet): `/home/claude/audette-skills` (recursive chmod)

- [ ] **Step 1: Make the local checkout writable**

```bash
chmod -R u+w /home/claude/audette-skills
```

- [ ] **Step 2: Verify it's writable**

```bash
touch /home/claude/audette-skills/.write-test && rm /home/claude/audette-skills/.write-test && echo "writable"
```

Expected: `writable` (no `Permission denied`).

- [ ] **Step 3: Confirm the repo is clean and on `main`, then branch**

```bash
cd /home/claude/audette-skills
git status --short
git branch --show-current
```

Expected: no uncommitted changes shown, current branch `main`. If there ARE uncommitted changes, stop and investigate before proceeding — do not branch over unknown local state.

```bash
git checkout -b migrate-building-setup-skill
```

- [ ] **Step 4: No commit for this task** (permissions aren't tracked by git; the branch creation is the only durable action, already done in Step 3).

---

### Task 2: Port the skill lint script (write the failing "test" first)

**Files:**
- Create: `/home/claude/audette-skills/scripts/lint-skill-audette-create-building.mjs`

**Interfaces:**
- Consumes: `/home/claude/audette-skills/skills/audette-create-building/skill.md` (read as plain text).
- Produces: a Node script that exits non-zero (throws) when the skill content is missing any of the required workflow markers — mirrors `soapbox-agent/scripts/lint-skill-building-setup.mjs` exactly, repointed at the new file location and skill name in its output message.

- [ ] **Step 1: Write the lint script**

Create `/home/claude/audette-skills/scripts/lint-skill-audette-create-building.mjs`:

```javascript
import { readFileSync } from 'node:fs'
const md = readFileSync(new URL('../skills/audette-create-building/skill.md', import.meta.url), 'utf8')
const must = [
  'switch_customer_account', 'account context', 'audette_property_id',
  'search_documents', 'documents', 'lease', 'general web', 'provenance', 'retrieval date',
  'documents > listings', 'conflicts', 'overture__nearby_buildings', 'save_building',
  'is_primary', 'single', 'multi', 'update_asset_fields', 'verify', 'never invent'
]
const missing = must.filter(s => !md.includes(s))
if (missing.length) throw new Error('audette-create-building skill.md missing: ' + missing.join(', '))
console.log('audette-create-building skill lint OK')
```

- [ ] **Step 2: Run it to verify it fails against the current stale content**

```bash
cd /home/claude/audette-skills
node scripts/lint-skill-audette-create-building.mjs
```

Expected: throws `Error: audette-create-building skill.md missing: ...` listing most or all of the `must` markers (the current 296-line `skill.md` is the old single-pass document-extraction version and doesn't contain this workflow's language — e.g. it has no `overture__nearby_buildings`, no `provenance`, no `never invent`).

- [ ] **Step 3: Commit**

```bash
git add scripts/lint-skill-audette-create-building.mjs
git commit -m "test: add lint for the migrated audette-create-building skill (currently failing)"
```

---

### Task 3: Replace the skill content

**Files:**
- Modify: `/home/claude/audette-skills/skills/audette-create-building/skill.md` (296 lines → replaced)
- Create: `/home/claude/audette-skills/skills/audette-create-building/references/evidence-gathering.md`
- Keep as-is: `/home/claude/audette-skills/skills/audette-create-building/references/archetypes.md` (not touched — still useful reference material the migrated skill can point to)

- [ ] **Step 1: Replace `skill.md`**

Write `/home/claude/audette-skills/skills/audette-create-building/skill.md` with this exact content (the `soapbox-agent/skills/building-setup/SKILL.md` content, with front-matter adapted to this repo's slug/name and a note added pointing at the kept `archetypes.md`):

```markdown
---
name: audette-create-building
description: >
  Creates the Audette building(s) for an asset — single or multi-building — with
  evidence-gathered profile enrichment and verified account/property linkage. Use whenever
  the user wants to add a property to Audette, onboard a new asset, or create a building
  model. Triggers on: "create a building for [property]", "add [property] to Audette",
  "onboard this asset", "set up the building", "multi-building site", or proactively when
  the user shares property documents with no building yet in Audette.
version: 2.0.0
requires:
  - audette-mcp
---

# Audette Create Building

You are creating the Audette building(s) for one asset. This workflow gathers evidence,
detects footprints, creates the building(s) in Audette, and verifies + persists the
account/property linkage so future threads bind correctly. It ends when the asset is linked
to correctly-created Audette building(s) backed by an enriched, cited building profile.

Out of scope (separate skills/steps): energy-data compilation, equipment survey, full report
generation. See `references/archetypes.md` for the building-archetype taxonomy referenced in
Step 4.

## Method

### Step 1 — Resolve account context

Call `switch_customer_account` to the portfolio's Audette account before touching anything
else. If the asset already has an `audette_property_id`, verify it resolves on that account —
do not trust a stored UID blindly. If it doesn't resolve (wrong account, stale link), surface
the mismatch to the user and treat the linkage as unverified rather than proceeding as if it
were good.

### Step 2 — Evidence gathering

Pointer: see `references/evidence-gathering.md` for the full recipes.

Consolidate ONE cited building profile from three sources, in authority order:
**documents > listings/records > general web**:
1. **Documents** (highest authority) — `search_documents` + reading the asset's files.
2. **Lease listings** (lease specs, tenancy, and lease structure) — brave-search on CRE
   listing sites.
3. **General web** — brave-search broadly (assessor records, owner sites, permits, news).

Every field in the profile carries **provenance** (source + **retrieval date**). Conflicts
between sources are **surfaced, not silently overwritten** — conflicts are reported to the
user rather than silently resolved by picking a winner yourself. Gaps stay unknown; **never
invent** a value that isn't backed by a document, listing, record, or Audette.

### Step 3 — Footprint detection

Always detect footprints before creating anything in Audette:
1. `list_buildings` — check for existing footprints first.
2. Else `overture__nearby_buildings(lat, lon, radius_m=120)` — pull candidate footprints from
   Overture.
3. `save_building` per footprint returned, marking the largest footprint `is_primary`.
4. If Overture returns nothing, fall back to a single point-footprint for the asset's address.

### Step 4 — Create Audette building(s)

- **Single footprint** → one building, named after the asset.
- **Multiple footprints** → one building per footprint, named `"<asset> — Bldg N"`, passing
  height/floors/class from the saved footprint plus the Step-2 profile specs wherever Audette
  accepts them. See `references/archetypes.md` for archetype selection.

### Step 5 — Verify + persist linkage

Confirm each created building UID resolves on the account. Write the correct
`audette_property_id` back to the asset via `update_asset_fields`:
- Single building → that building's UID.
- Multi-building → the **primary** building's UID; note the other UIDs for the user.

This closes the mid-session/stale-link failure mode so the next thread binds correctly at
session-create.

## Guardrails

- **No fabrication** — every profile attribute comes from a document, listing, record, or
  Audette; unknown stays unknown and is flagged, never invented.
- **Provenance on every field** — source + retrieval date, always.
- **Conflicts surfaced, not overwritten** — reconciliation reports disagreements for the user
  to adjudicate.
- **Footprints before creation** — never create a building in Audette without completing
  Step 3 first.
- **Linkage integrity** — never trust a stored `audette_property_id` that doesn't resolve on
  the current account.

## Degraded modes

- **Audette connector expired/degraded** — stop at Step 1 and tell the user to reconnect;
  never create buildings against a dead or unverified account.
- **Overture returns nothing** — use the single point-footprint fallback (Step 3).
- **No documents and no web coverage** — proceed with whatever resolves, flag the profile as
  thin; do not invent specs to fill it out.
- **`update_asset_fields` can't persist `audette_property_id`** — fall back to reporting the
  UID(s) to the user for manual linking, and flag that persistence failed.
```

- [ ] **Step 2: Create `references/evidence-gathering.md`**

Write `/home/claude/audette-skills/skills/audette-create-building/references/evidence-gathering.md` with this exact content (copied verbatim from `soapbox-agent/skills/building-setup/references/evidence-gathering.md`):

```markdown
# Evidence Gathering — Building Profile Recipes

Detailed recipes for Step 2 of the `audette-create-building` skill: consolidating one cited
building profile from documents, lease listings, and general web research, ranked
**documents > listings/records > general web**.

## a. Documents (highest authority)

Use `search_documents` against the asset's uploaded files, then read the relevant matches
(as-builts — HVAC/electrical/plumbing/structural; PCA; utility data; rent roll; OM). Extract
every building attribute present:

- Gross floor area (GFA)
- Number of floors
- Year built
- Construction type / building class (A/B/C)
- Systems & equipment (HVAC, envelope, DHW, controls)
- Occupancy / tenancy
- Address (confirm against other sources)

Cite each extracted field with the source **document filename** and the **retrieval date**
(the date you read it in this session).

## b. Lease listings

brave-search CRE listing sites (LoopNet, Crexi, CoStar-class) by asset name + address. Pull:

- Specs (GFA, floors, year built, class) to corroborate or fill gaps from documents.
- Tenancy & lease structure: single-tenant vs multi-tenant, NNN vs gross, WALT (weighted
  average lease term).
- Asking rent / sale comps, when present.

Cite each field with the **listing URL** and **retrieval date**.

## c. General web research

brave-search broadly for anything documents and listings didn't cover:

- County assessor / property records (parcel data, assessed value, legal description).
- Owner or property websites.
- Permits (renovation history, system replacements).
- News (ownership changes, major capital events).

Cite each field with the **web URL** and **retrieval date**.

## Reconciliation rules

- Consolidate all three sources into **one** building profile — not three separate profiles.
- **Provenance on every field**: source (document filename / listing URL / web URL) +
  retrieval date. A field with no source is not in the profile.
- **Ranking**: when sources disagree, prefer **documents > listings/records > general web**
  as the suggested resolution.
- **Conflicts are surfaced, not silently overwritten** — when two sources disagree (e.g. GFA
  from the PCA vs GFA from the LoopNet listing), report both values with their sources to the
  user rather than picking one and discarding the other.
- **Gaps stay unknown** — if no source has a value for an attribute, leave it unknown and flag
  it in the profile summary. **Never invent** a value to fill a gap.
```

- [ ] **Step 3: Run the lint script to verify it now passes**

```bash
cd /home/claude/audette-skills
node scripts/lint-skill-audette-create-building.mjs
```

Expected: `audette-create-building skill lint OK` (exit code 0).

- [ ] **Step 4: Commit**

```bash
git add skills/audette-create-building/skill.md skills/audette-create-building/references/evidence-gathering.md
git commit -m "feat: migrate building-setup workflow into audette-create-building"
```

---

### Task 4: Push and open the PR (requires user confirmation)

- [ ] **Step 1: Confirm with the user before pushing** — this is a push to a previously read-only, now-revived shared repo. State exactly what's being pushed (2 commits: the lint script + the migrated skill content) and wait for explicit go-ahead before Step 2.

- [ ] **Step 2: Push the branch**

```bash
cd /home/claude/audette-skills
git push -u origin migrate-building-setup-skill
```

- [ ] **Step 3: Open the PR**

```bash
gh pr create --repo soapboxbuild/audette-skills \
  --title "Migrate building-setup workflow into audette-create-building" \
  --body "$(cat <<'EOF'
## Summary
- Replaces the stale 296-line audette-create-building/skill.md (single-pass, document-only extraction) with the current building-setup workflow from soapbox-agent — evidence gathering across documents/listings/web, footprint detection via list_buildings/overture, single-and-multi-building creation, verified linkage persistence.
- Adds references/evidence-gathering.md (the Step 2 recipes) and a lint script asserting the workflow's required elements are present.
- Keeps references/archetypes.md and the audette-create-building slug (already published in platform-web's plugin catalog description) unchanged.

## Test plan
- [ ] node scripts/lint-skill-audette-create-building.mjs passes
- [ ] Re-sync the audette plugin on a test portfolio (Task 5) and confirm a fresh agent session actually runs this content, not the old one
EOF
)"
```

- [ ] **Step 4: Confirm with the user before merging** — wait for explicit go-ahead, then merge (`gh pr merge --repo soapboxbuild/audette-skills --squash` or via the GitHub UI, per the user's preference at the time).

---

### Task 5: Re-sync the `audette` plugin on one test portfolio and verify

This task has no code changes — it's the operational verification the design spec calls out as the risky part of this migration. Follow the exact mechanism recorded in this session's `managed-agent-skill-bundle-frozen` memory.

- [ ] **Step 1: Confirm the merged content is actually on `main`** (re-sync pulls from GitHub `main` via the git trees API, not any local checkout — a resync against an unpushed/unmerged `main` silently rebuilds the stale bundle):

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/soapboxbuild/audette-skills/contents/skills/audette-create-building/skill.md?ref=main" \
  | grep "never invent"
```

Expected: the line containing `never invent` prints (confirms `main` has the new content, not the old 296-line version). If `GITHUB_TOKEN` isn't set in this shell, pull it the same way this session pulled other secrets (`railway variables` on a service that has it, or Vaultwarden).

- [ ] **Step 2: Pick one real test portfolio with the `audette` plugin installed**, and record its current `anthropic_skill_id` before touching anything:

```sql
select portfolio_id, name, anthropic_skill_id, created_at
from installed_plugins
where plugin_id = 'audette'
order by created_at desc
limit 5;
```

Run this via the Supabase service-role REST call pattern already used earlier this session (`curl .../rest/v1/installed_plugins?...` with the service-role key), or via a direct SQL tool if available. Pick one portfolio_id from the results to use as the test case; write down its current `anthropic_skill_id` for comparison in Step 5.

- [ ] **Step 3: Trigger the re-sync for that portfolio's `audette` plugin row**

Use the admin refresh route (does the unregister+re-register in one call):

```bash
curl -s -X POST "https://soapbox-api-production.up.railway.app/api/portfolios/<portfolio_id>/installed-plugins/<installed_plugin_row_id>/refresh-commands" \
  -H "Authorization: Bearer <admin token>" \
  -H "Content-Type: application/json" \
  -d '{"skills_repo":"soapboxbuild/audette-skills"}'
```

(`<installed_plugin_row_id>` is the `id` column from the Step 2 query's row, not the `portfolio_id`. Use an admin-capable auth token — the `claude@agents.soapbox.build` service account used earlier this session, if it has platform-admin rights, or whichever admin credential this codebase's existing admin routes expect; check `apps/api/src/routes/` for this route's auth middleware if unsure which token qualifies.)

- [ ] **Step 4: Restart `soapbox-api` to clear the 30-minute warm cache** — this is CRITICAL; skipping it means the re-sync is invisible until the cache naturally expires:

```bash
railway redeploy --service soapbox-api -y
```

- [ ] **Step 5: Verify the rebuild actually took**

```sql
select portfolio_id, name, anthropic_skill_id, created_at
from installed_plugins
where plugin_id = 'audette' and portfolio_id = '<portfolio_id>';
```

Expected: `anthropic_skill_id` is a **different** value than what was recorded in Step 2 (a new Anthropic skill was created from the fresh bundle), and `created_at` reflects "now," not the original install time.

- [ ] **Step 6: Live-probe the actual skill content** — start (or resume) a thread on that test portfolio's asset and ask the agent to create a building for a multi-building test asset (ideally one already populated with real `buildings` rows via the companion `2026-07-15-onboarding-per-building-footprints` plan, if that's landed by this point). Confirm in the transcript that the agent follows the 5-step workflow (mentions evidence gathering, footprint detection via `list_buildings`, and creates one building per footprint for a multi-building asset) rather than defaulting to "one combined model."

---

### Task 6: Check for portfolios running the stale skill independently of this migration

This is a read-only investigative task — the spec explicitly calls out not to silently paper over this as part of the migration; report findings to the user rather than fixing them here.

- [ ] **Step 1: Find portfolios with `audette` installed but without `soapbox-agent`**

```sql
select p1.portfolio_id
from installed_plugins p1
where p1.plugin_id = 'audette'
and not exists (
  select 1 from installed_plugins p2
  where p2.portfolio_id = p1.portfolio_id and p2.plugin_id = 'soapbox-agent'
);
```

- [ ] **Step 2: Report the result to the user** — if the list is non-empty, these portfolios have been relying entirely on whatever's in their frozen `audette` bundle (the stale skill, until Task 5's re-sync reaches them too) with no `building-setup` pointer fallback at all. State the count and portfolio names; do not silently re-sync all of them as a side effect of this task — that's a separate, larger action the user should explicitly approve (it touches every affected portfolio's live agent).

---

### Task 7: Update the `agent-config.ts` pointer and remove the soapbox-agent copy

**Files:**
- Modify: `soapbox-platform/apps/api/src/services/agent-config.ts` (the "no `audette_property_id` yet" branch, originally around line 427 per the `2026-07-11-building-setup-workflow-design.md` spec — confirm the current line number before editing, it may have shifted)
- Delete: `soapbox-agent/skills/building-setup/SKILL.md`, `soapbox-agent/skills/building-setup/references/evidence-gathering.md`, `soapbox-agent/scripts/lint-skill-building-setup.mjs`

**This task is gated on Task 5's live-probe succeeding** — do not remove the soapbox-agent copy or repoint the prompt text until a real portfolio has been confirmed running the migrated `audette-create-building` skill correctly.

- [ ] **Step 1: Find and read the current pointer text**

```bash
cd /home/claude/soapbox-platform
grep -n "building-setup" apps/api/src/services/agent-config.ts
```

Read the surrounding ~10 lines to see the exact current wording before editing (it was written to say "follow the `building-setup` skill" per the original design — confirm this is still the literal text before writing a replacement).

- [ ] **Step 2: Update the pointer text**

Change the found line(s) from referencing "the `building-setup` skill" to "the `audette-create-building` skill" (in whichever plugin/skill the agent has installed — the wording should match this repo's existing style for referencing a skill by name; copy the surrounding sentence structure exactly, only swapping the skill name).

- [ ] **Step 3: Typecheck / build soapbox-platform's API**

Run whatever this repo's existing check command is for `apps/api` (e.g. `pnpm --filter api typecheck` or equivalent — check `package.json` scripts if unfamiliar) to confirm the edit didn't break anything (it's a string literal change, low risk, but verify).

- [ ] **Step 4: Commit and push soapbox-platform (requires user confirmation before push — this deploys via Railway auto-deploy)**

```bash
git add apps/api/src/services/agent-config.ts
git commit -m "fix(agent-config): point building-creation instructions at audette-create-building, not the retired soapbox-agent building-setup skill"
```

Confirm with the user, then:

```bash
git push origin main
```

- [ ] **Step 5: Remove the soapbox-agent copy**

```bash
cd /home/claude/soapbox-agent
rm -rf skills/building-setup
rm scripts/lint-skill-building-setup.mjs
```

- [ ] **Step 6: Check for any other reference to the removed skill/script before committing**

```bash
grep -rln "building-setup\|lint-skill-building-setup" /home/claude/soapbox-agent --include="*.ts" --include="*.md" --include="*.mjs" --include="*.json" | grep -v node_modules
```

Expected: no results (or only this plan/spec's own historical references in `docs/superpowers/`, which should stay — they're the historical record, not live code).

- [ ] **Step 7: Commit and push soapbox-agent (requires user confirmation before push)**

```bash
git add -A
git commit -m "chore: remove building-setup — migrated to audette-create-building in the audette-skills plugin"
```

Confirm with the user, then:

```bash
git push origin main
```

---

## Final verification (all tasks complete)

- [ ] `audette-skills` main has the migrated skill content (Task 3/4) and its lint script passes.
- [ ] At least one real portfolio's `audette` plugin bundle has been re-synced and live-probed to confirm it runs the new workflow (Task 5).
- [ ] The pre-existing "audette without soapbox-agent" portfolio list has been reported to the user (Task 6) — not silently fixed.
- [ ] `agent-config.ts`'s pointer no longer references a skill that doesn't exist in `soapbox-agent` anymore, and the old `building-setup` files are gone from that repo (Task 7).
- [ ] Re-run `grep -rn "building-setup"` across both `soapbox-agent` and `soapbox-platform` one final time to confirm no dangling reference survived the migration.
