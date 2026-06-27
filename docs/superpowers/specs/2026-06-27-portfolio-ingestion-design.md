# Portfolio Ingestion Workflow — Design Spec

**Date:** 2026-06-27
**Status:** Approved for implementation
**Prototype client:** Greystar (39 assets)
**Scope:** Spec 1 of 2 — ingestion only. Portfolio analysis workflow is a separate spec.

---

## Problem

Onboarding a new client with a large existing portfolio requires creating Soapbox assets for
each property, linking them to pre-existing records in Audette and ESPM, allocating source
documents (PCAs, audits, utility data) to the correct assets, and populating financial
parameters needed for analysis. Done manually or asset-by-asset this is slow, error-prone,
and doesn't scale. Done poorly it produces assets that are incomplete or mislinked, breaking
downstream analysis.

The workflow must handle the realistic case: documents stored in client-owned cloud storage
(Box, OneDrive) or Soapbox's own Drive, mixed naming conventions, some assets already in
Audette or ESPM and some not, and financial parameters that are partially known.

---

## Goals

- Create analysis-ready Soapbox assets in bulk from any source combination
- Match and allocate documents automatically, surfacing only genuine ambiguity to the user
- Link to Audette and ESPM where records exist; degrade gracefully when they don't
- Capture the three LL/TT allocation inputs (lease structure, metering config, jurisdiction)
  per asset rather than applying a flat building-type percentage
- Be reusable for every future client, not Greystar-specific

---

## Non-goals

- Running the financial analysis (portfolio analysis workflow, spec 2)
- Building or modifying Audette building models
- Handling >1000 assets in a single run (this is a guided workflow, not a bulk ETL pipeline)

---

## Architecture

The ingestion workflow is a `portfolio-ingest` skill in soapbox-agent. It runs as a
conversational skill (invoked in any Soapbox or Claude Code session) and orchestrates four
sequential stages:

```
[1. Source Discovery]
     Document source adapters: Google Drive / Box / OneDrive / direct upload
     Asset register: CSV, spreadsheet, or typed list as the ground-truth seed
          ↓
[2. Matching Engine]
     Per asset: fuzzy name + address match against Audette and ESPM
     Per document: extract property signals, score against asset list
     Output: confidence score (0.0–1.0) for every proposed match
          ↓
[3. Confidence Gate + Review Pass]
     ≥ 0.85 → auto-proceed (no user input)
     < 0.85 → batched into a per-asset review card
     Missing financial params → collected in same review card
          ↓
[4. Execution Pipeline]
     Per asset (parallel):
       1. Create Soapbox asset
       2. Link Audette building ID (or skip)
       3. Link ESPM property ID (or skip)
       4. Upload + associate documents
       5. Store financial + LL/TT parameters
       6. Set analysis_ready flag
     Final: create portfolio-level thread pre-loaded with all asset context
```

---

## Stage 1: Source Discovery

### Document source adapters

The skill accepts any of the following document sources. Multiple sources can be combined
for a single ingestion run (e.g. Soapbox Drive for audits + client Box for utility data).

| Source | Auth mechanism | Notes |
|--------|---------------|-------|
| Google Drive | Google Drive MCP (already connected) | Folder path or shared drive URL |
| Box | Box MCP (available in platform) | Folder ID or shared link |
| OneDrive / SharePoint | Microsoft 365 MCP | Drive ID + folder path |
| Direct upload | Files already in Supabase storage | Reference by portfolio tag |

The skill does not require all sources to be present. If a source is unavailable or
unconfigured for the org, it is skipped silently and documents from that source are marked
as not yet ingested.

### Asset register (seed)

The asset register is the authoritative list of property names and addresses. It can be
provided as:

- A CSV or spreadsheet column (name, address, city, state, fund, sub-asset type)
- The Greystar portfolio spreadsheet (parsed from Google Drive)
- A typed list ("here are my 39 properties: ...")

The skill extracts a canonical list of `{name, address, city, state}` tuples. This becomes
the matching ground truth.

---

## Stage 2: Matching Engine

Two independent matchers run per asset.

### System record matching (Audette + ESPM)

Each asset register entry is matched against Audette buildings (via `list_buildings` after
`switch_customer_account`) and ESPM properties. Candidates are scored:

| Signal | Score |
|--------|-------|
| Exact name match | +0.60 |
| Address match (street + city) | +0.25 |
| Address match (street only) | +0.15 |
| Fuzzy name match ≥ 80% similarity | +0.35 |
| Fuzzy name match 60–80% | +0.15 |
| State / zip match (tiebreaker) | +0.05 |

Top candidate wins if score ≥ 0.40. Below 0.40 → "not found". Above 0.85 → auto-link.
Between 0.40 and 0.85 → goes to review card.

If Audette is not connected for the org, the Audette matching step is skipped entirely and
`audette_id` is left null. ESPM is always optional — it is never a blocking requirement for
asset readiness. If ESPM is unconfigured or unavailable, ESPM linking is skipped silently
and does not appear in review cards.

### Document matching

Each document is scanned (filename + first ~500 words of text extraction) for property
signals:

1. Property name mentions
2. Street address strings
3. Fund name or asset codes

Extracted signals are scored against the asset list using the same fuzzy matching. A
document resolves to:

- **One asset at ≥ 0.85** → auto-assigned
- **One asset at 0.40–0.84** → flagged in that asset's review card
- **Multiple assets within 0.10 of each other** → flagged in both assets' review cards
- **No match (< 0.40)** → collected as "unallocated" and presented at the end

Documents are also tagged by inferred type based on filename and content keywords:

| Type | Keywords |
|------|----------|
| `pca` | property condition, PCA, capital needs, building survey |
| `audit` | energy audit, retro-commissioning, ASHRAE |
| `utility` | utility, meter, interval data, kWh, invoice |
| `capex` | capital plan, CapEx, budget, reserve study |
| `lease` | lease abstract, rent roll, lease agreement, tenant |
| `other` | anything else |

Inferred document type is shown in the review card for every document (auto-assigned or
flagged). The user can override the type inline during review by responding with
`type=audit` or similar. Lease documents are flagged specifically because they may contain
lease structure information useful for LL/TT allocation.

---

## Stage 3: Confidence Gate + Review Pass

Before any assets are created, the skill reports: "X of Y assets resolved automatically.
Showing Z that need attention."

Each flagged asset gets one structured review card presented sequentially in the
conversation. The card shows only fields that need resolution — auto-resolved fields are
shown as confirmed, not re-asked.

### Review card format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Asset 7 of 39 — Landmark at Colony Park
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM LINKS
  Audette  → "Landmark Colony Park" [0.78] — confirm? (y / enter ID / skip)
  ESPM     → not found — enter property ID or skip

DOCUMENTS (2 unresolved of 8 total)
  ✓ Landmark_PCA_2024.pdf              → auto-assigned
  ✓ Landmark_GreenRock_Audit.pdf       → auto-assigned
  ? Energy_Audit_Final_v3.pdf          → matches Landmark [0.71] AND Meridian [0.68]
                                         assign to: (1) Landmark  (2) Meridian  (3) neither
  ? GreenRock_Study_Unknown.pdf        → no match found
                                         assign to asset or discard?

FINANCIAL PARAMETERS
  ✓ Fund:            GEdR
  ✓ Sub-asset type:  High Rise
  ✓ Exit year:       2030
  ? Exit cap rate    → not found, please enter (e.g. 4.5%)

LL/TT ALLOCATION INPUTS
  ? Lease structure  → gross / nnn / modified-gross / rubs / green-lease?
  ? Metering config  → master-metered / individually-metered / submeter-passthrough?
  ✓ Jurisdiction:    Boston (BERDO jurisdiction — carbon fine liability flagged to LL)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Interaction model

The user responds inline — `y`, a number, a typed value, or `skip`. The skill advances
to the next card. Fully resolved assets are never shown.

After all cards: a final summary shows the complete plan before any writes occur.
"About to create 39 assets, link 36 to Audette, 28 to ESPM, upload 147 documents. Proceed?"
One confirmation, then execution begins.

### Edge case warnings (shown inline in card)

These are flagged automatically based on the combination of inputs — no user action needed,
just awareness:

- **NNN + envelope measure** → "LL bears capex but TT captures opex savings under NNN"
- **Solar + no green lease** → "rooftop solar typically requires tenant consent"
- **RUBS + in-unit measure** → "individual savings may not recover to LL under RUBS"
- **BPS jurisdiction** → "carbon fine liability sits with property owner regardless of lease"

---

## Stage 4: Execution Pipeline

All approved assets execute in parallel. Each asset is an independent unit.

### Per-asset steps (in order)

**1. Create Soapbox asset**

Fields populated from asset register + any document-extracted metadata:
- `name`, `address`, `city`, `state`
- `property_type` (mapped from sub-asset type)
- `fund_name`, `sub_asset_type`
- `tags: ["portfolio-ingestion", "<client-slug>"]`
- `year_built`, `gross_floor_area_m2`, `num_floors` — populated ONLY after step 2 succeeds

Asset register `fund_name` overrides any fund data from Audette. If the asset register is
missing fund data, fall back to the Audette record value.

**2. Link Audette**

Call `get_building_model_details` to confirm the candidate building ID resolves and is
accessible. Only on success: store `audette_building_id` in asset metadata AND backfill
`year_built`, `gross_floor_area_m2`, `num_floors` from the Audette response. If the
confirmation call fails, the Audette link is not written and the asset proceeds without it.
If Audette not connected → skip entirely, set `audette_id: null`.

**3. Link ESPM**

ESPM is always optional. If ESPM plugin is installed: store `espm_property_id` from the
user-confirmed ID (ESPM matching is manual — user provides the property ID during review;
no automated ESPM API matching in this version). If ESPM not installed or ID not provided
→ skip, set `espm_id: null`. Never blocks asset creation or `analysis_ready`.

**4. Upload + associate documents**

Each document uploaded to Supabase storage under the asset path, tagged with inferred type.
Documents confirmed "unallocated" or "discard" during review are not uploaded.

**5. Store financial + LL/TT parameters**

Written to asset metadata:

```json
{
  "exit_year": 2030,
  "exit_cap_rate": 0.045,
  "fund_name": "GEdR",
  "sub_asset_type": "High Rise",
  "lease_structure": "gross",
  "metering_config": "master",
  "jurisdiction": "Boston",
  "bps_liable": true,
  "ll_allocation_overrides": {},
  "analysis_ready": true
}
```

`analysis_ready` is set to `true` only when `exit_year`, `exit_cap_rate`, `lease_structure`,
and `metering_config` are all present. `jurisdiction` is required only for assets in known
BPS jurisdictions (NYC, Boston, DC, Vancouver, Denver — list maintained in skill config);
for all other jurisdictions it is optional and defaults to `"other"` with `bps_liable: false`.
Assets missing any required field are flagged `analysis_ready: false` and appear in the
completion report as requiring follow-up.

Exit year validation happens during the review pass, not execution: if the confirmed exit
year is in the past, the review card flags it inline ("Exit year 2017 is in the past — enter
a projected exit year or skip to mark asset as already disposed") before moving on. Already-
disposed assets are created with `status: "disposed"` and excluded from analysis.

**6. Create portfolio thread**

After all assets complete, one portfolio-level conversation thread is created in the
Soapbox conversations UI — the same thread model used for asset-level chat. It is tagged
`{client-slug}-portfolio-analysis`. The opening message (posted by the skill, not a system
prompt) summarises the ingestion outcome and lists all assets with their readiness status.
This thread is the launch point for the portfolio-analysis workflow (spec 2); the analysis
skill reads the thread tag to know which assets to include.

### Failure handling + idempotency

If an individual asset fails (API error, upload timeout), it is marked with metadata
`ingestion_status: "failed"` and `ingestion_error: "<reason>"`. Remaining assets continue.
Failures are collected and appended to the completion report.

The workflow is idempotent: re-running for failed assets checks for an existing Soapbox
asset with the same name + client tag before creating a new one. If found, it resumes from
the first incomplete step (skipping Soapbox asset creation and any steps already marked
complete in metadata). Documents that were already successfully uploaded are not re-uploaded
(checked by filename + asset ID match in Supabase storage). Audette and ESPM links that
already exist are not overwritten.

### Progress reporting

The skill streams asset-by-asset completion as it runs:
```
✓ Landmark at Colony Park (7/39) — Audette linked, 8 docs, analysis-ready
✓ SoMa at Brickell (8/39) — no ESPM, 3 docs, analysis-ready
⚠ Northern Michigan (9/39) — missing exit cap rate, not analysis-ready
```

---

## LL/TT Allocation Logic

### Why not a flat table

Prior approaches (including the Greystar helper spreadsheet) used a flat percentage lookup
by building sub-type (e.g. "High Rise = 15% LL on in-unit measures"). Research across
published DOE, ACEEE, IMT, and RMI sources shows this is incorrect: the real determinants
are lease structure, metering configuration, and jurisdiction — not building type. The same
High Rise under a gross lease captures 100% of savings to the landlord; under NNN, near 0%.

### The three-factor decision tree

The analysis workflow resolves LL capture % at runtime per asset per measure by traversing:

```
1. LEASE STRUCTURE
   gross           → ~100% LL (landlord pays utilities, captures all savings)
   nnn             → ~0–10% LL (tenant pays utilities; LL only captures BPS fine avoidance)
   modified-gross  → resolve by fuel type via metering config
   rubs            → common area loads only for LL (~20–40% of whole-building)
   green-lease     → follow specific clause language (operator must supply)

2. METERING CONFIGURATION (resolves modified-gross and RUBS)
   master-metered          → LL captures savings on all metered loads
   individually-metered    → LL captures common area only; in-unit is TT
   submeter-passthrough    → LL installs, bills back proportionally; LL captures the delta

3. JURISDICTION OVERRIDE
   BPS jurisdiction (NYC LL97 / Boston BERDO / DC BEPS / etc.)
   → Property owner is legally liable for carbon fines regardless of lease
   → Savings that reduce fine exposure are always treated as LL-captured
   → Fine-avoidance value is added on top of operating savings in financial model

4. MEASURE TYPE (modulates within the above)
   Elevators / common area systems  → always LL regardless of lease
   In-unit systems under NNN        → always TT regardless of metering
   Rooftop solar                    → follows system owner (usually LL; flag consent risk)
   Envelope under NNN               → LL capex, TT captures opex savings (NNN paradox)
   ITC / §179D / utility rebates    → follow capital expenditure owner / account holder
```

### Storage

Stored per asset as `lease_structure`, `metering_config`, `jurisdiction`, `bps_liable`, and
`ll_allocation_overrides` (for any measure-level manual overrides confirmed during review).
The analysis skill reads these at runtime — no static table is encoded anywhere.

---

## Skill Interface

```
User: "Ingest the Greystar portfolio from our Google Drive"

Skill prompts:
  → "Which folder? (paste URL or folder name)"
  → "Do you have an asset register / property list to use as the seed?
     (spreadsheet, CSV, or type them out)"
  → "Are Greystar's buildings already set up in Audette? (yes / no / some)"
  → "Is ESPM connected for this org? (yes / no)"

Skill then: discovers documents, runs matching, presents summary, shows review cards
for flagged items, confirms execution plan, runs.
```

The skill accepts partial inputs and adjusts. No Audette? Skips steps 2 + 3. No documents?
Skips document matching entirely, creates stub assets with financial params only.

---

## Completion Report

After all assets finish:

```
Portfolio Ingestion Complete — Greystar
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total assets:        39
  Analysis-ready:    34
  Missing params:     3  (exit cap rate not provided)
  Ingestion failed:   2  (see below)

Audette linked:      36 / 39
ESPM linked:         28 / 39
Documents uploaded: 147 across 37 assets

Funds:  GEdR (12)  GGIF (9)  Fund 11 (10)  Fund 10 (8)

Failed assets:
  ✗ Northern Michigan (The Woods) — Audette API timeout on link step
  ✗ ORE 82 — exit year 2017 is in the past; skipped, needs manual review

Portfolio thread created: /portfolio/threads/greystar-portfolio-analysis
Ready to run: portfolio-analysis workflow
```

---

## Open Questions for Implementation

1. **Fuzzy matching library** — use Python `rapidfuzz` (already available in scripts env)
   or implement in the skill using LLM judgement for ambiguous cases?
   Recommendation: `rapidfuzz` for speed on large sets; LLM fallback for < 0.60 cases.

2. **Document text extraction** — PDF text extraction requires `pdfplumber` or similar.
   Confirm this is available in the soapbox-agent script environment.

3. **Audette `switch_customer_account`** — confirm the Greystar account slug for the MCP
   call before implementation.

4. **ESPM MCP availability** — the `espm_installed` flag exists in platform-web's
   `PortfolioData` type but no ESPM MCP tools are currently configured. Clarify whether
   ESPM linking is manual (user provides property ID) or via MCP.

5. **Asset metadata schema** — the financial + LL/TT fields described in stage 4 step 5
   will be stored in a JSONB `metadata` column on the `assets` table (default approach,
   avoids migration churn for evolving fields). A typed schema is defined in the skill and
   validated on write. A Supabase migration is required to add the `metadata` column if it
   does not already exist. Confirm with platform-web whether a `metadata` column is already
   present before writing the migration.

---

## Implementation Plan

Handed off to `superpowers:writing-plans` for task breakdown.

Estimated deliverables:
- `skills/portfolio-ingest/SKILL.md` — skill definition
- `scripts/portfolio_ingest.py` — matching engine + execution pipeline
- `scripts/ll_allocation.py` — decision tree logic
- `scripts/document_classifier.py` — document type inference
- Supabase migration: add LL/TT + financial param fields to asset metadata
