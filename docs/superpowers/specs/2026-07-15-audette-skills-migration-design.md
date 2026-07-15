# Migrate `building-setup` Into `audette-skills` — Design

**Date:** 2026-07-15
**Status:** Approved design, pending spec review
**Origin:** The platform's plugin catalog (`platform-web/src/lib/plugin-registry.ts`) lists the
`audette` plugin's `skills_repo` as `soapboxbuild/audette-skills`, and its marketing copy describes
an `audette-create-building` skill. In reality, the current, correct, evidence-gathering
building-creation workflow lives in `soapbox-agent/skills/building-setup/` (see
`2026-07-11-building-setup-workflow-design.md`) — `audette-skills` still holds the old, stranded
296-line `skills/audette-create-building/skill.md` this replaced, and the whole repo was chmod'd
read-only and marked deprecated in favor of `soapbox-agent` (per
`feedback-audette-skills-readonly` memory: "superseded by the soapbox-agent plugin... which is the
live plugin used by every Soapbox portfolio asset"). The catalog's own metadata has been wrong since
that decision. This spec makes it true again: the Audette-specific skill lives in the Audette
plugin, not folded into soapbox-agent's general-purpose bundle.

## Goal

`audette-create-building` in `soapboxbuild/audette-skills` becomes the real, current
building-creation workflow (content-equivalent to `soapbox-agent/skills/building-setup/`), and
managed agents install it from there. No change to the workflow's decision logic — Step 3/4
("Multiple footprints → one building per footprint") is already correct; see the companion spec
`2026-07-15-onboarding-per-building-footprints-design.md` for why it wasn't firing (the `buildings`
table was simply empty).

## Non-goals

- No changes to the Audette MCP server itself (`mcp-server.prod.audette.io`) — already registered
  in `audette-skills/.claude-plugin/plugin.json` as `mcpServers.audette`.
- No changes to `building-setup`'s Step 3/4 logic — this is a location migration, not a rewrite.
- No decision here about the other `soapbox-agent` skills that reference Audette tooling
  (`decarb-plan`, `portfolio-analysis`, etc.) — they call Audette MCP tools directly and are
  general-purpose, cross-portfolio workflows; they stay in `soapbox-agent`.

## What's actually true today (verified, not assumed)

- `audette-skills` is **not** GitHub-archived and has **no** deprecation banner in its own README —
  the "deprecated, read-only" state is a local filesystem convention (`chmod 555` on the local
  checkout) recorded only in this session's memory, not a repo- or platform-level lock. Un-deprecating
  is just: make the local checkout writable again and open a normal PR — no GitHub settings, CI gate,
  or branch protection to reverse.
- `audette-skills/skills/audette-create-building/` exists today with `skill.md` (296 lines, the old
  single-pass "extract from documents in the project folder" version) plus
  `references/archetypes.md`. The archetypes reference is still useful (buildings archetype
  taxonomy) and should be kept; `skill.md` gets replaced.
- The plugin catalog's marketplace description (`plugin-registry.ts:248`) already describes
  `audette-create-building` accurately for what the *new* workflow does ("extracting property
  details from documents... onboard a new asset, or create a building model") — no copy change
  needed, just make the skill content match the promise.

## Architecture

**1. Replace, don't fork.** `audette-skills/skills/audette-create-building/skill.md` is replaced
with the content of `soapbox-agent/skills/building-setup/SKILL.md`, adapted only where the two
repos' skill conventions differ (see soapbox-agent's `scripts/lint-skill-building-setup.mjs` for
the current lint contract — port an equivalent lint into `audette-skills` if it has its own lint
convention, otherwise keep the soapbox-agent lint pointed at the new location).
`soapbox-agent/skills/building-setup/references/evidence-gathering.md` moves alongside it; the
existing `audette-skills/skills/audette-create-building/references/archetypes.md` is kept as an
additional reference the migrated skill can point to (archetype taxonomy is still useful for the
"identify property archetype" step).

**2. Keep the skill slug `audette-create-building`**, not `building-setup` — it's the name already
published in the plugin's marketplace description and (per `plugin-registry.ts`) the trigger name
users and other skills reference. Renaming would silently break that existing description and any
other skill that names it by slug.

**3. `soapbox-agent`'s pointer.** `soapbox-agent/skills/building-setup/` is removed once the
migrated version is confirmed live (see Rollout) — `agent-config.ts`'s "no `audette_property_id`
yet" branch already points at "the `building-setup` skill" by name per the original design; that
pointer text updates to reference `audette-create-building` in the `audette` plugin instead.

**4. No `soapbox-agent` skill is left half-pointing at a skill that no longer exists there** — the
pointer and the removal happen in the same change, gated on the rollout verification below, not
shipped as two separate PRs that could land out of order.

## Rollout (this is the risky part — sequence matters)

1. Open the `audette-skills` PR with the migrated skill content. Get it merged.
2. **Before** touching `soapbox-agent`: verify which portfolios currently have the `audette` plugin
   installed *without* `soapbox-agent` also installed — those portfolios have been running the
   stale 296-line skill this whole time, independent of this migration. Confirm this list exists or
   is empty; if non-empty, flag it to Christopher separately (it's a pre-existing gap, not something
   this migration should silently paper over).
3. Trigger a re-sync of the `audette` plugin bundle for a single test portfolio (per the "skill
   bundle frozen at install" mechanism — re-sync, not just re-merge) and confirm the new skill
   content is actually being served in a fresh agent session before rolling further.
4. Only after step 3 confirms clean: update `agent-config.ts`'s pointer text and delete
   `soapbox-agent/skills/building-setup/` (plus its lint script) in the same change.
5. Re-sync `soapbox-agent` org-wide as usual for that change to take effect everywhere.

## Testing / acceptance

- Port `soapbox-agent/scripts/lint-skill-building-setop.mjs`'s assertions (account-context verify,
  three evidence sources with provenance + ranking, footprint detection via
  `list_buildings`/`overture__nearby_buildings`/`save_building`, single-and-multi creation,
  verify+persist linkage) to wherever `audette-skills` runs its own skill lint, or keep running the
  same script against the new path if `audette-skills` has no lint convention of its own yet.
- Live validation (manual, per the `verify` skill): run the migrated `audette-create-building` skill
  on a real multi-building test asset (ideally one already populated with real `buildings` rows via
  the companion onboarding fix) and confirm it creates one Audette building per row instead of one
  combined model.
- Confirm the removed `soapbox-agent/skills/building-setup/` pointer text update lints clean (no
  dangling reference to a skill that no longer exists in that repo).

## Open question to resolve at build time

Does `audette-skills` have its own skill-content lint/CI check today (equivalent to
`lint-skill-building-setup.mjs`)? If not, decide whether to add one there or accept running
soapbox-agent's script against the new path as a manual pre-merge check. Either is fine; don't ship
without picking one — a skill this operationally important (creates real records in a paid third-party
system) shouldn't merge without some automated content check.
