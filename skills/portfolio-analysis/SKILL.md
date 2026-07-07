---
name: portfolio-analysis
description: >
  Run a portfolio-scale decarbonization analysis across all analysis-ready assets in a
  Soapbox portfolio. For each asset: pulls Audette decarb plan (physics), runs the
  compute_plan_economics cashflow engine (incremental value bridge + IRR), applies LL/TT
  allocation decision tree, screens measures by IRR ≥ hurdle. Aggregates to fund-level and
  portfolio-level summary. Produces
  presentation-ready HTML report. Works for any client portfolio — parameters are fully
  configurable per run. Spec 2 of 2 — portfolio ingestion (Spec 1) is a prerequisite.
  Triggers on: "run portfolio analysis", "analyze the portfolio", "portfolio decarbonization",
  "run the portfolio", "portfolio summary", "show me the portfolio results", "portfolio IRR",
  "portfolio CapEx", "run analysis on [client]",
  after portfolio-ingest completes.
version: 1.9.0
---

# Portfolio Analysis

You are running a **portfolio-scale decarbonization analysis** — the workflow that turns
a fully-ingested Soapbox portfolio into a presentation-ready view of required sustainability
capital, value creation, and emissions trajectory across all assets.

**Works for any client portfolio.** All parameters are set per run — there are no
hardcoded client assumptions.

**This skill replaces client-specific helper spreadsheets.** Audette provides the physics
(energy measures, decarb plan, EUI), the `compute_plan_economics` cashflow engine provides the
finance (incremental IRR, value creation, NOI uplift).

**Single-asset engagement:** if the ask is a full asset decarbonization engagement (one
asset, multi-week, gated, client-deliverable), route to the `decarb-plan` skill instead.

---

## Verification & Building-Science Discipline (applies throughout)

This skill runs the **same Data-Verification and Retrofit-Specialist (building-science) agents
that back `decarb-plan`** — the `verifier__*` and `retrofit__*` tools, which are live on every
portfolio agent. It applies them in a **batch-adapted** form, because a portfolio run screens
tens of assets in one pass and cannot human-adjudicate every conflict the way a single-asset
engagement does. These adaptations are deliberate — a full gated single-asset engagement routes
to `decarb-plan`; this is the screening-scale product.

**Ground rules — hold them on every asset:**

1. **No LLM arithmetic on reported numbers.** Every economic figure comes from the
   `compute_plan_economics` cashflow engine, an Audette model, or a cited source. You never
   compute a reported number yourself.
2. **`compute_plan_economics` owns the economics; the retrofit agent owns discipline + building
   science + the register.** ⚠️ **Do NOT call `run_dcf`, `run_intervention_irr`, `get_ll_capture`,
   or `screen_measure_portfolio`** — those four cashflow-MCP tools execute Python scripts that are
   NOT deployed in prod (`execFileSync python3` → ENOENT); they fail every time. The ONLY working
   economics tool is **`compute_plan_economics`** (pure TypeScript, deterministic) — it takes
   per-year owner-share cash flows and returns `irr_incremental` + the value-creation waterfall
   (capitalized owner savings/ancillary ÷ exit cap, PV of fine avoidance, net value creation,
   terminal exit-value delta). Determine the LL/TT split inline (Step 1 below), build each asset's
   per-year owner-share flows, and call `compute_plan_economics`. Feed its outputs *into*
   `retrofit__evaluate_measure` as `engine: "compute_plan_economics"`-provenanced fields; the
   provenance gate passes real numbers and rejects fabricated ones. The register's server-computed
   `exit_value_delta` (NOI÷cap) is a screening proxy — report **value creation** always comes from
   `compute_plan_economics`, never the register.
3. **Recommended = screen AND hurdle.** A measure is *recommended in the report* iff
   `retrofit__screen_measures` labels it `recommended` **AND** its DCF IRR ≥ `irr_hurdle`.
   Screen-recommended but IRR-missing → below-hurdle. Screen `defensive` → defensive. Screen
   `needs-data` → needs-data. Compliance-required measures are included regardless of IRR.
4. **Conflicts are logged, not silently picked.** A material data conflict (see Step 5) becomes a
   `verifier__record_finding`; the hierarchy suggestion is auto-applied at screening scale, but
   the finding is durable and surfaces in the Data Quality section.
5. **Verification is per-asset, called out — not fail-closed.** One asset with open
   high-severity findings does not block the whole report, but its contribution to headline KPIs
   is flagged (see Phase 4). Never let the totals silently absorb unverified data.
6. **Never fail silently.** Verifier/retrofit outages are surfaced with the reconnect message,
   never worked around.

**Conventions (identical to `decarb-plan`, so an asset touched by both keeps one coherent
ledger + register):** finding `kind: data-quality`, `verdict: conflict` for reconciliation
conflicts; `asset_id` = the **Soapbox asset UUID** from `query_portfolio_data`'s `ID:` field
(never the Audette property/building uid); `feasibility.score` = integer 1–5.

**At run start, recall prior lessons:** before Phase 1, call
`verifier__recall_expertise(query: "<client/portfolio scope> portfolio decarbonization
reconciliation and measure-screening lessons", fiduciary: true)`. Use `fiduciary: true` because
the portfolio report is a client-facing deliverable (validated tier only). Carry any relevant
lessons into reconciliation and screening. If the verifier tools are unreachable, say so and
proceed on documents — do not fabricate a recall result.

---

## Economics correctness — HARD rules (ported from decarb-plan; the verifier MUST check these)

These apply on **every asset**, at screening scale. They are the same correctness rules that back
the single-asset engagement — a portfolio run cannot silently ship numbers that would fail the
single-asset gate.

1. **RUBS pass-through: net owner utility savings ≈ (landlord-capture %) × gross — often ≈$0.**
   Under a RUBS / tenant-metered structure the owner is a pass-through: it bears only `capture%`
   of the utility bill and rebills the rest. A measure that cuts the bill by $X returns only
   `capture% × $X` to owner NOI. At a ~5–10% capture, owner savings round to **≈$0/yr**, NOT the
   gross. **Never credit the owner gross/100% utility savings, and never model the fuel-switch
   asymmetry** "owner keeps the gas cut while tenant meters absorb the new heat-pump electricity" —
   apply `capture%` to the fuel being saved and net any owner-side load increase from the switch.
   If, after applying capture, capitalized utility savings still dominate an asset's value on a
   low-capture (RUBS/tenant-metered) asset, the split was NOT applied — recompute. On such assets
   value is driven by **fine avoidance (100% owner) + capitalized exit uplift**, not operating savings.
   - **VERIFY the RUBS and VNM legislation per jurisdiction — never assume it.** The ~10% RUBS
     capture and the 80% VNM solar credit are CONDITIONAL on the jurisdiction actually permitting
     them. For each asset's jurisdiction, check (reference library → `brave-search`/web + `web_fetch`
     → **cite the statute/PUC rule + URL**): (a) whether RUBS / submetering pass-through is permitted
     and any allocation cap — **if RUBS is BARRED, the owner bears the utility → ~100% on
     master-metered, NOT ~10%**; (b) whether **Virtual Net Metering / aggregated NEM / community-solar
     export** is available — **if only behind-the-meter (BTM) net metering exists (no virtual/export
     aggregation), Scenario-C solar value = BTM self-consumption offset only** (owner-share on the
     loads it displaces), NOT the 80% VNM credit. Record each RUBS + VNM determination with its
     source as a `verifier__record_finding` (kind `data-quality`); an unconfirmed jurisdiction
     assumption is flagged in Data Quality, never silently applied.
2. **Landlord-capture is PER END-USE and turns on who BEARS the cost — not who pays the meter,
   not one blended number per asset.** Master-metered / landlord-paid loads (central heating/DHW
   plant, elevators, garage/common ventilation, common lighting, amenity): the owner pays the
   master bill but that is NOT 100% capture. **If the jurisdiction ALLOWS RUBS, assume the owner
   rebills up to ~90% to tenants → net owner capture ≈ 10%**, unless docs show the owner absorbs it
   (true gross lease / no RUBS → ~100%). In-unit tenant-metered loads carry the tenant % (~0–5%).
   Do NOT price a common/central load at the in-unit *blended* split (the elevator-regen −6%→+12%
   error) — but the right figure is the RUBS-recovery split (~10% when RUBS applies), **not an
   automatic 100%; never read "master-metered" as "100% owner."** Never inherit Audette's 15%
   account default either. **Solar under Virtual Net Metering (VNM): assume 80% of solar savings
   flows to the landlord.** BPS **fine avoidance is always 100% owner**. Tenant-side savings are a
   separate figure and do NOT capitalize into the value bridge.
3. **One value number = capitalized exit uplift.** The headline value is the capitalized exit-value
   uplift = (stabilized annual owner-NOI improvement ÷ exit cap), where NOI improvement =
   net-owner utility savings (post-capture, rule 1) + owner-share ancillary + annual avoided fine.
   `compute_plan_economics` returns this. Report ONE value number per asset/plan — do not present a
   PV-of-cashflows `net_value_creation` next to a contradicting capitalized `exit_value_delta`.
   Fine avoidance may also be shown cumulative + PV for context.
4. **CRREM provenance — real curve, never hand-built from Audette fields.** Pull the pathway from
   the **`crrem` MCP `get_pathway`** for each asset's actual country/property-type/region; put those
   points in the trajectory and set `crrem_meta` (country/property_type/region/scenario). Do NOT
   interpolate, eyeball, or reuse an Audette `crrem_pathway_target_*` model field as the plotted
   curve. Portfolio-weight the per-asset tool-fetched curves for the aggregate pathway. If the tool
   is unreachable, say so — never fabricate the curve.
5. **Fine avoidance assessed honestly against the governing metric.** Assess each BPS against the
   metric it actually uses. **Dual-pathway standards (comply via EITHER site-EUI OR GHG-intensity —
   e.g. CO Reg 28) require failing the GOVERNING/elected pathway**, not merely the harder one —
   don't manufacture a penalty off the EUI pathway if the asset clears the GHG pathway. A compliant
   asset gets fine avoidance **null, not 0-that-reads-as-a-number**. No phantom penalties in the
   headline compliance-exposure KPI.
6. **Sanity checks (reject + recompute if violated):** emissions trajectories are **non-increasing**
   (a rising with-plan/BAU carbon curve is a sign/axis bug); at-RUL / bundled-capital-event
   incremental cost is **positive** (only the upgrade spec above the mandatory like-for-like is
   incremental — a re-roof is baseline, only added insulation is incremental); **ancillary/DR revenue
   is NOT capitalized as a perpetuity** (risk-adjust / PV over term); **subscription measures judged
   on annual net**, not capitalized-fee-vs-savings; every headline % equals the underlying
   tonnage/energy math on the **same basis** (never mix grid-inclusive vs measure-only in one figure).
7. **On a re-run, REGENERATE — never `read_file` the prior rendered report HTML** to "get the
   structure." Rebuild the data object from `state` + live tool outputs + the template **schema**;
   re-call `crrem get_pathway`. A stored data object may predate template/rule changes.

---

## Design System

All RSRA HTML output must conform to these rules. Claude must apply them on every run — never drift.

**Colors**
- Navy: `#12253A` — headers, section titles, strong text
- Green: `#4CAF82` — eyebrows, accents, positive signals, chart fills
- Muted: `#64748B` — secondary text, axis labels
- Page bg: `#F8F9FB`
- Section bg: `#fff`
- Border: `#E2E8F0`
- Warn: `#F59E0B` · Danger: `#EF4444`

**Typography**
- Font stack everywhere: `-apple-system,'Helvetica Neue',Arial,sans-serif`
- Zero `Georgia`, zero `serif`, zero `@import`, zero web fonts
- Section label: 9px, weight 600, `letter-spacing:.15em`, `text-transform:uppercase`, color `#1F6B45`
- Section title: 18px, weight 700, color `#12253A`, `border-bottom:1.5px solid #12253A`, `padding-bottom:8px`

**Section chrome pattern**
```html
<div class="section">
  <div class="section-label">EYEBROW LABEL</div>
  <h2 class="section-title">Section Title</h2>
  <!-- content -->
</div>
```

**Charts — inline SVG only**
- Zero external charting libraries (no Chart.js, D3, Plotly, etc.)
- Zero `<canvas>` elements
- Zero CDN `<script>` tags
- All SVG coordinates computed at generation time from the data being reported
- If data is unavailable for a chart, omit the chart entirely — no placeholder SVG

**Hard prohibitions**
- `Paged.js` — never reference or import
- `Georgia` or any serif font
- Any `@import url(...)` for fonts
- Any `<link rel="stylesheet">` or `<script src="...">` pointing to an external host
- External `<img src="https://...">` — all images must be inline SVG or data URIs

**Artifact output rules**
- Two-phase artifact: Phase 1 = loading skeleton, Phase 2 = full report
- Both phases use the **identical** file path — one artifact, updated in place
- Never save the Phase 1 skeleton to asset documents — only the completed Phase 2 report
- Numeric precision: 2 significant figures (`$1.4M` not `$1,427,000`; `42 kgCO₂e` not `41.7`)
- Mark all benchmark-derived estimates inline with `(est.)`
- The portfolio **report is the design-forward deliverable** (Reports/, gate-only). All
  working/checklist material — per-asset readiness, financial-parameter provenance, open
  questions, adjudication log, verification findings — goes in the ONE growing **helper file**
  per the shared pattern in `skills/helper-files/SKILL.md`: `save_file` to folder `Helper Files`
  as `[start date] - Helper Files - Portfolio Analysis.html` (start date fixed, stored in
  `state.helper`), regenerated from state at each phase. Phase/checklist sections:
  Config · Readiness+Params · Per-Asset · Aggregation · Verification gate · Report. Do not create
  standalone intermediate HTML.

---

## Step 0: Resolve Run Configuration

### 0A — Kickoff gate (run this before anything else)

Check for a prior kickoff file:
```
search_portfolio("portfolio analysis kickoff parameters IRR hurdle")
```

**If a kickoff file is found:** extract the confirmed parameters from it (IRR hurdle, exit
params, utility escalation, value method, add-ons, Audette account, scope). Skip to the
"Confirm before proceeding" block below — present the kickoff params as a summary and ask
the user to confirm or adjust before running.

**If no kickoff file exists:** do not proceed with the analysis yet. Tell the user:
> "Before I start the analysis, let me collect the run parameters. This will only take a minute."

Then follow the **`project-kickoff` skill** for project type **`portfolio-analysis`** — read
`skills/project-kickoff/project-types/portfolio-analysis.md` and work through all 6 questions
one at a time. The kickoff skill will save a parameter file; once it's saved, return here and
continue from "Confirm before proceeding."

**If the user explicitly provides all parameters inline** (e.g. "run with 15% hurdle, 2028
floor, CRREM on, account slug: greystar") and there is no prior kickoff file: accept the inline
values, skip the kickoff Q&A, but still present the "Confirm before proceeding" summary before
starting the analysis.

---

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `client_name` | (required) | Client name — used in report header and file naming |
| `portfolio_id` | (required) | Soapbox portfolio ID or name to query |
| `fund_filter` | all funds | Comma-separated fund names to include, or "all" |
| `irr_hurdle` | 15% | Minimum IRR for a measure to be recommended |
| `utility_escalation` | 3%/yr | Annual escalation applied to energy savings |
| `discount_rate` | 8% | Discount rate for NPV calculations |
| `exit_year_floor` | 2028 | Assets exiting before this year are moved to floor date |
| `retrofit_lead_months` | 18 | Measures needing > this many months to implement are deferred for near-exit assets |
| `target_years` | [2030, 2035, 2040] | Emissions scenario target years for CRREM comparison |
| `value_method` | inclusive | `inclusive` = NOI uplift capitalised at exit cap + added to terminal CF; `standalone` = IRR on savings only without exit value |
| `top_n_assets` | 10 | Number of assets shown in "Top N by value creation" table |
| `audette_account` | (ask if not known) | Audette customer account slug for `switch_customer_account` |
| `include_crrem` | false | Include CRREM pathway analysis: emissions trajectory chart, stranding analysis, pathway-alignment KPIs |
| `include_bps` | false | Include Building Performance Standards exposure analysis: BPS liability per asset, compliance cost if no action, fine avoidance as a measure benefit |
| `org_goal` | null | Custom organizational sustainability goal (e.g. "net zero by 2040", "50% emissions reduction by 2035"). If not provided, search Portfolio Docs for ESG policy statements, fund mandates, or investor commitments before asking. When set, all report sections that reference emissions trajectory or CRREM add a line showing gap/progress vs. this goal. |

Prompt for each required parameter. Save the confirmed set to a comment in the portfolio
thread so future runs can reuse them without re-entering.

### Confirm before proceeding

Display the resolved parameters in a compact table and ask: "Run with these parameters? (y to proceed, or change any value)"

```
Client:         [client_name]
Portfolio:      [portfolio name]
Funds:          [all / fund list]
IRR hurdle:     [X]%
Exit year floor: [YYYY]
Target years:   [YYYY, YYYY, ...]
Utility escal.: [X]%/yr
Discount rate:  [X]%
Value method:   [inclusive / standalone]
Audette acct:   [slug]
CRREM analysis: [yes / no]
BPS analysis:   [yes / no]
Org goal:       [goal statement / none]
```

---

## Phase 1: Readiness Check & Financial Parameter Collection

**Before prompting the user for any parameters, search Portfolio Docs for existing data.**
Exit years, cap rates, fund assignments, hold periods, and IRR targets are often already
uploaded as spreadsheets, IC memos, or fund term sheets. Extract what you can before asking.

### 1A — Search Portfolio Docs first

**If the user attaches a file inline in the thread** (e.g. a spreadsheet with exit years), its content is already in the message — read it directly. Do NOT web_fetch the attachment URL or the Supabase signed URL.

For documents already uploaded to the portfolio (not attached inline), two tools — pick by content type:

- **`read_portfolio_file(file_name)`** — for SPREADSHEETS and any file where exact
  cell values matter (exit years, cap rates, asset registers, utility tables).
  Returns row-aligned CSV per sheet. Semantic search chunks flatten tables and lose
  row alignment — never rely on `search_portfolio` for per-asset numeric parameters.
- **`search_portfolio(query)`** — for narrative documents (IC memos, ESG policies,
  audits) where you need relevant passages, not exact rows.

**Never web_fetch any URL to access portfolio docs.**

Workflow: `list_portfolio_files()` to see what exists → `read_portfolio_file` for each
financial spreadsheet → `search_portfolio` for narrative parameters.

Call `search_portfolio` with specific terms to find financial parameters:
```
search_portfolio("exit year cap rate hold period")
search_portfolio("IRR hurdle rate fund")
search_portfolio("acquisition model underwriting")
search_portfolio("ESG sustainability net zero emissions target")
```

Extract from the returned chunks:
- `exit_year` per asset
- `exit_cap_rate` per asset or fund
- `fund_name` assignments
- IRR hurdle rate
- Hold period assumptions
- Any sustainability/emissions goal (e.g. "net zero by 2040")

Use `list_portfolio_files` only to see what documents exist — it does not return file content. Use `search_portfolio` for all content access.

Only ask the user for parameters that couldn't be found in the docs. If you found partial data (e.g. exit years but no cap rates), confirm what you found and ask only for what's missing.

### 1B — Load all assets and build the UUID map

Call `query_portfolio_data()` to get every asset's UUID, name, and current metadata in one call. **Do this before anything else — the UUID map is required for all write-back operations.**

```
query_portfolio_data(include_metadata: true, analysis_ready_only: false)
```

The tool returns a **pipe-delimited text block**, one asset per line, in this format:
```
ID: <uuid> | Asset: <name> | Address: <addr> | Type: <type> | Built: <year> | GFA: <m²> | Audette: <audette_property_id> | ESPM: <espm_property_id> | Fund: <fund> | Exit: <year> @ <cap_rate>% | Lease: <lease_structure> | Metering: <metering_config> | Analysis ready: yes/no
```

Fields only appear when they have a value — a missing `Fund:` or `Exit:` field means that metadata has not been set yet.

**Parse each line** and build an internal map:
```
{ asset_name → { uuid, audette_property_id, espm_property_id, fund_name, exit_year, exit_cap_rate, lease_structure, metering_config, analysis_ready } }
```

Critical rules:
- `ID:` is always the first field — that is the asset UUID to use for all write-back calls.
- Asset UUIDs come ONLY from the `ID:` field in this response. Never extract UUIDs from file paths, URLs, Audette IDs, or any other source.
- `audette_property_id` is a top-level field (prefixed `Audette:` in the output), NOT inside the metadata block.
- `exit_year` and `exit_cap_rate` are in the metadata section (prefixed `Exit:`). If absent, these fields are unset and must be collected from docs or the user.
- Do NOT call `get_asset_record` per asset — `query_portfolio_data` already returns everything in one call.

Partition assets into:
- **Analysis-ready** (`metadata.analysis_ready: true`) — proceed
- **Missing params** — collect before proceeding
- **Disposed** (`metadata.status: 'disposed'`) — emissions inventory only

### 1C — Bulk-fill from register (if available)

If the user attaches a spreadsheet in the thread, its content is already in the message — read it directly from the message context. Do NOT web_fetch any URL to access an attached file.

If a spreadsheet or asset register exists in the portfolio files, read it with
`read_portfolio_file(file_name)` — this returns actual rows, so each asset's exit
year/cap rate stays glued to its name. Match rows to the UUID map from 1B by asset
name (fuzzy match). Then write parameters back:

```
update_asset_metadata(asset_id: "<uuid-from-1B>", updates: { fund_name: "<fund>", exit_year: <year>, exit_cap_rate: <rate> })
```

Or in bulk when the same value applies to multiple assets:
```
bulk_update_metadata(asset_ids: ["<uuid1>", "<uuid2>", ...], updates: { exit_year: <year> })
```

**Always use UUIDs from the 1B map. Never guess or construct a UUID from any other source.**

Auto-populate any field found in the register. Only prompt for what's still missing.

### 1D — Collect missing parameters asset-by-asset

For each asset still missing required fields, present a focused card:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[N/total] — [Asset Name]   [fund] · [type]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Audette linked: [building name]
  Exit year       → ?  (e.g. 2030, or 'disposed')
  Exit cap rate   → ?  (e.g. 4.5%)
  Lease structure → gross / nnn / modified-gross / rubs / green-lease
  Metering config → master / individual / submeter-passthrough
  Jurisdiction    → [auto-detected or blank]
  BPS liable      → [yes / no / unknown]   ← only shown if include_bps: true
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Only show missing fields. `skip` leaves null and excludes the asset from analysis.
`disposed` marks the asset and includes it in emissions inventory only.

**Check the leasing brochures per asset (part of the workflow, not optional).** Before setting the
split, pull each asset's current leasing marketing — `apartments.com`, the property's own site,
Zillow rentals (via `brave-search`/`web_fetch`) — and read it for two things: (1) **whether
utilities are included** in rent or itemized as resident-paid ("utilities included", "resident pays
electric/gas/water", a RUBS/flat-fee line) — this is current, market-facing evidence of who bears
each fuel and directly sets/confirms the capture split; and (2) the **amenity set** (pool, spa,
clubhouse, fitness, common laundry, EV stalls, garage) — amenities are landlord-paid common loads
that carry their own 100%-owner capture AND surface measure opportunities (pool-heat HP, common-area
controls, EV). Cite the listing + URL; a brochure statement outranks a building-form inference.

Then determine LL/TT allocation **inline** (do NOT call `get_ll_capture` — it is broken in prod; the
hosted runtime ships no Python). Set `ll_capture_pct` per the **end-use capture map** in economics
correctness rules 1–2 above: master-metered/landlord-paid loads (central plant, elevators, common,
amenity) at their RUBS-recovery capture (~10% net owner where RUBS applies — verified per rule 1b —
or ~100% if the owner absorbs); in-unit tenant-metered ≈ 0.0–0.05; BPS fine avoidance = 1.0 always;
net owner utility savings = `capture% × gross` (≈$0 on low-capture/RUBS assets — never the gross).
If `include_bps: false`, treat fine avoidance as "not assessed" and omit it from owner NOI.

Write results to asset metadata:
```
update_asset_metadata(asset_id: "<asset_id>", updates: <params_object>)
```

Show edge-case warnings inline (NNN paradox, solar consent, RUBS recovery, BPS liability).

### 1E — Readiness summary

Report before proceeding:
```
[N_ready] assets ready · [N_missing] skipped (missing params) · [N_disposed] disposed
```

If `N_ready = 0`: stop and ask the user to provide financial parameters.

Confirm:

### 1E-bis — Load confirmed analysis-ready assets for the run

```sql
SELECT id, name, address, property_type, metadata
FROM assets
WHERE portfolio_id = '<portfolio_id>'
  AND metadata->>'analysis_ready' = 'true'
ORDER BY name;
```

Count: `N_ready` assets ready to analyze.

Confirm:
> "Found [N_ready] analysis-ready assets. [N_skipped] assets skipped — missing [fields].
> Ready to run? (y to proceed, or list specific assets to exclude)"

### 1F — Identify Audette gaps

For each asset loaded in 1B, check the `audette_property_id` column (NOT `metadata.audette_building_id` — that field does not exist). Assets without an Audette link will have lower-quality energy data.

| Status | Count | Treatment |
|--------|-------|-----------|
| `audette_property_id` not null | N | Full physics model from Audette MCP |
| `audette_property_id` is null | N | Use documents (PCA/audit) + BPD MCP benchmark — label all values `(est.)` |

Report the gap count before proceeding. Do not stop — assets without Audette are included with
lower confidence, clearly labeled.

---

## Phase 2: Phase 1 Artifact — Loading Skeleton

**Emit the loading skeleton immediately** (before any per-asset processing begins) at file path
`{client-slug}-portfolio-analysis.html`. Use the consulting aesthetic: navy `#12253A` header,
pure sans-serif (`-apple-system,'Helvetica Neue',Arial,sans-serif`), zero Paged.js, zero CDN.

```html
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;background:#F8F9FB;color:#1A1A2E}
  .report{max-width:960px;margin:0 auto;padding:40px 0 80px}
  .doc-header{background:#12253A;color:#fff;padding:32px 40px 0}
  .eyebrow{font-size:8px;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:#4CAF82;margin-bottom:8px}
  .port-name{font-size:28px;font-weight:700;margin:8px 0 4px}
  .port-sub{font-size:13px;font-weight:300;color:rgba(255,255,255,.65);margin-bottom:24px}
  .meta-strip{background:#1A3550;padding:8px 40px;display:flex;justify-content:space-between;font-size:11px;color:rgba(255,255,255,.5)}
  .kpi-bar{display:flex;gap:2px;margin:2px 0}
  .kpi{flex:1;background:#fff;padding:14px 16px;border:1px solid #E2E8F0}
  .kpi-lbl{font-size:9px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#64748B}
  .shimmer{background:linear-gradient(90deg,#e2e8ef 25%,#f1f5f9 50%,#e2e8ef 75%);background-size:200% 100%;animation:sh 1.4s infinite;border-radius:3px;display:block}
  @keyframes sh{0%{background-position:200% 0}100%{background-position:-200% 0}}
  .section{padding:32px 40px;background:#fff;margin-bottom:2px}
  .status{display:flex;align-items:center;gap:8px;font-size:12px;color:#64748B;margin-bottom:16px}
  .dot{width:6px;height:6px;border-radius:50%;background:#4CAF82;animation:pu 1.2s ease-in-out infinite;flex-shrink:0}
  .dot:nth-child(2){animation-delay:.4s}.dot:nth-child(3){animation-delay:.8s}
  @keyframes pu{0%,100%{opacity:.25}50%{opacity:1}}
</style>
<div class="report">
  <div class="doc-header">
    <div class="eyebrow">Portfolio Decarbonization Analysis</div>
    <div class="port-name">[CLIENT NAME] Portfolio</div>
    <div class="port-sub">[N] assets · [FUND LIST]</div>
  </div>
  <div class="meta-strip">
    <span>Soapbox Sustainability Intelligence</span>
    <span>CONFIDENTIAL · [DATE]</span>
  </div>
  <div class="kpi-bar">
    <div class="kpi"><div class="kpi-lbl">Total CapEx (mid)</div><div class="shimmer" style="width:80px;height:22px;margin-top:6px"></div></div>
    <div class="kpi"><div class="kpi-lbl">Value Creation</div><div class="shimmer" style="width:80px;height:22px;margin-top:6px"></div></div>
    <div class="kpi"><div class="kpi-lbl">Emissions Reduction</div><div class="shimmer" style="width:80px;height:22px;margin-top:6px"></div></div>
    <div class="kpi"><div class="kpi-lbl">Assets Above Hurdle</div><div class="shimmer" style="width:60px;height:22px;margin-top:6px"></div></div>
  </div>
  <div class="section">
    <div class="status"><span class="dot"></span><span class="dot"></span><span class="dot"></span>Running analysis across [N] assets…</div>
    <span class="shimmer" style="width:100%;height:40px;margin-bottom:2px"></span>
    <span class="shimmer" style="width:100%;height:40px;margin-bottom:2px"></span>
    <span class="shimmer" style="width:100%;height:40px;margin-bottom:2px"></span>
    <span class="shimmer" style="width:100%;height:40px"></span>
  </div>
</div>
```

---

## Phase 3: Per-Asset Analysis

**Audette is the mandatory primary data source. Call it for EVERY linked asset. Do not skip Audette and proceed on docs alone — if Audette is skipped, the analysis is incomplete and must say so.**

Process assets in sequence, streaming one progress line per asset as it completes.
Stream to the conversation: `✓ Landmark at Colony Park (7/39) — 4 measures above hurdle, $2.1M CapEx, +$1.4M value`

**Progress lines are mandatory, not optional.** During any fan-out longer than ~5 assets
(pulling models, decarb plans, running DCF), emit a short text line at least every 5
assets — e.g. `Pulled decarb plans 15/39…`. Never go more than ~10 tool calls without
a visible line of text; a silent multi-minute tool storm looks like a hang to the user.

### 3A — Pull all sources, reconcile, write back to Audette

For every asset with an `audette_property_id`: call Audette FIRST (Steps 1–3), then search docs (Step 4), then reconcile (Step 5), then write back (Step 6). **The doc search in Step 4 is secondary and supplementary — never a replacement for Audette.**

If you have already searched docs during Phase 1 (financial params), that does NOT count as Step 4. Step 4 must be a targeted per-asset search for energy measures, equipment data, and utility consumption — separate from the financial param search.

**If the Audette MCP is available:** complete Steps 1–6 for every linked asset. Completing the analysis on docs alone when Audette is available is not acceptable.

**If the Audette MCP is unavailable at runtime:** read uploaded docs only, build the plan from those, note the gap prominently, and skip the write-back steps. Do not silently omit this notice.

#### Step 1 — Switch to the correct Audette account

```
switch_customer_account("<audette_account_slug>")
```

Use `list_customer_accounts()` if unsure which slug applies — pick the account whose name matches the client.

#### Step 2 — Build the property map

```
list_properties()
```

Returns `{ property_uid, property_name }` pairs for the active account. Build:
`{ property_uid → property_name }`

Each asset's `audette_property_id` is a **property UID** in this map. Properties and
building models are different objects: analysis tools take a `building_model_uid`,
and one property can contain **multiple** building models.

**NEVER call bare `list_buildings()`** — large accounts contain thousands of buildings
and the result will not fit. Use `audette__find_buildings` instead (Step 3).

#### Step 3 — Resolve each asset's property to its building models

For each Soapbox asset where `audette_property_id` is not null:

```
property_name = property_map[asset.audette_property_id]
audette__find_buildings(name: property_name)
→ returns all building models whose property_name or building_name matches,
  each with building_model_uid, gross_floor_area, fund_name, modelling_status
```

Then for **every** returned building model:
```
get_building_model_details(building_model_uid)
```

**Multi-building properties — aggregate to the asset level:**
- CapEx, annual savings, and emissions reductions: **sum** across the property's buildings
- EUI and carbon intensity: **floor-area-weighted average** (weight by `gross_floor_area`)
- Measures: union the lists; prefix each with the building name when a property has >1 building (e.g. "Bldg A — LED retrofit")
- CRREM status: use the weighted carbon intensity for the property-level comparison
- Never report just one building of a multi-building property as if it were the whole asset

If `audette__find_buildings` returns no match for the property name, note the gap and
fall back to the BPD benchmark path — do not guess a different building.

Pull from the response:
- `current_eui_kwh_m2` — site EUI from Audette calibrated model
- `carbon_intensity_kg_co2_m2` — Scope 1+2, location-based
- `crrem_pathway_target_2030` — CRREM 1.5°C target for asset type *(only if include_crrem: true)*
- `crrem_misalignment_year` *(only if include_crrem: true)*
- `equipment_schedule` — age and condition of major systems
- `recommended_measures[]` — Audette decarb plan, each with:
  - `measure_type`, `capex`, `install_cost`, `annual_savings_kwh`, `annual_savings_$`

Also pull the capital plan:
```
list_building_plans(building_model_uid)   # once per building model in the property
→ get_carbon_reduction_plan_by_id(plan_id)   # for the active plan
```

This gives the full measure list with costs, savings, and implementation schedule.

#### Step 4 — Search uploaded documents as secondary source

After loading Audette data, call `search_portfolio` with the asset name to pull content from energy assessments. **Do not navigate to URLs or use web_fetch — `search_portfolio` is the only way to access document content in a portfolio thread.**

```
search_portfolio("energy audit [asset name]")
search_portfolio("engineering study [asset name]")
search_portfolio("capital plan [asset name]")
search_portfolio("measures recommendations [asset name]")
search_portfolio("utility consumption EUI [asset name]")
```

From the returned chunks, extract:
- Measures recommended (type, description, estimated cost, estimated savings)
- Measures already completed (if noted as "installed", "completed", "replaced")
- Equipment condition observations that differ from Audette's equipment schedule
- Utility consumption data if more recent than Audette's baseline

#### Step 5 — Reconcile Audette vs. uploaded docs

Build a unified measure list per asset, reconciling all sources **against the verifier's
rubrics**. The first time you reconcile a given data type in a run, pull its checklist —
`verifier__get_verification_checklist(data_type)` for `energy`, `equipment`, `physical`,
`financial` as relevant — and follow it (e.g. energy: sanity-check units before comparing
values, cross-check against ESPM/BPD peer bands; financial: every figure originates from a
deterministic engine or cited doc). The checklists are the same methodology `decarb-plan` uses;
they replace the ad-hoc confidence ladder this skill used to carry.

**Source certainty:** Audette and uploaded field documents (energy audits, PCAs,
engineering studies, drawings, condition assessments) carry **equal weight**. Neither is
authoritative over the other — a field-verified cost estimate from an engineering study is
as reliable as an Audette model figure. Only
BPD MCP benchmark estimates (no Audette, no uploaded doc) are lower certainty and must be labeled `(est.)`.

1. **De-duplicate**: if a measure appears in both Audette and a doc (e.g. LED upgrade),
   keep one entry. Use whichever source has the more detailed or recent cost/savings data.
   If figures differ by **> 25%**, this is a **material conflict**: do NOT silently pick one.
   Auto-apply the reconciliation hierarchy (measured/ESPM actuals > audit-reported 12-mo >
   Audette modeled > BPD estimate) to choose the working value, **and record the conflict** so
   it is durable and surfaces in the report's Data Quality section:
   ```
   verifier__record_finding(
     asset_id: "<Soapbox asset UUID>",       # never the Audette uid
     claim: "<field> for <asset>: Audette says X, <doc> says Y (>25% apart)",
     verdict: "conflict",
     severity: "high",                         # material to CapEx/savings/IRR → high; cosmetic → low
     kind: "data-quality",
     evidence: ["Audette model: X <unit>", "<doc name>: Y <unit>"],
     sources: ["Audette", "<doc name>"]
   )
   ```
   Set `severity` by materiality to CapEx, savings, or the IRR screen. At screening scale the
   hierarchy suggestion is applied automatically (no per-asset user gate) — the finding is the
   audit trail, and high-severity findings are the ones surfaced for optional review at Phase 4.

2. **Mark completed measures**: if any source shows a measure was already installed (e.g.
   "LED retrofit completed 2023"), **remove it from forward-looking CapEx**. Do not
   double-count. Doc evidence of completion overrides Audette if Audette still lists it
   as recommended.

3. **Confidence levels** (the verifier's two-source rule):
   - `High` — two or more independent sources agree (Audette + doc, or two docs)
   - `Medium` — single source, either Audette or a field doc (provisional)
   - `Low` — BPD MCP benchmark only (no Audette, no uploaded doc); these assets are handled as
     `needs-data` in Step 3C and excluded from the verified roster and headline aggregates

4. **Feasibility check per measure**:
   - Technically feasible given building vintage and HVAC config?
   - Can it be permitted and built within the hold period?
     (Heat pumps / envelope: 18+ months lead; LED/controls: 3–6 months)
   - Does LL/TT allocation flow savings to landlord?
     (NNN tenant-pays = near-zero NOI capture on in-unit measures)
   - Requires tenant cooperation? (solar on leased roof, sub-metering, RUBS rollout)

5. **IRR screen last** — apply IRR hurdle only after measures are compiled, de-duped,
   feasibility-checked, and LL/TT allocated. Exclude feasibility failures before IRR screen.

#### Step 6 — Write reconciled data back to Audette

Audette is the write-back destination (system of record for future runs). After
reconciliation, update it with anything the docs revealed that Audette doesn't yet reflect:

1. **Mark completed measures** — for any measure docs show as already installed, use
   `update_custom_plan_measures` to remove it from the active decarb plan.

2. **Submit utility data** — if uploaded utility bills are more recent than Audette's
   baseline, submit via `add_building_utility_data` to recalibrate the carbon reduction plan.

3. **Equipment updates** — if docs show equipment replacement not in Audette's schedule,
   call `edit_building_attributes` to update it.

4. **Flag calibration gaps** — if the Audette model is based on design specs rather than
   measured data, note: "Audette model not yet calibrated — submit utility bills to recalibrate."

**The goal: Audette should be more accurate at the end of the run than at the start.**

For assets with no Audette link and no uploaded docs:
- Call `get_statistics(analyze_by: "site_eui", filters: {building_type: ["<asset_type>"], climate_zone: ["<zone>"]})` on BPD MCP to get the median EUI for the asset's building type + climate zone. Use the 50th-percentile value as the baseline EUI — label every derived value `(est.)`.
- **Circular benchmarking rule:** Never use a BPD-derived benchmark EUI as the subject EUI in a subsequent BPD `get_eui_percentile` call. Skip the percentile comparison for that asset.

### 3B — Establish hold window (NO base DCF model)

There is **no `run_dcf` base model** — value creation is an **incremental** bridge, not a
levered whole-asset DCF, so a going-in NOI model is not required (and `run_dcf` is broken in prod
anyway — see ground rule 2). `compute_plan_economics` computes IRR and value creation from the NOI
**delta** (the incremental owner-share flows: capex out, owner utility savings + ancillary +
avoided fine in, terminal uplift = annual NOI delta ÷ exit cap) — it does **NOT** take the going-in
NOI level. **Never ask the user for going-in NOI, and never block or defer a run because it is
missing.** For each asset just fix the hold window:
```
hold_exit_year = max(asset.exit_year, exit_year_floor)
install→exit years = each measure's install_year … hold_exit_year
```
If `hold_exit_year - current_year < 1` (already past exit): mark disposed, skip financial analysis.

### 3C — Compute per-asset economics via `compute_plan_economics` + persist to the retrofit register

The economics run through **`compute_plan_economics`** (Steps 1–6 below); the **retrofit
(building-science) agent** frames the candidates, supplies feasibility/staging doctrine, and is
the **system of record** for the resulting measures (Step 0 and Step 7). Persisting to the
register means a later `decarb-plan` engagement on any of these assets **inherits** this work.

**Step 0 — Candidate framing & feasibility doctrine (retrofit agent):**

- Once per asset, call `retrofit__propose_candidates(asset_attributes: {archetype, jurisdiction,
  equipment, ...})` with the reconciled asset attributes — it returns the source checklist and
  origination prompts that make sure you haven't missed a candidate family.
- Pull the building-science doctrine that governs feasibility and phasing:
  `retrofit__get_retrofit_playbook('staging')` for sequencing against capital events/end-of-life,
  and the relevant measure-family playbook (`hvac`, `envelope`, `dhw`, `controls-rcx`,
  `solar-storage`, `electrification-staging`) for any measure whose feasibility you're scoring.
  This doctrine — combustion safety after air-sealing, A2L refrigerants, envelope-before-HVAC
  sizing — informs the feasibility check in Step 5 below and the `feasibility.score` in Step 7.

For each reconciled measure per asset, build the owner-share cash flows for
`compute_plan_economics` — do NOT use simple payback math, and do NOT call `get_ll_capture`
(broken in prod).

**Step 1 — LL/TT allocation (inline capture map — per correctness rules 1–2, no tool):**

Set `ll_capture_pct` per measure from **who BEARS the cost of that end-use** (metering AND
RUBS-recovery), not a blended building number and not "who pays the meter":
| End-use the measure touches | `ll_capture_pct` |
|---|---|
| Master-metered / landlord-paid (central heating/DHW plant, elevators, common/garage ventilation, common lighting, amenity) — **jurisdiction ALLOWS RUBS** (assume owner rebills up to ~90%) | **≈0.10** (net owner) — the default for master-metered in a RUBS jurisdiction |
| Same loads, but owner **absorbs** the utility (documented gross lease / RUBS not permitted) | **1.0 (100% owner)** |
| In-unit tenant-metered loads (in-unit HVAC/appliances) | tenant-metered owner share (**0.0–0.05**) |
| Solar under **Virtual Net Metering (VNM)** allowed | **0.80** (owner) |
| BPS fine avoidance | **1.0 (100% owner)** — always, regardless of lease/metering |

**Never read "master-metered" as "100% owner"** — that is the common error; master-metered just
means the owner pays the meter, and under RUBS ~90% is rebilled to tenants. Then compute **net
owner utility savings** = `measure.annual_savings_$ × ll_capture_pct`, and for a **fuel switch**
net any owner-side load increase (do not credit the owner the whole gas cut while assigning the new
electricity to tenants — rule 1). Never inherit Audette's 15% account default. Tenant-side savings
are tracked separately and do NOT enter the value bridge.

**Step 2 — Retrofit lead time feasibility:**
- Major capital (HVAC, electrification, envelope, solar): requires 18+ months — defer if hold_period < 1.5 yrs
- Compliance-required measures: never defer regardless of hold period
- Controls/LED/commissioning: 3–6 months — feasible for any hold period

**Step 3 — Value-inclusive IRR + value bridge (call `compute_plan_economics`):**

Build the per-year owner-share flow schedule for the measure (or, for the asset roll-up, all
recommended measures combined) and call the one working engine:
```
compute_plan_economics(
  flows: [ for each year install_year … hold_exit_year:
    { year,
      incremental_capex:    <incremental capex over like-for-like, in the install year(s); positive>,
      owner_utility_savings: <measure.annual_savings_$ × ll_capture_pct, net of owner-side load increase,
                              ESCALATED to year Y: × (1 + utility_escalation)^(Y − install_year)>,
      ancillary_revenue:     <owner-share solar/EV/DR this year — risk-adjusted, NOT a perpetuity>,
      incentives:            <IRA credit received this year>,
      bps_fine_avoidance:    <annual fine avoided, ESCALATED with the standard's fine schedule — only if
                              non-compliant on the GOVERNING pathway> } ],
  exit_cap_rate: asset.exit_cap_rate,
  exit_year:     hold_exit_year,
  discount_rate: <portfolio discount rate, default 0.08>
)
→ returns irr_incremental, the full cashflow schedule, and the value-creation waterfall
  (capitalized owner savings & ancillary ÷ exit cap, PV of fine avoidance, net_value_creation,
   terminal exit-value delta)
```
Feed only auditable inputs — never pre-compute IRR, capitalization, or PV yourself. **Apply
`utility_escalation` (the run parameter, default 3%/yr) to `owner_utility_savings` each year** —
savings grow as utility rates rise, so a flat savings line understates later-year NOI and the
capitalized exit value. The terminal exit uplift capitalizes the STABILIZED (exit-year, escalated)
owner-NOI improvement ÷ exit cap.

**For batch screening across assets:** loop `compute_plan_economics` per asset (there is no
`screen_measure_portfolio` — it is broken). One call per asset (all its recommended-measure flows)
gives the asset's value creation + IRR; per-measure calls give per-measure IRR for the screen.

**Step 4 — Use the engine's outputs directly:**

Use `irr_incremental` and the waterfall from `compute_plan_economics` — do **not** recompute with a
local `dcf_engine.py` script (not shipped) and do **not** call `run_dcf`/`run_intervention_irr`
(broken). The value bridge is unlevered and incremental:
- Outflow at `install_year` = incremental capex (over like-for-like)
- Annual inflow = net owner-NOI improvement (owner utility savings + ancillary + avoided fine)
- Terminal uplift at `exit_year` = annual NOI improvement ÷ exit cap  ← the reported value creation

**Step 5 — IRR screen (record BOTH IRRs from `compute_plan_economics`):**

Capture `irr_excl_exit` AND `irr_incremental` for every measure — they drive the two screens and
the A/B/C trajectory (Phase 4E). The **roster's "recommended" status uses `irr_incremental`**
(value-inclusive, scenario B — the standard recommendation bar); `irr_excl_exit` additionally tags
which measures also clear operationally (scenario A).

| Result | Action |
|--------|--------|
| `irr_incremental` ≥ `irr_hurdle` | Include in recommended measures (also tag `pays_operationally: true` if `irr_excl_exit` ≥ hurdle) |
| `irr_incremental` < hurdle | Exclude from recommendations; include in "below hurdle" table |
| Compliance-required measure | Include regardless of IRR; flag as mandatory |

> This IRR result is an **input** to the final status, not the status itself. Step 7 composes it
> with the `retrofit__screen_measures` label to produce the authoritative reported status — a
> measure that clears the IRR hurdle here can still be `screened-out`/`needs-data` if it fails the
> building-science feasibility or provenance screen. Do not assign a final status at this step.

**Step 6 — IRA incentive check:**

For measures with IRA eligibility:
- Solar/geothermal/battery: IRA §48E — 30% base ITC (REIT direct pay eligible)
- Envelope/HVAC/lighting: IRA §179D — up to $5.65/SF (only if renovation qualifies)
- Multifamily energy efficiency: §45L — $500–$5,000/unit
- Low-income / energy community bonus: check census tract (+10pp on §48E)

Reduce `net_capex = install_cost × (1 - ira_credit_rate)` for IRA-eligible measures.
Re-run IRR on `net_capex` — some measures below hurdle on gross may pass on net.

Label net capex separately from gross in all tables.

**Step 7 — Evaluate, persist, and screen through the retrofit register:**

Now that `compute_plan_economics` has produced the economics for the measure, record it in the
retrofit register through the provenance gate, then screen it. This is what makes the measure
durable and disciplined — the gate rejects any number without engine or source provenance.

1. **`retrofit__evaluate_measure`** — feed the engine outputs in as engine-provenanced fields.
   `feasibility.score` is an **integer 1–5** informed by the Step 0 playbook doctrine; every econ
   field carries `engine: "compute_plan_economics"` or a cited `source`:
   ```
   retrofit__evaluate_measure(
     asset_id: "<Soapbox asset UUID>",
     measure: {
       measure_family: "hvac", name: "...", candidate_source: "audette|pca|audit|originated",
       cost:                 { value: <net or gross incremental capex>, unit: "USD", engine: "compute_plan_economics" },
       owner_savings_annual: { value: <annual_savings_$ × ll_capture_pct, net of load increase>, unit: "USD/yr", engine: "compute_plan_economics" },
       noi_delta_annual:     { value: <annual owner-NOI improvement>, unit: "USD/yr", engine: "compute_plan_economics" },
       cap_rate:             { value: <exit_cap_rate>, unit: "ratio", source: "<verbatim source of the cap rate>" },
       incentives:           [{ value: <ira_credit_$>, unit: "USD", program: "§48E|§179D|§45L", eligibility_basis: "...", source: "<statute/rule>" }],
       feasibility:          { score: <1-5>, site_conditions: "...", disruption: "none|light|in-unit|vacancy-required", contractor_reality: "...", staging: "<from staging playbook>", sources: ["<audit/PCA/Audette/playbook>"] },
       future_proofing:      { rationale: "...", citations: ["..."] }
     }
   )
   ```
   **Populate `future_proofing.citations` ONLY when there is a genuine reason to keep a measure
   despite failing economics** — a pending code/BPS requirement, a forced end-of-life replacement,
   or a documented future-proofing rationale. Leave it **empty** otherwise. `screen_measures`
   labels any value-failing measure with non-empty citations `defensive` instead of `screened-out`;
   filling citations reflexively on every measure inflates the roster and lets weak measures escape
   the value screen. Empty citations let poor economics screen out honestly.
   The tool computes `exit_value_delta = noi_delta_annual ÷ cap_rate` server-side as a screening
   proxy — **do not** use it in report value-creation tables (those stay `compute_plan_economics`'s
   waterfall / terminal exit-value output). If the gate rejects a field, supply the real provenance —
   never fabricate an `engine`/`source` string to get past it.

2. **`retrofit__screen_measures(asset_id)`** — labels each measure
   `recommended / defensive / screened-out / needs-data` (feasibility ≥ 3, simple payback ≤ 15y,
   NOI-positive). This persists the label onto the register.

3. **Compose the portfolio label** (this is the reported status — the two screens must not fight):

   | `screen_measures` label | DCF IRR vs `irr_hurdle` | **Reported status** |
   |---|---|---|
   | `recommended` | IRR ≥ hurdle | **recommended** |
   | `recommended` | IRR < hurdle | **below hurdle** |
   | `defensive` | any | **defensive** (future-proofing) |
   | `screened-out` | any | **screened out** (name the failing test) |
   | `needs-data` | — | **needs-data** (excluded from roster + headline aggregates) |
   | any | compliance-required | **recommended (mandatory)** regardless of IRR |

4. **BPD-only assets** (no Audette, no doc): do NOT call `evaluate_measure` — its provenance gate
   will reject the `(est.)` numbers. Label these measures `needs-data`, keep them in the report
   for visibility, and **exclude them from the verified roster and headline KPI aggregates**.

5. **Register edits** — if a later step changes a measure's lifecycle status (e.g. marking one
   deferred or implemented), apply it via `retrofit__update_measure_state(asset_id, measure_id,
   status, note)`, not by editing local state — the register is the system of record.

> Note: `screen_measures`/`evaluate_measure` save sequentially per measure. Across 30–40 assets
> this is slower than a batch write but does not block; it is a known v1.1 batching follow-up.

### 3D — Asset-level output

For each asset, compile:

```json
{
  "asset_id": "...",
  "asset_name": "...",
  "fund": "GEdR",
  "exit_year": 2030,
  "exit_cap_rate": 0.045,
  "hold_period_years": 4,
  "gav": null,
  "audette_eui": 85.2,
  "carbon_intensity_kg": 42,
  "crrem_status": "above_pathway",        // only if include_crrem: true
  "crrem_misalignment_year": 2029,        // only if include_crrem: true
  "ll_capture_pct_avg": 0.72,
  "lease_structure": "modified-gross",
  "metering_config": "master-metered",
  "jurisdiction": "Boston",
  "bps_liable": true,                     // only if include_bps: true
  "recommended_measures": [
    {
      "measure": "LED lighting retrofit",
      "category": "LED lighting",
      "status": "recommended",
      "capex_gross": 280000,
      "capex_net": 196000,
      "ira_credit": "§179D 30%",
      "annual_savings": 31000,
      "ll_capture_pct": 1.0,
      "annual_noi_uplift": 31000,
      "exit_value_uplift": 688000,
      "install_year": 2026,
      "irr": 0.21,
      "value_creation": 688000,
      "value_per_tco2": 38222,
      "emissions_reduction_tco2": 18,
      "data_confidence": "High"
    }
  ],
  "below_hurdle_measures": [...],   // same shape as above, status: "below hurdle"
  "deferred_measures": [...],       // same shape as above, status: "deferred"
  "total_capex_gross": 1400000,
  "total_capex_net": 980000,
  "total_value_creation": 2100000,
  "total_noi_uplift_annual": 94500,
  "total_emissions_reduction_tco2": 67,
  "compliance_cost_if_no_action": 45000
}
```

Stream one line per asset as it completes.

### 3E — Build supporting data arrays for the XLSX companion

After all assets complete, flatten the per-asset outputs into two arrays the XLSX template requires for analyst verification:

**`all_measures`** — every measure across all assets (recommended + below hurdle + deferred), one row per measure:
```json
[
  {
    "asset_name": "Observer Park",
    "fund": "GGIF",
    "measure": "LED lighting retrofit",
    "category": "LED lighting",
    "status": "recommended",
    "install_year": 2026,
    "capex_gross": 280000,
    "ira_credit": "§179D 30%",
    "capex_net": 196000,
    "annual_savings": 31000,
    "ll_capture_pct": 1.0,
    "annual_noi_uplift": 31000,
    "exit_value_uplift": 688000,
    "irr": 0.21,
    "value_creation": 688000,
    "value_per_tco2": 38222,
    "emissions_reduction_tco2": 18,
    "data_confidence": "High"
  }
]
```

**`asset_source_data`** — raw inputs per asset (Audette data + DCF parameters) for analyst verification:
```json
[
  {
    "asset_name": "Observer Park",
    "fund": "GGIF",
    "property_type": "Multifamily",
    "gfa_m2": 12400,
    "year_built": 1998,
    "exit_year": 2031,
    "exit_cap_rate": 0.045,
    "gav": null,
    "hold_period_years": 5,
    "eui_kwh_m2": 85.2,
    "ghgi_kg_m2": 42.0,
    "baseline_emissions_tco2": 521,
    "lease_structure": "modified-gross",
    "metering_config": "master-metered",
    "jurisdiction": "Boston",
    "audette_linked": true,
    "data_source": "Audette calibrated model",
    "data_quality": "High"
  }
]
```

---

## Phase 4: Portfolio Aggregation

After all assets complete:

### 4A — Portfolio KPIs

| KPI | Formula |
|-----|---------|
| Total CapEx (gross) | Σ all recommended measures, all assets |
| Total CapEx (net of IRA) | Σ net_capex |
| Total value creation | Σ value_creation (at exit cap) |
| Total NOI uplift (annual) | Σ annual_noi_uplift |
| Total emissions reduction | Σ emissions_reduction_t_co2 |
| Assets above hurdle | Count where any recommended measure exists |
| Assets fully pathway-aligned (2035) | Count where carbon_intensity ≤ CRREM 2035 target after measures — **only if `include_crrem: true`** |
| Compliance exposure (no action) | Σ compliance_cost_if_no_action — **only if `include_bps: true`** |

Report all values with 2 significant figures: `$14M`, `$2.1M`, `68 tCO₂e`, `22 assets`.

### 4B — Fund-level breakdown

Group by `fund_name`. For each fund:

| Fund | Assets | CapEx (net) | Value Creation | Emissions Reduction | Avg IRR |
|------|--------|-------------|----------------|---------------------|---------|
| GEdR | 12 | $5.2M | $8.4M | 320 tCO₂ | 18% |
| GGIF | 9 | $3.1M | $4.7M | 190 tCO₂ | 22% |

### 4C — Top-N by value creation

Sort by `total_value_creation DESC`. Show top `top_n_assets` (default 10).

| Rank | Asset | Fund | Exit | CapEx Net | Value Created | Lead Measure |
|------|-------|------|------|-----------|---------------|--------------|
| 1 | Observer Park | GGIF | 2031 | $1.8M | $4.2M | Heat pump retrofit |

### 4D — Measure category aggregate

Roll up recommended measures across all assets by category:

| Category | Assets | Total CapEx Net | Value Creation | tCO₂ Reduced |
|----------|--------|-----------------|----------------|--------------|
| LED lighting | 28 | $2.1M | $3.8M | 120 tCO₂ |
| Smart HVAC/controls | 15 | $4.2M | $6.1M | 240 tCO₂ |
| Heat pump / electrification | 8 | $12M | $9.4M | 580 tCO₂ |
| Solar PV | 11 | $3.4M | $2.8M | 95 tCO₂ |
| EV charging | 19 | $1.9M | $1.1M | — |
| Envelope | 6 | $5.8M | $4.2M | 180 tCO₂ |

### 4E — Emissions trajectory: three-scenario time series (2025–2050) *(only if `include_crrem: true`)*

Skip this section entirely if `include_crrem: false`. Do not produce the chart, the scenario JSON, or the stranding flag.

Build a year-by-year portfolio emissions model for three scenarios and the CRREM 1.5°C pathway. This is the centrepiece of the report — it shows where the portfolio is going and what each investment strategy delivers.

**THE CENTRAL QUESTION this analysis answers:** *how far down the carbon-reduction curve can the
portfolio get under three progressively less-conservative capital screens?* Model BAU as the
reference, then three deployment scenarios — each is the SAME measure set filtered by a different
economic bar. Each scenario is cumulative over the one before it in ambition.

| Scenario | Definition |
|----------|-----------|
| **Business as Usual (BAU)** | No decarb capital deployed. Only passive grid decarbonization applies to Scope 2 (~3.5%/yr US multifamily, varies by grid region). Reference line. |
| **A — IRR ≥ hurdle, EXCLUDING exit residual** | Deploy every measure whose **`irr_excl_exit` ≥ `irr_hurdle`** (operating cashflows only: owner utility savings + ancillary + annual avoided fine − capex + incentives; **NO** capitalized exit-value uplift). The "pays for itself operationally" set. Shallowest curve. |
| **B — IRR ≥ hurdle, INCLUDING exit residual** | Deploy every measure whose **`irr_incremental` ≥ `irr_hurdle`** (value-inclusive: operating **+** the capitalized exit-value uplift / avoided-fine capitalization folded into the exit year). A superset of A — the exit residual pulls more measures over the bar. Deeper curve. |
| **C — B + max solar (BTM + VNM)** | Scenario B **plus** on-site solar sized to the maximum feasible: behind-the-meter self-consumption (100% owner offset) **and** virtual-net-metered export (**80% owner** per the capture rule). Add every asset's max-viable solar array regardless of whether a smaller array would have cleared the hurdle. |
| **D — Next Owner's Perspective** | The SAME `irr_incremental ≥ hurdle` screen as B **but computed at `exit_year = 2040`** (a rational acquirer's hold horizon), NOT a hold recommendation for the current owner. A 2031 buyer underwrites a longer hold + the 2030/2040 BPS & CRREM obligations + electrification risk, so more measures clear the hurdle → the **deepest** curve. Narrate strictly as the buyer's underwriting lens / the trajectory the asset is actually on — never as "you should hold to 2040." |

`irr_excl_exit` and `irr_incremental` both come from `compute_plan_economics` (per measure or the
asset roll-up; D re-runs it with `exit_year=2040`). A ⊆ B ⊆ C ⊆ D by construction. Compliance-required
measures are in all four.

**Exit-price protection (the seller's payoff on a short hold — populate `exit_price_protection`).**
Scenario D matters to a 2031 seller because the buyer **chips the bid** for what D would fix. Quantify
the avoided chip, grounded + cited: (a) **compliance/brown discount** — the cap-rate expansion or $
haircut a buyer applies to a CRREM-stranded / BPS-fine-exposed asset (state the bps or % assumption);
(b) **electrification deferred-retrofit reserve** — the future gas→electric capex + policy risk a buyer
deducts from their bid. Decarbing toward D removes both, so a short-hold owner captures the value **at
the closing table**, not the meter. This is the report's punchline — surface it in the executive summary.

**CRREM overlay — tool-fetched, never hand-built (economics correctness rule 4):** fetch each
asset's pathway from the **`crrem` MCP `get_pathway`** for its actual country/property-type/region
(set `crrem_meta` per asset), then GFA-weight the per-asset tool curves into the portfolio target.
Do NOT reuse an Audette `crrem_pathway_target_*` model field or interpolate a curve. If `crrem`
is unreachable, say so and omit the CRREM overlay — never fabricate it.

**Calculation method per year Y (2025–2050):**

For each asset:
1. Start from Audette baseline carbon intensity (kgCO₂e/m²) in 2025
2. BAU: apply grid decarbonization factor per year to Scope 2 component only
3. Scenario A: subtract each measure with `irr_excl_exit ≥ irr_hurdle` (+ compliance-required), from its install year onward
4. Scenario B: subtract each measure with `irr_incremental ≥ irr_hurdle` (superset of A; + compliance-required)
5. Scenario C: B's reductions PLUS each asset's max-viable solar generation offset (BTM self-consumption + VNM export)
6. Scenario D: the B screen re-run with `exit_year = 2040` (measures with `irr_incremental_2040 ≥ hurdle`) — the next-owner horizon; more measures clear → deepest reductions
7. Weight each asset's intensity by its gross floor area (m²) for portfolio aggregate
8. CRREM target = GFA-weighted `get_pathway` curve, NOT an Audette field

**Sanity check (rule 6):** each scenario curve must be **non-increasing**, and by construction
A ≥ B ≥ C ≥ D residual intensity (each reduces at least as much; D deepest) — if any is out of order,
the screen was mis-applied; reject and fix.

**Output:** JSON array of `{ year, bau, scenario_a, scenario_b, scenario_c, scenario_d, crrem_target }`
(kgCO₂e/m²) for years **2025–2050** (the template reads exactly these keys). ALWAYS include rows through
**2040** (the curve must be contextualized to at least 2040, past the 2031 exit) — the target-year table
reports 2030/2035/2040.

**Render as an inline SVG line chart** (the template draws it from the keys above):
- X axis 2025–2050 (curve visible through ≥2040); Y axis kgCO₂e/m² (portfolio GFA-weighted)
- Lines: BAU (grey dashed), CRREM target (red dashed), A (blue), B (green), C (purple), D — Next Owner (amber)
- Shaded stranding-risk zone between BAU and CRREM; annotate the year each scenario crosses under CRREM.

**Report the answer to the central question explicitly** — for A, B, C, **and D**: the achieved portfolio
GHGI-reduction % at **2030 / 2035 / 2040**, the net CapEx deployed, and whether/when it clears the CRREM
1.5°C line. Frame A/B/C as the current owner's 2031-exit screens and **D as the next-owner lens + the
exit-price-protection story** (`exit_price_protection`). That comparison IS the headline of this report.

Use inline SVG only — no external charting libraries. The chart should be self-contained and print-ready.

**Circular benchmarking rule:** Only include assets with actual EUI data (Audette or ESPM) in the pathway. Assets with BPD-estimated EUI are listed separately as "EUI unverified — excluded from trajectory."

Flag: "Under BAU, [N] assets cross the CRREM stranding threshold before [target_years[0]]. Under the 15% IRR pathway, [M] strand. Under maximum decarb, [P] strand."

### 4F — Verification pass (batch render gate)

`decarb-plan` fails the whole render closed on any open high-severity finding. At portfolio
scale that would let one bad asset block the entire report, which is wrong — so the gate is
**per-asset and called out**, not fail-closed:

1. For every analyzed asset, call `verifier__verification_status(asset_id)` → `{pass, open_high,
   open_total}`. Record each asset's `pass` and `open_high` alongside its output.
2. Also call `verifier__verification_status()` with **no asset_id** for any portfolio-level
   findings recorded during the run.
3. Assets with `pass: false` are **flagged inline** in the Asset-by-Asset table (a ⚠ marker) and
   **their contribution to the headline KPIs is disclosed in client-facing terms** — e.g.
   "3 assets rely on data still being confirmed; $2.1M of the $14M headline CapEx derives from
   those assets." Never let the totals silently absorb unconfirmed data. (Internal note: this
   is driven by `verifier__verification_status`, but that machinery must NOT appear in the
   rendered report — no "verifier", "finding", "high-severity", "Gate".)
4. The Data Quality section (Phase 5) summarizes confidence in **client-facing** terms
   (`data_quality.summary` + `items[]` dots) — how many assets use measured vs. estimated data
   and what remains to be confirmed. Do NOT render an internal findings/conflict table and do
   NOT pass `data_quality.findings` (it is no longer rendered).

This is the batch analog of decarb-plan's fail-closed gate: the report always renders, but it can
never present unconfirmed data as confirmed — and it never exposes internal QA machinery to the client.

### 4G — Portfolio-scale program & economies of scale (`programmatic_recommendation` + `scale_opportunities`)

The point of a PORTFOLIO analysis (vs N single-asset runs) is the plays that only exist at scale.
Derive these from the aggregation you just built — do NOT invent numbers; every capex/reduction
figure is engine-sourced and every quantified benefit needs a basis (label assumed discounts `(est.)`).

- **`programmatic_recommendation`** — the same recommended measures executed as a **sequenced
  portfolio program**, not asset-by-asset. Phase by the most defensible axis (CRREM-stranding
  urgency, capital-event/RUL timing, or measure family), each phase carrying its asset count,
  what it deploys, aggregate net CapEx (Σ engine), and the portfolio GHGI-reduction % it delivers.
  A natural shape: Phase 1 = the low-cost portfolio-wide controls/RCx + lighting rollout (clears the
  quick reduction), Phase 2 = clustered electrification/envelope at capital events, Phase 3 =
  solar/deep measures. Tie it to the A/B/C curve (which screen each phase belongs to).
- **`scale_opportunities`** — the economies-of-scale levers the run reveals, each grounded in the
  data (which measures/assets/geographies): **bulk/framework procurement** (e.g. one HPWH or LED
  order across the N assets that share the measure → volume discount), **clustered-metro contractor
  mobilization** (assets in the same market → shared mobilization/GC), **aggregated solar / VNM /
  community solar** across a utility territory, **portfolio green financing** (single green loan /
  C-PACE / Fannie-Freddie Green facility sized to total CapEx vs asset-by-asset), **shared M&V /
  monitoring subscription** at a portfolio rate, **IRA bonus stacking** (domestic-content / energy-
  community across the fleet), and **GRESB/disclosure leverage**. Quantify where the data supports
  it (e.g. "28 assets × LED = $X at a 10%-assumed bulk discount (est.)"); otherwise state the lever
  and mark the benefit "—". Use `applies_to` to show the count/segment each lever covers.

These render as the "Portfolio-Scale Program & Economies of Scale" section (hidden if both are absent).

---

## Phase 5: Full Report — render via `fill_report` (mirror RSRA/decarb; do NOT hand-write HTML)

**Render the report by computing the data object and calling `fill_report(template:'portfolio-analysis', data)`** — the same client-render path RSRA and decarb use. The server injects your JSON into `templates/portfolio-analysis/layout-agent.html`'s `<script id="report-data">` block and the template's own JavaScript renders every section and chart (including the **asset-prioritization quadrant** SVG). **You write NO report HTML and draw NO charts** — your only job is to assemble the data object.

1. **Assemble the data object** per `templates/portfolio-analysis/schema.json`. Top-level keys (from Phase 4 aggregation): `client_name, portfolio_id, report_date, prepared_by, parameters, portfolio_kpis, asset_source_data, assets, fund_summary, top_assets, all_measures, measure_categories, emissions_trajectory` (if include_crrem), `crrem_trajectory` (if include_crrem), `bps_assets` (if include_bps), `below_hurdle, deferred`, **plus the `prioritization` block** (per-asset ranking + driving dimensions — value_creation, pct_reduction, irr, gav, exit, above_hurdle — that powers the quadrant; see schema).
2. **Call `fill_report(template:'portfolio-analysis', data:<object>, title:"<Client> — Portfolio Decarbonization Analysis")`.** It returns the rendered artifact in the preview pane. On revisions, recompute the data and call `fill_report` again — never edit HTML.
3. 2 significant figures throughout; the template enforces sans-serif/no-web-fonts and safe citation links.

The template renders these sections (reference — this is the template's contract, not something you build): Document Header, Executive Summary, Portfolio KPIs, Asset-Prioritization Quadrant, Fund-Level Summary, Top Assets by Value Creation, Emissions Trajectory (if include_crrem), CRREM Pathway (if include_crrem), BPS Exposure (if include_bps), Measure Category Summary, Asset-by-Asset Detail, Below-Hurdle, Deferred, Data Quality & Verification, Methodology & Sources.

<details><summary>Legacy structure reference (the template implements this — kept for data-shape context)</summary>

### Report structure

```
[Navy header]
  Portfolio Decarbonization Analysis
  [Client] Portfolio · [N] assets · [Fund list]

[Meta strip]
  Soapbox Sustainability Intelligence · [Date] · CONFIDENTIAL

[KPI bar — 4 metrics]
  Total CapEx (net)  |  Value Creation  |  Emissions Reduction  |  Assets Above Hurdle
  If org_goal is set: add a 5th tile showing % of goal achieved under the 15% IRR pathway

[Section: Executive Summary]
  3–4 sentences: portfolio scope, primary opportunity, headline CapEx and value creation.
  If include_crrem: true, add emissions trajectory vs. CRREM 2035 target.
  If include_bps: true, add compliance exposure summary.
  If org_goal is set, add one sentence on gap/progress vs. that goal under each scenario.

[Section: Fund-Level Summary]
  Table: fund | assets | CapEx net | value creation | emissions reduction | avg IRR

[Section: Top 10 Assets by Value Creation]
  Table: rank | asset | fund | exit | CapEx net | value created | lead measure

[Section: Measure Category Summary]
  Table: category | assets | CapEx net | value creation | tCO₂ reduced

[Section: Emissions Trajectory (2025–2050)]  ← only if include_crrem: true
  Inline SVG line chart — three scenario lines + CRREM target:
    · BAU (grey dashed)
    · 15% IRR Decarb Pathway (blue solid)  
    · Maximum Decarb (green solid)
    · CRREM 1.5°C Target (red dashed)
    · Org goal marker (orange dotted vertical line at target year) — only if org_goal is set
  Stranding risk zone shaded between BAU and CRREM lines.
  Below chart: table of portfolio-weighted kgCO₂e/m² at 2030, 2035, 2040, 2050 per scenario.
  If org_goal is set: add row showing % gap vs. goal at the goal's target year for each scenario.

[Section: CRREM Pathway Analysis]  ← only if include_crrem: true
  Portfolio emissions trajectory table (current vs. measures, vs. 2030/2035/2040 targets)
  Number of stranding assets today vs. with measures
  Note any assets excluded from pathway analysis (estimated EUI)

[Section: Building Performance Standards Exposure]  ← only if include_bps: true
  Per-asset BPS liability status (liable / not liable / unknown)
  Compliance cost if no action (Σ projected fines at target years)
  Fine avoidance as a measure benefit — shown alongside IRR for each qualifying measure

[Section: Asset-by-Asset Detail]
  One row per asset:
    Asset name | Fund | Exit | CapEx Net | Value Created | Avg IRR
    + CRREM Status column if include_crrem: true
    + BPS Exposure column if include_bps: true
  Expandable / linked to per-asset RSRA thread

[Section: Below-Hurdle Measures (reference table)]
  Measures excluded from recommendations — IRR shown for transparency
  "These measures do not meet the [irr_hurdle]% hurdle at stated assumptions. They may become
  viable under different hold periods, exit cap rates, or if utility rates escalate faster."

[Section: Deferred Measures]
  Measures deferred due to retrofit lead time constraint — install year noted

[Section: Data Quality]  ← EXTERNAL DELIVERABLE — client-facing only
  Count of assets with measured/metered EUI vs. peer-benchmark estimates
  Confidence dots (data_quality.items[]) in client terms — cite the data SOURCE, never the
    internal QA step. NO internal-process language: no "verifier", "finding id", "adjudicated",
    "Gate", "phase", "high-severity finding". Use the verifier internally for QA, but do NOT
    render a findings/conflict table and do NOT pass data_quality.findings — it is not rendered.
  "All values labeled (est.) are based on BPD MCP peer-group median EUI and carry ±40% uncertainty."
  "Where sources conflicted by >25%, the most authoritative source was used (measured/ESPM >
    audit > Audette model > estimate)."

[Footer]
  Data sources: Audette · Soapbox compute_plan_economics engine · CRREM (tool get_pathway) · IRA §48E/§179D · BPD (LBNL)
  Parameters: IRR [X]% · Utility escalation 3% · Exit year floor [Y] · Value-inclusive IRR
  Limitations: This analysis is based on data available at time of run. CapEx estimates
  carry ±30% uncertainty without site inspection. IRR sensitivity to exit cap rate is high —
  a 50bp cap rate change can move IRR by 3–5pp. Verify with physical due diligence before
  committing capital.
```

---

</details>

## Phase 6: Save and Offer Follow-Ups

After `fill_report` renders the report:

1. Register the rendered artifact in portfolio documents as `{client-slug}-portfolio-analysis-{YYYYMMDD}.html`
2. Save per-asset JSON outputs to `.cashflow-models/portfolio-{client-slug}/`
3. **Generate the XLSX companion — best-effort.** If `build_xlsx.py` is available in the
   runtime, produce the analyst verification workbook (source data, measure economics, and all
   report output tables):
   ```bash
   python3 ~/soapbox-agent/scripts/build_xlsx.py \
     --template portfolio-analysis \
     --data '{ ...assembled portfolio JSON... }' \
     --brand '{ "primary_color": "#12253A", "secondary_color": "#1A3550", "accent_color": "#EFF6FF", "highlight_color": "#4CAF82", "text_color": "#1A1A2E", "text_muted": "#64748B", "border_color": "#E2E8F0" }' \
     --output .cashflow-models/portfolio-{client-slug}/{client-slug}-portfolio-analysis-{YYYYMMDD}.xlsx
   ```
   The hosted skill runtime typically does **not** include this script. If it is not present, do
   NOT search the filesystem for it or block the run — skip the XLSX, note "XLSX companion skipped
   (build_xlsx.py not available in this runtime)", and deliver the HTML report as the primary
   artifact.

   The `--data` JSON must include these top-level keys (assembled from Phase 4 aggregation):
   `client_name`, `portfolio_id`, `report_date`, `prepared_by`, `parameters`, `portfolio_kpis`,
   `asset_source_data`, `assets`, `fund_summary`, `top_assets`, `all_measures`,
   `measure_categories`, `emissions_trajectory` (if include_crrem), `crrem_trajectory` (if include_crrem),
   `bps_assets` (if include_bps), `below_hurdle`, `deferred`.

4. Report: "[N] assets analyzed. [N_above] above IRR hurdle. Recommended measures: $[X]M net
   CapEx, $[Y]M value creation, [Z] tCO₂e reduced across portfolio."
5. **Retain generalizable lessons.** For any client-anonymous, cross-portfolio lesson this run
   produced — a reconciliation pattern (e.g. a recurring Audette-vs-audit gap for a vintage/type),
   a jurisdiction/incentive finding, a source-reliability observation — call
   `verifier__retain_shared_expertise(fact, domain, evidence[])`. It requires **≥2 independent
   sources or a `confirmed_finding_id`** and refuses client/asset-identifying text. **Never
   rephrase to work around a refusal** — a refusal means the lesson isn't generalizable; drop it.
6. Offer:
   - **"Build per-asset RSRA threads"** — create individual asset threads pre-loaded with their
     analysis results for deeper due diligence
   - **"Export to PPTX"** — run `build_pptx.py` if available in the runtime (best-effort; skip with a note if not present)
   - **"Re-run with different parameters"** — change IRR hurdle, exit year floor, or target year
   - **"Filter to one fund"** — re-aggregate for a specific fund only

---

## Error Handling

**Asset with no `audette_property_id`:**
Include with estimated energy data. Label everything `(est.)`. Skip BPD comparison.
Never block the run on a missing Audette link.

**Audette MCP tools unavailable at runtime (auth error, network failure, tool not found):**
If `switch_customer_account`, `list_properties`, or `get_building_model_details` return an
error or are not available as tools:
1. Note at the top of the run: "⚠ Audette MCP unavailable — running on uploaded docs only."
2. Fall through to uploaded documents as the source for all assets. Doc-sourced figures
   carry the same certainty as Audette — only BPD MCP benchmark estimates get the `(est.)` label.
3. Do NOT silently proceed as if Audette ran — surface the gap clearly.
4. After the run, tell the user: "To include Audette models, ensure the Audette plugin is
   installed for this portfolio in Settings → Plugins."

**`switch_customer_account` fails (wrong slug or account not accessible):**
Call `list_customer_accounts()` to get the available account list, present names to the
user, and ask which one to use. Do not guess. Do not proceed with a wrong account —
data from another client's account would silently corrupt the analysis.

**`compute_plan_economics` failure:**
If `compute_plan_economics` returns an error for an asset (bad inputs, tool unreachable), mark that
asset `analysis_failed`, report the error, continue with remaining assets. Do NOT fall back to
`run_dcf`/`run_intervention_irr` (broken) or hand-compute the IRR/value bridge yourself.

**Verifier or retrofit tools unavailable at runtime:**
If `verifier__*` or `retrofit__*` tools error or are absent, say so at the top of the run
("⚠ Verifier/Retrofit plugin unreachable — running without the findings ledger / measure
register"). You may still produce the analysis from Audette + docs + `compute_plan_economics`, but:
do NOT fabricate finding ids, verification-status results, or register entries; note that conflicts
were not logged to the ledger and the measure register was not updated; and tell the user to
reconnect the plugin to restore verification and the shared register. Never present the report as
verified when the verifier was unreachable.

**IRR does not converge:**
Mark the measure `irr: "no_convergence"`, exclude from recommendations, note in output.

**All measures below hurdle for an asset:**
Still include the asset in the report. Show the "below hurdle" table with IRRs for
transparency. These assets still appear in the emissions and compliance sections.

**Hold period = 0 (already past exit year):**
Include in emissions inventory only. Flag `status: disposed`.

---

## Idempotency

Re-running the analysis for the same portfolio updates the existing artifact in-place.
Per-asset JSON files in `.cashflow-models/portfolio-{client-slug}/` are overwritten.
The HTML artifact is updated at the same file path — no duplicate files.
