---
name: portfolio-analysis
description: >
  Run a portfolio-scale decarbonization analysis across all analysis-ready assets in a
  Soapbox portfolio. For each asset: pulls Audette decarb plan (physics), runs Soapbox
  DCF engine (financial model), applies LL/TT allocation decision tree, screens measures by
  IRR ≥ hurdle. Aggregates to fund-level and portfolio-level summary. Produces
  presentation-ready HTML report. Works for any client portfolio — parameters are fully
  configurable per run. Spec 2 of 2 — portfolio ingestion (Spec 1) is a prerequisite.
  Triggers on: "run portfolio analysis", "analyze the portfolio", "portfolio decarbonization",
  "run the portfolio", "portfolio summary", "show me the portfolio results", "portfolio IRR",
  "portfolio CapEx", "run analysis on [client]", "Greystar analysis", "BCLC analysis",
  after portfolio-ingest completes.
version: 1.1.0
---

# Portfolio Analysis

You are running a **portfolio-scale decarbonization analysis** — the workflow that turns
a fully-ingested Soapbox portfolio into a presentation-ready view of required sustainability
capital, value creation, and emissions trajectory across all assets.

**Works for any client portfolio.** All parameters are set per run — there are no
hardcoded client assumptions. Greystar, BCLC, or any future client each get their own
parameter set confirmed at the start.

**This skill replaces client-specific helper spreadsheets.** Audette provides the physics
(energy measures, decarb plan, EUI), the Soapbox DCF engine provides the finance (IRR,
value creation, NOI uplift).

---

## Step 0: Resolve Run Configuration

**First, search Portfolio Docs for existing financial parameters before prompting the user.**
Check for spreadsheets, IC memos, fund term sheets, or asset registers that contain exit years,
cap rates, IRR hurdles, or hold periods. Extract what you find, then only ask for what's missing.

After checking docs, establish the run parameters. Accept them inline if the user
provided them ("run Greystar analysis with 15% hurdle"), or confirm what was found in docs first.

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

### Preset configurations

If the user says a client name without specifying parameters, apply the known preset
if one exists, then confirm before proceeding:

**Greystar:**
```
irr_hurdle: 15%, exit_year_floor: 2028, retrofit_lead_months: 18,
target_years: [2030, 2035], utility_escalation: 3%, discount_rate: 8%,
value_method: inclusive, audette_account: greystar
```

**BCLC:**
```
irr_hurdle: 12%, exit_year_floor: 2027, target_years: [2030, 2035, 2040],
utility_escalation: 3%, discount_rate: 7%, value_method: inclusive,
audette_account: bclc
```

New clients: prompt for each required parameter. Save the confirmed set to a comment
in the portfolio thread for future runs.

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
```

---

## Phase 1: Readiness Check & Financial Parameter Collection

**Before prompting the user for any parameters, search Portfolio Docs for existing data.**
Exit years, cap rates, fund assignments, hold periods, and IRR targets are often already
uploaded as spreadsheets, IC memos, or fund term sheets. Extract what you can before asking.

### 1A — Search Portfolio Docs first

Use `search_portfolio` and `list_portfolio_files` to check for:
- Asset registers or spreadsheets with exit years and cap rates (e.g. "exit-year", "cap rate", "hold period", "fund")
- IC memos, fund term sheets, or investment guidelines with IRR hurdle rates
- Acquisition models or underwriting summaries with per-asset financial parameters

For any file that looks relevant, read it and extract:
- `exit_year` per asset
- `exit_cap_rate` per asset or fund
- `fund_name` assignments
- IRR hurdle rate
- Hold period assumptions

Only ask the user for parameters that couldn't be found in the docs. If you found partial data (e.g. exit years but no cap rates), confirm what you found and ask only for what's missing.

### 1B — Load all assets

```sql
SELECT id, name, address, property_type, metadata
FROM assets
WHERE portfolio_id = '<portfolio_id>'
  -- apply fund_filter if not "all":
  -- AND metadata->>'fund_name' = ANY(ARRAY[<fund_list>])
ORDER BY name;
```

Partition into:
- **Analysis-ready** (`analysis_ready: true`) — proceed directly to Phase 2
- **Missing params** (`analysis_ready: false` or null) — collect before proceeding
- **Disposed** (`status: 'disposed'`) — include in emissions inventory only

### 1B — Bulk-fill from register (if available)

If a spreadsheet or asset register is available (e.g. Greystar asset prioritization sheet),
parse it first to bulk-populate `exit_year`, `exit_cap_rate`, and `fund_name` before
prompting asset-by-asset:

```bash
python3 ~/soapbox-agent/scripts/portfolio_match.py --mode financial --inputs '<json>'
```

Auto-populate any field that can be read from the register. Only prompt for what's still missing.

### 1C — Collect missing parameters asset-by-asset

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Only show missing fields. `skip` leaves null and excludes the asset from analysis.
`disposed` marks the asset and includes it in emissions inventory only.

Run LL/TT allocation once inputs are known:
```bash
python3 ~/soapbox-agent/scripts/ll_allocation.py --inputs '{"lease_structure":"<val>","metering_config":"<val>","jurisdiction":"<val>","bps_liable":<bool>,"measure_category":"in_unit_hvac"}'
```

Write results to asset metadata using `||` merge (preserves Audette/ESPM IDs and docs):
```sql
UPDATE assets SET metadata = metadata || '<params_json>'::jsonb WHERE id = '<asset_id>';
```

Show edge-case warnings inline (NNN paradox, solar consent, RUBS recovery, BPS liability).

### 1D — Readiness summary

Report before proceeding:
```
[N_ready] assets ready · [N_missing] skipped (missing params) · [N_disposed] disposed
```

If `N_ready = 0`: stop and ask the user to provide financial parameters.

Confirm:

### 1E — Load confirmed analysis-ready assets for the run

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

### 1B — Identify Audette gaps

For each asset, check `metadata.audette_building_id`. Assets without an Audette link will
have lower-quality energy data.

| Status | Count | Treatment |
|--------|-------|-----------|
| Audette-linked | N | Full physics model from Audette |
| No Audette link | N | Use documents (PCA/audit) + CBECS benchmark estimates — label all values `(est.)` |
| Audette linked but disconnected | N | Flag and exclude from analysis; do not use stale data |

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

**Audette is the mandatory primary data source. Call it for every linked asset before using any other data.**

Process assets in sequence, streaming one progress line per asset as it completes.
Stream to the conversation: `✓ Landmark at Colony Park (7/39) — 4 measures above hurdle, $2.1M CapEx, +$1.4M value`

### 3A — Load Audette data (mandatory first step — do this before anything else)

**If Audette is connected, call it for every linked asset.** Then cross-check Audette figures against other available sources — uploaded Greenrock assessments, utility bills, ESPM scores — and reconcile discrepancies before presenting numbers.

**Measure blending — synthesize across all sources, assess feasibility critically:**

1. **Compile all recommended measures** from every source: Audette decarb plan, Greenrock utility assessment, PCA capital items, ESPM recommendations. Build a unified measure list per asset.

2. **De-duplicate**: if a measure appears in multiple sources (e.g. LED upgrade in both Audette and Greenrock), keep one entry. Use the most detailed cost estimate and flag which source it came from.

3. **Mark completion status**: if the Greenrock assessment shows a measure was already completed, remove it from the forward-looking CapEx — do not double-count.

4. **Critical feasibility check per measure**:
   - Is it technically feasible given building vintage, HVAC configuration, and fuel type?
   - Can it be permitted and built within the hold period? (Heat pumps / envelope: 18+ months lead time; LED/controls: 3–6 months)
   - Does the LL/TT allocation actually flow savings to the landlord? (NNN tenant-pays = near-zero NOI capture on in-unit measures)
   - Does it require tenant cooperation or consent (solar on leased roof, sub-metering, RUBS rollout)?

5. **Confidence levels**: label each measure as High / Medium / Low confidence based on data quality. Audette + field-verified Greenrock = High. Audette only or Greenrock only = Medium. CBECS benchmark = Low.

6. **IRR screen last**: only after measures are compiled, de-duped, feasibility-checked, and allocated — then apply the IRR hurdle. A measure that fails on feasibility should be excluded before the IRR screen, not after.

**Audette is the system of record for reconciled plans and calibrated energy models.**

After reconciliation, write findings back to Audette so the model stays current:

1. **Submit utility consumption data** — if utility bills are uploaded and more recent than Audette's baseline, extract monthly consumption and submit to Audette via the energy command. This triggers Audette to re-model the carbon reduction plan with current data.

2. **Mark completed measures** — if Greenrock or PCA documents show a measure was already installed (LED retrofit done, HVAC replaced), mark it complete in Audette so it's removed from the forward-looking decarb plan and not counted in CapEx.

3. **Update equipment records** — if field documents show equipment has been replaced (e.g. new chiller installed 2024) and Audette's equipment schedule doesn't reflect it, update the record so future calibrations are accurate.

4. **Note calibration gaps** — if the Audette model appears based on design specs rather than measured data (common for new buildings), flag this and recommend submitting actual utility bills to recalibrate.

The goal: by the end of the analysis, Audette should be more accurate than when you started. The Audette model is the living system of record — not a static snapshot to read from once.

For each Audette-linked asset:

```
switch_customer_account(<client_account_slug>)
list_buildings() → match by audette_building_id
get_building_model_details(building_id) → pull:
  - current_eui_kwh_m2 (actual site EUI from Audette calibrated model)
  - carbon_intensity_kg_co2_m2 (Scope 1+2, location-based)
  - crrem_pathway_target_2030 (kgCO2e/m² — CRREM 1.5°C target for asset type)
  - crrem_misalignment_year
  - equipment_schedule (age + condition of major systems)
  - recommended_measures[] (Audette decarb plan — each with capex, annual_savings_kwh, install_cost, measure_type)
```

**Data hierarchy rule:** Audette is the primary source. Do not replace Audette-provided energy
data with CBECS estimates. If Audette provides EUI, use it — even if it differs from what the OM
stated. Flag the discrepancy in the asset report if > 20%.

For assets without Audette:
- Check uploaded documents (PCA, energy audit) for EUI, equipment age, and any measure estimates
- If no document data: use CBECS median EUI for asset type + climate zone — label every value `(est.)`
- **Circular benchmarking rule:** Never use a CBECS benchmark EUI in the BPD peer comparison.
  If EUI is estimated, skip BPD comparison for that asset.

### 3B — Run DCF base model (use the cashflow MCP tool)

Call `run_dcf` for each asset:
```
run_dcf(
  asset_type: "multifamily",
  hold_period_years: max(exit_year, exit_year_floor) - current_year,
  exit_cap_rate: asset.exit_cap_rate,
  going_in_noi: <from Audette model or document-extracted NOI>
)
```

If hold period < 1 year (already past exit): mark as disposed, skip financial analysis.

### 3C — Apply each measure through the cashflow MCP

For each reconciled measure per asset, use the cashflow MCP tools — do NOT use simple payback math:

**Step 1 — LL/TT allocation (call `get_ll_capture`):**
```
get_ll_capture(
  lease_structure: asset.lease_structure,
  metering_config: asset.metering_config,
  jurisdiction: asset.jurisdiction,
  measure_type: measure.category,
  bps_liable: asset.bps_liable
)
→ returns ll_capture_pct + warnings
```

**LL capture is the fraction of energy savings that flows to landlord NOI.**
A NNN tenant-metered building gets `ll_capture_pct ≈ 0.05` on in-unit measures.
BPS fine avoidance is always LL-captured regardless of lease structure.

**Step 2 — Retrofit lead time feasibility:**
- Major capital (HVAC, electrification, envelope, solar): requires 18+ months — defer if hold_period < 1.5 yrs
- Compliance-required measures: never defer regardless of hold period
- Controls/LED/commissioning: 3–6 months — feasible for any hold period

**Step 3 — Value-inclusive IRR (call `run_intervention_irr`):**
```
run_intervention_irr(
  base_model: <result from run_dcf>,
  intervention_type: <mapped from measure category>,
  capex: measure.install_cost,
  annual_savings: measure.annual_savings_$ × ll_capture_pct,
  utility_escalation: utility_escalation,
  start_year: measure.install_year - current_year,
  ll_capture_pct: ll_capture_pct
)
→ returns IRR, payback_years, exit_value_delta, yield_on_cost
```

**For batch screening across assets:** use `screen_measure_portfolio` to run one measure type across all assets at once.

**Step 4 — IRR screen (use the `irr_hurdle` parameter):**

```python
python3 scripts/dcf_engine.py \
  --base-model {asset_id}_base.json \
  --intervention-capex <measure.install_cost> \
  --annual-noi-uplift <annual_noi_uplift> \
  --install-year <install_year> \
  --value-creation <annual_noi_uplift / exit_cap_rate> \
  --irr-method inclusive \
  --output-json
```

IRR is unlevered, inclusive of asset value:
- Cash outflow at `install_year` = capex
- Annual cash inflow = `annual_noi_uplift` for each year from `install_year` to `exit_year`
- Terminal value uplift at `exit_year` = `annual_noi_uplift / exit_cap_rate`

**Step 5 — IRR screen:**

| Result | Action |
|--------|--------|
| IRR ≥ `irr_hurdle` | Include in recommended measures |
| IRR < hurdle rate | Exclude from recommendations; include in "below hurdle" table |
| Compliance-required measure | Include regardless of IRR; flag as mandatory |

**Step 6 — IRA incentive check:**

For measures with IRA eligibility:
- Solar/geothermal/battery: IRA §48E — 30% base ITC (REIT direct pay eligible)
- Envelope/HVAC/lighting: IRA §179D — up to $5.65/SF (only if renovation qualifies)
- Multifamily energy efficiency: §45L — $500–$5,000/unit
- Low-income / energy community bonus: check census tract (+10pp on §48E)

Reduce `net_capex = install_cost × (1 - ira_credit_rate)` for IRA-eligible measures.
Re-run IRR on `net_capex` — some measures below hurdle on gross may pass on net.

Label net capex separately from gross in all tables.

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
  "audette_eui": 85.2,
  "carbon_intensity_kg": 42,
  "crrem_status": "above_pathway",
  "crrem_misalignment_year": 2029,
  "ll_capture_pct_avg": 0.72,
  "lease_structure": "modified-gross",
  "metering_config": "master-metered",
  "jurisdiction": "Boston",
  "bps_liable": true,
  "recommended_measures": [
    {
      "measure": "LED lighting retrofit",
      "capex_gross": 280000,
      "capex_net": 196000,
      "ira_credit": "§179D 30%",
      "annual_noi_uplift": 31000,
      "ll_capture_pct": 1.0,
      "install_year": 2026,
      "irr": 0.21,
      "value_creation": 688000,
      "emissions_reduction_t_co2": 18
    }
  ],
  "below_hurdle_measures": [...],
  "deferred_measures": [...],
  "total_capex_gross": 1400000,
  "total_capex_net": 980000,
  "total_value_creation": 2100000,
  "total_noi_uplift_annual": 94500,
  "total_emissions_reduction_t_co2": 67,
  "compliance_cost_if_no_action": 45000
}
```

Stream one line per asset as it completes.

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
| Assets fully pathway-aligned (2035) | Count where carbon_intensity ≤ CRREM 2035 target after measures |
| Compliance exposure (no action) | Σ compliance_cost_if_no_action |

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

### 4E — Emissions trajectory: three-scenario time series (2025–2050)

Build a year-by-year portfolio emissions model for three scenarios and the CRREM 1.5°C pathway. This is the centrepiece of the report — it shows where the portfolio is going and what each investment strategy delivers.

**Three scenarios to model:**

| Scenario | Definition |
|----------|-----------|
| **Business as Usual (BAU)** | No decarb capital deployed. Only passive grid decarbonization applies to Scope 2 emissions (~3.5%/yr for US multifamily, varies by grid region). Equipment degrades naturally. |
| **15% IRR Pathway** | Only measures that pass the IRR hurdle (`irr_hurdle`) are deployed, at their modelled install years. Emissions drop as each measure comes online. |
| **Maximum Decarb** | All Audette-recommended measures deployed at earliest viable install year, regardless of IRR. Represents the fastest achievable pathway given the existing building stock. |

**CRREM overlay:** Plot the portfolio-weighted CRREM 1.5°C pathway target for each year.

**Calculation method per year Y (2025–2050):**

For each asset:
1. Start from Audette baseline carbon intensity (kgCO₂e/m²) in 2025
2. BAU: apply grid decarbonization factor per year to Scope 2 component only
3. 15% IRR: subtract each IRR-passing measure's annual emission reduction from its install year onward
4. Max decarb: subtract all recommended measures from their install years onward
5. Weight each asset's intensity by its gross floor area (m²) for portfolio aggregate

**Output:** JSON array of `{ year, bau_intensity, irr_intensity, max_intensity, crrem_target }` for years 2025–2050.

**Render as an inline SVG line chart** in the HTML report:
- X axis: 2025–2050
- Y axis: kgCO₂e/m² (portfolio weighted average)
- Lines: BAU (grey dashed), CRREM target (red dashed), 15% IRR pathway (blue solid), Max decarb (green solid)
- Shaded area between BAU and CRREM target = stranding risk zone
- Annotation: year where 15% IRR pathway crosses CRREM target (if it does)

Use inline SVG only — no external charting libraries. The chart should be self-contained and print-ready.

**Circular benchmarking rule:** Only include assets with actual EUI data (Audette or ESPM) in the pathway. Assets with estimated EUI are listed separately as "EUI unverified — excluded from trajectory."

Flag: "Under BAU, [N] assets cross the CRREM stranding threshold before [target_years[0]]. Under the 15% IRR pathway, [M] strand. Under maximum decarb, [P] strand."

---

## Phase 5: Phase 2 Artifact — Full Report

Update the same `{client-slug}-portfolio-analysis.html` artifact. Do not create a new file.

**Typography:** Pure sans-serif everywhere. Zero Georgia, zero serif, zero web fonts.
**Citation links:** All external references use `target="_blank" rel="noopener noreferrer"`.
**Numeric precision:** 2 significant figures throughout.

### Report structure

```
[Navy header]
  Portfolio Decarbonization Analysis
  [Client] Portfolio · [N] assets · [Fund list]

[Meta strip]
  Soapbox Sustainability Intelligence · [Date] · CONFIDENTIAL

[KPI bar — 4 metrics]
  Total CapEx (net)  |  Value Creation  |  Emissions Reduction  |  Assets Above Hurdle

[Section: Executive Summary]
  3–4 sentences: portfolio scope, primary opportunity, headline CapEx and value creation,
  emissions trajectory vs. CRREM 2035 target.

[Section: Fund-Level Summary]
  Table: fund | assets | CapEx net | value creation | emissions reduction | avg IRR

[Section: Top 10 Assets by Value Creation]
  Table: rank | asset | fund | exit | CapEx net | value created | lead measure

[Section: Measure Category Summary]
  Table: category | assets | CapEx net | value creation | tCO₂ reduced

[Section: Emissions Trajectory (2025–2050)]
  Inline SVG line chart — three scenario lines + CRREM target:
    · BAU (grey dashed)
    · 15% IRR Decarb Pathway (blue solid)  
    · Maximum Decarb (green solid)
    · CRREM 1.5°C Target (red dashed)
  Stranding risk zone shaded between BAU and CRREM lines.
  Below chart: table of portfolio-weighted kgCO₂e/m² at 2030, 2035, 2040, 2050 per scenario.

[Section: CRREM Pathway Analysis]
  Portfolio emissions trajectory table (current vs. measures, vs. 2030/2035/2040 targets)
  Number of stranding assets today vs. with measures
  Note any assets excluded from pathway analysis (estimated EUI)

[Section: Asset-by-Asset Detail]
  One row per asset:
    Asset name | Fund | Exit | CapEx Net | Value Created | Avg IRR | CRREM Status
  Expandable / linked to per-asset RSRA thread

[Section: Below-Hurdle Measures (reference table)]
  Measures excluded from recommendations — IRR shown for transparency
  "These measures do not meet the [irr_hurdle]% hurdle at stated assumptions. They may become
  viable under different hold periods, exit cap rates, or if utility rates escalate faster."

[Section: Deferred Measures]
  Measures deferred due to retrofit lead time constraint — install year noted

[Section: Data Quality Notes]
  Count of assets with Audette-verified vs. estimated EUI
  "All values labeled (est.) are based on CBECS benchmarks and carry ±40% uncertainty."

[Footer]
  Data sources: Audette · Soapbox DCF Engine · CRREM 2024 · IRA §48E/§179D · CBECS
  Parameters: IRR [X]% · Utility escalation 3% · Exit year floor [Y] · Value-inclusive IRR
  Limitations: This analysis is based on data available at time of run. CapEx estimates
  carry ±30% uncertainty without site inspection. IRR sensitivity to exit cap rate is high —
  a 50bp cap rate change can move IRR by 3–5pp. Verify with physical due diligence before
  committing capital.
```

---

## Phase 6: Save and Offer Follow-Ups

After generating the Phase 2 report:

1. Save to portfolio documents: `{client-slug}-portfolio-analysis-{YYYYMMDD}.html`
2. Save per-asset JSON outputs to `.cashflow-models/portfolio-{client-slug}/`
3. Report: "[N] assets analyzed. [N_above] above IRR hurdle. Recommended measures: $[X]M net
   CapEx, $[Y]M value creation, [Z] tCO₂e reduced across portfolio."
4. Offer:
   - **"Build per-asset RSRA threads"** — create individual asset threads pre-loaded with their
     analysis results for deeper due diligence
   - **"Export to XLSX"** — run `build_xlsx.py` to generate the Greystar-format spreadsheet
     with all measure tables and fund-level pivot
   - **"Export to PPTX"** — run `build_pptx.py` for the presentation deck
   - **"Re-run with different parameters"** — change IRR hurdle, exit year floor, or target year
   - **"Filter to one fund"** — re-aggregate for a specific fund only

---

## Error Handling

**Asset with no Audette link:**
Include with estimated energy data. Label everything `(est.)`. Skip BPD comparison.
Never block the run on a missing Audette link.

**DCF engine failure:**
If `dcf_engine.py` returns an error for an asset, mark that asset `analysis_failed`,
report the error, continue with remaining assets.

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
