---
name: sustainability-passport
description: >
  Generate a Sustainability Passport for a property being disposed, traded, refinanced, or brought
  to market. Compiles energy performance, carbon trajectory, certifications, regulatory compliance,
  capital history, CRREM misalignment risk, GRESB alignment, EU Taxonomy eligibility, and ESG narrative into
  a standardized, investor-grade disclosure document. The passport is the sustainability data room
  — it gives institutional buyers, lenders, and ESG fund managers everything they need to verify,
  underwrite, and report on the asset's environmental profile.
  Triggers on: "sustainability passport", "green passport", "green credentials", "ESG summary",
  "sustainability disclosure", "disposition sustainability", "green due diligence package",
  "sustainability report for buyers", "prepare the passport", "sustainability data room",
  "ESG data room", "GRESB data", "green building profile".
version: 2.0.0
---

# Sustainability Passport

You are generating a **Sustainability Passport** — the definitive sustainability disclosure for a property at a liquidity event (disposition, refinancing, recapitalization, or fund reporting). This document is the sustainability data room. It gives institutional buyers, lenders, fund managers, and ESG committees everything they need.

**Audience:** Varies. Write for the most demanding audience present:
- **Institutional equity buyers** — care about GRESB, net-zero pathway, CRREM misalignment risk, forward capex
- **Lenders / debt** — care about MEES/compliance risk, insurance, green financing eligibility, physical risk
- **ESG-mandated funds** — care about EU Taxonomy, SFDR alignment, SBTi-compatible trajectory, CSRD
- **Brokers / advisors** — care about concise executive summary and certification highlights
- **Operators** — care about utility data, equipment condition, certification maintenance cost

**Default posture:** Only claim what you can source. Every number must have a source and period. Estimates must be labeled. Buyers will verify — overclaiming destroys credibility.

---

## Step 1: Data Inventory & Gap Assessment

Before writing a word, inventory what's available. Surface gaps to the user immediately.

### 1A — Source Checklist

**Energy & Utility Data (minimum 24 months; 36 preferred):**
- [ ] Electricity bills (kWh by month, $ by month)
- [ ] Natural gas bills (therms/GJ by month, $ by month)
- [ ] District steam/chilled water (if applicable)
- [ ] Water bills (gallons/m³ by month)
- [ ] ENERGY STAR Portfolio Manager report (includes verified score + EUI)
- [ ] Landlord vs. tenant utility breakdown (whole-building vs. landlord-controlled)
- [ ] Smart meter / interval data (15-min or hourly if available)

**Building Documentation:**
- [ ] Current ENERGY STAR score (Portfolio Manager — not a stale screenshot)
- [ ] LEED certification + scorecard (v4 or higher preferred; note version)
- [ ] BREEAM assessment + certificate
- [ ] BOMA BESt assessment + level
- [ ] Fitwel / WELL / RESET certification
- [ ] Local green building designations (LEED EB, Toronto TGBES, etc.)

**Compliance & Legal:**
- [ ] LL97 compliance report or consultant analysis (NYC)
- [ ] BERDO compliance filings (Boston)
- [ ] Building benchmarking filings (any required jurisdiction)
- [ ] Energy audit reports (ASHRAE Level 1, 2, or 3)
- [ ] Retro-commissioning report (RCx)
- [ ] Phase I Environmental Site Assessment (date + conclusions)
- [ ] Phase II Environmental Site Assessment (if applicable)
- [ ] Any outstanding violations or fines (energy, environmental)

**Capital & Operations:**
- [ ] Capital improvements log (last 10 years, sustainability-related)
- [ ] Deferred maintenance schedule / PCA (Property Condition Assessment)
- [ ] Operating expense history (energy % of total OpEx)
- [ ] Any green lease provisions in existing leases

**External / Connected Tools — query in this order:**
1. **Audette** (primary): `list_buildings()` → `get_building_model_details(building_id)` — calibrated carbon model, CRREM pathway, equipment schedule, decarb recommendations. This is the most defensible source; always check first.
2. **ESPM / ENERGY STAR Portfolio Manager**: connected via integration or shared report — verified utility consumption.
3. **Building Performance Database (BPD)**: `get_eui_percentile()` + `get_statistics()` — peer EUI comparisons. **Only query BPD when actual EUI from Audette, ESPM, or utility bills is available.** Do not feed a CBECS benchmark EUI into BPD comparison — that produces circular results.
4. **Overture Maps**: building footprint, height, floor count for GFA cross-check.

**Data source hierarchy for energy figures:**
1. Audette calibrated model (best — use and cite directly)
2. ESPM verified consumption data
3. Utility bills from the data room
4. CBECS benchmark estimate (last resort — label every figure as `(est.)` and skip peer benchmarking)

**Circular benchmarking rule:** Never use a CBECS benchmark EUI in the Section 2B peer comparison table. If no actual EUI is available, replace the peer comparison row with: *"Measured EUI unavailable — peer comparison not shown."*

### 1B — Gap Messaging

After the inventory, report what's missing:
```
DATA GAPS IDENTIFIED:
⚠ Utility data: [specific gap]
⚠ [Missing certification or report]

Impact: Without utility data, I cannot compute EUI or operational carbon. The passport can still
document certifications, compliance status, and capital improvements. Options:
1. Request utility bills from property management (cover the last 36 months)
2. Share ENERGY STAR Portfolio Manager login or export
3. Proceed with CBECS benchmark estimates, clearly labeled as estimated

Proceeding with available data. All estimates are marked [EST].
```

---

## Step 2: The Passport Document

### Section 1 — Property Identity

| Field | Value |
|-------|-------|
| Property name | |
| Address | |
| Asset type | |
| Asset class | |
| Year built | |
| Last major renovation | Year + scope |
| Gross floor area (GFA) | SF / SM |
| Number of stories | |
| Parking | Stalls + type |
| Ownership entity | |
| Reporting boundary | Whole building / landlord-only / portfolio |
| Passport date | |
| Passport prepared by | Aris (Soapbox AI) |
| Data period | [Start] – [End] |

---

### Section 2 — Energy Performance

**2A — Consumption Summary**

| Metric | Value | Unit | Period | Source |
|--------|-------|------|--------|--------|
| Total site energy | | kBtu/yr | | |
| Site EUI | | kBtu/SF/yr | | |
| ENERGY STAR Score | | 1–100 | | |
| Electricity consumption | | kWh/yr | | |
| Natural gas consumption | | therms/yr | | |
| District steam/chilled water | | kBtu/yr | | |
| Water consumption | | kGal/yr | | |
| Total energy cost | | $/yr | | |
| Energy cost per SF | | $/SF/yr | | |

**2B — Peer Benchmarking**

Compare against:
- CBECS median for asset type (US DOE Energy Information Administration)
- ENERGY STAR baseline for asset type + climate zone (Portfolio Manager)
- CRREM intensity benchmark for asset type + country

| Benchmark | This Property | Peer Median | Top Quartile | ENERGY STAR 75th %ile |
|-----------|--------------|-------------|--------------|----------------------|
| EUI (kBtu/SF/yr) | | | | |
| Energy Star Score | | — | — | 75 |
| Carbon Intensity (kgCO₂e/m²) | | | | |

**2C — 3-Year Trend**

| Year | EUI | ENERGY STAR | Total Cost | YoY Change |
|------|-----|-------------|-----------|-----------|
| [Y-2] | | | | |
| [Y-1] | | | | |
| [Y] (current) | | | | |
| Trend | Improving / Flat / Worsening | | | |

---

### Section 3 — Carbon Footprint

**3A — Emissions Inventory**

| Scope | Source | Annual tCO₂e | Method | Emission Factor |
|-------|--------|-------------|--------|----------------|
| Scope 1 — Natural gas (heating) | Direct combustion | | IPCC/EPA AP-42 | |
| Scope 1 — Refrigerant leakage | If known | | GWP-based | |
| Scope 2 — Electricity (market-based) | Utility + RECs | | Supplier factor | |
| Scope 2 — Electricity (location-based) | Grid average | | eGRID / GHG Protocol | |
| Scope 2 — District steam/chilling | If applicable | | Supplier or estimate | |
| **Total Scope 1+2 (market-based)** | | | | |
| **Total Scope 1+2 (location-based)** | | | | |

**3B — Carbon Intensity**

| Metric | Value | Unit |
|--------|-------|------|
| Carbon intensity (location-based) | | kgCO₂e/m²/yr |
| Carbon intensity (market-based) | | kgCO₂e/m²/yr |
| Carbon intensity (lbs/SF/yr) | | lbs CO₂e/SF/yr |

**3C — CRREM Pathway Analysis**

CRREM (Carbon Risk Real Estate Monitor) defines the 1.5°C-aligned decarbonization pathway for each property type and country. Properties above the pathway are "stranded" — they will face increasing obsolescence, regulatory penalties, and capital market pressure.

| Metric | Value |
|--------|-------|
| CRREM asset type | [Office / Multifamily / Retail / etc.] |
| Current carbon intensity | [X] kgCO₂e/m² |
| CRREM 2025 target | [X] kgCO₂e/m² |
| CRREM 2030 target | [X] kgCO₂e/m² |
| CRREM 2035 target | [X] kgCO₂e/m² |
| Status vs. 2025 target | Above / On / Below pathway |
| Estimated CRREM Misalignment Year | [Year or "Not stranded through 2050 under current trajectory"] |
| Capex to stay on pathway through 2030 | $[X] |
| Capex to stay on pathway through 2040 | $[X] |

Provide a simple narrative:
> "[Property] is currently [X] kgCO₂e/m², which is [above/on/below] the CRREM 1.5°C pathway for [asset type] in [country]. At the current trajectory without intervention, the property is projected to strand in [year]. The capital investment required to maintain pathway alignment through 2030 is estimated at $[X]–$[Y]M."

**If Audette data is available:** Use the Audette CRREM chart data directly and cite it. This is the most defensible source. If Audette is not connected: label the CRREM Misalignment Year as "(est. — Audette not connected)" and note the limitation.

---

### Section 4 — Green Certifications & Ratings

List all active and recently expired certifications. Flag any expiring within 12 months.

| Certification | Level / Score | Year Earned | Expiry | Status | Notes |
|--------------|--------------|-------------|--------|--------|-------|
| ENERGY STAR Certification | | | | Active / Expired | Annual recertification |
| LEED | Certified/Silver/Gold/Platinum | | | Active / Expired | v4 EB O+M preferred |
| BREEAM | Pass/Good/Very Good/Excellent/Outstanding | | | | |
| BOMA BESt | Level 1–4 | | | | |
| Fitwel | 1–3 stars | | | | |
| WELL | Bronze/Silver/Gold/Platinum | | | | |
| RESET | | | | | |
| Toronto TGBES | | | | | |
| Other | | | | | |

**Certification Pathway Recommendation (if buyer is asking):**
> "ENERGY STAR certification costs approximately $5–15K and can be achieved within 3–6 months with a score ≥ 75. At this building's current score of [X], it [qualifies / would need to improve by N points]. LEED O+M recertification, if the existing certification lapses, typically costs $30–80K."

---

### Section 5 — Regulatory Compliance

For each applicable regulation, report current status and forward compliance risk. Buyers underwriting green bonds or ESG funds need this in writing.

| Regulation | Jurisdiction | Threshold | Current Status | 2027 Risk | 2030 Risk | Annual Penalty (if non-compliant) | Capital to Comply |
|-----------|-------------|---------|--------------|----------|----------|----------------------------------|------------------|
| Local Law 97 | NYC | >25K SF | | | | $268/tCO₂e over | |
| BERDO 2.0 | Boston | >20K SF | | | | | |
| BEPS | DC | >50K SF | | | | $2/SF/yr | |
| Energize Denver | Denver | >25K SF | | | | | |
| MEES | UK | All | Min. EPC E | Min. EPC B by 2030 | | Unable to let | |
| [Other applicable] | | | | | | | |

**Compliance narrative:** For each high-risk regulation, write 2–3 sentences explaining the specific compliance gap, the trajectory to compliance, and the estimated cost.

**Outstanding violations:** Explicitly state whether any energy, environmental, or building violations are currently open. If unknown: "No violations disclosed by seller. Buyer to verify through [city agency] prior to close."

---

### Section 6 — Physical Climate Risk

**Format per TCFD (Task Force on Climate-related Financial Disclosures):**

| Hazard | Risk Level | 2030 Outlook | 2050 Outlook | Primary Source |
|--------|-----------|-------------|-------------|----------------|
| Riverine flooding | | | | FEMA / First Street |
| Coastal flooding / storm surge | | | | FEMA / NOAA |
| Extreme heat | | | | NOAA / First Street |
| Wildfire | | | | USFS / CalFire |
| Drought / water stress | | | | WRI Aqueduct |
| Hurricane / wind | | | | NOAA HURDAT |
| Winter storm / freeze | | | | NOAA |
| Seismic | | | | USGS |

**Insurance implications:**
- Current insurer and coverage type
- Premium trend (3-year history if available)
- Any market withdrawal concerns by jurisdiction
- Flood insurance status (NFIP vs. private)

**Adaptation measures in place** (if any):
- Flood barriers, backup power, cool roofing, stormwater management, etc.

---

### Section 7 — Capital Improvements (Sustainability-Related)

Document completed capital investments that improve the sustainability profile. This is the evidence base for the passport's credibility.

| Year | Measure | Cost | Energy / Carbon Impact | Certification Impact |
|------|---------|------|----------------------|---------------------|
| | LED lighting retrofit | | -X% kWh/yr | ENERGY STAR ↑ N pts |
| | HVAC replacement (chiller) | | | |
| | Solar PV installation | | +X kW capacity | |
| | Building envelope — windows | | -X kBtu/SF/yr | |
| | BAS / controls upgrade | | | |
| | EV charging installation | | | |
| | [Other] | | | |
| **Total** | | | | |

---

### Section 8 — Water Performance

| Metric | Value | Unit | Period | Source |
|--------|-------|------|--------|--------|
| Total water consumption | | kGal/yr | | |
| Water intensity | | Gal/SF/yr | | |
| ENERGY STAR water score | | 1–100 | | |
| Irrigation water | | kGal/yr | | |
| Potable vs. non-potable | | % | | |
| Water recycling / reuse | | | | |

---

### Section 9 — Tenant Sustainability Profile

For multi-tenant assets, the tenant base affects both the risk and opportunity profile.

| Tenant | SF | % of Building | Green Lease? | Sustainability Requirements | Lease Expiry |
|--------|-----|--------------|-------------|---------------------------|-------------|
| | | | Y/N | | |

**Green lease analysis:**
- Does any existing lease include energy reporting obligations?
- Do any institutional tenants (government, REIT, large cap) have ESG mandates that require data sharing?
- Are there CAM provisions that incentivize or restrict landlord sustainability capex?

---

### Section 10 — GRESB Alignment

GRESB (Global ESG Benchmark for Real Assets) is the standard for institutional real estate ESG reporting. Many equity and debt investors require GRESB participation.

**GRESB assessment components relevant to this asset:**

| Component | Data Available? | Status |
|----------|----------------|--------|
| Management — policies | | |
| Management — targets | | |
| Management — reporting | | |
| Performance — energy | | |
| Performance — GHG | | |
| Performance — water | | |
| Performance — waste | | |
| Performance — certifications | | |
| Standing investments score (est.) | | /100 |

**Note for buyer:** If this asset is to be included in a GRESB-participating fund, confirm: (1) whether the seller has GRESB portal data available for handover, (2) the asset's historical GRESB component scores, and (3) whether utility data can be transferred at close.

---

### Section 11 — EU Taxonomy Eligibility (If Applicable)

For European-domiciled funds or assets subject to SFDR/EU Taxonomy:

**Economic Activity:** [Select: Acquisition and ownership of buildings / Renovation of existing buildings / Construction of new buildings]

**Technical Screening Criteria:**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| EPC rating A or Top 15% in national building stock | | |
| Nearly Zero Energy Building (NZEB) standard | | |
| Primary energy demand ≤ 10% of NZEB threshold | | |
| Substantial contribution to climate change mitigation | | |
| Do No Significant Harm (DNSH) — climate adaptation | | |
| Do No Significant Harm (DNSH) — water | | |
| Do No Significant Harm (DNSH) — biodiversity | | |
| Minimum social safeguards | | |

**Taxonomy alignment:** Eligible / Not Eligible / Partially Eligible (note limitations)

---

### Section 12 — ESG Narrative

**For institutional investors and ESG committees.** Write this section to stand alone — it should be citable in an investment memo.

**Structure:**
1. **Lead with the strongest credential** — What is this building's headline sustainability story?
2. **Carbon trajectory** — Where is it today, where is it going, and what's the plan?
3. **Regulatory posture** — Is the building ahead of, on track with, or behind the regulatory curve?
4. **Upside framing** — What sustainability improvements are available to the buyer and what do they unlock (green financing, certification premium, institutional tenant attraction)?
5. **Material risks** — State the primary sustainability risk honestly. Institutional buyers will find it. Disclosing it builds credibility.
6. **Forward-looking statement** — What pathway is the building on and what would a committed buyer need to invest to align it to net zero by 2040/2050?

**Template:**
> "[Property Name] is a [asset type, vintage, size] located in [market]. The building [lead credential — e.g., holds LEED Gold certification and an ENERGY STAR score of 82, placing it in the top quartile of its peer group]. 
>
> On a carbon basis, the building currently emits [X] kgCO₂e/m²/yr — [above / on / below] the CRREM 1.5°C pathway for [asset type] in [country]. [If above: The building's CRREM Misalignment Year is projected to be [year] without intervention — meaning it will exceed its carbon budget before then. A capital investment of $[X]–$[Y]M would align the building to the 2035 pathway.] [If on/below: The building is pathway-aligned through [year] under current operations, providing regulatory durability for the hold period.]
>
> From a regulatory perspective, the building [is compliant with / faces risk from] [specific regulations]. [If risk: The estimated compliance cost to avoid penalties through the [year] compliance period is $[X]. This represents [X]% of the asking price.] 
>
> The primary sustainability risk is [honest statement]. [Mitigation or buyer opportunity].
>
> For the right buyer, this asset represents [opportunity statement — e.g., 'a PACE-eligible retrofit pipeline that could unlock $X in green financing while upgrading the building to pathway alignment and supporting a green certification premium of approximately X%']."

---

### Section 13 — Data Confidence & Transparency

Before finalizing, produce a data transparency summary. This is important for institutional buyers — they need to know what is measured vs. estimated.

| Data Point | Status | Source | Period Covered | Confidence |
|-----------|--------|--------|----------------|-----------|
| Electricity consumption | Collected / Estimated / Gap | [Bill / ESPM / Benchmark] | | High/Med/Low |
| Natural gas consumption | Collected / Estimated / Gap | | | |
| Water consumption | Collected / Estimated / Gap | | | |
| Carbon Scope 1 | Calculated / Estimated | | | |
| Carbon Scope 2 (location) | Calculated / Estimated | | | |
| Carbon Scope 2 (market) | Calculated / Estimated | | | |
| ENERGY STAR score | Verified / Self-reported / Estimated | | | |
| EPC / building rating | Certified / Expired / Not assessed | | | |
| CRREM carbon intensity | Measured / Modeled / Benchmark | | | |

**Coverage rate:** [X]% of energy data is from verified meter readings; [Y]% is estimated or benchmark-derived.

**Data assurance:** [None / Internal review / Third-party verified / ISAE 3000 equivalent]

Note: Deepki (the market-leading ESG data platform for institutional real estate) has made data transparency — distinguishing collected vs. estimated data — a core credibility signal for institutional buyers. Any passport lacking this distinction will be challenged.

---

### Section 14 — Lender / Financing Profile

For assets being refinanced, recapitalized, or acquired with institutional debt:

**PCAF Score (Partnership for Carbon Accounting Financials):**
PCAF is the standard for how lenders report financed emissions. Lenders increasingly require this for green loan/bond structuring.

| Metric | Value |
|--------|-------|
| PCAF asset class | Commercial Real Estate |
| PCAF data quality score | 1–5 (1=best — operational energy from verified bills) |
| Total Scope 1+2 emissions | [X] tCO₂e |
| Physical asset value | $[X]M |
| Outstanding debt (if known) | $[X]M |
| Attributed emissions (for lender) | [X] tCO₂e |

**Green Financing Eligibility:**
| Program | Eligible? | Notes |
|---------|-----------|-------|
| Green Bond Principles (ICMA) | | |
| Climate Bonds Standard | | |
| EU Green Bond Standard | | |
| Fannie Mae Green Rewards (multifamily) | | ENERGY STAR score + utility verification required |
| Freddie Mac Green Advantage | | |
| HUD Green MIP reduction | | 25–45bp MIP reduction |
| PACE financing | | Check state/municipality eligibility |
| Green CMBS | | |

**Green Asset Ratio (GAR):**
For lenders subject to EU Taxonomy reporting, the Green Asset Ratio measures the share of assets aligned with the EU Taxonomy. For this asset:
- **EU Taxonomy alignment:** [Aligned / Not aligned / Partially aligned]
- **Reason:** [Top 15% of energy performance in building stock / NZEB standard / Not assessed]
- **EPC equivalent:** [A / B / C / Not assessed]

---

### Section 15 — INREV / Institutional Fund Reporting

For European funds reporting to institutional investors under INREV SDDS (Sustainability Data Delivery Standard):

INREV SDDS requires 109 KPIs at fund and asset level. Key asset-level KPIs this passport covers:

| KPI Category | KPIs Covered | Source |
|-------------|-------------|--------|
| Energy — electricity | Absolute consumption, intensity | Utility data |
| Energy — gas/heating | Absolute consumption, intensity | Utility data |
| GHG — Scope 1 | Absolute, intensity | Calculated |
| GHG — Scope 2 | Absolute (market + location), intensity | Calculated |
| Water | Absolute consumption, intensity | Utility data |
| Certifications | Green certification type + level | Registry |
| CRREM alignment | Above/on/below pathway | Modeled |
| BPS compliance | Applicable regulations + status | Assessed |

**Coverage rating:** [X]% of mandatory INREV SDDS KPIs available for this asset.

**SFDR Principal Adverse Impacts (PAI) indicators contributed:**
| PAI Indicator | Value | Notes |
|--------------|-------|-------|
| GHG intensity of real estate assets | [X] tCO₂e/m² | ESRS E1-4 |
| Energy performance of real estate assets | [X] kWh/m² | ESRS E1-5 |
| Share of real estate assets with EPC | [X]% | |
| Real estate assets in flood high-risk areas | Y/N | TCFD physical risk |

---

### Section 16 — Data Room Index

**Sustainability documents available in the data room:**

| Document | Available | Date | Notes |
|---------|-----------|------|-------|
| 36-month utility bills (electricity) | | | |
| 36-month utility bills (gas) | | | |
| 36-month utility bills (water) | | | |
| ENERGY STAR Portfolio Manager report | | | |
| LEED certification + scorecard | | | |
| BREEAM assessment | | | |
| Local law compliance filings | | | |
| Phase I Environmental Site Assessment | | | |
| Phase II Environmental Site Assessment | | | |
| Energy audit (ASHRAE Level 1/2/3) | | | |
| Retro-commissioning report | | | |
| Capital improvements log | | | |
| Property Condition Assessment (PCA) | | | |
| Green lease provisions (lease abstracts) | | | |
| GRESB asset data (if available) | | | |
| Audette building model / carbon plan | | | |
| Insurance certificates | | | |
| Any outstanding violations | | | |

---

## Step 3: Quality Checks Before Delivery

Before finalizing, verify:
- [ ] All EUI and carbon numbers are sourced — no ungrounded estimates pass without [EST] labels
- [ ] Compliance status reflects the most current regulatory requirements (not 2022 versions)
- [ ] All certification expiry dates are verified and flagged if within 12 months
- [ ] Penalty estimates cite the specific regulation name, section, and rate
- [ ] CRREM CRREM Misalignment Year is labeled "estimated" if modeled rather than from Audette
- [ ] Physical risk section follows TCFD framing
- [ ] GRESB section only includes confirmed data — no speculation
- [ ] EU Taxonomy section is clearly marked as applicable or not applicable
- [ ] No greenwashing — do not overclaim on partial-year data, projected improvements, or design-phase certifications
- [ ] ESG narrative is honest — states the primary risk clearly

---

## Step 4: Output Format

Deliver the passport as a two-phase artifact using the same file path. The loading skeleton emits immediately; the full passport replaces it when all sections are complete.

### Phase 1 — Loading Skeleton (emit at file path before research begins)

Navy header with property name and address already filled in. Shimmer placeholders for the 16 sections. Three pulsing dots with status text.

Use the same consulting aesthetic as the RSRA loading skeleton: navy `#12253A` header, `#F8F9FB` background, section cards in `#fff`, pure sans-serif (`-apple-system,'Helvetica Neue',Arial,sans-serif`). Zero Paged.js, zero external CDN.

### Phase 2 — Full Passport (update the same file path)

**Typography:** Every element must use `-apple-system,'Helvetica Neue',Arial,sans-serif`. Zero `Georgia`, zero `serif`, zero web font imports. The passport should look like it came from a high-end consulting firm — not a Word document.

**Citation links:** All external references must use `target="_blank" rel="noopener noreferrer"`.

**Numeric precision:** 2 significant figures on all calculated values (`$1.4M`, `42 kgCO₂e/m²`, `18 kBtu/SF/yr`). Never write `$1,427,000` or `41.7 kg`.

**File path:** Save as `Sustainability_Passport_[PropertyName]_[YYYYMMDD].html`. The loading skeleton and final document use the same path — never create a second file or a stub with only placeholder text.

**Layout structure:** Navy header → meta strip (date, preparer, CONFIDENTIAL) → meta bar (key stats) → section cards (one per section, #fff on #F8F9FB background). Each section card has an uppercase eyebrow label, bold section title with navy underline, then content.

**Omit sections with no data** rather than showing empty tables.

**3 required outputs:**
1. **Full passport HTML artifact** — the primary deliverable, designed for screen reading and Mila export to PDF/PPTX
2. **Executive summary card** — key metrics only (1 page, separate artifact on request):
   - Property snapshot
   - ENERGY STAR score
   - Carbon intensity vs. CRREM pathway
   - Certification badges
   - Compliance status summary
   - Primary risk (1 sentence)
   - Green financing eligibility (Y/N + program)
3. **GRESB-ready data export (on request)** — structured table of GRESB performance indicators with values and sources

After generating, offer to:
- Save to asset documents: `Sustainability_Passport_[PropertyName]_[YYYYMMDD].html`
- Export to PDF/PPTX via Mila (for data room upload)
- Create the 1-page executive summary separately
- Populate the RSRA CapEx section from the passport data (if running disposition → RSRA)

---

## Edge Cases

**No utility data:**
> "Utility data is the foundation of any credible passport. Without it, I can document certifications and compliance status but cannot compute EUI or carbon. Options: (1) request bills from the operator (cover 36 months), (2) use ENERGY STAR Portfolio Manager if connected, (3) note 'data not available' and use CBECS benchmarks with explicit [EST] labels. Institutional buyers will notice the gap — it's better to disclose it cleanly than to paper over it."

**Poor performance / deferred maintenance:**
> "The data shows [specific performance gap]. I'll document this accurately and frame it honestly. Institutional buyers will find it in due diligence — surfacing it in the passport with a remediation cost and buyer opportunity framing is more credible than omitting it."

**Certification expired:**
> "The [certification] expired [date]. I'll note the expiry and include the historical score. Options for the buyer: (1) recertification cost estimate: $[X], (2) estimated timeline: [months], (3) score trajectory suggests [able / not able] to recertify without capital investment."

**European fund vehicle:**
> "This asset will be acquired by an EU-regulated fund. Adding EU Taxonomy screening and SFDR classification analysis. Note: this is a preliminary assessment — legal counsel should confirm final taxonomy eligibility."

**Disposition → hand-off to broker:**
> "The passport is complete. For the broker package: use the 1-page executive summary. The full passport goes in the data room. I'd recommend attaching it as [Property Name] — Sustainability Passport — [Date].pdf at the root of the data room rather than buried in a subfolder — institutional buyers often look for it first."

**Multifamily — whole building vs. tenant data:**
> "Multifamily utility data is complicated by the landlord/tenant boundary. I'll document: (1) landlord-controlled energy (common areas, central systems), (2) whole-building energy if the property is master-metered or data is available, (3) estimate for in-unit consumption if not. This affects the ENERGY STAR score — Portfolio Manager requires a complete picture."
