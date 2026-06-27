# Portfolio Ingest Skill

Bulk-creates Soapbox assets from client document sources, links pre-existing Audette
buildings and ESPM properties, and collects all financial and LL/TT parameters needed
for portfolio analysis. Runs four sequential stages: source discovery → matching →
confidence-gated review → execution.

## When to Invoke

Trigger this skill when the user says anything like:
- "Ingest the [client] portfolio"
- "Set up assets for [client]"
- "Import [N] properties from [Drive/Box/OneDrive]"
- "Create Soapbox assets from this property list"

## Computation Scripts

All matching, classification, and allocation logic lives in standalone Python scripts.
Call them via bash tool:

```bash
# LL/TT allocation
python3 ~/soapbox-agent/scripts/ll_allocation.py --inputs '<json>'

# Document type inference
python3 ~/soapbox-agent/scripts/document_classifier.py --inputs '<json>'

# Fuzzy matching — system records
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode system --inputs '<json>'

# Fuzzy matching — documents to assets
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode document --inputs '<json>'
```

## Stage 1: Source Discovery

### Step 1a — Collect document source

Ask the user:
> "What's the document source? (1) Google Drive folder  (2) Box folder  (3) OneDrive/SharePoint  (4) Files already uploaded to Soapbox"

- Drive: use `mcp__claude_ai_Google_Drive__search_files` with the folder ID or name; retrieve file list
- Box: use `mcp__claude_ai_Box__*` tools if available; otherwise ask user to share a file list
- OneDrive/SharePoint: use `mcp__claude_ai_Microsoft_365__*` tools if available
- Already uploaded: query Supabase storage for files tagged with the client portfolio tag

For each document found, extract:
- `filename`
- `path` / `file_id` (for later download)
- First 500 words of text (use `mcp__claude_ai_Google_Drive__read_file_content` for Drive;
  for PDFs use the file content tool; fall back to filename-only classification if unavailable)

### Step 1b — Collect asset register seed

Ask the user:
> "Do you have an asset register or property list? (1) Yes — spreadsheet/CSV  (2) Yes — I'll type them  (3) No — build from Audette"

- Option 1: read the file and extract rows as `{name, address, city, state, fund_name, sub_asset_type, exit_year, exit_cap_rate}`
- Option 2: accept a typed list, one property per line, extract what you can
- Option 3: call `mcp__claude_ai_Audette_AI__switch_customer_account` then `mcp__claude_ai_Audette_AI__list_buildings` to build the register from Audette

### Step 1c — Check external system availability

Ask:
> "Are this client's buildings already set up in Audette? (yes / no / some)"
> "Is ESPM connected for this org? (yes / no)"

Note answers — they control whether matching steps run.

## Stage 2: Matching

### Step 2a — Match asset register entries against Audette

For each asset in the register (if Audette is available):

1. Call `mcp__claude_ai_Audette_AI__switch_customer_account` with the client account
2. Call `mcp__claude_ai_Audette_AI__list_buildings` to get all buildings
3. Call the matching script:

```bash
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode system --inputs '{
  "asset": {"name": "<asset_name>", "address": "<address>", "city": "<city>", "state": "<state>"},
  "candidates": [<audette_buildings_as_json>]
}'
```

4. Record: `{asset_name, audette_candidate_id, audette_candidate_name, score, auto_link, needs_review}`

### Step 2b — Match documents to assets

For each document discovered in Stage 1:

```bash
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode document --inputs '{
  "filename": "<filename>",
  "text": "<first_500_words>",
  "assets": [<asset_register_as_json>]
}'
```

Record the top match and whether it is `auto_assign` or `ambiguous`.

Also classify each document:

```bash
python3 ~/soapbox-agent/scripts/document_classifier.py --inputs '{
  "filename": "<filename>",
  "text": "<first_500_words>"
}'
```

### Step 2c — Detect BPS jurisdiction

For each asset, check if its `city` or `state` is in the BPS list:
`NYC, New York, Boston, Washington DC, Vancouver, Denver, Seattle, Chicago`

Set `bps_liable: true` for matches. Auto-set `jurisdiction` to the matched city name.

### Step 2d — Report pre-review summary

Tell the user:
> "Matching complete. X of Y assets resolved automatically (Audette + documents). Z assets need review."

List auto-resolved assets briefly. Then begin Stage 3 for flagged assets.

## Stage 3: Review Pass

For each asset where ANY of the following is true, present a review card:
- Audette match score is 0.40–0.84 (needs confirmation)
- Any document match is ambiguous or unresolved
- `exit_year`, `exit_cap_rate`, `lease_structure`, or `metering_config` is missing
- Exit year is in the past

Present cards one at a time. Format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Asset N of M — [Asset Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM LINKS
  Audette  → "[candidate_name]" [score] — confirm? (y / enter ID / skip)
  ESPM     → not found — enter property ID or skip

DOCUMENTS ([N] unresolved of [total] total)
  ✓ [filename] → auto-assigned [pca]
  ? [filename] → matches [Asset A] [0.71] AND [Asset B] [0.68]
                  assign to: (1) [Asset A]  (2) [Asset B]  (3) neither
  ? [filename] → no match — assign to this asset or discard?

FINANCIAL PARAMETERS
  ✓ Fund:            [value]
  ✓ Sub-asset type:  [value]
  ? Exit year        → [if in past: "PAST DATE — enter projected exit year or type 'disposed'"]
  ? Exit cap rate    → not found, please enter (e.g. 4.5%)

LL/TT ALLOCATION INPUTS
  ? Lease structure  → gross / nnn / modified-gross / rubs / green-lease?
  ? Metering config  → master / individual / submeter-passthrough?
  ✓ Jurisdiction:    [city] ([BPS warning if applicable])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Parsing user responses:**
- `y` or `yes` → confirm the proposed value
- A number → select numbered option
- A typed value → use as the field value (e.g. `4.5%` → `exit_cap_rate: 0.045`)
- `skip` → leave field null; mark `analysis_ready: false`
- `disposed` (for exit year) → set `status: "disposed"`, exclude from analysis

**After user response, show edge case warnings inline if applicable:**
- NNN + envelope measure in plan → "Note: NNN paradox — LL bears capex, TT captures savings"
- Solar + no green lease → "Note: rooftop solar typically requires tenant consent"
- RUBS + individual metering → "Note: savings may not recover to LL — collective action problem"
- BPS jurisdiction → "Note: carbon fine liability sits with property owner regardless of lease"

After all cards, present final execution plan:
> "Ready to create [N] assets, link [N] to Audette, upload [N] documents. [N] will be analysis-ready. Proceed? (y/n)"

## Stage 4: Execution Pipeline

Execute all assets in parallel (run independently — no cross-asset dependencies).

### For each asset:

**Step 4.1 — Idempotency check**

Query Supabase for existing asset with same name + client tag:
```sql
SELECT id, metadata FROM assets 
WHERE name = '<asset_name>' 
AND '<client-slug>' = ANY(tags)
LIMIT 1
```

If found and `ingestion_status = 'success'`, skip this asset (already done).
If found and `ingestion_status = 'failed'`, resume from first incomplete step.

**Step 4.2 — Create Soapbox asset**

Use `mcp__plugin_supabase_supabase__execute_sql`:
```sql
INSERT INTO assets (name, building_name, property_type, tags, metadata)
VALUES (
  '<name>',
  '<building_name>',
  '<property_type>',
  ARRAY['portfolio-ingestion', '<client-slug>'],
  '{}'::jsonb
)
RETURNING id;
```

Map `sub_asset_type` to `property_type`:
- "High Rise", "Midrise", "Garden Style", "Low-Rise", "Townhomes", "Wrap", "Urban Style" → `"multifamily"`
- "Clubhouse" → `"amenity"`
- Default → `"multifamily"`

**Step 4.3 — Link Audette**

If Audette ID is confirmed:
1. Call `mcp__claude_ai_Audette_AI__get_building_model_details` with the confirmed ID
2. If successful: update asset metadata with `audette_building_id` and backfill `year_built`, `gross_floor_area_m2`, `num_floors` from response
3. If call fails: log error, leave `audette_id: null`, continue

**Step 4.4 — Link ESPM**

If ESPM ID was provided by user: store `espm_property_id` in asset metadata.
ESPM is never a blocking step — always continue regardless.

**Step 4.5 — Upload documents**

For each document assigned to this asset:
- Download file content (Drive MCP / Box MCP as appropriate)
- Upload to Supabase storage: path = `assets/<asset_id>/documents/<filename>`
- Record `{filename, storage_path, doc_type, source}` in asset metadata `documents` array

Check idempotency: if `<asset_id>/<filename>` already exists in storage, skip upload.

**Step 4.6 — Store financial + LL/TT metadata**

Write final metadata to asset:

```json
{
  "ingestion_status": "success",
  "ingestion_client": "<client-slug>",
  "audette_building_id": "<id_or_null>",
  "espm_property_id": "<id_or_null>",
  "fund_name": "<fund>",
  "sub_asset_type": "<type>",
  "exit_year": 2030,
  "exit_cap_rate": 0.045,
  "lease_structure": "gross",
  "metering_config": "master",
  "jurisdiction": "Boston",
  "bps_liable": true,
  "ll_allocation_overrides": {},
  "analysis_ready": true,
  "documents": [{"filename": "...", "storage_path": "...", "doc_type": "pca"}]
}
```

`analysis_ready: true` only if `exit_year`, `exit_cap_rate`, `lease_structure`, `metering_config` are all non-null.
For BPS jurisdictions, also require `jurisdiction` to be non-null.

Use SQL UPDATE:
```sql
UPDATE assets SET metadata = '<json>'::jsonb WHERE id = '<asset_id>';
```

**Step 4.7 — Report progress**

After each asset completes, output one line:
```
✓ Landmark at Colony Park (7/39) — Audette linked, 8 docs, analysis-ready
⚠ Northern Michigan (9/39) — missing exit_cap_rate, not analysis-ready
✗ ORE 82 (11/39) — disposed, excluded from analysis
```

### Step 4.8 — Create portfolio thread

After all assets finish:

1. Query Supabase for the portfolio's conversations table
2. Create a new conversation tagged `<client-slug>-portfolio-analysis`
3. Post an opening message summarising:
   - Total assets created, by fund
   - Analysis-ready count vs. pending
   - List of failed assets with error reasons
   - "Ready to run: portfolio-analysis workflow (spec 2)"

### Step 4.9 — Completion report

Present to user:
```
Portfolio Ingestion Complete — [Client]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total assets:       [N]
  Analysis-ready:   [N]
  Missing params:   [N]  ([fields])
  Disposed:         [N]
  Failed:           [N]

Audette linked:     [N] / [total]
ESPM linked:        [N] / [total]
Documents uploaded: [N] across [N] assets

Funds: [fund1 (N)]  [fund2 (N)] ...

Portfolio thread: /portfolio/threads/[client-slug]-portfolio-analysis
```

## Error Handling

- If a required MCP tool is unavailable, tell the user which tool and what to configure, then continue without that integration
- If Supabase INSERT fails, report the asset as failed with the SQL error
- Never silently swallow errors — always report what failed and why
- A failed asset does not stop other assets from processing
