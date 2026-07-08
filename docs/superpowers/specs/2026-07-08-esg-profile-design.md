# ESG Profile — Design Spec

**Date:** 2026-07-08
**Author:** Christopher (via Claude)
**Status:** Draft for review
**Client driver:** the asset manager (VP ESG, the Investor) — IMN ESG & Decarbonizing Real Estate Summer Forum demo
**Related:** `decarb-plan`, `portfolio-analysis`, `rsra`, `sustainability-passport` (shared spine); `soapbox-report` (render path)

---

## 1. Summary

A new sibling skill, **`esg-profile`**, that produces an **ESG Profile** — a
**sponsor-level** (with fund-level rollup) monitoring deliverable that collates disparate
ESG, climate, building-performance, and investment data into decision-useful information
for an asset-management team. It supports **risk monitoring, budget planning, and
asset-management decision-making**, moving a firm from raw GRESB-style data collection to
actionable, investment-level insight.

> **Grain (confirmed from the asset manager's Template v3 + extract):** the Investor invests in **sponsors**
> (JV / GP positions) held across funds (Fund VI / VII / VIII). The profile is produced
> **per sponsor**, benchmarked against **Fund avg**, **Asset-Class avg**, **MIR avg**
> (Investor-wide) and **MIEPPI**. "Investment/asset-level" in earlier notes = **sponsor-level**.
> Fund-level rollup aggregates a fund's sponsors.

It reuses the exact design spine of `decarb-plan` / `portfolio-analysis` / `rsra`:
durable state ledger, no-LLM-arithmetic discipline, Verifier + Retrofit agent gates,
`fill_report` → Paged.js HTML artifact → PDF/PPTX/XLSX export.

**Primary near-term use:** the IMN stage demo — a "60-second transformation" where raw,
messy sponsor files become a branded, investor-grade ESG Profile live on stage, with
connected tools visibly streaming.

### Positioning vs. siblings
| Skill | Stage | Frame |
|-------|-------|-------|
| `rsra` | Pre-acquisition | Rapid screening from an OM |
| `decarb-plan` | Hold / capex | Full retrofit engagement, gated |
| `sustainability-passport` | Disposition / refi | Investor-grade disclosure data room |
| **`esg-profile`** | **Quarterly asset management** | **Monitoring + Q4 budget planning** |

`esg-profile` fills the gap the asset manager named: firms hold the data post-GRESB-submission (July)
but rarely operationalize it before Q4 budget season.

---

## 2. Design goals

1. **Swappable data sources (first-class requirement).** Every input is bound through a
   uniform **connector abstraction**. The demo runs some connectors live (MCP) and some
   static (from anonymized extract files); swapping a static source for a real API is a
   **binding change only** — no workflow, schema, or template change. This is the load-
   bearing architectural decision (see §5).
2. **Same discipline as the engagement products.** No LLM arithmetic; every reported number
   carries provenance; Verifier/Retrofit gates apply (batch-adapted, per `portfolio-analysis`).
3. **Deterministic, demo-safe.** No interactive human gate mid-run; the render gate
   fails closed but auto-passes when there are no open-high findings on the asset.
4. **Fund + sponsor level.** Sponsor-level profile is primary; fund-level is an aggregation
   rollup over the fund's sponsors.
5. **Client-fidelity output.** Render a Soapbox-branded HTML artifact (stage wow), and
   export a **PPTX mapped to the asset manager's `ESG Profile Template v3`** for her team's real use.
6. **Anonymization.** Sponsor identity is scrubbed by default (`anonymize: true`); the real
   sponsor name never surfaces in state, artifact, or export. Demo uses "the real sponsor".

---

## 3. Inputs → connectors

The 9 inputs the asset manager specified, plus CRREM, mapped to the **actual fields in her template +
extract**. Each row is a **connector**; the demo binding is what the IMN run uses. The
"Fills a live gap" column is the wow: three inputs are **blank in the asset manager's own data today**
("not provided / analysis underway") and our live connectors populate them.

| # | Input | Connector id | Produces (her fields) | Live source (target) | Demo binding | Fills a live gap? |
|---|-------|--------------|------------------------|----------------------|--------------|-------------------|
| 1 | Energy Star / energy | `energy` | EUI, carbon intensity, renewable %, % energy ratings | ESPM `citizen-energy` (US); EPC for EU | static (EU demo) | — |
| 2 | Green Street | `green_street` | GreenStreet Sector Risk Rating | Green Street API (pending) | static | **yes — "not provided"** |
| 3 | Physical climate risk | `physical_risk` | Physical impact rating (hazard) | `physrisk` MCP (First Street target) | **LIVE** | **yes — "not provided"** |
| 4 | Building regulation monitoring | `bps` | Market regulation, fine exposure | `run_compliance_analysis` / browser-mcp | static-cached | — |
| 5 | Sponsor questionnaire | `questionnaire` | **4 pillar scores + Total + all qual status** | Fabric or Cambio API (pending) | static (extract) | — |
| 6 | Fund / asset-class / MIR averages | `peer_benchmark` | Fund/AssetClass/MIR/MIEPPI avgs | fund data + LPAC deck | static | — |
| 7 | Materiality considerations | `materiality` | Market/asset-class materiality | reference library | static | — |
| 8 | Basic investment info | `investment_info` | Asset class, location, size, exit date, standing/dev # | fund system / manual | static (extract) | — |
| 9 | Governance rights | `governance` | 4 approval rights (budget/leasing/capex/contractor) | fund system / manual | static (extract) | — |
| + | CRREM stranding | `crrem` | Stranding year, misalignment | `crrem` MCP | **LIVE** | **yes — "analysis underway, not yet provided"** |

> **`questionnaire` is the core connector** — it produces the 4-pillar ESG scorecard (Policy
> & Strategy, Governance & Resourcing, Portfolio Management, Monitoring & Reporting → Total)
> plus the qualitative status the profile narrates. Today it's questionnaire PDFs; the live
> target is Fabric/Cambio.
>
> **The demo's headline:** CRREM + physical_risk + green_street are the three fields the asset manager's
> team leaves blank. Running them **live on stage** turns "not provided" into real values —
> the profile does something her current manual process cannot.
>
> **EU context:** the demo sponsor is Southern-Europe-based residential/BTR. ESPM (US) does not apply;
> EU energy performance is EPC-based. The `energy` connector's adapter is region-aware
> (ESPM for US, EPC for EU) — another reason the connector abstraction matters.

---

## 4. Report sections (from Template v3 — now obtained)

the asset manager's template has **two content layouts** plus two static boilerplate pages. The
`esg-profile` template reproduces these; PPTX export maps to them 1:1.

### 4A. Fund ESG Overview (fund scope)
- **Fund overview** — asset classes, locations, total size, standing/dev #, scorecard
  response rate, YoY ESG scorecard performance, **avg CRREM stranding year**, fine exposure
- **Sponsor ESG metrics matrix** — each sponsor × {green cert %, energy rating %, GRESB,
  Net Zero policy, energy data coverage, renewable %} with MIEPPI + MIR columns
- **Sponsor ESG ranking** — scorecard score, YoY change, vs MIEPPI, vs MIR (fund + MIR avg rows)
- **Underperformers** — sponsors below fund/MIR avg → **identified risk → mitigation measure**

### 4B. Sponsor ESG Profile (sponsor scope — the primary deliverable)
- **Investment overview** — asset class, location, size, projected exit, standing/dev #
- **Risk profile**
  - *Transition:* GreenStreet Sector Risk Rating, **CRREM stranding year**, market
    regulation, estimated fine exposure
  - *Physical:* physical impact rating (hazard)
- **ESG scorecard** — 4 pillars (Policy & Strategy, Governance & Resourcing, Portfolio
  Management, Monitoring & Reporting) → Total, **YoY trend**, and **regression flags**
- **Initiatives timeline** — Completed / In Progress (+budget) / Planned (+budget), with
  **regression markers ⚠️** on backslidden items
- **ESG governance approval rights** — annual budget, leasing, capex variance, contractor
- **ESG metrics benchmark** — sponsor vs **MIEPPI / Asset-Class / MIR** (never national median)

### 4C. Glossary + 4D. Endnotes/Methodology
Reusable static boilerplate (BREEAM, EPC, GRESB, LEED, CRREM, physical/transition risk
definitions; asset-class grouping + metric methodology). Lifted from her deck; template-owned.

### Distinctive analytics this template demands (design must implement)
1. **4-pillar scorecard + Total** from the questionnaire, with **year-over-year trend**.
2. **Regression detection** — items present/better in a prior year now absent/flat/worse
   (Net Zero, green lease, embodied carbon, employee engagement). A first-class output.
3. **Reconciliation from conflict notes** — the extract ships explicit `notes_conflicts`
   (DISCREPANCY entries) + a source-precedence rule ("official scorecard PDF authoritative",
   "LPAC slide authoritative"). This maps directly onto our decarb-plan reconciliation
   hierarchy + Verifier findings ledger (§5).

Applies the standing **Analytics Standards** (kWh + kWh/m²; ≤2 sig figs; peer/fund/MIR
benchmarks, never national median). **Unit normalization required:** her data is in
kBTU/sq ft and mixes lb/kg CO₂/sq ft across years — the `energy` connector normalizes to
kWh/m² and standardizes carbon units (a flagged discrepancy in her own notes).

---

## 5. Architecture

### 5.1 Connector abstraction (the swap layer)

Every input resolves through one uniform interface. A connector never bakes in "live vs
static" — that is decided by a **binding** in config.

```
Connector.resolve(context) -> ProvenancedValue

ProvenancedValue = {
  value,                       // the datum(s)
  provenance: {
    source_id,                 // e.g. "espm", "green_street"
    mode: "live" | "static" | "estimate",
    origin,                    // MCP tool name / file path / "manual"
    period,                    // reporting period the value covers
    retrieved_at
  },
  status: "ok" | "missing" | "error",
  notes
}
```

- **Binding config** (`connectors` block in run config, see §6) maps each `source_id` to an
  **adapter**: `{ kind: "mcp" | "file" | "manual", ...params }`.
  - `mcp` adapter: names the MCP tool + argument mapping (e.g. `citizen-energy get_benchmarking`).
  - `file` adapter: points at a static extract in the project's static-data repo, with a
    field map from spreadsheet/doc columns → schema fields.
  - `manual` adapter: literal values supplied in config.
- **Swapping a source = editing one binding.** The workflow calls `resolve(source_id)`;
  it does not know or care whether the value came from an API or a file. `mode` propagates
  into provenance so the artifact can label live vs. static data honestly (per the
  never-fail-silently rule).
- **Registry.** `connectors/registry.json` lists all known `source_id`s, their schema
  contract (what fields `value` must contain), and their default live adapter. Adding a real
  API later means: implement/point its live adapter, flip the binding. No schema churn.

### 5.2 Workflow phases (state machine)

Durable state at `projects/<fund>/<sponsor>/esg-profile.json` (resumable, per decarb-plan).
JSON schema at `skills/esg-profile/state-schema.json`.

1. **kickoff** — scope: which fund + sponsor (or fund-rollup), connector bindings,
   `anonymize` flag, reporting year.
2. **collect** — for each `source_id`, call `Connector.resolve`; record ProvenancedValue +
   `mode` into state. **This is the visible tool-streaming phase for the demo** — and where
   CRREM / physical_risk fill the fields her data leaves blank.
3. **reconcile** — assemble the profile data object; apply Analytics Standards + unit
   normalization; compute only via engines/tools (CRREM pathway from `crrem` MCP; BPS fines
   from compliance analysis). No LLM arithmetic. **Apply the source-precedence hierarchy to
   conflicting inputs** (official scorecard/measured > authoritative slide > extract >
   estimate); every conflict becomes a **Verifier finding** with the suggested resolution —
   never silently auto-resolved. Also run **regression detection** across reporting years.
4. **verify** — batch-adapted Verifier/Retrofit pass; findings logged to the ledger
   (`verifier__*`), not human-gated mid-run.
5. **render** — **hard, fail-closed, asset-scoped render gate**: block only on open-high
   findings on THIS asset (or a documented override). Then `fill_report(template:
   'esg-profile', data)` → HTML artifact.
6. **export** — PDF (Playwright), **PPTX mapped to Template v3**, XLSX (openpyxl) via the
   `report-review` workflow.

### 5.3 Fund-level rollup (v1, §4A Fund ESG Overview)

Fund profile = aggregation over the fund's sponsor-level profiles (same connectors, same
schema, `scope: "fund"`). Produces the §4A layout: sponsor metrics matrix, scorecard ranking
(with vs-MIEPPI / vs-MIR deltas), fund overview stats (response rate, YoY performance, **avg
CRREM stranding year**, fine exposure), and the underperformers → risk/mitigation table.
Rollup metrics (weighted stranding, aggregate fine exposure, avg scorecard) computed by the
same engines, never by the LLM. Sponsors below fund/MIR avg are auto-selected into the
underperformers table.

---

## 6. Run config (example)

```jsonc
{
  "scope": "sponsor",                 // or "fund"
  "fund": "Fund VII",
  "sponsor": "sponsor-pseudonym-01",  // NEVER the real name; scrubbed
  "reporting_year": 2025,
  "anonymize": true,                  // sponsor name + PII scrubbed everywhere
  "connectors": {
    "energy":          { "kind": "file", "region": "EU", "path": "static/extract.xlsx" },
    "physical_risk":   { "kind": "mcp",  "tool": "physrisk get_hazard_exposure" },
    "crrem":           { "kind": "mcp",  "tool": "crrem get_pathway" },
    "questionnaire":   { "kind": "file", "path": "static/extract.xlsx", "sheet": "30_input_qualitative" },
    "green_street":    { "kind": "file", "path": "static/extract.xlsx", "sheet": "30_input_qualitative" },
    "bps":             { "kind": "file", "path": "static/extract.xlsx", "sheet": "30_input_qualitative" },
    "peer_benchmark":  { "kind": "file", "path": "static/extract.xlsx", "sheet": "30_input_qualitative" },
    "materiality":     { "kind": "file", "path": "reference/materiality.json" },
    "investment_info": { "kind": "file", "path": "static/notes_scrubbed.docx" },
    "governance":      { "kind": "file", "path": "static/extract.xlsx", "sheet": "30_input_qualitative" }
  }
}
```

**To go live later:** change a `file` binding to `mcp` (or `api`), e.g.
`"green_street": { "kind": "mcp", "tool": "green-street get_metrics" }`. Nothing else moves.

---

## 7. Deliverables (build scope)

1. `skills/esg-profile/SKILL.md` — the workflow (phases, gates, discipline rules).
2. `skills/esg-profile/state-schema.json` — durable state contract.
3. `skills/esg-profile/connectors/registry.json` — source_id → schema + default live adapter.
4. `templates/esg-profile/` — `fill_report` template (layout + schema + xlsx map), built via
   the `soapbox-report` meta-skill, mapped to Template v3. **v1 includes BOTH layouts:**
   **Sponsor ESG Profile** (§4B) and **Fund ESG Overview** (§4A, a rollup over the fund's
   sponsors), plus Glossary + Endnotes boilerplate.
5. Static demo data repo — the asset manager's **scrubbed** extracts placed under the project's
   static-data repository, plus `bps_cache.json` and `materiality.json`.
6. Smoke tests — (a) one sponsor → Sponsor Profile artifact + PPTX; (b) fund rollup over ≥2
   sponsors → Fund Overview artifact + PPTX. Both end-to-end through the render gate.

---

## 8. Demo choreography (the wow)

One managed workspace, static-data repo pre-loaded with the asset manager's anonymized extracts and the
live connectors (ESPM, CRREM, physrisk) connected. Single instruction → **collect** phase
fans out with visibly streaming tool calls (paced ESPM → CRREM → physrisk) → reconcile →
**branded HTML artifact renders live in ~60s**. Close: "and here's the same profile as the
PPTX her team actually uses" (PPTX export to Template v3). No live Q&A dependency.

---

## 9. Open items / risks

1. **Template v3 fidelity.** ✓ **Obtained** via the Superhuman MCP and reverse-engineered
   (§4 now reflects the real 2-layout + glossary + endnotes structure and field list).
   Remaining build task: pixel-match the PPTX export to her master layout.
2. **⚠️ Anonymization is NOT actually done in the asset manager's files.** Despite her note, the extract +
   notes leak the real sponsor: **the real sponsor names / **, contact names + emails
   (`the real contact domain`), and specific specific city names. **Before anything goes on stage or into the
   static repo, run a scrub pass** (sponsor→pseudonym, strip PII/contacts/locations). This
   validates the `anonymize` requirement — and is a concrete pre-demo checklist item. Flag to
   the asset manager that her "anonymized" files still contain the real identity.
3. **Green Street / First Street API access** — the asset manager action item; static until confirmed.
   Note these + CRREM are exactly the fields blank in her data (the demo gap-fillers).
4. **Fabric / Cambio questionnaire API** — future live binding for the core `questionnaire`
   connector (today: questionnaire PDFs).
5. **physrisk latency** — RSRA has seen ~45-min runs; for the demo scope the physical-risk
   call tightly (single sponsor location, cached where possible) to protect the 60-second beat.
6. **Unit normalization** — her data mixes kBTU/sq ft and lb vs kg CO₂/sq ft across years
   (her own flagged discrepancy). The `energy` connector must normalize to kWh/m² and a single
   carbon unit.
7. **EU applicability** — ESPM is US-only; the demo sponsor is Southern Europe. `energy` connector must
   be region-aware (EPC for EU). Do not promise live ESPM for this specific demo sponsor.

**Extracted source artifacts** (for the build) are in the session scratchpad:
`the raw source files` + this reverse-engineered structure.

---

## 10. Out of scope (YAGNI)

- Live Q&A / interrogation layer on the profile (explicitly deferred; not needed for demo).
- Automated quarterly scheduling / consumption-spike alerting (separate future workflow the asset manager
  raised; not this skill).
- Writing back to Audette / fund systems.
