# Onboarding Writes Per-Building Footprints — Design

**Date:** 2026-07-15
**Status:** Approved design, pending spec review
**Origin:** Onboarding "Cinnamon Run" (an 11-building, 511-unit apartment complex at 14120 Weeping
Willow Dr) through the platform-web asset-onboarding map picker: the user multi-selected each
building's footprint one at a time, expecting Soapbox to remember them as distinct buildings on the
one asset. Instead the picker merged every selected shape into a single `FeatureCollection` string
on `assets.footprint_geojson`. Downstream, the `building-setup` Audette skill calls `list_buildings`
first and only falls back to its own Overture auto-detection when that's empty — since nothing was
ever written to the `buildings` table, `list_buildings` returned nothing, and the skill defaulted to
"no individual footprints were selected," creating one combined Audette model instead of one
building per footprint.

## Goal

When the onboarding map picker is used to multi-select 2+ existing building shapes for one asset,
persist each selected building as its own row in the `buildings` table (already migrated, already
has a working CRUD API), instead of collapsing them into one merged shape on the asset. The asset
itself stays singular — this never creates multiple Soapbox assets from one multi-select.

## Non-goals

- **No multi-asset split.** An earlier direction explored turning a multi-select into N separate
  Soapbox assets; the user corrected this — "one asset in Soapbox, multiple buildings in Audette."
  This spec does not touch asset count.
- **No change to the Audette skill's decision logic.** `building-setup`'s Step 3/4 ("Multiple
  footprints → one building per footprint") is already correct; it just needs real data to read.
  Migrating/verifying that skill is a separate spec (see
  `2026-07-15-audette-skills-migration-design.md`).
- **Hand-drawn polygons are unaffected.** Draw-mode shapes (one or more hand-drawn polygons) keep
  today's behavior — merged into one `footprint_geojson` on the asset, no `buildings` rows. Only
  clicking existing building shapes (`+Multi` / shift-drag select) triggers per-building rows.

## Background: what already exists

- `buildings` table (`supabase/migrations/20260617000002_buildings.sql`): `asset_id` FK, one row
  per physical building, `is_primary` boolean, `footprint_geojson text not null` (a single
  building's own geometry, not a collection), `source` (`overture` | `drawn` | `manual`).
- `GET/POST/PATCH/DELETE /api/assets/:assetId/buildings` (`apps/api/src/routes/buildings.ts`) —
  full CRUD, already live, already used by `building-setup`'s `list_buildings`/`save_building`
  tools.
- `POST /api/assets` (`apps/api/src/routes/assets.ts`) already accepts an optional `buildings: [...]`
  array in the create payload: it inserts each into `buildings`, and — for backward compatibility —
  copies the primary building's `footprint_geojson` onto the asset row itself if the asset didn't
  already have one set directly.
- What's missing is entirely on the platform-web frontend: nothing in the onboarding flow ever
  populates that array.

## Architecture

**1. New pure helper in `src/lib/asset-map.ts`** — `buildSelectedBuildingRows(buildings, selectedIds)`:
returns `Array<{ overture_id: string | null; name: string | null; footprint_geojson: string;
building_class: string | null; height_m: number | null; num_floors: number | null; is_primary:
boolean; source: "overture" }>`, one entry per selected building (in `selectedIds` order), with
`is_primary: true` on the entry with the largest footprint area (matches `building-setup`'s "largest
= primary" convention, computed via a small polygon-area helper next to the existing `geo.ts`
helpers). Returns `[]` when fewer than 2 buildings are selected or when any hand-drawn polygon/point
exists (those keep the merged single-footprint path).

**2. `useAssetMap` exposes `isMultiBuildingSelection: boolean`** — `selectedIds.size >= 2 &&
drawnPolygons.length === 0 && drawPoints.length < 3`. Single source of truth so both pickers
(`MapScreen`, `MapFootprintPicker`) show the same "Confirm N buildings →" label and drive the same
code path, instead of duplicating the condition.

**3. `ReviewRow` gains an optional `buildings?: ReturnType<typeof buildSelectedBuildingRows>`.**
When set, it travels through the row alongside the existing single `footprint_geojson` field (left
`null` in this case — the asset itself doesn't get a merged shape when it has real per-building
rows; `POST /api/assets` already derives the asset's own `footprint_geojson` from the primary
building when `buildings` is present).

**4. Two call sites, two persistence paths:**
- **New-asset path (`MapScreen`, single-address search):** `buildRow()` now includes `buildings` when
  `isMultiBuildingSelection` is true. The asset is created via the existing single-asset fast path
  (`createAndUploadAsset` → `POST /api/assets`), which already threads a `buildings` array through
  to row inserts — no new endpoint call needed here, just populating the field.
- **Existing-asset path (bulk footprint queue `MapFootprintPicker`, and the post-creation
  `AssetMapModal` settings editor):** the asset already exists, so `onConfirm` — when
  `isMultiBuildingSelection` — calls `POST /api/assets/:assetId/buildings` once per row (small
  sequential loop; these are low-volume, interactive-triggered writes, not worth parallel-batching)
  instead of `PATCH`-ing a merged `footprint_geojson`.

**5. UI:** Confirm button reads "Confirm N buildings →" instead of "Confirm footprint →"/"Confirm
→" when `isMultiBuildingSelection` is true, in both `MapScreen` and `MapFootprintPicker`, so the
user can see their multi-select will land as separate building records rather than one shape.

## Data flow example (Cinnamon Run, redone)

1. User searches "14120 Weeping Willow Dr" → `MapScreen` loads, radius widened to 500m (already
   shipped), shows every Overture+OSM building footprint in the complex.
2. User turns on `+Multi`, clicks each of the 11 buildings that belong to Cinnamon Run.
   `isMultiBuildingSelection` becomes true; Confirm reads "Confirm 11 buildings →".
3. Confirm → `buildRow()` returns one `ReviewRow` (asset name "Cinnamon Run") with `buildings: [11
   entries]`, `footprint_geojson: null`.
4. Create stage → `POST /api/assets` with that payload → API inserts 11 rows into `buildings`
   (`asset_id` = the new Cinnamon Run asset), copies the primary (largest) building's shape onto
   `assets.footprint_geojson` for back-compat map rendering.
5. Later, `building-setup` runs: `list_buildings` returns the 11 rows → creates 11 Audette buildings
   under one property, per its existing (unchanged) Step 3/4 logic.

## Error handling

- If a `POST /api/assets/:assetId/buildings` call fails mid-loop (existing-asset path), surface the
  error the same way the current single `PATCH` failure is surfaced today (inline error message,
  footprint not marked confirmed) — do not silently drop remaining buildings; report which ones
  succeeded so the user isn't left guessing.
- `buildSelectedBuildingRows` never fabricates a name — `name` is `null` when a building has no
  `name` from Overture/OSM (matches existing `Building` type nullability); the API layer already
  accepts `name: null`.

## Testing

- Unit tests for `buildSelectedBuildingRows` in `asset-map.test.ts`: 0/1/N selections, primary =
  largest area, draw-mode present → returns `[]`.
- Extend `AssetOnboardingModal.test.tsx` (single-address path) and `.parallel.test.tsx` (bulk queue
  path) with a multi-building-select case: mock 2+ selected buildings, assert the create/PATCH
  payload includes a `buildings` array with the right length and `is_primary` on exactly one entry.
- Manual verification (per `verify` skill): drive the real onboarding flow against a multi-building
  address, confirm `GET /api/assets/:id/buildings` returns one row per selected building afterward.

## Rollout

- Single-repo (`platform-web`) change, no migration or infra risk — the schema/API already exist
  and are already live. Ship behind no flag; it only changes behavior when 2+ buildings are
  multi-selected, which today always produced a merged blob nobody downstream could use per-building
  anyway.
