# Onboarding Per-Building Footprints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the onboarding map picker multi-selects 2+ existing building shapes for one asset, persist each as its own row in the already-existing `buildings` table instead of merging them into one blob on the asset.

**Architecture:** Two new pure functions (`polygonAreaM2` in `geo.ts`, `buildSelectedBuildingRows` in `asset-map.ts`) compute a per-building row list from the existing map-selection state. `useAssetMap` exposes `isMultiBuildingSelection` as the single source of truth for "would Confirm split into buildings?" `ReviewRow` gains an optional `buildings` field that both onboarding pickers populate. Every place that already creates or edits an asset — `SingleAssetFinalizer`, `AssetCreationRunner`, `AssetMapModal` — is extended to persist that array via the existing `POST /api/assets` (`buildings` array, already supported server-side) or `POST /api/assets/:assetId/buildings` (already-existing asset) endpoints. No backend changes are needed — `buildings` table + full CRUD API already exist and are already live.

**Tech Stack:** Next.js (Turbopack) App Router, React 19, TypeScript, Vitest + Testing Library, MapLibre GL.

## Global Constraints

- Repo: `/home/claude/platform-web`. Test command: `~/.bun/bin/bun run test -- <path>`. Typecheck: `~/.bun/bin/bun x tsc --noEmit -p tsconfig.json`.
- This never creates more than one Soapbox asset from one multi-select — only `buildings` rows change. Do not touch asset-count logic.
- Hand-drawn polygons (Draw mode) are unaffected — they keep merging into one `footprint_geojson` on the asset. Only building-click multi-select (`+Multi` / shift-drag) produces per-building rows.
- No fabricated data: a building with no name from Overture/OSM gets `name: null`, never an invented string.
- Follow existing code style in touched files: inline style objects, no new abstractions beyond what's specified below.

---

### Task 1: `polygonAreaM2` — pure polygon area helper

**Files:**
- Modify: `src/lib/geo.ts`
- Test: `src/lib/__tests__/geo.test.ts` (new file — no existing test file for `geo.ts`)

**Interfaces:**
- Produces: `polygonAreaM2(coords: Vec2[]): number` — approximate area in square meters of a closed polygon ring (first and last point equal), using the shoelace formula scaled by degrees-to-meters at the ring's own latitude. `Vec2` is `[number, number]`, already exported from `geo.ts`.

- [ ] **Step 1: Write the failing test**

Create `src/lib/__tests__/geo.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { polygonAreaM2 } from "@/lib/geo";

describe("polygonAreaM2", () => {
  it("returns ~0 for a degenerate (zero-area) ring", () => {
    const ring: [number, number][] = [[0, 0], [0, 0], [0, 0], [0, 0]];
    expect(polygonAreaM2(ring)).toBeCloseTo(0, 5);
  });

  it("returns a larger area for a larger ring at the same location", () => {
    // Small square: ~0.0001 degrees on a side (~11m at the equator)
    const small: [number, number][] = [[0, 0], [0.0001, 0], [0.0001, 0.0001], [0, 0.0001], [0, 0]];
    // Large square: ~0.001 degrees on a side (~111m at the equator)
    const large: [number, number][] = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]];
    expect(polygonAreaM2(large)).toBeGreaterThan(polygonAreaM2(small));
  });

  it("returns a positive area regardless of ring winding direction", () => {
    const clockwise: [number, number][] = [[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]];
    const counterClockwise: [number, number][] = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]];
    expect(polygonAreaM2(clockwise)).toBeGreaterThan(0);
    expect(polygonAreaM2(counterClockwise)).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/lib/__tests__/geo.test.ts`
Expected: FAIL — `polygonAreaM2 is not exported` / `Module has no exported member 'polygonAreaM2'`.

- [ ] **Step 3: Write minimal implementation**

In `src/lib/geo.ts`, add (near `polygonizeSegments`, which has an equivalent private `area()` helper this generalizes and exports):

```typescript
// Approximate area of a closed polygon ring in square meters (shoelace formula,
// scaled by degrees-to-meters at the ring's own latitude). Used to pick the
// "primary" building when multiple footprints are selected for one asset.
export function polygonAreaM2(coords: Vec2[]): number {
  let a = 0;
  for (let i = 0, j = coords.length - 1; i < coords.length; j = i++) {
    a += (coords[j][0] + coords[i][0]) * (coords[j][1] - coords[i][1]);
  }
  const refLat = coords[0]?.[1] ?? 0;
  const mPerDeg = 111_320;
  return Math.abs(a / 2) * mPerDeg * mPerDeg * Math.cos(refLat * Math.PI / 180);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/lib/__tests__/geo.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd /home/claude/platform-web
git add src/lib/geo.ts src/lib/__tests__/geo.test.ts
git commit -m "feat(onboarding): add polygonAreaM2 helper for picking the primary building"
```

---

### Task 2: `buildSelectedBuildingRows` — per-building row builder

**Files:**
- Modify: `src/lib/asset-map.ts`
- Test: `src/lib/__tests__/asset-map.test.ts:1-56` (existing file — add a new `describe` block)

**Interfaces:**
- Consumes: `polygonAreaM2(coords: Vec2[]): number` from Task 1 (`@/lib/geo`). `Building` type (already exported from `geo.ts`: `{ id: string; geometry_geojson: string | object; height?: number; class?: string; names?: Record<string,string>; num_floors?: number }`). `parseGeom(raw: string | object)` (already exported from `geo.ts`).
- Produces: `interface SelectedBuildingRow { overture_id: string | null; name: string | null; footprint_geojson: string; building_class: string | null; height_m: number | null; num_floors: number | null; is_primary: boolean; source: "overture" }` and `buildSelectedBuildingRows(buildings: Building[], selectedIds: string[]): SelectedBuildingRow[]` — both exported from `@/lib/asset-map`. Returns `[]` when fewer than 2 of `selectedIds` resolve to real buildings. The largest-area entry (by `polygonAreaM2`) gets `is_primary: true`; ties keep the first (lowest index) as primary. Order of the returned array matches `selectedIds` order.

- [ ] **Step 1: Write the failing test**

Add to `src/lib/__tests__/asset-map.test.ts` (after the existing `import` and mock, alongside the existing `describe("buildFootprintFromState", ...)` block):

```typescript
import { buildFootprintFromState, buildSelectedBuildingRows } from "@/lib/asset-map";

// ... (existing buildFootprintFromState describe block stays unchanged) ...

describe("buildSelectedBuildingRows", () => {
  const small = { id: "b-small", geometry_geojson: JSON.stringify({ type: "Polygon", coordinates: [[[0, 0], [0.0001, 0], [0.0001, 0.0001], [0, 0.0001], [0, 0]]] }) };
  const large = { id: "b-large", geometry_geojson: JSON.stringify({ type: "Polygon", coordinates: [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]] }), names: { primary: "Big Building" } };
  const unrelated = { id: "b-unrelated", geometry_geojson: JSON.stringify({ type: "Polygon", coordinates: [[[5, 5], [5.001, 5], [5.001, 5.001], [5, 5.001], [5, 5]]] }) };

  it("returns [] when fewer than 2 ids are selected", () => {
    expect(buildSelectedBuildingRows([small, large], [])).toEqual([]);
    expect(buildSelectedBuildingRows([small, large], ["b-small"])).toEqual([]);
  });

  it("returns [] when fewer than 2 selected ids resolve to real buildings", () => {
    expect(buildSelectedBuildingRows([small, large], ["b-small", "nonexistent"])).toEqual([]);
  });

  it("returns one row per selected building, marking the largest as primary", () => {
    const rows = buildSelectedBuildingRows([small, large, unrelated], ["b-small", "b-large"]);
    expect(rows).toHaveLength(2);
    expect(rows.find((r) => r.overture_id === "b-small")?.is_primary).toBe(false);
    expect(rows.find((r) => r.overture_id === "b-large")?.is_primary).toBe(true);
  });

  it("extracts a name from the building's names map when present, else null", () => {
    const rows = buildSelectedBuildingRows([small, large], ["b-small", "b-large"]);
    expect(rows.find((r) => r.overture_id === "b-large")?.name).toBe("Big Building");
    expect(rows.find((r) => r.overture_id === "b-small")?.name).toBeNull();
  });

  it("preserves selectedIds order in the returned array", () => {
    const rows = buildSelectedBuildingRows([small, large], ["b-large", "b-small"]);
    expect(rows.map((r) => r.overture_id)).toEqual(["b-large", "b-small"]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/lib/__tests__/asset-map.test.ts`
Expected: FAIL — `buildSelectedBuildingRows is not exported`.

- [ ] **Step 3: Write minimal implementation**

In `src/lib/asset-map.ts`, find the existing geo import (lines 4-7):

```typescript
import {
  Building, Vec2,
  parseGeom, buildingDist, pointInPolygon, polygonCentroid,
} from "@/lib/geo";
```

Replace with:

```typescript
import {
  Building, Vec2,
  parseGeom, buildingDist, pointInPolygon, polygonCentroid, polygonAreaM2,
} from "@/lib/geo";
```

Then add, near the top (after the `buildFootprintFromState` export, before `mergeWithOSM`):

```typescript
export interface SelectedBuildingRow {
  overture_id: string | null;
  name: string | null;
  footprint_geojson: string;
  building_class: string | null;
  height_m: number | null;
  num_floors: number | null;
  is_primary: boolean;
  source: "overture";
}

// Turns a multi-select of existing building shapes into one row per building,
// for persisting to the `buildings` table (one asset, N buildings) instead of
// merging every shape into the asset's own single footprint_geojson.
export function buildSelectedBuildingRows(
  buildings: Building[],
  selectedIds: string[],
): SelectedBuildingRow[] {
  const selected = selectedIds
    .map((id) => buildings.find((b) => b.id === id))
    .filter((b): b is Building => !!b);
  if (selected.length < 2) return [];

  const areas = selected.map((b) => {
    const geom = parseGeom(b.geometry_geojson);
    if (geom?.type !== "Polygon" || !Array.isArray(geom.coordinates)) return 0;
    return polygonAreaM2((geom.coordinates as Vec2[][])[0]);
  });
  const maxArea = Math.max(...areas);
  const primaryIdx = areas.indexOf(maxArea);

  return selected.map((b, i) => ({
    overture_id: b.id,
    name: Object.values(b.names ?? {})[0] ?? null,
    footprint_geojson: typeof b.geometry_geojson === "string" ? b.geometry_geojson : JSON.stringify(b.geometry_geojson),
    building_class: b.class ?? null,
    height_m: b.height ?? null,
    num_floors: b.num_floors ?? null,
    is_primary: i === primaryIdx,
    source: "overture" as const,
  }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/lib/__tests__/asset-map.test.ts`
Expected: PASS (all `buildFootprintFromState` tests + 5 new `buildSelectedBuildingRows` tests).

- [ ] **Step 5: Commit**

```bash
cd /home/claude/platform-web
git add src/lib/asset-map.ts src/lib/__tests__/asset-map.test.ts
git commit -m "feat(onboarding): add buildSelectedBuildingRows to split a multi-select into per-building rows"
```

---

### Task 3: `useAssetMap` exposes `isMultiBuildingSelection`

**Files:**
- Modify: `src/lib/asset-map.ts` (the `useAssetMap` hook and its `UseAssetMapResult` interface)
- Test: `src/lib/__tests__/asset-map.test.ts` (existing file — this is a hook-internal derived value; covered indirectly by Task 6/7's component tests, no new unit test needed here since it's a one-line boolean expression with no branching to fail)

**Interfaces:**
- Consumes: `selectedIds: Set<string>`, `drawnPolygons: Vec2[][]`, `drawPoints: Vec2[]` — all already local state in `useAssetMap`.
- Produces: adds `isMultiBuildingSelection: boolean` to `UseAssetMapResult` (the interface already returned by `useAssetMap`, consumed by `MapScreen`, `MapFootprintPicker`, and `AssetMapModal` in Tasks 6–9).

- [ ] **Step 1: Add the field to the return type**

In `src/lib/asset-map.ts`, in the `UseAssetMapResult` interface (currently ends with `clearSelection: () => void;`), add:

```typescript
  clearSelection: () => void;
  // True when 2+ existing building shapes are multi-selected with nothing
  // hand-drawn — the "Confirm" action in this state creates N buildings on
  // one asset instead of merging into one footprint. See buildSelectedBuildingRows.
  isMultiBuildingSelection: boolean;
```

- [ ] **Step 2: Compute and return it**

In the `return { ... }` object at the bottom of `useAssetMap` (right after `clearDraw,` `clearSelection,` — before the closing brace), add:

```typescript
    clearDraw,
    clearSelection,
    isMultiBuildingSelection: selectedIds.size >= 2 && drawnPolygons.length === 0 && drawPoints.length < 3,
```

- [ ] **Step 3: Typecheck**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep asset-map`
Expected: no output (no type errors in `asset-map.ts`). This will show unrelated errors in files that destructure `useAssetMap`'s return without listing `isMultiBuildingSelection` — that's fine, destructuring a subset of fields is always valid TypeScript; if it instead shows errors ABOUT `isMultiBuildingSelection` specifically, something is wrong with the interface edit in Step 1.

- [ ] **Step 4: Commit**

```bash
cd /home/claude/platform-web
git add src/lib/asset-map.ts
git commit -m "feat(onboarding): expose isMultiBuildingSelection from useAssetMap"
```

---

### Task 4: `ReviewRow.buildings` field

**Files:**
- Modify: `src/lib/bulk-ingest.ts:56-72` (the `ReviewRow` interface)

**Interfaces:**
- Consumes: `SelectedBuildingRow` from Task 2 (`@/lib/asset-map`).
- Produces: `ReviewRow.buildings?: SelectedBuildingRow[]` — consumed by Tasks 5–9.

- [ ] **Step 1: Add the field**

In `src/lib/bulk-ingest.ts`, add the import and field:

```typescript
import type { SelectedBuildingRow } from "@/lib/asset-map";
```

(add alongside the existing top-of-file imports)

In the `ReviewRow` interface, add after `footprint_geojson: string | null;`:

```typescript
  footprint_geojson: string | null;
  // Set instead of footprint_geojson when the user multi-selected 2+ existing
  // building shapes for this one asset — persisted as individual `buildings`
  // table rows rather than merged into the asset's own footprint_geojson.
  buildings?: SelectedBuildingRow[];
```

- [ ] **Step 2: Typecheck**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep bulk-ingest`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
cd /home/claude/platform-web
git add src/lib/bulk-ingest.ts
git commit -m "feat(onboarding): add optional buildings field to ReviewRow"
```

---

### Task 5: `MapScreen` populates `buildings` on multi-select

**Files:**
- Modify: `src/components/app/AssetOnboardingModal.tsx` (the `MapScreen` function, its `useAssetMap` destructure, `buildRow()`, and its Confirm button JSX)

**Interfaces:**
- Consumes: `isMultiBuildingSelection: boolean` and `buildings: Building[]` and `selectedIds: Set<string>` (all already returned by `useAssetMap`, Task 3), `buildSelectedBuildingRows(buildings, selectedIds): SelectedBuildingRow[]` (Task 2, import from `@/lib/asset-map`), `ReviewRow.buildings` (Task 4).
- Produces: `buildRow()` now returns a `ReviewRow` with `buildings` populated and `footprint_geojson: null` when `isMultiBuildingSelection` is true (consumed by Task 7's `SingleAssetFinalizer` and Task 7's `AssetCreationRunner` path).

- [ ] **Step 1: Destructure the new hook fields**

Find this line in `MapScreen` (currently):

```typescript
  const {
    buildings, selectedIds, drawMode, setDrawMode, drawPoints, drawnPolygons,
    loading, buildFootprintGeoJSON, clearDraw,
    multiSelectMode, setMultiSelectMode, recenter, noNearbyBuildings,
    radiusM: currentRadiusM, setRadiusM,
  } = useAssetMap(mapContainerRef, { lat, lon, portfolioId, auth, radiusM: demoOverride?.radiusM });
```

Replace with:

```typescript
  const {
    buildings, selectedIds, drawMode, setDrawMode, drawPoints, drawnPolygons,
    loading, buildFootprintGeoJSON, clearDraw,
    multiSelectMode, setMultiSelectMode, recenter, noNearbyBuildings,
    radiusM: currentRadiusM, setRadiusM, isMultiBuildingSelection,
  } = useAssetMap(mapContainerRef, { lat, lon, portfolioId, auth, radiusM: demoOverride?.radiusM });
```

- [ ] **Step 2: Add the import**

At the top of `AssetOnboardingModal.tsx`, find the existing import of `asset-map` exports (used by both `MapFootprintPicker` and `MapScreen` already — search for `from "@/lib/asset-map"`) and add `buildSelectedBuildingRows` to it. If `asset-map` is currently imported only inside the file via `useAssetMap` from `@/lib/asset-map`, change that import line to:

```typescript
import { useAssetMap, buildSelectedBuildingRows } from "@/lib/asset-map";
```

- [ ] **Step 3: Populate `buildings` in `buildRow()`**

Find `buildRow()` in `MapScreen` (currently ending with):

```typescript
    return {
      name: assetName,
      address: street, city, state, lat: centerLat, lon: centerLon,
      building_class: "unknown",
      audette_match: null, espm_match: null,
      footprint_geojson: buildFootprintGeoJSON(),
      docs: singleFiles,
      skip: false,
      audette_action: null,
      espm_action: null,
    };
```

Replace with:

```typescript
    const splitBuildings = isMultiBuildingSelection
      ? buildSelectedBuildingRows(buildings, [...selectedIds])
      : [];
    return {
      name: assetName,
      address: street, city, state, lat: centerLat, lon: centerLon,
      building_class: "unknown",
      audette_match: null, espm_match: null,
      footprint_geojson: splitBuildings.length > 0 ? null : buildFootprintGeoJSON(),
      buildings: splitBuildings.length > 0 ? splitBuildings : undefined,
      docs: singleFiles,
      skip: false,
      audette_action: null,
      espm_action: null,
    };
```

- [ ] **Step 4: Update the Confirm button label**

Find (in `MapScreen`'s toolbar JSX):

```typescript
        <button onClick={() => onConfirm(buildRow())} style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: "pointer", background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}>
          {hasFootprint ? "Confirm footprint →" : "Skip footprint →"}
        </button>
```

Replace with:

```typescript
        <button onClick={() => onConfirm(buildRow())} style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: "pointer", background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}>
          {isMultiBuildingSelection ? `Confirm ${selectedIds.size} buildings →` : hasFootprint ? "Confirm footprint →" : "Skip footprint →"}
        </button>
```

This task has no dedicated test file of its own — `buildRow()`'s `buildings` output is exercised end-to-end by Task 7's `SingleAssetFinalizer` test (which drives a fixture row with `buildings` set through the real Confirm → Create POST-body assertion) and Task 8's `AssetCreationRunner` test. Writing a standalone test here would just re-mock the same component with no new assertion available yet.

- [ ] **Step 5: Typecheck**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep AssetOnboardingModal`
Expected: no output.

- [ ] **Step 6: Commit**

```bash
cd /home/claude/platform-web
git add src/components/app/AssetOnboardingModal.tsx
git commit -m "feat(onboarding): MapScreen populates ReviewRow.buildings on multi-select"
```

---

### Task 6: `MapFootprintPicker` / `FootprintPickerOverlay` populate `buildings`

**Files:**
- Modify: `src/components/app/AssetOnboardingModal.tsx` (the `MapFootprintPicker` function's `useAssetMap` destructure and Confirm button; the `FootprintPickerOverlay`'s `onConfirm` prop type and its two callers: `advanceFootprintQueue` and the single-row `onRequestFootprint` path)

**Interfaces:**
- Consumes: same `isMultiBuildingSelection`, `buildSelectedBuildingRows` as Task 5.
- Produces: `FootprintPickerOverlay`'s `onConfirm` callback now receives `(geojson: string | null, buildings?: SelectedBuildingRow[])` instead of just `(geojson: string | null)` — consumed by `advanceFootprintQueue` (updated in this task).

- [ ] **Step 1: Destructure `isMultiBuildingSelection` in `MapFootprintPicker`**

Find:

```typescript
  const { selectedIds, drawMode, setDrawMode, multiSelectMode, setMultiSelectMode, drawPoints, drawnPolygons, loading, noNearbyBuildings, buildFootprintGeoJSON, clearDraw, clearSelection, recenter, radiusM: currentRadiusM, setRadiusM } = useAssetMap(containerRef, { lat, lon, portfolioId, auth, radiusM });
```

Replace with:

```typescript
  const { buildings, selectedIds, drawMode, setDrawMode, multiSelectMode, setMultiSelectMode, drawPoints, drawnPolygons, loading, noNearbyBuildings, buildFootprintGeoJSON, clearDraw, clearSelection, recenter, radiusM: currentRadiusM, setRadiusM, isMultiBuildingSelection } = useAssetMap(containerRef, { lat, lon, portfolioId, auth, radiusM });
```

- [ ] **Step 2: Update the `onConfirm` prop type**

Find, in the `MapFootprintPicker` props type:

```typescript
  onConfirm: (geojson: string | null) => void;
```

Replace with:

```typescript
  onConfirm: (geojson: string | null, buildings?: SelectedBuildingRow[]) => void;
```

Add `SelectedBuildingRow` to the existing `import { useAssetMap, buildSelectedBuildingRows } from "@/lib/asset-map";` (from Task 5, Step 2) as a type import: change to

```typescript
import { useAssetMap, buildSelectedBuildingRows, type SelectedBuildingRow } from "@/lib/asset-map";
```

- [ ] **Step 3: Update the Confirm button's click handler and label**

Find:

```typescript
          {hasFootprint
            ? <button onClick={() => { onConfirm(buildFootprintGeoJSON()); if (isLast) onDone(); }} style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: "pointer", background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}>
                {isLast ? "Done — review & create →" : "Confirm →"}
              </button>
```

Replace with:

```typescript
          {hasFootprint
            ? <button onClick={() => {
                const splitBuildings = isMultiBuildingSelection ? buildSelectedBuildingRows(buildings, [...selectedIds]) : [];
                onConfirm(splitBuildings.length > 0 ? null : buildFootprintGeoJSON(), splitBuildings.length > 0 ? splitBuildings : undefined);
                if (isLast) onDone();
              }} style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: "pointer", background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}>
                {isMultiBuildingSelection ? `Confirm ${selectedIds.size} buildings →` : isLast ? "Done — review & create →" : "Confirm →"}
              </button>
```

- [ ] **Step 4: Update `FootprintPickerOverlay`'s `onConfirm` prop type**

Find, in `FootprintPickerOverlay`'s props type:

```typescript
  onConfirm: (geojson: string | null) => void;
```

Replace with:

```typescript
  onConfirm: (geojson: string | null, buildings?: SelectedBuildingRow[]) => void;
```

And its pass-through to `MapFootprintPicker` — find:

```typescript
      onConfirm={onConfirm} onSkip={onSkip} onDone={onDone}
```

This line already forwards the (now-updated-signature) `onConfirm` unchanged — no edit needed here, TypeScript will verify the signatures match.

- [ ] **Step 5: Update `advanceFootprintQueue` to consume the second argument**

Find, in `AssetOnboardingModal` (the top-level component):

```typescript
  function advanceFootprintQueue(geojson: string | null) {
    if (geojson) {
      const currentRow = fpQueue[fpQueueIdx];
      setRows((prev) => {
        const rowIdx = prev.findIndex((r) => r === currentRow || (r.name === currentRow.name && r.address === currentRow.address && r.lat === currentRow.lat));
        if (rowIdx === -1) return prev;
        return prev.map((r, i) => i === rowIdx ? { ...r, footprint_geojson: geojson } : r);
      });
    }
    const next = fpQueueIdx + 1;
    if (next < fpQueue.length) { setFpQueueIdx(next); }
    else { setFpQueue([]); setStage("review"); }
  }
```

Replace with:

```typescript
  function advanceFootprintQueue(geojson: string | null, splitBuildings?: SelectedBuildingRow[]) {
    if (geojson || splitBuildings?.length) {
      const currentRow = fpQueue[fpQueueIdx];
      setRows((prev) => {
        const rowIdx = prev.findIndex((r) => r === currentRow || (r.name === currentRow.name && r.address === currentRow.address && r.lat === currentRow.lat));
        if (rowIdx === -1) return prev;
        return prev.map((r, i) => i === rowIdx ? { ...r, footprint_geojson: geojson, buildings: splitBuildings } : r);
      });
    }
    const next = fpQueueIdx + 1;
    if (next < fpQueue.length) { setFpQueueIdx(next); }
    else { setFpQueue([]); setStage("review"); }
  }
```

Add the `SelectedBuildingRow` type import at the top of `AssetOnboardingModal.tsx` if not already present from Task 5/6's earlier edits (it is — Step 2 of this task already added it as a named type import; it's file-scoped, available here too).

- [ ] **Step 6: Typecheck**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep AssetOnboardingModal`
Expected: no output.

- [ ] **Step 7: Run existing onboarding tests to confirm no regression**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetOnboardingModal.test.tsx`
Expected: PASS (same pass count as before this task — this task only widens optional parameters, it doesn't change behavior when `buildings` is absent).

- [ ] **Step 8: Commit**

```bash
cd /home/claude/platform-web
git add src/components/app/AssetOnboardingModal.tsx
git commit -m "feat(onboarding): MapFootprintPicker/advanceFootprintQueue populate buildings on multi-select"
```

---

### Task 7: `SingleAssetFinalizer` persists `buildings`

**Files:**
- Modify: `src/components/app/AssetOnboardingModal.tsx` (the `SingleAssetFinalizer` function's `finalize()`)
- Test: `src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx` (existing file — add one test)

**Interfaces:**
- Consumes: `row.buildings?: SelectedBuildingRow[]` (Task 4/5/6), `apiFetch(auth, url, opts)` (already imported in this file from `@/lib/api-client`).
- Produces: after a successful asset create/PATCH, one `POST /api/assets/:id/buildings` call per entry in `row.buildings` (endpoint already exists — `apps/api/src/routes/buildings.ts`, no backend change needed).

- [ ] **Step 1: Write the failing test**

In `src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx`, find the existing test `"(d) confirm issues a PATCH (not a second POST /api/assets) and no re-upload"` (around line 181) for the exact pattern of driving this component to the Create stage with a pre-set `provisionalAssetIdRef`. Add a new test right after it, in the same `describe` block:

```typescript
  it("(d2) confirming a multi-building selection POSTs one /buildings row per building, no merged footprint PATCH", async () => {
    const splitBuildings = [
      { overture_id: "b1", name: "Building 1", footprint_geojson: '{"type":"Polygon","coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}', building_class: null, height_m: null, num_floors: null, is_primary: true, source: "overture" as const },
      { overture_id: "b2", name: "Building 2", footprint_geojson: '{"type":"Polygon","coordinates":[[[2,2],[3,2],[3,3],[2,2]]]}', building_class: null, height_m: null, num_floors: null, is_primary: false, source: "overture" as const },
    ];
    mockApiFetch.mockImplementation((_auth, url: string) => {
      if (url.includes("/buildings")) return Promise.resolve({ ok: true, json: async () => ({ id: "row-id" }) } as Response);
      return Promise.resolve({ ok: true, json: async () => ({ id: "asset-1", name: "Cinnamon Run" }) } as Response);
    });

    const provisionalAssetIdRef = { current: "asset-1" };
    const createAndUploadRef = { current: null };
    const finalizedRef = { current: false };
    const row = {
      name: "Cinnamon Run", address: "14120 Weeping Willow Dr", city: "Silver Spring", state: "MD",
      lat: 39.088, lon: -77.067, building_class: "unknown",
      audette_match: null, espm_match: null, footprint_geojson: null, buildings: splitBuildings,
      docs: [], skip: false, audette_action: null, espm_action: null,
    };

    render(
      <SingleAssetFinalizer
        row={row} auth={AUTH_NONDEMO}
        provisionalAssetIdRef={provisionalAssetIdRef}
        createAndUploadRef={createAndUploadRef}
        finalizedRef={finalizedRef}
        onAssetCreated={() => {}}
        onDone={() => {}}
      />
    );

    await waitFor(() => {
      const buildingsCalls = mockApiFetch.mock.calls.filter(([, url]: [unknown, string]) => url.includes("/buildings"));
      expect(buildingsCalls).toHaveLength(2);
    });

    const patchCalls = mockApiFetch.mock.calls.filter(([, url, opts]: [unknown, string, { method?: string }]) => url === "/api/assets/asset-1" && opts?.method === "PATCH");
    expect(patchCalls).toHaveLength(1);
    expect(patchCalls[0][2].body.footprint_geojson).toBeNull();
  });
```

`SingleAssetFinalizer` is not currently exported (`AssetOnboardingModal.tsx:962` reads `function SingleAssetFinalizer({`, not `export function`) and the test file's existing import (`AssetOnboardingModal.parallel.test.tsx:4`, currently `import { AssetOnboardingModal, matchCandidate } from "../AssetOnboardingModal";`) doesn't include it. Make both changes as part of this step:
- In `AssetOnboardingModal.tsx:962`, change `function SingleAssetFinalizer({` to `export function SingleAssetFinalizer({`.
- In `AssetOnboardingModal.parallel.test.tsx:4`, change the import to `import { AssetOnboardingModal, matchCandidate, SingleAssetFinalizer } from "../AssetOnboardingModal";`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx -t "d2"`
Expected: FAIL — 0 `/buildings` calls recorded (current code never calls that endpoint).

- [ ] **Step 3: Write minimal implementation**

Find, in `SingleAssetFinalizer`'s `finalize()`:

```typescript
    if (id) {
      // Provisional asset + docs already exist — PATCH the reviewed fields.
      const patch: Record<string, unknown> = {
        name: row.name,
        address: row.address || null,
        city: row.city || null,
        state: row.state || null,
        footprint_geojson: row.footprint_geojson ?? null,
        metadata: { setup_complete: false, ingestion_source: "asset-onboarding" },
      };
      if (row.audette_action === "link" && row.audette_match) patch.audette_property_id = row.audette_match.property_uid;
      if (row.espm_action === "link" && row.espm_match) patch.espm_property_id = row.espm_match.property_id;
      const res = await apiFetch(auth, `/api/assets/${id}`, { method: "PATCH", body: patch });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return id;
    }
```

Replace with:

```typescript
    if (id) {
      // Provisional asset + docs already exist — PATCH the reviewed fields.
      const patch: Record<string, unknown> = {
        name: row.name,
        address: row.address || null,
        city: row.city || null,
        state: row.state || null,
        footprint_geojson: row.footprint_geojson ?? null,
        metadata: { setup_complete: false, ingestion_source: "asset-onboarding" },
      };
      if (row.audette_action === "link" && row.audette_match) patch.audette_property_id = row.audette_match.property_uid;
      if (row.espm_action === "link" && row.espm_match) patch.espm_property_id = row.espm_match.property_id;
      const res = await apiFetch(auth, `/api/assets/${id}`, { method: "PATCH", body: patch });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // A multi-building selection isn't representable by PATCH's single
      // footprint_geojson field — persist each building as its own row via
      // the buildings sub-resource endpoint instead. Deliberately not
      // .catch()-swallowed: a failed insert here should surface as an error
      // (this component's useEffect already turns a thrown finalize() into
      // the "Something went wrong" state) rather than silently produce an
      // asset with fewer buildings than the user actually selected.
      for (const building of row.buildings ?? []) {
        const bRes = await apiFetch(auth, `/api/assets/${id}/buildings`, { method: "POST", body: building });
        if (!bRes.ok) throw new Error(`HTTP ${bRes.status} creating building ${building.overture_id}`);
      }
      return id;
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx -t "d2"`
Expected: PASS.

- [ ] **Step 5: Run the full parallel test file to confirm no regression**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx`
Expected: same pass/fail counts as the pre-existing baseline (7 pre-existing failures unrelated to this change, confirmed via `git stash` earlier this session — do not try to fix those; they're a separate `vi.mocked`/test-infra issue) plus this task's new passing test.

- [ ] **Step 6: Commit**

```bash
cd /home/claude/platform-web
git add src/components/app/AssetOnboardingModal.tsx src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx
git commit -m "feat(onboarding): SingleAssetFinalizer persists row.buildings via /buildings endpoint"
```

---

### Task 8: `AssetCreationRunner` passes `buildings` through the existing POST

**Files:**
- Modify: `src/components/app/AssetCreationRunner.tsx:45-56`
- Test: `src/components/app/__tests__/AssetCreationRunner.test.tsx` (existing file — add one test)

**Interfaces:**
- Consumes: `row.buildings?: SelectedBuildingRow[]` (Task 4).
- Produces: the existing `POST /api/assets` call (already accepts `buildings` server-side — see `apps/api/src/routes/assets.ts:55-89`, no backend change) now sends `row.buildings` instead of always `[]`.

- [ ] **Step 1: Write the failing test**

`src/components/app/__tests__/AssetCreationRunner.test.tsx` mocks `@/lib/api-client` module-wide (`vi.mock("@/lib/api-client", () => ({ apiFetch: vi.fn() }))`), asserts via `vi.mocked(apiFetch)`, and drives the component by clicking its "Create 1 asset" button (it does not auto-start). It also already has a `makeRow(name, skip = false): ReviewRow` fixture helper (lines 8-12) — extend it with an optional `buildings` param rather than inlining a new row object. Change:

```typescript
const makeRow = (name: string, skip = false): ReviewRow => ({
  name, address: "123 Main", city: "Austin", state: "TX",
  lat: 30, lon: -97, building_class: "residential",
  audette_match: null, espm_match: null, footprint_geojson: null, docs: [], skip,
});
```

to:

```typescript
const makeRow = (name: string, skip = false, buildings?: ReviewRow["buildings"]): ReviewRow => ({
  name, address: "123 Main", city: "Austin", state: "TX",
  lat: 30, lon: -97, building_class: "residential",
  audette_match: null, espm_match: null, footprint_geojson: null, docs: [], skip,
  buildings,
});
```

Then add this test inside the existing `describe("AssetCreationRunner", ...)` block:

```typescript
  it("passes row.buildings through to the POST /api/assets body when present", async () => {
    const splitBuildings: ReviewRow["buildings"] = [
      { overture_id: "b1", name: "Building 1", footprint_geojson: "{}", building_class: null, height_m: null, num_floors: null, is_primary: true, source: "overture" },
      { overture_id: "b2", name: "Building 2", footprint_geojson: "{}", building_class: null, height_m: null, num_floors: null, is_primary: false, source: "overture" },
    ];
    render(<AssetCreationRunner rows={[makeRow("Cinnamon Run", false, splitBuildings)]} auth={AUTH} onAssetCreated={vi.fn()} onDone={vi.fn()} />);
    fireEvent.click(screen.getByText(/Create 1 asset/));
    await waitFor(() => expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(1));
    const [, , opts] = vi.mocked(apiFetch).mock.calls[0];
    expect((opts as { body: { buildings: unknown } }).body.buildings).toEqual(splitBuildings);
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetCreationRunner.test.tsx`
Expected: FAIL — `postCalls[0][2].body.buildings` is `[]`, not the fixture array (current code hardcodes `buildings: []`).

- [ ] **Step 3: Write minimal implementation**

In `src/components/app/AssetCreationRunner.tsx`, find:

```typescript
        const res = await apiFetch(auth, "/api/assets", {
          method: "POST",
          body: {
            name: row.name,
            address: row.address || null,
            city: row.city || null,
            state: row.state || null,
            buildings: [],
            footprint_geojson: row.footprint_geojson ?? null,
            lat: row.lat ?? null, lon: row.lon ?? null,
          },
        });
```

Replace with:

```typescript
        const res = await apiFetch(auth, "/api/assets", {
          method: "POST",
          body: {
            name: row.name,
            address: row.address || null,
            city: row.city || null,
            state: row.state || null,
            buildings: row.buildings ?? [],
            footprint_geojson: row.footprint_geojson ?? null,
            lat: row.lat ?? null, lon: row.lon ?? null,
          },
        });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun run test -- src/components/app/__tests__/AssetCreationRunner.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/claude/platform-web
git add src/components/app/AssetCreationRunner.tsx src/components/app/__tests__/AssetCreationRunner.test.tsx
git commit -m "feat(onboarding): AssetCreationRunner passes row.buildings to POST /api/assets"
```

---

### Task 9: `AssetMapModal` (settings-page footprint editor) persists `buildings`

**Files:**
- Modify: `src/components/app/AssetMapModal.tsx`

**Interfaces:**
- Consumes: `isMultiBuildingSelection`, `buildings`, `selectedIds` from `useAssetMap` (Task 3), `buildSelectedBuildingRows` (Task 2).
- Produces: `handleSave` persists per-building rows via `POST /api/assets/:assetId/buildings` when the settings-page redraw is a multi-building selection, instead of always PATCHing a merged `footprint_geojson`.

- [ ] **Step 1: Destructure the new hook fields**

Find:

```typescript
  const { selectedIds, drawMode, setDrawMode, multiSelectMode, setMultiSelectMode, drawnPolygons, drawPoints, loading, noNearbyBuildings, buildFootprintGeoJSON, clearDraw, clearSelection, recenter } =
    useAssetMap(containerRef, { lat, lon, portfolioId, auth });
```

Replace with:

```typescript
  const { buildings, selectedIds, drawMode, setDrawMode, multiSelectMode, setMultiSelectMode, drawnPolygons, drawPoints, loading, noNearbyBuildings, buildFootprintGeoJSON, clearDraw, clearSelection, recenter, isMultiBuildingSelection } =
    useAssetMap(containerRef, { lat, lon, portfolioId, auth });
```

- [ ] **Step 2: Add the import**

At the top of `AssetMapModal.tsx`, find:

```typescript
import { useAssetMap } from "@/lib/asset-map";
```

Replace with:

```typescript
import { useAssetMap, buildSelectedBuildingRows } from "@/lib/asset-map";
```

- [ ] **Step 3: Update `handleSave` to persist buildings when multi-selected**

Find:

```typescript
  async function handleSave(geojson: string) {
    setSaving(true); setError(null);
    try {
      const res = await apiFetch(auth, `/api/assets/${assetId}`, { method: "PATCH", body: { footprint_geojson: geojson } });
      if (!res.ok) throw new Error("Failed to save");
      onDone(geojson);
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed"); setSaving(false); }
  }
```

Replace with:

```typescript
  async function handleSave(geojson: string) {
    setSaving(true); setError(null);
    try {
      const splitBuildings = isMultiBuildingSelection ? buildSelectedBuildingRows(buildings, [...selectedIds]) : [];
      if (splitBuildings.length > 0) {
        for (const building of splitBuildings) {
          await apiFetch(auth, `/api/assets/${assetId}/buildings`, { method: "POST", body: building });
        }
      } else {
        const res = await apiFetch(auth, `/api/assets/${assetId}`, { method: "PATCH", body: { footprint_geojson: geojson } });
        if (!res.ok) throw new Error("Failed to save");
      }
      onDone(geojson);
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed"); setSaving(false); }
  }
```

- [ ] **Step 4: Update the save button's label to match** (this modal doesn't currently have per-building label text; find the button that calls `handleSave` — around line 49, `onClick={() => { const g = buildFootprintGeoJSON(); if (g) onSave(g); }}` — note `onSave` is the prop name here, which is `handleSave` from `SettingsView.tsx`'s perspective; no rename needed, just add a label branch):

Find:

```typescript
          <button
            onClick={() => { const g = buildFootprintGeoJSON(); if (g) onSave(g); }}
            disabled={!hasFootprint || saving}
            style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: hasFootprint ? "pointer" : "default", background: hasFootprint ? "var(--primary)" : "var(--muted)", color: hasFootprint ? "var(--primary-foreground)" : "var(--muted-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}
          >
            {saving ? "Saving…" : "Confirm"}
          </button>
```

Replace with:

```typescript
          <button
            onClick={() => { const g = buildFootprintGeoJSON(); if (g) onSave(g); }}
            disabled={!hasFootprint || saving}
            style={{ padding: "5px 14px", borderRadius: "var(--radius-md)", border: "none", cursor: hasFootprint ? "pointer" : "default", background: hasFootprint ? "var(--primary)" : "var(--muted)", color: hasFootprint ? "var(--primary-foreground)" : "var(--muted-foreground)", fontSize: "var(--text-xs)", fontWeight: 600 }}
          >
            {saving ? "Saving…" : isMultiBuildingSelection ? `Confirm ${selectedIds.size} buildings` : "Confirm"}
          </button>
```

- [ ] **Step 5: Typecheck**

Run: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep AssetMapModal`
Expected: no output.

- [ ] **Step 6: Manual verification (per the `verify` skill — this component has no existing test file)**

Start the dev server (`~/.bun/bin/bun run dev`), log in as the `claude@agents.soapbox.build` service account (credentials in Vaultwarden per this session's earlier work), open an existing asset's Settings page, click "Redraw" footprint, multi-select 2+ buildings, click Confirm, and verify via `GET /api/assets/:id/buildings` (curl with the Supabase service-role key, as done earlier this session) that N rows now exist for that asset.

- [ ] **Step 7: Commit**

```bash
cd /home/claude/platform-web
git add src/components/app/AssetMapModal.tsx
git commit -m "feat(onboarding): AssetMapModal persists multi-building selections via /buildings endpoint"
```

---

## Final verification (all tasks complete)

- [ ] Run the full test suite: `cd /home/claude/platform-web && ~/.bun/bin/bun run test 2>&1 | tail -30` — confirm no new failures beyond the pre-existing 7 (documented in this session as unrelated `vi.mocked` test-infra issues, verified via `git stash` to exist on `main` before any of this work).
- [ ] Run the full typecheck: `cd /home/claude/platform-web && ~/.bun/bin/bun x tsc --noEmit -p tsconfig.json 2>&1 | grep -E "asset-map\.ts|AssetOnboardingModal\.tsx|AssetMapModal\.tsx|AssetCreationRunner\.tsx|bulk-ingest\.ts|geo\.ts"` — expect no output.
- [ ] Manually drive the full single-address onboarding flow (per the `verify` skill) against a real multi-building address, and confirm via `GET /api/assets/:id/buildings` that it returns one row per selected building, with exactly one `is_primary: true`.
- [ ] Push to `main` only after explicit user confirmation (this repo auto-deploys to production on push, per this session's established norm).
