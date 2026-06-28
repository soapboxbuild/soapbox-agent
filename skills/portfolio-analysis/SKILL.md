---
name: portfolio-analysis
description: >
  Run a portfolio-scale decarbonization analysis across all analysis-ready assets in a
  Soapbox portfolio. For each asset: pulls Audette decarb plan (physics), runs Soapbox
  DCF engine (financial model), applies LL/TT allocation decision tree, screens measures by
  IRR ≥ hurdle. Aggregates to fund-level and portfolio-level summary. Produces
  presentation-ready HTML report. Spec 2 of 2 — portfolio ingestion (Spec 1) is a prerequisite.
  Triggers on: "run portfolio analysis", "analyze the portfolio", "portfolio decarbonization",
  "run the portfolio", "portfolio summary", "show me the portfolio results", "portfolio IRR",
  "portfolio CapEx", "run analysis on [client]", "Greystar analysis", after portfolio-ingest completes.
version: 1.0.0
---

# Portfolio Analysis

You are running a **portfolio-scale decarbonization analysis** — the workflow that turns
a fully-ingested Soapbox portfolio into a presentation-ready view of required sustainability
capital, value creation, and emissions trajectory across all assets.

**Prerequisite:** Portfolio ingestion (Spec 1 / `portfolio-ingest` skill) must be complete.
All assets must have `analysis_ready: true` in their metadata, with `exit_year`,
`exit_cap_rate`, `lease_structure`, `metering_config`, and `jurisdiction` populated.

**This skill replaces the Greystar helper spreadsheet.** All calculations that lived
in that sheet now run in Soapbox — Audette provides the physics (energy measures, decarb
plan, EUI), the Soapbox DCF engine provides the finance (IRR, value creation, NOI uplift).

---

## Global Parameters

Establish at the start of every run. If values were set in a prior session, confirm before proceeding.

| Parameter | Default | Greystar | Notes |
|-----------|---------|----------|-------|
| IRR threshold | 15% | 15% | Hurdle rate — measures below are excluded from recommendations |
| Utility escalation rate | 3%/yr | 3%/yr | Applied to all future utility savings |
| Discount rate | 8% | 8% | For NPV calculations |
| Exit year floor | 2028 | 2028 | Assets with exit year < floor get moved to floor |
| Value creation method | inclusive | inclusive | NOI uplift / exit cap = value creation, added to exit year CF |
| Retrofit lead time cutoff | 18 months | 18 months | Measures that can't permit+build before exit are deferred to next-period exit |
| Target year 1 | 2035 | 2035 | Primary emissions target for scenario analysis |

Ask: "Should I use the default parameters, or do you want to change any?"

If the user sets different values, confirm before proceeding.

---

## Phase 1: Asset Inventory

### 1A — Load analysis-ready assets

Query Soapbox for all assets in the portfolio tagged `analysis_ready: true`:

```sql
SELECT id, name, address, property_type, metadata
FROM assets
WHERE portfolio_id = '<portfolio_id>'
  AND metadata->>'analysis_ready' = 'true'
ORDER BY name;
```

Count: `N_ready` assets ready to analyze.

Check for `analysis_ready: false` assets — report them as skipped with their missing fields.

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

Process assets in sequence, streaming one progress line per asset as it completes.
Stream to the conversation: `✓ Landmark at Colony Park (7/39) — 4 measures above hurdle, $2.1M CapEx, +$1.4M value`

### 3A — Load Audette data (primary energy source)

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

### 3B — Run Soapbox DCF (base model)

For each asset, run the DCF engine with asset parameters from metadata:

```python
python3 scripts/dcf_engine.py \
  --asset-type <property_type> \
  --exit-year <max(exit_year, exit_year_floor)> \
  --exit-cap-rate <exit_cap_rate> \
  --going-in-noi <audette_noi or document-extracted NOI> \
  --hold-period <exit_year - current_year> \
  --utility-escalation 0.03 \
  --output-json
```

Store the base DCF as `{asset_id}_base.json`.

If hold period < 1 year (already past exit): mark asset as `status: disposed`, skip financial analysis,
include in portfolio emissions inventory only.

### 3C — Apply each Audette measure through the DCF

For each recommended measure from Audette:

**Step 1 — Retrofit lead time check:**
- If `hold_period < 1.5 years` AND measure type is major capital (HVAC replacement, electrification,
  envelope, solar): defer to next-period exit (set `install_year = exit_year_floor + 1`). Flag
  as "deferred — insufficient lead time."
- Compliance-required measures are never deferred regardless of hold period.

**Step 2 — LL/TT allocation:**

Call `scripts/ll_allocation.py` with asset inputs:

```python
python3 scripts/ll_allocation.py \
  --lease-structure <lease_structure> \
  --metering-config <metering_config> \
  --jurisdiction <jurisdiction> \
  --measure-type <measure.measure_type> \
  --output-json
```

Returns: `ll_capture_pct` (0.0–1.0) + any edge case warnings.

**LL capture is the fraction of energy savings that flows to landlord NOI.**
Do not model NOI uplift on savings the landlord cannot capture. A NNN tenant-metered
building gets `ll_capture_pct ≈ 0.05` on in-unit measures — only fine avoidance, not
energy savings.

**BPS jurisdiction override:** If `bps_liable: true`, add the avoided annual fine to
landlord NOI regardless of lease structure:
```
avoided_fine_annual = projected_excess_emissions_t × fine_rate_per_t
```
This is always landlord-captured (property owner is liable regardless of lease).

**Step 3 — Compute annual NOI impact:**

```
annual_noi_uplift = measure.annual_savings_$ × ll_capture_pct
                  + avoided_fine_annual (if bps_liable)
```

Apply utility escalation: savings grow at 3%/yr from install year.

**Step 4 — Compute IRR (value-inclusive):**

Run the intervention through DCF engine:

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
| IRR ≥ hurdle rate (15%) | Include in recommended measures |
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

Sort by `total_value_creation DESC`. Show top 10 (or configurable top-N from global settings).

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

### 4E — Emissions trajectory vs. CRREM

For each target year (2030, 2035, 2040, 2050):

1. Compute portfolio-weighted average carbon intensity (kgCO₂e/m²) with no action
2. Compute portfolio-weighted average carbon intensity with all recommended measures implemented
3. Compare to CRREM 1.5°C pathway target for asset type + country
4. Report % of portfolio above / below / on pathway in each scenario

Flag: "Under current trajectory, [N] assets strand before 2035 (cross the CRREM pathway). With
recommended measures, [M] assets are pathway-aligned through 2035."

**Circular benchmarking rule:** Only include assets with actual EUI data (Audette or ESPM) in
the pathway comparison. Assets with estimated EUI are listed separately as "EUI unverified —
excluded from pathway analysis."

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
  "These measures do not meet the [X]% hurdle at stated assumptions. They may become
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
