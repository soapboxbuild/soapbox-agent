# Fast Parallel Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make asset onboarding snappy and visually engaging by launching doc upload+indexing, address extraction, and match-cache warming in parallel at the moment of drop, with the sustainability analysis never waiting on indexing.

**Architecture:** Three independent streams fire at drop — (A) create asset + upload docs (OM first) so indexing starts at t=0; (B) 3-page address-only extract → geocode → trimmed map; (C) match-cache warm. Audette/ESPM matching moves off every waited path (cache-only). The RSRA agent reads the OM via `read_file` (raw storage, index-independent), so the analysis starts immediately. A Demo-org override centers the map on Prosper Crossing with a 100 m footprint preload.

**Tech Stack:** platform-web (Next.js/React, maplibre-gl, `apiFetch`), soapbox-platform apps/api (Hono, Supabase JS, BullMQ `indexingQueue`, pdf-parse `PDFParse`), Supabase Postgres.

## Global Constraints
- **No live Audette/ESPM MCP fetch on any path the user waits on** (modal open, address extract, map, review). Live fetch only via the explicit background `…/refresh` POST.
- **Address step parses ≤3 pages, address-only** — no matching.
- **Indexing starts at drop; OM indexed first** (BullMQ `priority`; lower number = higher priority).
- **`read_file` is index-independent** (files-server.ts:111–119 — raw storage + on-demand PDFParse). The analysis reads the OM without waiting on `indexing_status`. Do NOT add system-prompt OM-text injection.
- **Demo override gated on Demo org `8ebc72a7-dca1-4cb1-be02-eed12f38340f`**, Prosper Crossing coords **`33.26502434078016, -96.80066966641807`**, footprint preload radius **100 m**. Non-demo: geocode + **~400 m / ~80** map fetch.
- **Orphan cleanup:** modal closed before finalize → delete the provisional asset + its docs.
- Keep existing patterns: `apiFetch(auth, path, {method, body|form})`, `run(fn, errMsg)`, `flash(type,msg)`.

---

### Task 1: API — `bulk-extract` address-only mode (≤3 pages, no matching)

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/bulk-extract.ts`
- Test: `soapbox-platform/apps/api/src/routes/__tests__/bulk-extract.address-only.test.ts` (create)

**Interfaces:**
- Produces: `POST /api/portfolios/bulk-extract?address_only=1` → `{ assets: [{ address, city, state, lat, lon }] }` with **no** `audette_match`/`espm_match` and **no** Audette/ESPM candidate fetch; server parses only the first 3 pages.

- [ ] **Step 1: Write the failing test.** Assert that with `address_only=1`, the response assets have no `audette_match`/`espm_match` keys and that the Audette candidate loader is not invoked. Mock `anthropic.messages.create` to return a fixed address JSON and spy on the Audette candidate fetch.

```ts
import { describe, it, expect, vi } from 'vitest'
// import the app/route harness used by sibling tests in this folder
describe('bulk-extract address_only', () => {
  it('skips Audette/ESPM matching and only parses first pages', async () => {
    const res = await callBulkExtract({ addressOnly: true, pdf: sampleOmPdf })
    expect(res.assets[0]).toHaveProperty('address')
    expect(res.assets[0]).not.toHaveProperty('audette_match')
    expect(audetteFetchSpy).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run it — expect FAIL** (`address_only` not handled). `cd ~/soapbox-platform/apps/api && ./node_modules/.bin/vitest run src/routes/__tests__/bulk-extract.address-only.test.ts`

- [ ] **Step 3: Implement.** In `bulk-extract.ts`: read the flag `const addressOnly = c.req.query('address_only') === '1'`. When set: (a) in the PDF parse, use `getText({ first: 3 })` instead of `{ first: 10 }`; (b) short-circuit **before** the Audette candidates block (currently ~line 363) — skip both candidate fetches and the per-asset matching loop, returning the grouped assets with only `{ name, address, city, state, lat, lon }`. Guard the matching block with `if (!addressOnly) { …existing audette/espm candidate + match code… }`.

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git add apps/api/src/routes/bulk-extract.ts apps/api/src/routes/__tests__/bulk-extract.address-only.test.ts && git commit -m "feat(onboarding): bulk-extract address_only mode — 3-page parse, no matching"`

---

### Task 2: API — `GET /audette/properties` + `/espm/properties` cache-only

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/portfolios.ts` (GET `/audette/properties` ~line 420; GET `/espm/properties`)
- Test: `soapbox-platform/apps/api/src/routes/__tests__/portfolios.properties-cache.test.ts` (create)

**Interfaces:**
- Produces: both GETs return the cached array (or `[]` when cache empty) and **never** perform a live MCP fetch. `POST …/refresh` remains the only live path (unchanged).

- [ ] **Step 1: Write failing test.** With an empty `audette_properties_cache`, `GET /audette/properties` returns `[]` and the live MCP `callTool` is not invoked (spy asserts 0 calls).

```ts
it('returns [] on cold cache without a live fetch', async () => {
  setPortfolioCache(null)
  const res = await getAudetteProperties()
  expect(res).toEqual([])
  expect(callToolSpy).not.toHaveBeenCalled()
})
```

- [ ] **Step 2: Run it — expect FAIL** (current code fetches live on empty cache).

- [ ] **Step 3: Implement.** In the GET handler, remove the "fetch live if no cache" branch: read `audette_properties_cache` (and `espm_properties_cache`) and return it or `[]`. Delete the `switch_customer_account`/`list_properties` live fallback from the GET. Leave `POST …/refresh` untouched.

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git commit -m "perf(onboarding): properties GET is cache-only — no live MCP fetch on modal open"`

---

### Task 3: API — OM-first indexing priority + read_file index-independence guard

**Files:**
- Modify: `soapbox-platform/apps/api/src/routes/files.ts` (~line 42–75)
- Test: `soapbox-platform/apps/api/src/routes/__tests__/files.priority.test.ts` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `POST /api/assets/:id/files` accepts an optional `priority` form field (`"high"`); when `"high"`, enqueues the index job with BullMQ `{ priority: 1 }` (default enqueues with no priority = lowest). Response unchanged.

- [ ] **Step 1: Write failing test.** Uploading with `priority=high` calls `indexingQueue.add('index-file', {...}, { priority: 1 })`; without it, `.add` is called with no options object (or `{}`).

```ts
it('enqueues OM index job at high priority', async () => {
  await uploadFile2({ priority: 'high', mime: 'application/pdf' })
  expect(addSpy).toHaveBeenCalledWith('index-file', expect.any(Object), { priority: 1 })
})
```

- [ ] **Step 2: Run it — expect FAIL.**

- [ ] **Step 3: Implement.** Read `const priority = (formData.get('priority') as string | null) === 'high' ? { priority: 1 } : undefined`. Change the enqueue to `await indexingQueue.add('index-file', { fileId: record.id, assetId, mimeType: file.type }, priority)`. (BullMQ accepts `undefined` opts.)

- [ ] **Step 4: Add a read_file index-independence test** in the same file: assert `read_file` on a file whose `indexing_status` is `'indexing'` (not `'indexed'`) still returns parsed text — locking the guarantee the analysis relies on. If a harness for the files MCP server is impractical, instead assert `getFileContent(storage_path)` returns bytes regardless of `indexed` (unit test against `file-storage.ts`).

- [ ] **Step 5: Run tests — expect PASS. Commit.** `git commit -m "feat(onboarding): OM-first index priority + read_file index-independence test"`

---

### Task 4: platform-web — map fetch trim + Demo Prosper Crossing override

**Files:**
- Modify: `platform-web/src/lib/asset-map.ts` (init fetch ~line 216–221; recenter ~line 302–307)
- Modify: `platform-web/src/components/app/AssetOnboardingModal.tsx` (FootprintPickerOverlay ~line 724–760: initial lat/lon + radius; pass a `demoOverride` prop from the modal which knows the org)
- Test: `platform-web/src/lib/__tests__/asset-map.params.test.ts` (create) — assert the fetch URL params.

**Interfaces:**
- Consumes: `useAssetMap(containerRef, { lat, lon, portfolioId, auth, radiusM })` — add optional `radiusM` (default 400) and `limit` (default 80).
- Produces: general map fetch uses `radius=400&limit=80`; demo override centers on the Prosper Crossing coords with `radius=100`.

- [ ] **Step 1: Write failing test.** With `radiusM: 100`, the mocked `fetch` is called with a URL containing `radius=100`; default call contains `radius=400&limit=80` (not 1500/500).

- [ ] **Step 2: Run it — expect FAIL** (hard-coded 1500/500).

- [ ] **Step 3: Implement.** In `asset-map.ts`, replace the two hard-coded `radius=1500&limit=500` with template literals using `radiusM` (default 400) and `limit` (default 80) from the hook opts; thread them through both the init and recenter fetches (and the parallel OSM fetch radius). In the modal, define the demo constant and pass it down:

```ts
// AssetOnboardingModal.tsx (module scope)
const DEMO_ORG_ID = '8ebc72a7-dca1-4cb1-be02-eed12f38340f'
const DEMO_FOOTPRINT = { lat: 33.26502434078016, lon: -96.80066966641807, radiusM: 100 }
// when in demo org, center + preload override:
const demoOverride = orgId === DEMO_ORG_ID ? DEMO_FOOTPRINT : null
```

Pass `demoOverride` into `FootprintPickerOverlay`; when set, use its `lat/lon` as the initial map center (skip geocode) and pass `radiusM: 100` to `MapFootprintPicker`→`useAssetMap`. Otherwise pass `radiusM: 400`.

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git commit -m "perf(onboarding): trim map fetch to 400m/80 + Demo Prosper Crossing 100m override"`

---

### Task 5: platform-web — parallel-from-drop: create asset early + upload docs (OM first)

**Files:**
- Modify: `platform-web/src/components/app/AssetOnboardingModal.tsx` (`handleFiles` single-mode ~line 200–235; add a provisional-asset ref + a background kickoff)
- Test: `platform-web/src/components/app/__tests__/AssetOnboardingModal.parallel.test.tsx` (extend existing onboarding test harness)

**Interfaces:**
- Consumes: address-only extract (Task 1), priority upload (Task 3), demo constants (Task 4).
- Produces: on single-mode drop, a provisional asset id in `provisionalAssetIdRef`; all docs uploaded in the background (OM with `priority=high`) before/while the map opens. Extract runs with `?address_only=1` on a 3-page-lightened PDF.

- [ ] **Step 1: Write failing test.** On drop of a single OM, assert (a) `POST /api/assets` is called before the map stage renders, (b) the OM file upload POST includes `priority=high`, (c) the extract POST URL includes `address_only=1`, (d) only 3 pages are uploaded to extract (the lightened file is smaller / `lightenFilesForDetect([pdf], 3)` was called).

- [ ] **Step 2: Run it — expect FAIL.**

- [ ] **Step 3: Implement.** Refactor `handleFiles` single branch:
  1. `setStage("extracting")`; kick off Stream A immediately (do not await before showing progress):
```ts
provisionalAssetIdRef.current = null
const createAndUpload = (async () => {
  const cres = await apiFetch(auth, "/api/assets", { method: "POST",
    body: { name: pdf.file.name.replace(/\.pdf$/i, ""), portfolio_id: portfolioId } })
  if (!cres.ok) return null
  const { id } = await cres.json() as { id: string }
  provisionalAssetIdRef.current = id
  // OM first (priority), then the rest
  const om = new FormData(); om.append("file", pdf.file); om.append("priority", "high")
  await apiFetch(auth, `/api/assets/${id}/files`, { method: "POST", form: om }).catch(() => {})
  for (const f of files.filter(x => x !== pdf)) {
    const fd = new FormData(); fd.append("file", f.file)
    await apiFetch(auth, `/api/assets/${id}/files`, { method: "POST", form: fd }).catch(() => {})
  }
  return id
})()
```
  2. Stream B (address): lighten to 3 pages and extract address-only:
```ts
const [light3] = await lightenFilesForDetect([pdf], 3) // confirm arity; else slice pages to 3
const form = new FormData(); form.append("files[]", light3)
const res = await apiFetch(auth, "/api/portfolios/bulk-extract?address_only=1", { method: "POST", form })
```
  Then geocode + `selectGeocode` (or the demo override → straight to map center) as today.
  3. Store `createAndUpload` promise in a ref so finalize can await it.
  - Verify `lightenFilesForDetect` supports a page-count arg; if it is first-page-only, add an optional `maxPages = 1` param and pass `3` here (small, local change in the same file/util).

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git commit -m "feat(onboarding): create asset + upload docs (OM first) at drop, address-only 3-page extract"`

---

### Task 6: platform-web — matching in review from warm cache (no live fetch)

**Files:**
- Modify: `platform-web/src/components/app/AssetOnboardingModal.tsx` (review stage; add client-side match against on-open candidates `audetteCandidates`/`espmCandidates`)
- Test: extend `AssetOnboardingModal.parallel.test.tsx`

**Interfaces:**
- Consumes: `audetteCandidates`/`espmCandidates` already fetched on open (state at lines ~102–144).
- Produces: `row.audette_match`/`row.espm_match` computed client-side from the warm candidates when the review stage loads; no server matching call.

- [ ] **Step 1: Write failing test.** When the review stage loads with a resolved address and `audetteCandidates` containing a name/address-adjacent property, `row.audette_match` is populated — and no `bulk-extract` (matching) or Audette live call fires during review.

- [ ] **Step 2: Run it — expect FAIL.**

- [ ] **Step 3: Implement.** Add a small pure helper `matchCandidate(row, audetteCandidates, espmCandidates)` (name similarity + lat/lon proximity, mirroring the server thresholds: name-token Jaccard with the CRE stopword list, or distance < ~2000 m for ESPM). Call it when entering `review` to set `audette_match`/`espm_match` on the row. Keep it lightweight and local.

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git commit -m "feat(onboarding): match Audette/ESPM in review from warm cache, no live fetch"`

---

### Task 7: platform-web — finalize = PATCH + orphan cleanup

**Files:**
- Modify: `platform-web/src/components/app/AssetOnboardingModal.tsx` (confirm stage ~line 571–616; `AssetCreationRunner` usage; reset effect ~line 88–94; `onClose`)
- Modify: `platform-web/src/components/app/AssetCreationRunner.tsx` (accept a `finalizeOnly` path that PATCHes an existing asset instead of create+upload) OR bypass it in single-mode
- Test: extend `AssetOnboardingModal.parallel.test.tsx`

**Interfaces:**
- Consumes: `provisionalAssetIdRef` + `createAndUpload` promise (Task 5).
- Produces: confirm PATCHes `{ ...address, footprint_geojson, audette_property_uid, espm_property_id, metadata }` onto the provisional asset (no new create/upload). On modal close before finalize, `DELETE /api/assets/:id` for the provisional asset.

- [ ] **Step 1: Write failing test.** (a) Confirm in single-mode issues a `PATCH /api/assets/:id` (not a second `POST /api/assets`) and no re-upload of docs. (b) Closing the modal at the map/review stage (provisional id set, not finalized) issues `DELETE /api/assets/:id`.

- [ ] **Step 2: Run it — expect FAIL.**

- [ ] **Step 3: Implement.**
  - Single-mode confirm: `await createAndUpload` (ensure upload done), then `PATCH /api/assets/${provisionalAssetIdRef.current}` with the review row's fields + footprint; skip `AssetCreationRunner`'s create/upload. Reuse the existing thread-creation + `?prompt=` handoff (lines 585–609) with `provisionalAssetIdRef.current`.
  - Track a `finalizedRef` set true once confirm completes.
  - In the reset effect (`open === false`) and `onClose`: if `provisionalAssetIdRef.current && !finalizedRef.current`, fire `apiFetch(auth, /api/assets/${id}, { method: "DELETE" })` (best-effort) and clear the ref.
  - Bulk-mode (multi-asset) keeps the existing `AssetCreationRunner` path unchanged.

- [ ] **Step 4: Run test — expect PASS.**

- [ ] **Step 5: Commit.** `git commit -m "feat(onboarding): finalize via PATCH + orphan cleanup on early close"`

---

### Task 8: platform-web — engaging load states + OM-first-turn priming

**Files:**
- Modify: `platform-web/src/components/app/AssetOnboardingModal.tsx` (extracting stage UI; a background "Indexing N documents…" chip; footprint fade-in already in map)
- Modify: RSRA handoff prompt (line ~609) — ensure the first turn reads the OM immediately.
- Test: none new (visual); manual + typecheck.

**Interfaces:**
- Consumes: `extractPhase`/`extractProgress` state (exists); `provisionalAssetIdRef`.
- Produces: a tight phase indicator during the 3-page scan; a subtle "Indexing N documents…" chip while docs upload/index in the background; the RSRA `?prompt=` unchanged (the agent's file-awareness + index-independent `read_file` already surface the OM — no system-prompt injection).

- [ ] **Step 1: Add the background indexing chip.** During map/review, show `Indexing {docCount} document{s}…` (from the count of docs in `files`) as a small muted chip with a subtle animated dot — reinforces prep. Remove when finalize navigates.
- [ ] **Step 2: Style the extracting stage** with a compact phase line ("Reading first pages…" → "Locating address…") using the existing `extractPhase`; add a shimmer/orange accent per Soapbox brand.
- [ ] **Step 3: Confirm the RSRA first turn reads the OM.** The RSRA prompt stays `"Run a rapid sustainability risk assessment"`. Verify (manual) the agent's first turn calls `read_file` on the OM (it appears in the file-awareness "Most recent" list and `read_file` is index-independent). No code change unless the agent skips it — if so, append to the prompt: `" — start by reading the offering memorandum on file."`
- [ ] **Step 4: Typecheck both repos.** `cd ~/platform-web && ./node_modules/.bin/tsc --noEmit` (only pre-existing `__tests__` errors allowed); `cd ~/soapbox-platform/apps/api && ./node_modules/.bin/tsc --noEmit` (clean).
- [ ] **Step 5: Commit.** `git commit -m "feat(onboarding): engaging load states + background indexing chip"`

---

## Self-Review

**Spec coverage:**
- Stream A (create early + upload + OM-first index) → Tasks 3, 5.
- Stream B (3-page address-only + geocode + trimmed map) → Tasks 1, 4, 5.
- Stream C / cache-only → Task 2.
- Matching in review from cache → Task 6.
- OM into first turn / no indexing wait → Task 3 (read_file index-independence) + Task 8 (priming). Resolved simpler than the spec's "inline context" fork because `read_file` is index-independent — noted in Global Constraints.
- Finalize PATCH + orphan cleanup → Task 7.
- Demo Prosper Crossing override → Task 4.
- Engaging load states → Task 8.
- Testing bullets → covered across task tests.

**Placeholder scan:** Two spots depend on verifying an existing helper's arity (`lightenFilesForDetect` page-count arg, Task 5) and the exact review-match thresholds (Task 6) — both instruct the implementer to confirm against the sibling code and give the fallback, not left as "TODO."

**Type consistency:** `provisionalAssetIdRef` / `createAndUpload` / `finalizedRef` used consistently across Tasks 5→7; `radiusM`/`limit` hook opts consistent across Task 4; `priority=high` form field consistent across Tasks 3, 5.

**Scope:** single cohesive feature across the two repos; ordered so API tasks (1–3) land before the client tasks (4–8) that call them.
