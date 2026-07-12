# Fast, Parallel Asset Onboarding — Design

**Date:** 2026-07-12
**Owner:** Christopher
**Repos:** `platform-web` (AssetOnboardingModal, asset-map hook, chat handoff), `soapbox-platform` apps/api (bulk-extract, files/indexing, assets).

**Problem:** A recent change (Audette/ESPM matching + Overture footprint preload) made onboarding "very very slow." The perceived drag is the **extract/review wait**, and the sustainability analysis then waits again on document indexing. Goal: make onboarding snappy and visually engaging, and make the rapid sustainability analysis start effectively instantly.

## Root cause (diagnosed)
- **Live Audette fetch on waited paths.** `GET /audette/properties` fetches live when the cache is cold (portfolios.ts:420); `bulk-extract` *also* does its own live Audette fetch mid-extraction (bulk-extract.ts:398). Matching was placed on the address-extraction critical path.
- **Whole-doc parse for the address.** Single-mode uploads the entire OM PDF; the address only needs the first ~3 pages.
- **Indexing starts last.** Docs upload + index only at the final "confirm" step (AssetCreationRunner), so the analysis waits on indexing that could have started at drop.
- **Map over-fetch.** asset-map hook requests `radius=1500&limit=500` (vs route defaults 200/50).

## Principle
Everything that can run independently launches **at the moment of drop (t=0)**. The map gates only the *UI*; indexing gates only the *analysis*; both start at zero. Nothing the user waits on does a live Audette/ESPM fetch.

## Architecture — three parallel streams from drop

### Stream A — asset + docs + indexing (the analysis long-pole)
1. On drop, immediately `POST /api/assets` with a **placeholder** (name from filename, address null) → asset id.
2. Immediately upload **all** docs (`POST /assets/:id/files`); upload auto-enqueues indexing (`indexing_status → indexing`).
3. **OM-first indexing:** the primary OM is enqueued/prioritized ahead of utility CSVs / appendices so analysis-readiness isn't gated on the whole set. (Add a priority hint to the file-upload/index enqueue path; OM identified as the largest PDF / the single-mode source doc.)

### Stream B — address → geocode → map (the UI gate)
1. Client lightens the OM to its **first 3 pages** and calls extract in **address-only mode** (`?address_only=1`): server parses ≤3 pages, returns `{ address, lat, lon }`, and **skips all Audette/ESPM matching**. ~1–2s.
2. Geocode → center map. Map fetch trimmed to **~400 m / ~80 buildings**, progressive render, auto-highlight the building containing/nearest the point.
3. Address PATCHed onto the asset created in Stream A when it resolves.

### Stream C — match cache warm (already on open)
- The on-open refresh warms `audette_properties_cache` / `espm_properties_cache`. Change `GET /audette/properties` (and ESPM) to return **cache-or-empty instantly — never a live fetch**; the background `…/refresh` POST is the only live path.

## Matching — step 2 (review, post-map), cache-only
- Audette/ESPM matching runs in the **review** stage, against the **warm cache only**. `bulk-extract` in address-only mode does no matching; a separate lightweight match (client-side against the on-open candidates, or a cache-only server match endpoint) produces `audette_match`/`espm_match` for the review UI. No path the user waits on ever triggers a live MCP fetch.

## OM text straight into the first analysis turn (no indexing wait)
- The analysis must not block on RAG indexing. Server extracts the OM's full text once (pdf-parse, already available) and the first analysis turn receives it as **inline context** (attached to the conversation's initial message / passed alongside the `?prompt=`), so the agent has the OM immediately.
- Full RAG indexing still completes in the background for deeper follow-up retrieval; the first turn simply does not wait for it.
- Mechanism: on finalize, stash the OM text (e.g. on the conversation's seed context or a first system/context message) so `ChatView`'s auto-send first turn carries it. The plan pins the exact hook (conversation seed vs. injected context message).

## Finalize
- "Confirm" becomes a **PATCH** of footprint geojson + chosen matches onto the already-created asset (no create/upload here — that happened at drop).
- **Orphan cleanup:** if the modal closes before finalize, delete the provisional asset (and its uploaded docs). Clean, no drafts.

## Demo-only override (Prosper Crossing)
- Gated on the **Demo org** (`8ebc72a7-dca1-4cb1-be02-eed12f38340f`), scoped to the Prosper Crossing RSRA asset: **skip geocode**, center the map on **`33.26502434078016, -96.80066966641807`**, and preload footprints within a tight **100 m** radius. Snappy, focused, deterministic for the live demo.
- Non-demo orgs use the general Stream B geocode + ~400 m map.

## Visually engaging
- Fast 3-page address scan with a tight phase indicator.
- Map appears quickly (trimmed fetch), footprints fade in progressively, matched building highlighted (Claude-design orange accent / subtle motion).
- A background **"Indexing N documents…"** chip shows prep happening while the user picks footprints — reinforces that the analysis is being made ready.

## Out of scope
- Full SSE streaming extract endpoint (rejected in favor of the parallel-from-drop approach).
- Bulk (multi-building) flow changes beyond what falls out of the shared extract/matching refactor.
- Changing the RSRA skill itself.

## Testing
- Address-only extract returns `{address,lat,lon}` from a 3-page OM with no Audette/ESPM fetch (assert no live MCP call).
- `GET /audette/properties` cold cache returns instantly (empty) — no live fetch.
- Cold-cache onboarding: no live Audette fetch on any awaited path; docs indexing begins before the map renders.
- Demo org onboarding centers on the Prosper Crossing coords with a 100 m footprint preload.
- First analysis turn contains the OM text even when `indexing_status != indexed`.
- Modal closed at map/review deletes the provisional asset + docs.
