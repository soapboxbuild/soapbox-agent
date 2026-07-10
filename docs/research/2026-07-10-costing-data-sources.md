# Soapbox Costing — Cost-Data Source Landscape & MCP-Buildability Assessment

**Date:** 2026-07-10
**Author:** Research agent (Opus 4.8)
**Purpose:** Map candidate cost-data sources for a "Soapbox Costing" MCP that estimates construction CapEx (low/base/high) and annual OpEx change for building decarbonization / energy-retrofit measures in commercial & multifamily real estate (US primary, Canada secondary), and includes an electrical **service-capacity upgrade** cost model for electrification measures.

---

## 1. The question that decides everything: redistributability

The output object we want (per-measure `capex_low/base/high` + `opex_delta` + `service_upgrade_cost`, queryable by measure × archetype × region × size) is only useful if we can **legally serve the underlying values through our own multi-tenant hosted MCP**. That reframes the entire evaluation: coverage and granularity are secondary; the primary filter is *license + redistribution rights + whether a real queryable interface exists*.

Two hard truths fall straight out of the research:

1. **The best data (RSMeans/Gordian) is the least usable** — its license explicitly prohibits serving its values through a product offered for distribution or storing them in a searchable database. This is a flat legal blocker, not a pricing negotiation you can paper over cheaply.
2. **The most usable data (EIA, NREL/OpenEI, DOE Scout, DEER, TRMs) is public-domain or permissively licensed** — but it is *thin on commercial-sector per-measure CapEx* and *silent on electrical service-capacity upgrades*, which are exactly our two hardest requirements.

The whole recommendation is an exercise in stitching the redistributable-but-thin sources into something defensible, and being honest about the two gaps that remain.

### MCP-ability rubric (applied uniformly below)

- **High** — open/redistributable license (public domain, CC0, CC-BY, Apache/BSD) **AND** a queryable API or a clean structured downloadable dataset **AND** unit/assembly-level granularity.
- **Medium** — redistributable, but delivered as PDF/spreadsheet/scattered repo files needing real ETL, **OR** an API exists but redistribution is contractually restricted, **OR** granularity is coarser than per-measure unit cost.
- **Low** — proprietary with redistribution restricted, data locked inside an app, or only whole-project/prose estimates.

---

## 2. RSMeans / Gordian — the industry standard, and a licensing dead end

**What it is / publisher.** RSMeans Data, published by **Gordian** (a Fortive company). North America's de-facto construction-cost standard: 92,000+ unit line items, tens of thousands of researcher-hours per year, used by USACE/DoD, architects, and GCs. Delivered via "RSMeans Data Online" (Gordian Cloud Platform), annual cost books (2026 base year), and packaged Excel/CD datasets.

**Coverage.** New construction **and renovation/retrofit** (facilities MR&R), **commercial and residential**, plus heavy civil; US + Canada with 970+ localized City Cost Index areas. **Electrical service/switchgear: YES** — full CSI MasterFormat Division 26; the 2026 Electrical Costs dataset carries ~14,000 line items including switchgear, service entrance, breakers, and EV chargers. This is the *only* source in the entire landscape with genuine, structured commercial electrical-service line-item costs.

**Access model.** Paid per-seat SaaS (Core/Complete/Complete Plus). **No public REST/JSON developer API** — only closed partner integrations inside the Gordian Cloud Platform. Redistribution is **flatly prohibited.** The RSMeans Online User Agreement states verbatim that the customer may not "use, copy, download, store, publish, modify, translate, transmit, transfer, sell or prepare derivative works of the Estimating Data," that "Downloaded Data shall not be stored or used in an archival database or **other searchable database**," and may not "use the Estimating Data **as a component of or as a basis for any material or product offered for sale, license or distribution.**" The base SaaS terms independently bar making the data available via "software as a service, cloud, or other technology or service."

**Granularity & freshness.** Best-in-class: $/unit line items **and** assemblies **and** square-foot models; City Cost Indexes for regional factors; quarterly updates on Data Online, annual 2026 base-year books. Naturally supports bare-cost / O&P / localized ranges.

**MCP-ability: LOW.** The data is exactly what we want and the license targets exactly what we want to do. Serving RSMeans values through our hosted MCP is prohibited without a **bespoke OEM/data-redistribution agreement negotiated with Gordian** (no public pricing; enterprise deal). Treat RSMeans as: (a) an internal-only estimator reference under a per-seat license, or (b) a licensing conversation — not a wrappable source.

Sources: [gordian.com/rsmeans-data-services](https://www.gordian.com/products/rsmeans-data-services/), [2026 Electrical Costs](https://www.rsmeans.com/2026-electrical-costs-book), [City Cost Index](https://www.rsmeans.com/rsmeans-city-cost-index), [RSMeans Online User Agreement (PDF)](https://www.rsmeansonline.com/Content/RSMeansOnlineUserAgreement.pdf).

---

## 3. Commercial estimating APIs (the "buy an embedding license" path)

These are the realistic build-on candidates if we want RSMeans-grade breadth via a live API and are willing to sign a contract. Neither grants redistribution in its *public* terms — both require a signed embedding/OEM deal.

### 3a. 1build
- **Coverage:** 68M data points; material / burdened-labor / equipment / **assemblies**; county-level for 3,000+ US counties; sourced daily. Electrical present; depth vs RSMeans unverified. US-only.
- **Access:** Paid (per-estimate or subscription). **GraphQL API** (`gateway-external.1build.com`, `1build-api-key` header) with `EXTERNAL` (backend) and `EMBEDDED` (domain-locked client) key types — proof they license embedding, but only under contract. Public ToS reserves all IP, forbids extraction/scraping, grants only a "limited, non-exclusive, non-transferable, revocable license."
- **Granularity/freshness:** $/unit + assemblies, county cost variation, **updated daily** (freshest of any source).
- **MCP-ability: MEDIUM** — clean queryable API + good granularity, but redistribution is a partner deal, not open.
- Sources: [1build API docs](https://developer.1build.com/1build-api-reference/), [1build ToS](https://estimating.1build.com/terms-of-service).

### 3b. Craftsman Book (National Estimator)
- **Coverage:** National Construction Estimator (22k items), Renovation & Insurance Repair (12k), National Building Cost Manual (80+ building types), electrical + specialty trades. Residential + commercial + industrial; US + Canada area modifiers.
- **Access:** Paid subscription **API** (National Estimator API; Replacement Cost API) + bulk datasets (Excel/SQL Bacpac/Access/PDF). REST/JSON not confirmed. Redistribution terms **not public** ("plain-English license terms provided during negotiation").
- **Granularity/freshness:** $/unit + whole-building models; US/Canada area modifiers; annual cadence.
- **MCP-ability: MEDIUM** — structured bulk data for ETL + an API, but licensing is negotiated and REST availability unconfirmed. Likely the most approachable licensor to actually talk to.
- Source: [craftsman-book.com/data-licensing](https://craftsman-book.com/data-licensing).

*Others (ProEst, Sage, Buildxact, Togal, Handoff) are estimating/takeoff software, not redistributable cost-data APIs — Buildxact actually consumes 1build's data. Not source candidates.*

---

## 4. Existing cost-estimation MCP servers — effectively greenfield

A sweep of GitHub, npm, mcp.so, Glama, LobeHub, and mcpmarket found **no production MCP server wrapping a real construction-cost database**. Only:

- **`AbhiGit-Trimble/construct-cost-mcp`** — MIT, Python, no-auth; wraps a single public Google Sheet (~8 categories incl. electrical/HVAC), 5 tools. Demo/PoC, no real data, no regional factors. Useful only as a **code skeleton**. [GitHub](https://github.com/AbhiGit-Trimble/construct-cost-mcp).
- **"Blackmount Construction"** ([mcpmarket](https://mcpmarket.com/server/blackmount-construction)) — 48 estimating *calculators* (formulas, not a cost database).

**Takeaway:** there is no incumbent to reuse and no licensing entanglement to inherit. The value of a Soapbox Costing MCP lives in the *curated data layer*, not the wrapper — the wrapper is a weekend's work.

---

## 5. NREL / OpenEI suite

> **Infrastructure note — confirmed by direct fetch 2026-07-10:** NREL has been **rebranded to the "National Laboratory of the Rockies" (NLR)** and migrated off `nrel.gov` to **`nlr.gov`**. Verified directly: `developer.nlr.gov/docs/energy-optimization/reopt/` serves live REopt API docs branded "The National Laboratory of the Rockies is a national laboratory of the U.S. Department of Energy... operated under Contract No. DE-AC36-08GO28308" (NREL's actual management contract — confirming institutional continuity). Both `developer.nrel.gov` **and** `www.nrel.gov` now return DNS `ENOTFOUND`; the developer portal was retired **May 29, 2026**. **Consequence: every `nrel.gov` / `docs.nrel.gov` / `reopt.nrel.gov` URL is dead and must be re-pointed to the `nlr.gov` equivalent** (e.g. `docs.nrel.gov/docs/...` → `docs.nlr.gov/docs/...`); the GitHub `NREL` org reportedly redirects to `NatLabRockies`. Some legacy `nrel.gov` links remain in citations below for traceability — treat them as historical and substitute the `nlr.gov` host at build time. Any MCP must target `developer.nlr.gov` for API calls.

### 5a. OpenEI Utility Rate Database (URDB) — the cleanest OpEx source in the entire landscape
- **What/coverage:** Rate-structure database for 3,700+ US utilities (energy charges, demand charges, TOU, tiers), QC'd by Illinois State University for DOE. **Residential + commercial + industrial** tariffs. This computes the utility-bill (OpEx) side of a retrofit properly — including demand charges, which flat $/kWh misses.
- **Access & license:** Free. **CC0 (public domain) — fully redistributable, no attribution required.** REST/JSON API (`developer.nlr.gov/docs/electricity/openei-utility-rates/`) + bulk CSV/JSON download + web UI.
- **Granularity/freshness:** Full tariff structures (not just averages); annual updates; ~70% of US load covered.
- **MCP-ability: HIGH.** CC0 + real API + structured tariffs. Wire directly.
- Sources: [URDB wiki](https://openei.org/wiki/Utility_Rate_Database), [OpenEI Utility Rates API](https://developer.nlr.gov/docs/electricity/openei-utility-rates/).

### 5b. REopt (formerly REopt Lite) — DER CapEx/OpEx engine
- **Coverage:** Techno-economic optimization for **solar PV + battery storage + generators + CHP + (v3) central GHP** at commercial/residential sites. Best fit for the solar/storage portion of a decarb plan. Not an envelope/HVAC unit-cost source.
- **Access & license:** Free **REST/JSON API** (`developer.nlr.gov/docs/energy-optimization/reopt/`, stable V3; v1/v2 decommissioned Mar 2024), free API key. **BSD-style permissive license** (redistribution allowed w/ attribution + "REopt®" trademark restriction). **Returns cost figures**: `initial_capital_costs`, `initial_capital_costs_after_incentives`, `lifecycle_capital_costs`, per-tech `initial_capital_cost` / `year_one_om_costs` / `lifecycle_om_cost_after_tax`. Cost defaults ($/kW, $/kWh, O&M) are user-overridable.
- **Granularity/freshness:** System-level (per-kW/per-kWh capital + O&M + whole-project economics), continuously maintained.
- **MCP-ability: HIGH — scoped to PV/storage/GHP only.** Open license + genuine API returning costs.
- Sources: [REopt API](https://developer.nlr.gov/docs/energy-optimization/reopt/), [REopt.jl outputs](https://natlabrockies.github.io/REopt.jl/dev/reopt/outputs/).

### 5c. National Residential Efficiency Measures Database (NREMDB / REMDB)
- **Coverage:** Residential retrofit measures (envelope + HVAC + water heating + lighting + appliances) with retail **price ranges**. **Residential ONLY** — do not apply to office/lab/warehouse. Panel/service upgrades not itemized.
- **Access & license:** Free, **CC-BY 4.0**. Consumer UI (`remdb.nrel.gov`) dead; authoritative copy is downloadable spreadsheets on **OEDI submission #8336** (`REMDB 2024.xlsx` etc.). No live API.
- **Granularity/freshness:** Explicit **low/base/high price ranges** per measure (good for uncertainty bands) at $/unit level; data as of Sep 2023, last updated Mar 2025. "Not designed for specific project cost estimates."
- **MCP-ability: MEDIUM** — redistributable + built-in ranges, but spreadsheet ETL and residential scope. Best use: **multifamily in-unit** measures + uncertainty-band calibration.
- Source: [OEDI REMDB #8336](https://data.openei.org/submissions/8336).

### 5d. ComStock (commercial) / ResStock (residential)
- **Coverage:** Physics-based national building-stock models. **ComStock = commercial** (office, retail, warehouse, lodging, healthcare, education). Upgrade measures **include HVAC electrification / heat pumps** — verified **HP-RTU** and **ASHP-Boiler** measures, plus envelope, LED, DCV, ERV, economizers. Service/switchgear not itemized.
- **Access & license:** Free, **BSD-style** (Alliance for Sustainable Energy). Per-measure **cost assumptions live in EUSS upgrade-package PDFs (OSTI docs) + the measure code** (`measures/ApplyUpgrade`, `resources/`), not a single cost table. No cost API.
- **Granularity/freshness:** $/unit ($/ton, $/ft², $/kBtu·h) point estimates; annual release cycle; base years vary.
- **MCP-ability: MEDIUM** — commercial + heat pumps + redistributable, but cost assumptions are scattered across PDFs/code → real ETL.
- Sources: [ComStock upgrade measures](https://nrel.github.io/ComStock.github.io/docs/upgrade_measures/upgrade_measures.html), [ASHP-Boiler EUSS (OSTI 86199)](https://docs.nrel.gov/docs/fy24osti/86199.pdf).

### 5e. End-Use Load Profiles (EULP / End-Use Savings Shapes)
- **Coverage:** Calibrated 15-min load profiles, residential + commercial, all US. **Load data, not cost data.**
- **Access/license:** Free, CC-BY 4.0, AWS S3 open data lake (~265 TB). No cost API.
- **MCP-ability: LOW (for costing)** — wrong axis. Useful only downstream to size kWh savings that feed the OpEx delta.
- Source: [OEDI EULP #4520](https://data.openei.org/submissions/4520).

### 5f. BEopt
- Residential desktop tool; its cost library **IS REMDB** (plus EIA, manufacturer data, and **proprietary RSMeans** inputs). Not an independent redistributable source. **MCP-ability: LOW** — use REMDB directly. [BEopt](https://www.nlr.gov/buildings/beopt).

### 5g. OpenEI Transparent Cost Database (TCDB) / ATB
- Cost/performance for **electricity generation, biofuels, vehicles** (LCOE-oriented) — **not building-retrofit measures.** Out of scope. **MCP-ability: LOW/N-A.** [TCDB wiki](https://openei.org/wiki/Transparent_Cost_Database).

---

## 6. DOE Building Technologies Office — Scout (the best structured commercial CapEx seed)

**What it is.** DOE BTO tool (with LBNL/NREL) estimating national energy/CO₂/cost impacts of energy-conservation measures (ECMs). `scout.energy.gov` + GitHub (`scout`).

**Coverage.** **Both commercial and residential**, split by sector in `ecm_definitions/` — hundreds of measures incl. "Commercial Rooftop Heat Pumps," "Commercial Ground Source Heat Pumps," commercial gas boilers, chillers, envelope, lighting. **Includes HVAC electrification / heat pumps.** US national/regional. Service/switchgear not itemized.

**Access & license.** Free, **Apache 2.0** (fully redistributable). Delivered as **web UI + Python + per-ECM JSON files** on GitHub — no REST API, but the cost data is a **clean structured dataset**: each ECM JSON carries `installed_cost`, `cost_units`, `installed_cost_source`, `energy_efficiency`, `product_lifetime`, plus baseline `cpl_*.json`.

**Granularity & freshness.** **$/unit with source attribution** (e.g. Commercial Rooftop Heat Pumps → `installed_cost: 7325`, `cost_units: "2013$"`). Base years embedded per measure (**often 2013$ — needs CPI/PPI escalation**). Scout supports **probability distributions** on cost → can produce **low/base/high ranges** natively. Updated with BTO analysis cycles.

**MCP-ability: MEDIUM–HIGH.** Redistributable (Apache 2.0), commercial + residential, per-measure structured JSON with unit costs, sources, lifetimes, and native uncertainty. Held back from High only by "no live API" (vendor/ETL the JSON) and base-year escalation. **Arguably the best single retrofit-measure CapEx starting point for commercial measures.**

Advanced Energy Retrofit Guides (AERGs) are public-domain **PDF whole-project** guides → **LOW** (narrative benchmarks only).

Sources: [Scout (DOE)](https://www.energy.gov/eere/buildings/scout), [scout.energy.gov](https://scout.energy.gov/).

---

## 7. EIA — the OpEx price backbone

**What it is.** U.S. Energy Information Administration Open Data **API v2** (`api.eia.gov/v2/...`), REST/JSON, exposing retail electricity and natural-gas price/sales/revenue series by **state × sector × month**.

**Coverage.** Electricity retail price by sector (`sectorid`: `COM`/`RES`/`IND`/…) and state (`stateid`), monthly/annual, via `/v2/electricity/retail-sales/data` (`price`, `sales`, `revenue`, `customers`). Natural-gas delivered prices by state/sector under `/v2/natural-gas/` (confirm exact facet path at build time). No CapEx — energy prices only.

**Access & license.** Free REST/JSON + twice-daily bulk files + Excel add-in; free API key. **U.S. government work — public domain, freely redistributable including commercially** (attribution acknowledgment requested; only the EIA logo/photos are restricted, not the values). We can absolutely serve these values.

**Granularity & freshness.** State × sector × month, ¢/kWh and $/Mcf; monthly cadence. No native low/base/high, but derivable from historical volatility.

**MCP-ability: HIGH.** Open public-domain license + clean queryable API + regional/sector granularity. The natural OpEx engine (pair with URDB when demand charges matter).

Sources: [eia.gov/opendata](https://www.eia.gov/opendata/), [API docs](https://www.eia.gov/opendata/documentation.php), [Copyright & Reuse](https://www.eia.gov/about/copyrights_reuse.php).

---

## 8. TRMs, DEER, and other utility-program cost sources (the commercial-CapEx workhorses)

### 8a. State/Regional Technical Reference Manuals (TRMs)
- **What:** PUC/program-administrator manuals standardizing deemed savings and, for many measures, **incremental cost** and O&M cost. Key ones: Illinois (IL-TRM), Mid-Atlantic (NEEP, DC/DE/MD…), New York (DPS), Massachusetts (MA-EEAC), Pennsylvania, Efficiency Maine.
- **Coverage:** Measure-level incremental cost (IL-TRM defines both time-of-sale incremental and early-replacement full-cost conventions). **Commercial included** — IL, Mid-Atlantic, NY, MA all carry C&I volumes; Efficiency Maine has a dedicated **C&I/Multifamily** TRM. One of the better *free, commercial* per-measure cost sources. Panel/service upgrades: generally **not** costed (measure only).
- **Access & license:** Free, publicly redistributable (gov docs). Dominant form is **large PDF** (+ some Excel for MA/NY). California is the structured exception (see eTRM below). Significant ETL/parsing required.
- **Granularity/freshness:** $/unit incremental cost per measure, annual/biennial, state-specific. Single deemed values (not ranges).
- **MCP-ability: MEDIUM** — redistributable + commercial-inclusive, but PDF/spreadsheet ETL; best as a curated parsed internal dataset.
- Sources: [IL-TRM v14 Vol.1](https://www.icc.illinois.gov/downloads/public/IL-TRM_Effective_010126_v14.0_Vol_1_Overview_09192025_FINAL.pdf), [Mid-Atlantic TRM v9 (NEEP)](https://neep.org/sites/default/files/resources/Mid_Atlantic_TRM_V9_Final_clean_wUpdateSummary%20-%20CT%20FORMAT.pdf), [Efficiency Maine C&I/MF TRM](https://www.efficiencymaine.com/docs/EMT-TRM_Commercial_Industrial_Multifamily_v2024_3.pdf).

### 8b. DEER / eTRM (California)
- **What:** CPUC ratepayer-funded **Database for Energy Efficient Resources** — deemed measures with **cost and savings** for residential **and nonresidential (commercial)**. Legacy `deeresources.com` → CEDARS portal → modern **eTRM** (`caetrm.com`, statewide system of record).
- **Coverage:** DEER2023 cost tables (baseline cost, early-replacement/accelerated cost, fuel-substitution labor cost). Explicitly commercial + residential → **the strongest structured commercial cost source** in the open set. Service/switchgear not itemized.
- **Access & license:** Free, public (ratepayer-funded). Historically **downloadable database** (READI web tool / MS Access "MASControl") via CEDARS — the safe, confirmed redistributable path. eTRM reportedly has an API, but external/bulk-export redistribution terms are **unconfirmed** — prefer the CEDARS downloads.
- **Granularity/freshness:** $/unit measure cost by building type/climate zone, versioned; DEER2023 recent base. Multiple baselines + climate zones give spread (not native low/base/high).
- **MCP-ability: HIGH (via downloadable structured DB)** / MEDIUM if you insist on live API. **California-specific — values need regional adjustment before applying elsewhere.**
- Sources: [CPUC DEER Updates](https://www.cpuc.ca.gov/industries-and-topics/electrical-energy/demand-side-management/energy-efficiency/database-of-energy-efficiency-resources-updates), [CEDARS DEER Resources](https://cedars.cpuc.ca.gov/deer-resources/), [caetrm.com](https://www.caetrm.com/).

### 8c. LBNL — Cost of Saved Energy / DSM Program Impacts Database
- **What:** LBNL Electricity Markets & Policy "What It Costs to Save Energy" — DSM database of ~8,790 programs across 41 states.
- **Coverage:** **Program-level $/kWh cost of saved energy** by sector (res ~$0.018/kWh; C&I/ag ~$0.021/kWh) — **NOT per-measure CapEx.** Answers "what a kWh of savings costs a program," not "what installing this heat pump costs this building."
- **Access/license:** Free, public-domain federal work; PDF reports + some structured data. Naturally produces distributions.
- **MCP-ability: LOW–MEDIUM** — good **savings-economics sanity/benchmark layer**, weak as primary CapEx.
- Source: [LBNL — What It Costs to Save Energy](https://emp.lbl.gov/projects/what-it-costs-save-energy), [LBNL-6595E](https://eta-publications.lbl.gov/sites/default/files/lbnl-6595e.pdf).

### 8d. NEEP REED / ENERGY STAR / secondary aggregators
- REED (regional program data) and ENERGY STAR are **program-level or product-performance**, not per-measure commercial install cost. Redistributable but wrong granularity/sector. **MCP-ability: LOW** — secondary benchmarks only. Confirms the honest read: **no single clean open API for commercial per-measure CapEx exists.**
- Source: [NEEP Regional & National EM&V (REED)](https://neep.org/initiatives/emv-forum/regional-national-emv).

---

## 9. Canada — thin

- **NRCan RETScreen Expert** integrates a cost/product/benchmark database for commercial/institutional buildings, but the data is **locked inside the desktop app** — free Viewer / paid Pro, **no documented public API, no exportable structured cost dataset, no license to re-serve the values.** **MCP-ability: LOW.**
- CMHC is financing/housing programs, no measure-cost DB. There is **no Canadian open DEER/TRM equivalent** with per-measure costs.
- **Plan:** adapt US TRM/DEER values with Canadian regional cost factors + NRCan Retrofit Hub reference PDFs; confirm any RETScreen reuse with NRCan directly.
- Sources: [NRCan RETScreen](https://natural-resources.canada.ca/maps-tools-publications/tools-applications/retscreen), [NRCan Retrofit Hub](https://natural-resources.canada.ca/energy-efficiency/building-energy-efficiency/retrofit-hub).

---

## 10. Electrical service-capacity upgrade costs — the highest-value gap (no database exists)

**Finding: there is no queryable database of building electrical service-upgrade costs.** It must be *synthesized into our own $/A or $/kW lookup table* from scattered studies + contractor benchmarks. This is a build-your-own, not a wrappable source. Best available evidence:

### Residential (well-characterized) — PG&E/SDG&E "Service Upgrades for Electrification Retrofits Study" (NV5 + Redwood Energy, May 2022, CALMAC PG&E0467.01)
This is the best primary source. Single-family focus, publicly funded. Figures:
- **Total service upgrade cost to customer: $2,000 – $30,000+** (labor + materials + permits + utility-side).
- **Customer-owned panel upgrade: $2,000 – $4,500, avg $2,780** (electrician-reported).
- **100A overhead → 200A service ≈ $3,200** (of which $1,800–$2,200 is the panel, ~$700 permitting).
- **New utility transformer: $6,000 – $8,000**; utility-side transformer/pole/line: additional **$2,850 – $30,000+**.
- Overhead→underground conversion / panel relocation: **$3,000 – $10,000**.
- Cross-cited literature service-upgrade values: $2,480 (Palo Alto 2018), $4,700 (Electrification of Buildings & Industry US 2018), $3,904 (Local Govt Existing-Building Decarb 2021).
- Source: [PG&E Service Upgrades Study (PDF)](https://pda.energydataweb.com/api/view/2635/Service%20Upgrades%20for%20Electrification%20Retrofits%20Study%20FINAL.pdf).

### Commercial / industrial (poorly characterized — contractor/aggregator ranges only, low authority)
- 400A service upgrade ≈ **$15,000 – $50,000**; 800–1200A ≈ **$50,000 – $100,000**; major with switchgear + utility coordination ≈ **$100,000 – $150,000+**.
- Three-phase conversion adds ≈ **$10,000 – $30,000**; underground trenching **$50 – $150/linear ft**.
- These are electrician/contractor blog estimates (deltawye.com, pennaelectric.com) — directional only, not defensible on their own. **RSMeans Division 26 is the only structured commercial source** here — and it isn't redistributable (§2).

### $/kW analog — LBNL generator-interconnection cost studies
Not a direct match (it prices *generation export* interconnection at the distribution/transmission level, not load-side building service), but a useful upper-bound sanity check: complete projects 2018–2024 averaged **$194/kW** (solar $243/kW, storage $265/kW); small (1–50 MW) projects ran up to ~$763/kW. Use only to bound the solar/storage interconnection line, not building panel upgrades.
- Source: [LBNL Generator Interconnection Costs](https://emp.lbl.gov/publications/generator-interconnection-costs-0).

### Supporting public work
- DOE CMEI "Affordable and Equitable Residential Electrification Under Electrical Panel and Service Constraints" (panel-capacity datasets; ~21% of US homes ≤100A): [energy.gov/cmei](https://www.energy.gov/cmei/buildings/articles/affordable-and-equitable-residential-electrification-under-electrical-panel).
- NREL Richmond CA "Equitable Electrification Analysis for Existing Buildings" (2023, commercial + residential): [docs.nrel.gov/docs/fy23osti/86954.pdf](https://docs.nrel.gov/docs/fy23osti/86954.pdf).

**Verdict:** build an internal parametric model — `service_upgrade_cost = f(target_amperage, phase, overhead/underground, utility-side scope)` — seeded from the PG&E study (residential/MF) and RSMeans-if-licensed or contractor ranges (commercial), expressed as **low/base/high** because the real spread is 5–10×. This is the single most defensible-but-hardest piece and should be flagged to users as an estimate with wide bands.

---

## 11. Cross-cutting gaps to state plainly

1. **Commercial per-measure CapEx has no single open API.** It is assembled from **DOE Scout (JSON) + DEER (CA) + state TRMs (PDF/XLS)**, then regionalized and escalated. Expect meaningful ETL and curation.
2. **Electrical service-capacity upgrade costs** have no database at all (§10) — synthesize a parametric model; wide uncertainty bands are honest, not a defect.
3. **Lab / fume-hood VAV** is poorly covered by *every* generic source. Neither Scout, DEER, TRMs, nor ComStock carries defensible fume-hood/VAV lab retrofit costs. Flag as a bespoke-input archetype (likely RSMeans-licensed or engineering-estimate territory).
4. **Low/base/high ranges** are native only in **REMDB** and **Scout** (probability distributions). EIA/URDB/DEER/TRM give point values → we derive ranges from historical volatility, multiple baselines, or applied ± factors.
5. **Base-year escalation** — Scout is often 2013$, TRMs vary. Need a CPI/PPI (BLS Producer Price Index for construction) escalation layer to bring everything to a common current-year basis.
6. **Regionalization** — most open sources are national or single-state (DEER = CA). Without RSMeans City Cost Indexes we need a substitute regional factor (BLS regional PPI, RSMeans indices if licensed, or a coarser Census-region factor).
7. **Canada** is weak — adapt US values; no open per-measure DB.

---

## 12. Ranked recommendation — the backbone

**Build the Soapbox Costing MCP on 4 redistributable pillars, and treat RSMeans as a licensing decision, not a data feed.**

| Rank | Source | Role | License | Interface | MCP-ability |
|------|--------|------|---------|-----------|-------------|
| **1** | **EIA API v2 + OpenEI URDB** | **OpEx delta** (energy prices + full tariffs incl. demand charges) | Public domain / **CC0** | REST/JSON APIs | **HIGH** |
| **2** | **DOE Scout** | **Commercial + residential per-measure CapEx seed** (incl. heat pumps, native uncertainty) | **Apache 2.0** | GitHub JSON (ETL) | **MED–HIGH** |
| **3** | **NREL REopt** | **Solar PV / storage / GHP CapEx + OpEx** | BSD-style | REST/JSON API | **HIGH** (DER-scoped) |
| **4** | **DEER (CA) + state TRMs** | **Commercial measure-cost depth + regional incremental costs** | Public | DB download / PDF-XLS ETL | HIGH (DEER dl) / MED (TRMs) |
| supp. | REMDB | Residential / MF in-unit measures + range calibration | CC-BY | XLSX | MED |
| supp. | PG&E study + parametric model | **Electrical service-capacity** (§10) | Public | Build-your-own | (synthesize) |
| — | **RSMeans/Gordian** | Gold-standard breadth incl. commercial electrical | **Proprietary — NOT redistributable** | SaaS, no open API | **LOW** |

**Rationale.**
- **OpEx is solved cleanly and defensibly today** — EIA (public domain) + URDB (CC0) are the two easiest, most redistributable wins. Start here.
- **Commercial CapEx backbone = Scout + DEER + TRMs.** Scout is the best single structured, redistributable, commercial, per-measure seed (Apache 2.0 JSON with uncertainty). DEER adds California commercial depth; TRMs add incremental costs across IL/Mid-Atlantic/NY/MA/Maine. All three need an ETL + escalation + regionalization layer — that layer *is* the Soapbox Costing product.
- **REopt** cleanly owns the solar/storage/GHP measures via a real cost-returning API — don't hand-roll DER economics.
- **Electrical service-capacity** is a synthesized parametric model seeded from the PG&E study (residential/MF, solid) and contractor/RSMeans ranges (commercial, weak) — shipped with wide low/base/high bands.

**Honest blockers to call out to stakeholders:**
- **RSMeans cannot be served through our MCP without a bespoke Gordian OEM/data-redistribution license.** Its ToU explicitly bars using the data "as a component of or as a basis for any product offered for distribution" and storing it in "a searchable database." If leadership wants RSMeans-grade commercial + electrical coverage, that is a **contract negotiation** (or a per-seat internal-estimator use), full stop — not something to quietly wrap.
- **Commercial per-measure CapEx and electrical service-capacity remain the two thin spots** even after stitching the open sources; both should ship as clearly-labelled estimates with wide bands, with RSMeans licensing (or 1build/Craftsman embedding) held as the upgrade path if defensibility requirements tighten.

**Suggested phasing:** (1) EIA + URDB OpEx MCP tool → (2) Scout-seeded CapEx tool with CPI/PPI escalation + Census-region factors → (3) REopt DER tool → (4) DEER/TRM enrichment for commercial depth → (5) parametric electrical-service model. Re-point all NREL URLs to `developer.nlr.gov` and verify OSTI/GitHub paths at build time.
