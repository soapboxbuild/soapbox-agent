# ESG Profile — Design Spec

**Date:** 2026-07-08
**Author:** Christopher (via Claude)
**Status:** Draft for review
**Client driver:** Katie Cappola (VP ESG, Madison International Realty) — IMN ESG & Decarbonizing Real Estate Summer Forum demo
**Related:** `decarb-plan`, `portfolio-analysis`, `rsra`, `sustainability-passport` (shared spine); `soapbox-report` (render path)

---

## 1. Summary

A new sibling skill, **`esg-profile`**, that produces an **ESG Profile** — an
investment-level (with fund-level rollup) monitoring deliverable that collates disparate
ESG, climate, building-performance, and investment data into decision-useful information
for an asset-management team. It supports **risk monitoring, budget planning, and
asset-management decision-making**, moving a firm from raw GRESB-style data collection to
actionable, investment-level insight.

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

`esg-profile` fills the gap Katie named: firms hold the data post-GRESB-submission (July)
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
4. **Fund + investment level.** Investment-level profile is primary; fund-level is an
   aggregation rollup over the fund's investments.
5. **Client-fidelity output.** Render a Soapbox-branded HTML artifact (stage wow), and
   export a **PPTX mapped to Katie's `ESG Profile Template v3`** for her team's real use.
6. **Anonymization.** Sponsor identity is scrubbed by default (`anonymize: true`); the real
   sponsor name never surfaces in state, artifact, or export. Demo uses "Azora".

---

## 3. Inputs → connectors

The 9 inputs Katie specified, plus CRREM (her named preferred connector for transition/
stranding risk). Each row is a **connector**; `demo mode` is the binding used for the IMN run.

| # | Input | Connector id | Live source (target) | Demo binding |
|---|-------|--------------|----------------------|--------------|
| 1 | Energy Star / benchmarking | `espm` | ESPM via `citizen-energy` MCP | **LIVE** |
| 2 | Green Street | `green_street` | Green Street API (pending access) | static (extract) |
| 3 | Physical climate risk | `physical_risk` | `physrisk` MCP (First Street target) | **LIVE** |
| 4 | Building regulation monitoring | `bps` | `run_compliance_analysis` / browser-mcp | static-cached |
| 5 | Sponsor questionnaire | `questionnaire` | Fabric or Cambio API (pending) | static (extract) |
| 6 | Fund / asset-class averages | `peer_benchmark` | BPD peers + Green Street averages | static |
| 7 | Materiality considerations | `materiality` | reference library | static |
| 8 | Basic investment info | `investment_info` | fund system / manual | static (extract) |
| 9 | Investment governance rights | `governance` | fund system / manual | static (extract) |
| + | CRREM stranding (transition risk) | `crrem` | `crrem` MCP | **LIVE** |

> Green Street + First Street API access is a Katie action item; until confirmed those stay
> static. `physrisk` is the live physical-risk engine standing in for First Street; when
> First Street access lands, only the `physical_risk` connector's live adapter changes.

---

## 4. Report sections

Reconciled against Katie's `ESG Profile Template v3.pptx` at build time (see §9 Open items).
Derived from her 9 inputs + stated business purpose:

1. **Cover / investment identity** — anonymized sponsor, fund, asset, period
2. **ESG snapshot** — headline posture, key flags
3. **Energy performance** — EUI, ENERGY STAR score, **kWh + kWh/m² only, ≤2 sig figs**
4. **Carbon trajectory + CRREM stranding** — stranding year, misalignment
5. **Physical climate risk** — hazard exposure (physrisk / First Street)
6. **Regulatory / BPS exposure** — applicable BPS, fine-risk timeline
7. **Peer benchmark** — vs **BPD peer set / fund averages (never national median)**
8. **Materiality** — market-, asset-class-, investment-specific
9. **Governance rights** — investor influence levers
10. **Risk monitoring & Q4 budget recommendations** — the "so what": prioritized actions

Applies the standing **Analytics Standards** (kWh + kWh/m²; ≤2 sig figs; BPD peers, not
national median; IRR = incremental cost + landlord-share savings + conditional exit value).

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

Durable state at `projects/<asset-key>/esg-profile.json` (resumable, per decarb-plan). JSON
schema at `skills/esg-profile/state-schema.json`.

1. **kickoff** — scope: which fund/investment, connector bindings, `anonymize` flag.
2. **collect** — for each `source_id`, call `Connector.resolve`; record ProvenancedValue +
   `mode` into state. **This is the visible tool-streaming phase for the demo.**
3. **reconcile** — assemble the profile data object; apply Analytics Standards; compute only
   via engines/tools (CRREM pathway from `crrem` MCP; BPS fines from compliance analysis).
   No LLM arithmetic.
4. **verify** — batch-adapted Verifier/Retrofit pass; findings logged to the ledger
   (`verifier__*`), not human-gated mid-run.
5. **render** — **hard, fail-closed, asset-scoped render gate**: block only on open-high
   findings on THIS asset (or a documented override). Then `fill_report(template:
   'esg-profile', data)` → HTML artifact.
6. **export** — PDF (Playwright), **PPTX mapped to Template v3**, XLSX (openpyxl) via the
   `report-review` workflow.

### 5.3 Fund-level rollup

Fund profile = aggregation over the fund's investment-level profiles (same connectors, same
schema, `scope: "fund"`). Rollup metrics (portfolio EUI, weighted stranding, aggregate fine
exposure) computed by the same engines, never by the LLM.

---

## 6. Run config (example)

```jsonc
{
  "scope": "investment",              // or "fund"
  "fund": "Fund IV",
  "investment": "azora-asset-001",
  "anonymize": true,                  // sponsor name scrubbed everywhere
  "connectors": {
    "espm":            { "kind": "mcp",  "tool": "citizen-energy get_benchmarking" },
    "physical_risk":   { "kind": "mcp",  "tool": "physrisk get_hazard_exposure" },
    "crrem":           { "kind": "mcp",  "tool": "crrem get_pathway" },
    "green_street":    { "kind": "file", "path": "static/Azora_ESG_Structured_Extract_2025.xlsx", "sheet": "GreenStreet" },
    "questionnaire":   { "kind": "file", "path": "static/Azora_ESG_Engagement_Notes_2025.docx" },
    "bps":             { "kind": "file", "path": "static/bps_cache.json" },
    "peer_benchmark":  { "kind": "file", "path": "static/Azora_ESG_Structured_Extract_2025.xlsx", "sheet": "Peers" },
    "materiality":     { "kind": "file", "path": "reference/materiality.json" },
    "investment_info": { "kind": "file", "path": "static/Azora_ESG_Structured_Extract_2025.xlsx", "sheet": "Investment" },
    "governance":      { "kind": "file", "path": "static/Azora_ESG_Engagement_Notes_2025.docx" }
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
   the `soapbox-report` meta-skill, mapped to Template v3 sections.
5. Static demo data repo — Katie's anonymized extracts placed under the project's static-data
   repository, plus `bps_cache.json` and `materiality.json`.
6. Smoke test — one investment, demo bindings, end-to-end to rendered artifact + PPTX.

---

## 8. Demo choreography (the wow)

One managed workspace, static-data repo pre-loaded with Katie's anonymized extracts and the
live connectors (ESPM, CRREM, physrisk) connected. Single instruction → **collect** phase
fans out with visibly streaming tool calls (paced ESPM → CRREM → physrisk) → reconcile →
**branded HTML artifact renders live in ~60s**. Close: "and here's the same profile as the
PPTX her team actually uses" (PPTX export to Template v3). No live Q&A dependency.

---

## 9. Open items / risks

1. **Template v3 fidelity.** `ESG Profile Template v3.pptx` + the two extract files are Gmail
   attachments the Gmail MCP cannot extract as binary. **Superhuman MCP installed for this
   purpose** — pending one-time OAuth. Obtain and reconcile §4 sections + the PPTX export map
   against her real layout before finalizing the template.
2. **Green Street / First Street API access** — Katie action item; static until confirmed.
3. **Fabric / Cambio questionnaire API** — future live binding for `questionnaire`.
4. **physrisk latency** — RSRA has seen ~45-min runs; for the demo, scope the physical-risk
   call tightly (single asset, cached where possible) to protect the 60-second beat.
5. **Anonymization completeness** — verify sponsor name is absent from extract file *contents*
   (not just filenames) before the static repo is loaded.

---

## 10. Out of scope (YAGNI)

- Live Q&A / interrogation layer on the profile (explicitly deferred; not needed for demo).
- Automated quarterly scheduling / consumption-spike alerting (separate future workflow Katie
  raised; not this skill).
- Writing back to Audette / fund systems.
