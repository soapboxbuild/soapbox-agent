---
name: building-setup
description: >
  Reusable workflow for creating the Audette building(s) for an asset — single or
  multi-building — with evidence-gathered profile enrichment and verified account/property
  linkage. Triggers on: "create a building", "set up the building", "onboard this building
  in Audette", "create Audette building", "multi-building site".
version: 0.1.0
---

# Building Setup

You are creating the Audette building(s) for one asset. This workflow gathers evidence,
detects footprints, creates the building(s) in Audette, and verifies + persists the
account/property linkage so future threads bind correctly. It ends when the asset is linked
to correctly-created Audette building(s) backed by an enriched, cited building profile.

Out of scope (separate skills): **equipment surveys** (the Audette `audette-equipment-survey` skill —
bundled with the Audette MCP — owns the schema + tons units; use it once buildings exist),
energy-data compilation, full report generation.

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
  accepts them.

### Step 5 — Verify + persist linkage

Confirm each created building UID resolves on the account, then **auto-link** the asset by writing
the **PROPERTY UID** back to `audette_property_id` via `update_asset_fields` (this now persists —
`audette_property_id` is an allowed field — so no manual linking step is needed):
- Write the Audette **property_uid** that groups the building(s) — the one returned/used by
  `create_property_for_building` / `assign_property_to_building`, NOT a `building_model_uid`.
  This holds for **single and multi-building alike** — even one building belongs to a property.
- ⚠️ **Never write a building UID into `audette_property_id`.** A property is not a building;
  downstream tools that treat `audette_property_id` as a property (get_property, list its
  buildings) will 404 if it's a building UID. Record the individual building_model_uids in
  `metadata.audette_building_uids` for the roster instead.

This closes the mid-session/stale-link failure mode so the next thread binds correctly at
session-create — and the asset is linked automatically at the end of setup.

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
- **Linkage write errors** — `update_asset_fields` DOES persist `audette_property_id` (it is an
  allowed top-level field), so **auto-link by default** (Step 5). Only if the write returns an
  actual error: retry once, then report the property UID for manual linking and flag the failure.
  Do not skip auto-linking pre-emptively — the "can't persist" limitation no longer applies.
