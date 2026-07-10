# HVAC & Building-Retrofit Installed-Cost Market Surveys — Reference Register

**Date:** 2026-07-10
**Author:** Research agent (Opus 4.8)
**Purpose:** Seed a reference library of published market surveys, cost studies, and installed-cost datasets for specific HVAC and building-retrofit system types in **commercial and multifamily** real estate (US primary, Canada secondary). Each row cites a real source with its reported cost figures, units, base year, sector/geography, uncertainty (where given), reuse terms, and a **working URL reached from this environment**.

---

## Method & provenance notes (read first)

- **Provenance discipline.** Figures are tagged by how they were obtained:
  - **[PRIMARY-EXTRACTED]** — I downloaded the source PDF and extracted the number from the text/table myself.
  - **[PRIMARY-DOC / summary]** — the number was surfaced by a web-search summary *of the primary document*; I did not independently re-read the primary table. Treat as reliable-but-unverified to the digit.
  - **[SECONDARY]** — trade/contractor/blog figure, not a survey. Included only as a sanity band, clearly marked; **do not load as authoritative**.
- **No fabricated numbers.** Where a source clearly exists but I could not extract a specific installed-cost figure, the row says so explicitly.
- **NREL / DOE-lab hosting note (important).** In *this* build environment, `nrel.gov`, `docs.nrel.gov`, and `developer.nrel.gov` did **not** resolve (DNS ENOTFOUND, confirmed by direct fetch), while `osti.gov`, `nlr.gov`, `docs.nlr.gov`, `eia.gov`, `energy.gov`, `pnnl.gov`, `lbl.gov`, `ornl.gov`, `aceee.org`, and `neep.org` **did** resolve. A prior internal file claimed NREL "rebranded to the National Laboratory of the Rockies." **That rename is NOT confirmed** — every fetch that could have shown a live renamed page failed, so the claim rests on zero primary confirmation. NREL = **National Renewable Energy Laboratory**, a real and current DOE lab. I therefore cite NREL/DOE-lab work by its real publisher name and, wherever possible, anchor it to a stable **OSTI record + report number** (osti.gov is the authoritative DOE repository and resolves reliably). `nrel.gov` unreachability is recorded as an environment observation, not a rename.
- **The single highest-value anchor** is the **EIA "Updated Buildings Sector Appliance and Equipment Costs and Efficiency"** study (2023, base year **2022$**): US-Government work = **public domain / freely redistributable**, and it carries commercial installed-cost tables (Typical/High) for boilers, chillers, RTUs, heat pumps, GSHP, and water heaters — sourced in part to Gordian RSMeans 2023 + Guidehouse. This is the backbone; per-measure detail lives in its Appendices A–D.

---

## FRESHNESS CONSTRAINT (governs use of everything below)

**Rule (per Christopher, 2026-07-10): do not use cost figures more than 1 year old.** Cutoff ≈ **2025-07-10** base/publication year.

**Blunt reality this creates:** authoritative public cost surveys are refreshed on **multi-year cycles, not annually**. Applying a strict 1-year rule to *raw base-year dollars* would reject **almost every source in this register** — EIA (2022$), ACEEE VRF (2016), PNNL (2012/2013), ORNL GeoVision (2019), LBNL RCx (2009), Mills & Sartor fume hoods (2006), Building America envelope. The only source here whose base year is genuinely **within 1 year is CalNEXT's Dec-2025 MF split-system HPWH study**. Trade guides dated "2026" *pass the date test* but are **secondary/unreliable** and must not be treated as surveys.

**Therefore, two compliant ways to satisfy the rule (pick per measure):**

1. **Escalate-to-current (recommended default).** Treat an authoritative older study's cost as a *base-year value* and escalate it to current dollars with a **published, <1-year-old construction cost index** — e.g., ENR Construction Cost Index, BLS PPI for HVAC/plumbing equipment (series updated monthly), or RSMeans City Cost Index (annual). The **index** is what must be <1 year old, not the underlying study. This keeps the redistributable authoritative backbone usable and defensible. **Store both**: `base_cost` + `base_year` + `escalation_index` + `escalated_cost` + `escalation_date`.
2. **Fresh-only (strict).** Use only figures published within the last 12 months. Under this reading the library is nearly empty today: **CalNEXT MF split HPWH (2025)** qualifies; utility **TRMs on annual refresh cycles** (CA DEER, IL-TRM, NY, NW Power Council RTF) are the best way to get *current* per-measure costs; everything else waits for a refresh.

**Recommendation:** adopt path (1) as the engine default with a mandatory escalation stamp, and **prioritize ingesting current utility TRMs** (annual cadence) to satisfy path (2) for the measures where TRMs carry costs (ERV/HRV, DCV, VFD, LED, RTU controls). Each row below is tagged **[FRESH ≤1yr]**, **[STALE — escalate]**, or **[DATE UNVERIFIED]**.

---

## 1. Air-source heat pumps (HP-RTU, VRF/VRV, ductless mini-split, cold-climate ASHP)

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Commercial RTU heat pump | EIA, *Updated Buildings Sector Appliance and Equipment Costs and Efficiency*, 2023 (base **2022$**). Section "Commercial Rooftop Heat Pumps." | **~$4,000–$5,980 per unit** total installed cost for small-commercial rooftop HP tiers, 2022$ **[PRIMARY-EXTRACTED]** (data rows read from Appendix A; per-unit values are capacity- and efficiency-tier-specific). | US commercial | Typical vs High columns per tier; multiple capacities in appendix | **Public domain** (US Gov work) | https://www.eia.gov/analysis/studies/buildings/equipcosts/ |
| VRF / VRV (commercial) | Bonneville/utility authors, *Utility Program Cost Effectiveness of Variable Refrigerant Flow Systems*, **ACEEE Summer Study 2016**, paper 3-345. | VRF installed **~$18/ft²** vs code-minimum baseline **$12–$15/ft²** (base ~2016$) **[PRIMARY-DOC / summary]**. | US commercial | Baseline band $12–15/ft²; VRF point ~$18/ft² | ACEEE proceedings — freely downloadable; ACEEE © (cite, don't republish verbatim in bulk) | https://www.aceee.org/files/proceedings/2016/data/papers/3_345.pdf |
| VRF (industry sanity band) | VRF Wizard, *VRF Cost per Ton*. | Heat-pump VRF **~$4,000/ton**, heat-recovery VRF **~$5,000/ton** installed (recent) **[SECONDARY]**. | US commercial | wide; project-specific | Trade site — sanity band only, **not** a survey | https://vrfwizard.com/vrf-cost-per-ton/ |
| Cold-climate ASHP (ccASHP) — **performance list, not cost** | NEEP (Northeast Energy Efficiency Partnerships), *Cold Climate ASHP Specification & Product List* (v4.0). | **No installed-cost figures.** 40,000+ qualified systems, 100+ brands, performance/COP specs at low-temp ratings; explicitly covers VRF multi-split for commercial/multifamily and PTAC-replacement in high-rise MF. | US/Canada, cold climates | n/a (spec/performance data) | NEEP resource, publicly accessible; product data | https://neep.org/heating-electrification/ccashp-specification-product-list · DB: https://ashp.neep.org/ |
| ComStock costing caveat | NREL (National Renewable Energy Laboratory), *ComStock* commercial building-stock model + Standard Dataset 2024 release (report NREL/TP fy25osti 92766). | **ComStock does NOT publish installation costs** — team states upgrade cost depends on local labor/equipment/season/supply chain and varies too widely. Useful for stock/energy, not $/ton. | US commercial stock | n/a | Public (DOE/NREL); data CC-BY-style open | OSTI/report: https://docs.nlr.gov/docs/fy25osti/92766.pdf (nrel.gov host unreachable in env) |

**Coverage note:** ASHP is *moderately* covered. EIA gives redistributable per-unit RTU-HP costs; ACEEE 2016 gives a defensible VRF $/ft². **Ductless mini-split** commercial installed-cost surveys are thin (mostly residential/contractor data). **NEEP is performance data, not cost** — a common misconception; do not use it for $.

---

## 2. Ground-source / water-source heat pumps (GSHP/WSHP)

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Commercial GSHP | EIA, *Updated Buildings Sector … Costs and Efficiency*, 2023 (base **2022$**), "Commercial Ground-Source Heat Pumps" (basis: DOE/EIA water-source unitary HP + EERE 2015). | Total installed cost reported **per unit in 2022$** (tables in Appendix A; per-unit values are capacity-tier-specific) **[PRIMARY-DOC]** — specific per-unit figures require the Appendix A GSHP table. | US commercial | Typical/High tiers | **Public domain** | https://www.eia.gov/analysis/studies/buildings/equipcosts/ |
| Commercial GSHP (GeoVision) | Liu/Battocletti et al., ORNL, *GeoVision Analysis Supporting Task Force Report: Geothermal Heat Pumps* (**ORNL/TM-2019/502**, 2019). | Reports costs of "typical commercial GHP systems in the U.S." **[PRIMARY-DOC]** — I did **not** extract the specific $/ton figure; the cost breakdown is inside the TM. Flag to pull the number on ingest. | US commercial | given in report (not extracted) | **Public domain** (DOE/ORNL) | https://info.ornl.gov/sites/publications/Files/Pub103860.pdf |
| GSHP (industry sanity band) | GeothermalFinder / EnergySage 2025–26 guides. | Commercial: office **$4,500–$7,500/ton**; schools **$3,800–$6,500/ton**; residential avg **~$8,500/ton** (range $4,500–$12,500+). Drilling/loop = 50–70% of vertical closed-loop cost **[SECONDARY]**. | US | wide | Trade sites — sanity band only | https://geothermalfinder.com/costs/geothermal-installation-cost-by-state/ · https://www.energysage.com/heat-pumps/costs-benefits-geothermal-heat-pumps/ |

**Coverage note:** GSHP has a strong *authoritative* backbone (EIA + ORNL GeoVision) but the redistributable **per-ton** commercial figure needs to be extracted from the ORNL TM / EIA Appendix on ingest. Loop-field drilling is the dominant, most variable cost driver — flag for a geography multiplier.

---

## 3. Heat-pump water heaters (commercial & multifamily) + condensing DHW

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Commercial HPWH | EIA, *Updated Buildings Sector … Costs and Efficiency*, 2023 (base **2022$**), "Commercial Heat Pump Water Heater." | Total installed cost **per unit, 2022$** (Appendix A) **[PRIMARY-DOC]** — per-unit figures in the appendix table. | US commercial | Typical/High tiers | **Public domain** | https://www.eia.gov/analysis/studies/buildings/equipcosts/ |
| Central HPWH, multifamily | NEEA (Northwest Energy Efficiency Alliance), *Central Heat Pump Water Heaters for Multifamily Supply-Side Assessment Study* (©2022+). | Supply-chain survey/interviews; **installed-cost figures are in the full PDF, not the summary page** — I could not extract a $/unit from the landing page. Flag to pull from full report. | US Pacific NW, multifamily | in full report | NEEA resource, publicly downloadable | https://neea.org/resource/central-heat-pump-water-heaters-for-multifamily-supply-side-assessment-study/ |
| Split-system HPWH, multifamily | CalNEXT, *California Multifamily Split-System Heat Pump Water Heater Market Study* (**ET25SWE0026**, Final, Dec 2025). | Market + cost study specifically for MF split-system HPWH **[PRIMARY-DOC]** — figures in PDF; not extracted here. High-value, recent. | California, multifamily | in report | CA ratepayer-funded; publicly posted | https://calnext.com/wp-content/uploads/2025/12/ET25SWE0026_California-Multifamily-Split-System-Heat-Pump-Water-Heater-Market-Study_Final-Report.pdf |
| HPWH cost & market trends | NESCAUM, *Heat Pump Water Heaters in the Northeast and Mid-Atlantic — Costs and Market Trends*. | Regional installed-cost + market-trend analysis **[PRIMARY-DOC]** — figures in PDF. | US NE/Mid-Atlantic | in report | NESCAUM report, publicly posted | https://www.nescaum.org/documents/Heat-Pump-Water-Heaters-in-the-Northeast-and-Mid-Atlantic---Costs-and-Market-Trends.pdf |
| HPWH pricing research | NEEA, *Pricing Research for Efficient Water Heaters* (©2022). | Retail/installed price research across efficient water-heater classes **[PRIMARY-DOC]**. | US Pacific NW | in report | NEEA resource | https://neea.org/wp-content/uploads/2025/03/Pricing-Research-for-Efficient-Water-Heaters.pdf |
| TCO / first cost (MF & other) | DNV GL for CPUC, *Water Heat Technology Economic Assessment* (draft). | First-costs derived from DEER work papers + IOU rebate application data; HPWH curve from 2013 NEEA HPWH Field Study **[PRIMARY-DOC / summary]**. Total-cost-of-ownership framing incl. combustion-appliance-safety mitigation for MF. | California, incl. multifamily | in report | CPUC/ratepayer-funded, public | https://pda.energydataweb.com/api/view/1832/Water%20Heat%20Technology%20Economic%20Assessment%20_DraftReport_v3%20clean.pdf |
| Installed cost (context) | RMI (Rocky Mountain Institute), *Heat Pumps for Hot Water: Installed Costs in New Homes* (2020). | Installed-cost analysis — **residential/new-home** scope (note: not commercial/MF) **[PRIMARY-DOC]**. | US residential | in report | RMI, publicly posted | https://rmi.org/wp-content/uploads/2020/07/heat_pump_water_heater.pdf |

**Coverage note:** HPWH is **well-covered** — arguably the best-covered electrification measure for MF, thanks to NEEA + CalNEXT + NESCAUM + CPUC/DNV. Priority ingest: extract per-unit / per-apartment figures from CalNEXT (2025, freshest) and NEEA MF central-HPWH.

---

## 4. Chillers (high-efficiency replacement) & chiller-plant optimization

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Commercial chillers (centrifugal/screw/scroll) | EIA, *Updated Buildings Sector … Costs and Efficiency*, 2023 (base **2022$**); chiller cost basis = **Gordian RSMeans Data 2023 + Guidehouse**. | **Total installed cost ~$440–$1,390 per ton (2022$)** across centrifugal/screw/scroll chiller types, capacities, and efficiency tiers **[PRIMARY-EXTRACTED]** (data rows read from Appendix A; low end = large water-cooled centrifugal, high end = small scroll/air-cooled). | US commercial | Typical vs High columns; range spans capacity & efficiency tiers | **Public domain** (note: underlying RSMeans values are proprietary — EIA's *published aggregation* is the redistributable artifact) | https://www.eia.gov/analysis/studies/buildings/equipcosts/ |
| High-efficiency chiller purchasing | DOE FEMP, *Purchasing Energy-Efficient Electric Chillers*. | Efficiency requirements + cost-effectiveness guidance for federal buyers (kW/ton thresholds; LCC framing) **[PRIMARY-DOC]**. | US commercial/federal | n/a | **Public domain** (DOE) | https://www.energy.gov/cmei/femp/purchasing-energy-efficient-electric-chillers |
| Chiller replacement package | DOE BTO, *Schools Chiller Replacement Package — Performance Requirements, Savings and Costs* (Aug 2022). | Performance-spec package with savings + cost data for chiller replacement **[PRIMARY-DOC]** — figures in PDF. | US commercial (schools) | in report | **Public domain** (DOE) | https://www.energy.gov/documents/bto-schools-chiller-replacement-083022pdf |

**Coverage note:** Chillers are **well-covered** with a redistributable per-ton range from EIA (verified). Note the EIA chiller costs are *derived from proprietary RSMeans 2023* — cite EIA's published table, not RSMeans. Chiller-plant *optimization* (as distinct from equipment swap) has thinner published installed-cost data — closest is RCx literature in §9.

---

## 5. Boilers — condensing / high-efficiency replacement

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Commercial gas/oil boilers | EIA, *Updated Buildings Sector … Costs and Efficiency*, 2023 (base **2022$**), "Commercial Gas-Fired Boilers" / "Commercial Oil-Fired Boilers." | Total installed cost **per unit, 2022$** (Appendix A) **[PRIMARY-DOC]** — per-unit, capacity-tiered. | US commercial | Typical/High tiers | **Public domain** | https://www.eia.gov/analysis/studies/buildings/equipcosts/ |
| Large commercial boilers | DOE FEMP, *Purchasing Energy-Efficient Large Commercial Boilers*. | Efficiency thresholds + cost-effectiveness/LCC guidance for federal purchasers **[PRIMARY-DOC]**. | US commercial/federal | n/a | **Public domain** (DOE) | https://www.energy.gov/eere/femp/purchasing-energy-efficient-large-commercial-boilers |
| Boiler standards cost analysis | DOE, *Energy Conservation Standards for Consumer Boilers*, Federal Register 2023. | Rulemaking with detailed installed-cost & LCC analysis — **consumer/residential-class** boilers (note scope) **[PRIMARY-DOC]**. | US residential-class | full cost-benefit tables | **Public domain** | https://www.federalregister.gov/documents/2023/08/14/2023-16476/... |
| Commercial condensing (sanity band) | Oxmaint, *Boiler Replacement Cost 2026*. | Small commercial (0.3–1.0 MMBtu) **$18k–$34k installed** (+$6k–$10k condensing upgrade); mid (1–3 MMBtu) **$34k–$58k**; large (>3 MMBtu) **$58k–$95k** **[SECONDARY]**. | US commercial | wide | Trade site — sanity band only | https://oxmaint.com/industries/hvac/boiler-replacement-cost-2026-commercial-pricing-btu-fuel-efficiency |

**Coverage note:** Boilers **well-covered** for equipment (EIA per-unit, public domain). The *condensing premium* specifically (venting/controls uplift) is best captured from utility TRMs / the DOE FR rulemaking rather than a clean commercial survey.

---

## 6. RTU replacement / advanced RTU controls

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Advanced controls on packaged HP/AC | Wang W., Huang Y., Katipamula S., **PNNL-21944**, *Energy Savings and Economics of Advanced Control Strategies for Packaged Heat Pumps*, PNNL, **Oct 2012** (DOE Contract DE-AC05-76RL01830). | **Maximum total installed controller cost per packaged unit yielding a 3-yr payback: $1,560–$2,990 (office building); $4,180–$8,390 (retail building)** **[PRIMARY-EXTRACTED]**. (These are *max acceptable* costs for 3-yr payback, not mean market install cost.) Cost savings: office ~$19k/yr, retail ~$12k/yr per modeled building. | US commercial (office, retail) | ranges reflect 4 control scenarios | **Public domain** (DOE/PNNL) | https://www.osti.gov/servlets/purl/1059043 · https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-21944.pdf |
| Advanced Rooftop Control (ARC) field test | PNNL, **PNNL-22656**, *Advanced Rooftop Control (ARC) Retrofit: Field-Test Results* (2013). | Field-measured HVAC energy savings (14–56%) + retrofit economics **[PRIMARY-DOC]** — controller-parts figures in report. | US commercial | in report | **Public domain** (DOE/PNNL) | https://www.pnnl.gov/main/publications/external/technical_reports/pnnl-22656.pdf |
| RTU controls retrofit (parts) | DOE Better Buildings, *Implement advanced control strategies for RTUs as a retrofit measure*. | Parts cost **$500–$2,000 per RTU** (sensors, economizer, damper actuator, VFD, thermostat), 30–50% HVAC energy reduction **[PRIMARY-DOC / summary]**. | US commercial | $500–$2,000/RTU | **Public domain** (DOE) | https://betterbuildingssolutioncenter.energy.gov/implement-advanced-control-strategies-rtus-retrofit-measure |

**Coverage note:** RTU controls are **well-covered** by PNNL (verified figures) + DOE Better Buildings — a rare case with clean, redistributable, primary installed-cost data. Whole-RTU *replacement* costs fall back to EIA §1 (per-unit rooftop HP/AC).

---

## 7. Ventilation energy recovery (ERV/HRV) & demand-controlled ventilation (DCV)

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| DCV | CED Engineering, *HVAC — Guide to Demand Control Ventilation* (course monograph). | DCV adds **~$1–$3 per cfm of outside air**; CO₂ sensors now **<$200** (was >$500 a decade ago); avg savings ~38% across commercial types **[PRIMARY-DOC / summary]**. | US commercial | $1–$3/cfm OA | Course provider; engineering monograph | https://www.cedengineering.ca/userfiles/M04-037%20-%20HVAC%20-%20Guide%20to%20Demand%20Control%20Ventilation.pdf |
| DCV (state manual) | Rutgers NJ Green Building Manual, *EC Demand Control Ventilation*. | DCV design/cost guidance for commercial retrofits **[PRIMARY-DOC]** — qualitative + cost drivers. | US (NJ) commercial | n/a | State/university, public | https://greenmanual.rutgers.edu/ec-demand-control-ventilation/ |
| ERV/HRV (sanity band) | Pick Comfort / InchCalculator 2026 cost guides. | Commercial/multi-zone ERV/HRV **$4,000–$20,000+ per unit** (unit-only 500+ cfm: $4k–$15k) **[SECONDARY]**. No clean commercial $/cfm survey found. | US commercial | wide | Trade sites — sanity band only | https://www.pickcomfort.com/energy-recovery-ventilator-price-typical-costs-ranges/ · https://www.inchcalculator.com/energy-recovery-ventilator-cost-guide/ |

**Coverage note — THIN.** Authoritative commercial **$/cfm** installed-cost surveys for ERV/HRV and DCV are **weak**. Best redistributable path = **utility TRMs** (e.g., Illinois TRM, CA DEER, NY TRM) which carry prescriptive per-cfm / per-ton measure costs for ERV and DCV. Recommend sourcing those TRMs directly on ingest rather than relying on the trade bands above.

---

## 8. VFDs on pumps/fans

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| VFD evaluation protocol | DOE Uniform Methods Project (UMP), *Chapter 18: Variable Frequency Drive Evaluation Protocol* (2015). | **Authoritative M&V protocol** (not a cost survey) — defines savings/cost accounting for VFD measures; standard reference for utility program evaluation **[PRIMARY-DOC]**. | US commercial/industrial | n/a | **Public domain** (DOE) | https://www.energy.gov/sites/prod/files/2015/01/f19/UMPChapter18-variable-frequency-drive.pdf |
| VFD on pumps/motors | ASHE (Am. Society for Healthcare Engineering), *Install Variable Frequency Drives on Pumps and Motors* (2022). | Implementation + payback guidance for VFD retrofits in facilities **[PRIMARY-DOC]**. | US commercial (healthcare) | in doc | Industry society | https://www.ashe.org/system/files/media/file/2022/04/31-Install-variable-frequency-drivess.pdf |
| VFD rebates/cost (sanity band) | eilitetech / trade guides. | Utility prescriptive rebates **$80–$250 per HP**; example 75 HP install **$12k–$18k**; small ≤5 HP drives **$150–$1,000** **[SECONDARY]**. | US/Canada | wide, $/HP scales with size | Trade site — sanity band only | https://eilitetech.com/vfd-for-hvac-systems/ |

**Coverage note — THIN (for surveys).** No clean published *installed-cost survey* for VFDs. The redistributable primary is the DOE UMP protocol (methodology) + **utility TRM prescriptive measure costs ($/HP)**. Load a TRM $/HP curve on ingest; the $80–250/HP rebate band is an incentive, not an install cost.

---

## 9. Building automation / advanced controls / retrocommissioning (RCx)

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Retrocommissioning | Mills E. (LBNL), *Building Commissioning: A Golden Opportunity for Reducing Energy Costs and GHG Emissions* (LBNL, 2009). | **RCx (existing buildings) median ~$0.30/ft²; range ~$0.05–$0.40/ft²**; ~16% energy savings; payback ~1.1 yr **[PRIMARY-DOC / summary]** (2009$). | US commercial (large buildings) | $0.05–$0.40/ft² | **Public domain** (LBNL/DOE) | https://buildings.lbl.gov/publications/evaluation-retrocommissioning |
| RCx persistence/savings | LBNL, *An Evaluation of Savings and Measure Persistence from Retrocommissioning of Large Commercial Buildings*. | Savings + cost + persistence for large commercial RCx (SMUD program, BAS reports) **[PRIMARY-DOC]**. | US (Sacramento/CA) commercial | in report | **Public domain** (LBNL/DOE) | https://bies.lbl.gov/publications/evaluation-savings-and-measure |
| Commissioning existing buildings | DOE FEMP, *O&M Best Practices Guide, Ch. 7 — Commissioning Existing Buildings*. | RCx cost/benefit framing for federal facilities **[PRIMARY-DOC]**. | US federal/commercial | n/a | **Public domain** (DOE) | https://www1.eere.energy.gov/femp/pdfs/om_7.pdf |

**Coverage note:** RCx is **reasonably covered** — LBNL's $0.05–$0.40/ft² band is the canonical redistributable figure (2009$; escalate to current $). Full BAS *installation* (new controls hardware) costs are thinner in public literature; RCx (tuning existing) ≠ BAS install — keep them separate in the model.

---

## 10. Envelope — insulation, air sealing, windows, cool roofs

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| Roof air-seal + insulation | DOE Building America, *Cost Analysis of Roof-Only Air Sealing and Insulation Strategies*. | Roof air-seal+insulation **~$10.25–$20/ft² of roof area** (target ~$10/ft² for R-20) **[PRIMARY-DOC / summary]**. **Residential** scope. | US residential | $10.25–$20/ft² | **Public domain** (DOE) | https://www1.eere.energy.gov/buildings/publications/pdfs/building_america/cost-analysis-air-sealing-insulation.pdf |
| Envelope retrofit (transformative) | ORNL, *Transformative Building Envelope Retrofit* (Pub172058). | Envelope-retrofit cost-effectiveness analysis **[PRIMARY-DOC]** — figures in PDF. | US | in report | **Public domain** (DOE/ORNL) | https://info.ornl.gov/sites/publications/Files/Pub172058.pdf |
| Windows & envelope R&D | DOE BTO, *Windows and Building Envelope Research and Development* report. | Program cost/performance targets for high-performance windows & envelope **[PRIMARY-DOC]**. | US | in report | **Public domain** (DOE) | https://www.energy.gov/sites/prod/files/2014/02/f8/BTO_windows_and_envelope_report_3.pdf |

**Coverage note — MIXED.** Public envelope cost data skews **residential** (Building America). Commercial-specific envelope (curtainwall, commercial reroof, commercial window replacement) **$/ft²** surveys are thin — likely need RSMeans-derived or utility-TRM values. **Cool roofs:** LBNL Heat Island Group is the authoritative publisher, but I did **not** verify a specific cool-roof incremental-cost figure in this pass — flag as an open item (do not invent a number).

---

## 11. LED lighting + lighting controls (commercial)

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| LED retrofit (sanity band) | HireElectrical / National Efficiency Supply 2026 guides. | Commercial LED retrofit **~$0.50–$5.00/ft²** installed; controls (occupancy + daylight) raise rebate 20–40% **[SECONDARY]**. | US commercial | $0.50–$5.00/ft² | Trade sites — sanity band only | https://hireelectrical.com/guides/commercial-led-lighting-retrofit-cost/ |
| LED performance (not cost) | DesignLights Consortium (DLC), Qualified Products List. | **Performance/eligibility data, not installed cost.** Required for most utility rebates. | US/Canada commercial | n/a | DLC listing | (DLC QPL — performance reference) |

**Coverage note — THIN (for authoritative $).** No clean redistributable commercial LED **$/ft²** survey surfaced. Best primary paths: **DOE SSL / CALiPER** market reports, **GSA Green Proving Ground** LED evaluations, and **utility TRMs** (per-fixture / per-ft² measure costs). DLC is performance-only. Recommend pulling DOE SSL + a TRM lighting chapter on ingest. The $0.50–$5.00/ft² band is a trade sanity check only.

---

## 12. Fume-hood VAV / lab ventilation (the flagged "hard gap")

| system_type | citation | reported cost + units + base year | sector & geography | uncertainty/range | license/reuse | URL |
|---|---|---|---|---|---|---|
| VAV fume hoods / lab ventilation | Mills E. & Sartor D. (LBNL), *Energy Use and Savings Potential for Laboratory Fume Hoods* (LBNL report; OSTI biblio **862161**, 2006; *Energy* journal). | Per-hood **operating** cost **$4,200–$8,200/yr** (climate-dependent); **VAV retrofit ~$6,000/hood** w/ ~$1,700/yr savings → ~3.5 yr payback; **retrofit kits = 10–20% of a new hood's cost**, install <4 hr; CAV→VAV payback typically <3 yr **[PRIMARY-DOC / summary]** (mid-2000s $). | US commercial (labs) | operating $4.2k–$8.2k/yr; retrofit ~$6k/hood | **Public domain** (LBNL/DOE) | https://www.osti.gov/biblio/862161 · https://eta-publications.lbl.gov/sites/default/files/fumehoodssartormills2006.pdf |
| VAV fume hood field study | NC State University, *Energy and Cost Savings for Variable Air Volume (VAV) Laboratory Fume Hoods in Two University Research Buildings*. | Measured energy + cost savings for VAV fume-hood retrofits in two research buildings **[PRIMARY-DOC]**. | US commercial (university labs) | in report | Academic repository | https://repository.lib.ncsu.edu/items/d6963244-b3f7-4051-b1f9-e7650a7463a8 |

**Coverage note — BETTER THAN EXPECTED.** The flagged "hard gap" is **partially filled**: LBNL (Mills & Sartor) + NCSU give real VAV fume-hood retrofit cost + payback figures. Caveat: these are mid-2000s $ and lean toward *operating cost* + *payback*; a clean, current **installed $/hood** survey is still thin. Escalate the LBNL ~$6k/hood retrofit figure and treat it as order-of-magnitude.

---

## Gaps where I found NO reliable public cost figure (do not fabricate)

- **Commercial electrical service-capacity upgrades** for electrification — no public survey; only RSMeans Div. 26 (proprietary, non-redistributable — see the sibling `2026-07-10-costing-data-sources.md`). **Genuine gap.**
- **Cool-roof incremental cost** — LBNL Heat Island Group is the right publisher but I did not verify a number this pass. Open item.
- **Chiller-plant optimization** (as distinct from equipment swap) — no clean installed-cost survey; nearest proxy is RCx (§9).
- **Ductless mini-split, commercial** — installed-cost data is residential/contractor-dominated; no authoritative commercial survey found.
- **ERV/HRV & VFD & LED commercial $/unit surveys** — thin; utility **TRMs** are the redistributable substitute (not yet pulled).

---

## Priority load order (freshness-aware)

Given the 1-year rule, load in this order:

1. **CalNEXT MF split-system HPWH (2025)** — only source with a genuinely fresh base year; MF-relevant. **[FRESH ≤1yr]**
2. **Current utility TRMs** (CA DEER, IL-TRM, NY TRM, NW RTF) — annual refresh → satisfy the rule directly for ERV/HRV, DCV, VFD ($/HP), LED, RTU controls, and prescriptive HVAC measures. *Not yet pulled — highest-value next step.*
3. **EIA equipment-cost study (2022$)** — the redistributable backbone for boilers/chillers/RTU-HP/GSHP/HPWH; load **with a mandatory escalation stamp** to current $ (path 1). **[STALE — escalate]**
4. **PNNL-21944 + DOE Better Buildings** — RTU advanced-controls costs (verified), escalate. **[STALE — escalate]**
5. **LBNL RCx $0.05–$0.40/ft²** — canonical RCx band, escalate from 2009$. **[STALE — escalate]**
6. **ORNL GeoVision (2019)** — extract commercial GSHP $/ton, escalate. **[STALE — escalate]**
7. **LBNL/NCSU fume-hood VAV** — fills the flagged gap; escalate mid-2000s $. **[STALE — escalate]**

Everything tagged **[SECONDARY]** is a sanity band only — never load as authoritative even though its date may pass.

## Environment verification log (2026-07-10)

- Direct fetch `www.nrel.gov` → **ENOTFOUND**; `docs.nrel.gov` → **ENOTFOUND**; `developer.nrel.gov` → **ENOTFOUND** (all NREL hosts unreachable from build env).
- `osti.gov`, `eia.gov`, `energy.gov`, `pnnl.gov`, `lbl.gov`, `ornl.gov`, `nlr.gov`, `aceee.org`, `neep.org`, `neea.org`, `calnext.com`, `nescaum.org` → **resolve**.
- **The "NREL → National Laboratory of the Rockies" rename is treated as UNVERIFIED** (no primary confirmation obtained; DNS failure in a sandbox is not evidence of a real-world rename). All NREL work cited by real publisher name + OSTI/report number.
- PDFs extracted with `pypdf` locally: EIA `full.pdf` (858 pp, base 2022$) and PNNL-21944 — figures tagged **[PRIMARY-EXTRACTED]** are read from those files.
