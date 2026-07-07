---
name: portfolio-ingest
description: >
  Onboard a client portfolio into app.soapbox.build end-to-end: create the org +
  portfolio, bulk-create assets from a register or helper-data drop, link Audette
  (including grouping ungrouped buildings into properties) and ESPM, and upload +
  index all source documents (PCAs, audits, surveys, reference data). Headless,
  agent-driven counterpart to the frontend "Add assets" wizard — use it for zip/
  Taildrop batch drops, new-client onboarding, or any run too big or too scripted
  for the UI. Spec 1 of 2 — portfolio-analysis (Spec 2) runs after this.
  Triggers on: "onboard [client]", "create a soapbox account for", "portfolio
  onboarding workflow", "ingest the [client] portfolio", "run portfolio ingestion",
  "set up [client] in soapbox", a batch/zip of PCAs+audits with an asset register.
version: 1.0.1
---

# Portfolio Ingest

Proven end-to-end on **Cortland Batch 1 (2026-07-02)**: 1 org, 10 assets, 10 Audette
links (5 required property grouping), 9/10 ESPM links, 30/30 documents indexed
(7,406 chunks). Follow the stages in order — ordering constraints are real.

## Relationship to the frontend onboarding wizard

The platform UI has an interactive flow (`AssetOnboardingModal` → `AssetReviewTable`
→ `AssetCreationRunner` in platform-web) that does drag-drop → LLM extraction →
geocode/footprint → fuzzy-match review → create+link+upload. **This skill and the
wizard call the same soapbox-api endpoints and must stay convention-compatible:**

- Same endpoints: `POST /api/assets`, `PATCH /api/assets/:id`,
  `GET/POST /api/portfolios/audette|espm/properties[/refresh]`,
  `POST /api/assets/:id/files`, `POST /api/portfolios/files`.
- Same auto-match threshold: **≥ 0.85** auto-link, 0.40–0.85 review, < 0.40 no match.
- Same metadata convention: `metadata.setup_complete: false` +
  `metadata.ingestion_source` — the wizard writes `"asset-onboarding"`, this skill
  writes `"portfolio-onboarding"`. Both are recognized downstream; keep the
  distinction so runs are attributable.
- Division of labor: the wizard assumes the org/portfolio already exist and works
  asset-by-asset with a human reviewing matches. This skill additionally creates the
  org/portfolio/members, does Audette **property grouping** (the wizard can only
  link or open a "Create in Audette" thread), handles portfolio-level reference
  files, splits oversized PDFs, retries failed indexing, and enriches asset
  metadata from helper data. If the user is present and wants to eyeball matches,
  you can stop after Stage 2 and hand them to the UI ("Add assets") instead.
- Footprint mapping ("📍 Map" chip — Overture footprint queue) is the wizard's specialty; skip
  it here unless asked.
- **BUT backfill the postal-address fields (`street_address, city, state_province, postal_zip_code,
  country`) when you link Audette.** Audette's building model (`get_building_model_details`) carries
  the full address for every property, and you are already pulling that model to link the asset —
  copy the address into those columns in the same asset-update call. Do NOT leave them null (the
  Greystar ingest did: 37/39 had lat/lon from geocoding but 0/39 had street/city/state, so every
  downstream run — BPS applicability, CRREM region, RUBS/VNM legislation, physrisk, brave lookups —
  had to re-pull addresses from Audette). `state_province` especially gates the jurisdiction checks.
  If Audette is unavailable, reverse-geocode from lat/lon (Overture) as a fallback and label `(est.)`.

## Prerequisites

- Service account: Vaultwarden item `Soapbox Service Account
  (claude@agents.soapbox.build)` (`vw get password "..."`). Sign in via Supabase
  auth REST (`POST {SUPABASE_URL}/auth/v1/token?grant_type=password` with the anon
  key from `~/platform-web/.env.local`). Tokens last 1h — re-auth before long stages.
- API: `https://soapbox-api-production.up.railway.app`; every call needs
  `Authorization: Bearer <token>` + `x-organization-id: <org uuid>` (tenant
  middleware resolves the portfolio from the org).
- Supabase project `fplbvanvwvnviczozwhz` (direct SQL via Supabase MCP) for the
  steps with no API endpoint: org + member creation, connector-row copies,
  metadata jsonb merges, and verification rollups. All asset fields go through
  the API.
- Scripts (already built, `scripts/`): `portfolio_match.py` (fuzzy matching),
  `document_classifier.py` (doc typing), `ll_allocation.py` (LL/TT tree). Use them
  when name matches aren't obvious; skip when filenames are unambiguous.

## Stage 0 — Source discovery

Accept any of: zip/Taildrop drop, Google Drive/Box folder, typed register. Extract
zips excluding `__MACOSX/` and `.DS_Store`. **Dedupe by sha256** — client drops
routinely duplicate files across folders (Cortland: 31 of 60 were dupes). Prefer
the copy inside a typed subfolder (`PCAs/`, `Audits/`) as canonical.

Build the asset register: `{name, address, city, state, zip, gfa, year_built,
floors, units}` per asset from helper data / spreadsheet / audits. Preserve any
confidence tags — mark everything not client-verified as such in metadata.

## Stage 1 — Org + portfolio + members

1. SQL: `insert into organizations (name) values ('<Client>')`; add
   `organization_members` rows for christopher@soapbox.build
   (`f243660a-6991-4f7a-97f4-fefce9e24873`) and claude@agents.soapbox.build
   (`63025178-e0ac-4018-910d-55b876e441db`), role `owner`.
2. API: `POST /api/portfolios {name, organization_id}` **as the service account** —
   this provisions the Stripe customer, core plugins (plugin_catalog auto-
   provision), and the caller's portfolio membership. Do NOT insert the portfolio
   by SQL.
3. SQL: add christopher as portfolio_members `admin` (the API only adds the caller).

## Stage 2 — Create assets (BEFORE installing the Audette connector)

**Ordering constraint:** `POST /api/assets` fires `triggerAudettePropertyCreate`,
which auto-creates Audette properties **if** `plugin_audette` is installed on the
portfolio. Creating assets first (no connector yet) makes the pipeline skip
(`audette_pipeline_state: skipped_no_plugin`) and prevents duplicate Audette
properties when records already exist.

Per asset:
- `POST /api/assets {name, lat?, lon?, num_floors?}`.
- `PATCH /api/assets/:id {metadata}` — include `ingestion_source:
  "portfolio-onboarding"`, `batch`, `setup_complete: false`, num_buildings,
  archetype, regulatory_driver, energy (with source + units), equipment_survey,
  and confidence notes.
- `PATCH /api/assets/:id` also accepts (since soapbox-api `962ab29`, 2026-07-02):
  `street_address, city, state_province, postal_zip_code, country, property_type,
  gross_floor_area_m2 (ft² × 0.09290304), year_built, num_floors, tags` (tag with
  `portfolio-onboarding` + `<client>-batch-N`). No direct SQL needed for asset
  fields — everything goes through the API.

## Stage 3 — Audette linking + grouping

1. Install the connector: copy the freshest `plugin_audette` row in
   `asset_connectors` (any portfolio; tokens are user-scoped and work across
   portfolios; the connector proxy refreshes them) into a new row for this
   portfolio.
2. `GET /api/portfolios/audette/accounts` → find the client account uid →
   `PATCH /api/portfolios {audette_account_id}` (clears the properties cache).
3. `POST /api/portfolios/audette/properties/refresh` → per-building rows with
   `property_uid`, `property_name`, `building_uid`, `building_name`.
4. Match each asset by name (exact/fuzzy; `portfolio_match.py` for ambiguous):
   - **Grouped** (has `property_uid`) → `PATCH /api/assets/:id
     {audette_property_id}`.
   - **Ungrouped** (buildings match by name but `property_uid` is null — common;
     half of Cortland): collect the building uids, then call the Audette MCP
     directly (`https://mcp-server.prod.audette.io/mcp`, bearer = connector
     `api_key`; JSON-RPC `tools/call`):
     `switch_customer_account {customer_account_uid}` then
     `create_property_for_building {building_model_uids: [...], property_name}` →
     returns `property_uid` → PATCH the asset. Also `assign_property_to_building`
     exists for adding buildings to an existing property. Store the building uids
     in `metadata.audette_building_uids` regardless (analysis tools take
     building_model_uid).
   - **No match** → leave null; the asset card shows no Audette badge; record as
     follow-up.
5. Re-run `.../audette/properties/refresh` at the end so the cache reflects new
   groupings.

## Stage 4 — ESPM linking (always optional, never blocking)

1. Copy a `plugin_energy_star` connector row (shared ESPM account) to the portfolio.
2. `POST /api/portfolios/espm/properties/refresh` (~2,300 properties; cached on the
   portfolio).
3. Match by name against `property_name` (watch for suffixed codes like
   "(tn97)" and typo'd cities). `PATCH /api/assets/:id {espm_property_id}`.
4. Expect true misses (Cortland Belmar). Record them in the completion report as
   "needs ESPM property creation or client confirmation" — do not block.

## Stage 5 — Upload + index documents

Routing: per-asset docs → `POST /api/assets/:id/files` (multipart `file` +
`folder`); portfolio-wide reference/helper files → `POST /api/portfolios/files`.
Folder by type: `Audits` (energy/water audit reports), `PCAs` (PCAs, PCRs,
surveys), `Reference Data`. Indexing is queued automatically for indexable MIMEs.

Hard-won mechanics (all hit on Cortland):
- **50MB API cap** → split bigger PDFs with PyMuPDF (`insert_pdf` page ranges,
  "(Part N of M)" names). Lossless split beats lossy compression for source docs.
- **curl `-F` breaks on commas in filenames** → always quote: `-F 'file=@"<path>";
  type=<mime>'` (returns empty-body failure otherwise).
- **Portfolio files endpoint 500s on non-ASCII filenames** (em-dash) → rename to
  ASCII first. It also 500s on `text/markdown` / `application/json` MIME in prod →
  send md/json/txt as `text/plain` (still indexes).
- **Verify indexing**: poll `files.indexing_status` until all `indexed`. On
  `failed`, check Railway deploy logs (project `soapbox-platform`, service
  `soapbox-api`, deploys from **main**) and retry with
  `POST /api/assets/:id/files/:fileId/reindex`. Known fixed bug: PDFs with NUL
  bytes in extracted text (fixed `ac77a12`).
- Count embeddings chunks at the end as a sanity check (`embeddings` table by
  asset/portfolio id).

## Stage 6 — Verify + report

- SQL rollup: assets / audette_linked / espm_linked / files / indexed / chunks.
- Optional but recommended: Playwright pass on `https://app.soapbox.build` (service
  account login → workspace switcher → client org) to confirm the portfolio
  renders with Audette/ESPM badges; screenshot for the report.
- Completion report to the user: totals, per-asset link status, misses +
  follow-ups (ESPM gaps, unmatched docs, missing financial params), and what was
  NOT done (address mapping, LL/TT params if not collected).
- `metadata.setup_complete` stays `false` until the client verifies helper data;
  LL/TT allocation inputs (lease structure, metering config, jurisdiction) are
  collected in the review pass per the 2026-06-27 design spec when running the
  full conversational flow.

## Idempotency

Before creating anything, check for an existing org/portfolio by name and existing
assets by name + client tag. Resume from the first incomplete step; never
re-upload a file whose name already exists under the same asset; never overwrite
existing audette/espm links.
