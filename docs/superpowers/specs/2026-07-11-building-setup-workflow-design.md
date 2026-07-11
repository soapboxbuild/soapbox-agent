# Building-Setup Workflow — Design

**Date:** 2026-07-11
**Status:** Approved design, pending spec review
**Origin:** Creating Audette buildings for an asset (single or multi-building) is today an inline
"Multi-Building Site Protocol" prompt blob in `soapbox-platform` `agent-config.ts`, with the old
`audette-create-building` skill stranded in the deprecated read-only `audette-skills`. The Clarion
/ Kingsland Ranch experience exposed the gaps: footprints hunted manually, no document/web
enrichment, and a stale/mislinked `audette_property_id` (building linked mid-session, agent bound
to the wrong UID). We need a real, reusable **building-creation workflow**.

## Goal

A reusable, testable workflow an agent follows to create the Audette building(s) for an asset —
single or multi-building — that first **gathers all available evidence** (the asset's uploaded
documents + lease listings + general web research), then detects footprints, creates the
building(s) in Audette, and **verifies and persists the account/property linkage** so future
threads bind correctly.

## Scope

In scope: **building creation** for one asset. Non-goals (separate skills/steps): energy-data
compilation, equipment survey, full report generation. This workflow ends when the asset is
linked to correctly-created Audette building(s) with an enriched, cited building profile.

## Architecture

- **New skill `skills/building-setup/` in `soapbox-agent`** — the reusable workflow (this is the
  source of truth). `soapbox-agent` is a provisioned plugin, so the skill reaches portfolios on
  the next `soapbox-agent` bundle re-sync.
- **Thin pointer in `agent-config.ts`** — replace the inline "Multi-Building Site Protocol"
  (`agent-config.ts:427`, the `no audette_property_id yet` branch) with a short instruction:
  "To create or set up Audette building(s) for this asset, follow the `building-setup` skill."
  This is live for every managed agent immediately (system prompt is built per session); the full
  skill logic arrives with the bundle re-sync.
- The skill drives existing agent tools — no new MCP. Tools it uses: `search_documents` + file
  reads (documents), the brave-search connector (lease + general web), `overture__nearby_buildings`
  + `save_building` (footprints), `audette__switch_customer_account` + Audette building-creation
  tools, `get_asset_record` + `update_asset_fields` (linkage read/write).

## Workflow (the skill's method)

**Step 1 — Resolve account context.** `switch_customer_account` to the portfolio's
`audette_account_id`. If the asset already has an `audette_property_id`, verify it resolves on
that account; if it doesn't, surface the mismatch (the Kingsland failure mode) and treat the
linkage as unverified rather than trusting the stale UID.

**Step 2 — Evidence gathering (build one cited building profile).**
- **a. Documents (highest authority).** Use `search_documents` + read the asset's files
  (as-builts: HVAC/electrical/plumbing/structural; PCA; utility data; rent roll; OM) and extract
  every building attribute present: GFA, floors, year built, construction/class, systems &
  equipment, occupancy/tenancy, address, etc.
- **b. Lease listings.** brave-search CRE listing sites (LoopNet / Crexi / CoStar-class) by asset
  name + address → specs, tenancy & lease structure (single/multi-tenant, NNN vs gross, WALT),
  asking rent / sale comps.
- **c. General web research.** brave-search broadly — county assessor / property records, owner or
  property websites, permits, news — to fill gaps and corroborate.
- **Reconciliation:** consolidate into one building profile; **provenance on every field** (source
  = document filename / listing URL / web URL + retrieval date); rank **documents >
  listings/records > general web**; **conflicts are surfaced, not silently overwritten**; gaps are
  flagged, never invented.

**Step 3 — Footprint detection.** `list_buildings` (existing footprints) → else
`overture__nearby_buildings(lat, lon, radius_m=120)` → `save_building` per footprint (largest =
`is_primary`); single point-footprint fallback if Overture returns nothing. Always detect before
creating.

**Step 4 — Create Audette building(s).** Single footprint → one building (name = asset name).
Multiple → one per footprint ("<asset> — Bldg N"), passing height/floors/class from the saved
footprint plus the Step-2 profile specs where Audette accepts them.

**Step 5 — Verify + persist linkage.** Confirm each created building UID resolves on the account.
Write the correct `audette_property_id` back to the asset via `update_asset_fields` (multi → the
primary building's UID; note the others). This closes the mid-session/stale-link failure so the
next thread binds correctly at session-create.

## Guardrails

- **No fabrication** — every attribute comes from a document, listing, record, or Audette; unknown
  stays unknown and is flagged.
- **Provenance** — every profile field carries its source + retrieval date.
- **Conflicts surfaced, not overwritten** — reconciliation reports disagreements for the user.
- **Footprints before creation** — never create in Audette without Step 3.
- **Linkage integrity** — never trust a stored `audette_property_id` that doesn't resolve on the
  account.

## Error handling / degraded modes

- Audette connector degraded/expired → the workflow stops at Step 1 and tells the user to
  reconnect (don't create against a dead account).
- Overture returns nothing → point-footprint fallback (Step 3).
- No documents and no web coverage → proceed with whatever resolves, flag the thin profile; do not
  invent specs.
- `update_asset_fields` cannot write `audette_property_id` → fall back to reporting the UID for the
  user to link, and flag (see verify-at-build).

## Verify-at-build

- Confirm `update_asset_fields` (agent tool) permits writing `audette_property_id`; if it is
  field-restricted, add that field to its allowlist (small `soapbox-platform` change) — otherwise
  Step 5 can only report, not persist.
- Confirm the brave-search connector is available to the agents that will run this (it is a
  provisioned plugin); if a portfolio lacks it, Step 2b/2c degrade to documents-only with a note.

## Testing / acceptance

- `scripts/lint-skill-building-setup.mjs` (mirrors the soapbox-agent lint convention) asserts the
  skill contains: account-context verify, three evidence sources (documents / lease listings /
  general web) with provenance + source ranking, footprint detection (Overture + save_building),
  single-and-multi creation, and verify+persist linkage via `update_asset_fields`.
- The agent-config pointer lints: the inline protocol is replaced and references the
  `building-setup` skill.
- Live validation (not automated): run `building-setup` on a test asset — confirm it extracts from
  documents, cites web/listing findings, creates the building(s), and writes back a resolving
  `audette_property_id`.

## Rollout

- Ship the skill + the agent-config pointer together. Pointer is live immediately; the full skill
  reaches a portfolio on its next `soapbox-agent` bundle re-sync.
- Non-goal reminder: this does not re-onboard energy data or equipment surveys — those remain
  separate steps invoked after the building exists.
