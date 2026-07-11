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

Out of scope (separate skills/steps): energy-data compilation, equipment survey, full report
generation.

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
