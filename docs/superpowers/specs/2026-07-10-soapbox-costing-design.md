# Soapbox Costing — Design

**Date:** 2026-07-10
**Status:** Draft design, pending user review
**Origin:** The `construction-costing` skill (shipped in the decarb economic-realism upgrade)
produces a validated `measure.cost` object, but every dollar in its `cost-bases.md` is a
hand-seeded placeholder. This project replaces those placeholders with real, sourced cost data
served through a dedicated MCP, packaged as a standalone **Soapbox Costing** plugin with its own
costing-specialist persona — broadening coverage to a wide range of HVAC and building-retrofit
measures, plus energy-price (OpEx), distributed-energy (DER), and electrical service-capacity
costs.

**Companion research:** `docs/research/2026-07-10-costing-data-sources.md` (the source-landscape
and redistributability assessment this design is built on).

## Goal

Give every Soapbox portfolio agent a defensible, provenance-tagged cost estimate — CapEx
(low/base/high) and annual OpEx delta — for a broad set of decarbonization / retrofit measures,
without inventing numbers and without violating any data license. Ship it as a reusable plugin
(`soapbox-costing`) so it auto-provisions to portfolios like the other function plugins.

## The redistributability constraint (why the design looks the way it does)

The single axis that governs everything: **can we legally serve a source's values through our
own multi-tenant hosted MCP?**

- **RSMeans/Gordian** — the only source with structured *commercial electrical-service* and deep
  commercial line items — **cannot be served** through our MCP; its license bars using the data
  "as a component of or as a basis for any product offered for distribution" and storing it in "a
  searchable database." (Exact ToU language to be re-verified against the primary source at
  plan-writing time — it is load-bearing for this whole architecture.) RSMeans stays a **licensed
  upgrade path**, not a data feed.
- The redistributable sources (**EIA, OpenEI URDB, DOE Scout, NREL REopt, DEER, state TRMs,
  REMDB**) are public-domain or permissively licensed but are thin on commercial per-measure
  CapEx and silent on electrical service-capacity. The product *is* the curated layer that
  stitches, escalates, and regionalizes them.

**Two gaps persist even at full scope, and ship as clearly-flagged wide-band estimates, not
hidden:** (1) commercial electrical service-capacity upgrades (synthesized parametric model);
(2) lab / fume-hood VAV (bespoke input — no open source covers it).

## Scope (v1 — the full build, per user direction)

In scope for v1:
1. **`soapbox-costing` plugin** — standalone repo, structured like `crrem-skills`.
2. **Costing Specialist persona** — provenance-gated agent.
3. **Costing skill** — evolved from `construction-costing`; orchestrates the MCP into a
   `measure.cost` object.
4. **Costing MCP** (`costing.mcp.soapbox.build`, deployed to the `soapbox-mcps` project) with:
   - **CapEx** — a curated data layer (DOE Scout + DEER + state TRMs + REMDB, escalated and
     regionalized) covering a **broad HVAC + building-retrofit measure taxonomy**.
   - **OpEx** — live EIA + OpenEI URDB (energy prices + full tariffs incl. demand charges).
   - **DER** — live REopt (solar PV / storage / GHP).
   - **Electrical service-capacity** — synthesized parametric $/A model.
5. **Rewiring** `decarb-plan` measure screening to call the MCP-backed costing skill; the
   `measure.cost` contract stays canonical in `soapbox-agent` and `quality-review` reads it
   unchanged.

Non-goals (YAGNI): wrapping or redistributing RSMeans/1build/Craftsman (licensing path, tracked
separately); a takeoff/quantity-survey workflow; per-project bid generation; changing Audette's
optimizer; live utility-rate contract negotiation. Lab/fume-hood defensible unit costs are
explicitly out of reach from open data — v1 flags them, it does not solve them.

## Architecture

### Repository & packaging

New repo **`github.com/soapboxbuild/soapbox-costing`**, mirroring `crrem-skills`:

```
soapbox-costing/
  .claude-plugin/plugin.json     # name: soapbox-costing; references the MCP
  .mcp.json                      # costing → https://costing.mcp.soapbox.build/mcp
  skills/costing/SKILL.md        # the orchestrating skill (+ references/)
  agents/subagents/costing-specialist.md
  commands/                      # optional slash entrypoints
  README.md, logo.svg, LICENSE
```

The MCP server itself lives in its own service in the **`soapbox-mcps` Railway project**
(domain `costing.mcp.soapbox.build`) — never a new project. The plugin's `.mcp.json` and
`plugin.json` point at it (authenticated connector; omit `mcp_url` where the platform injects it,
per the connector-hookpoint convention).

### Contract home (single source of truth, no vendoring)

The `measure.cost` JSON Schema + `validate-measure-cost.mjs` **stay canonical in
`soapbox-agent`**. Rationale: the consumers (`decarb-plan`, `quality-review`) live there and the
core must not depend on a plugin being installed. The costing skill **produces** a `measure.cost`
object; consumers **validate on receipt**. The plugin carries **no copy** of the schema (zero
drift). If a future need forces the persona to self-validate standalone, only then vendor a copy —
and add a drift assertion test against the canonical file.

**Additive contract extension (backward-compatible):** to carry contingency and labour detail,
the canonical `measure.cost.cost` object gains optional fields — `contingency_pct`,
`cost_breakdown { material, labour, equipment }`, and an `escalation { index, index_vintage,
escalated_to, base_year }` stamp. These are additive (existing objects stay valid); the schema +
validator update is a small task in the rewiring plan, and `quality-review` gains a WARN if a
CapEx figure lacks an escalation stamp (stale-cost guard, enforcing the ≤ 1-year policy).

### Data-layer split (static vs live vs computed)

- **CapEx → static curated store.** An offline **ETL pipeline** ingests Scout JSON, DEER
  downloads, parsed TRMs, and REMDB spreadsheets into a **curated read-only DuckDB file** shipped
  with the MCP service (escalated to a common base year, regionalized, uncertainty-banded). The
  MCP queries this file — fast, deterministic, no per-request external calls, redistribution-safe
  because values are curated from redistributable sources.
- **OpEx → live API.** EIA v2 + URDB called at request time, response-cached. (These change
  monthly; no benefit to freezing them.)
- **DER → live API.** REopt called at request time.
- **Electrical service-capacity → computed in code.** A parametric $/A model, no external call.

The ETL pipeline is a repo-internal build tool (its own directory + docs), run to regenerate the
curated DuckDB when sources update; it is **not** a runtime dependency of the MCP.

## Broad measure taxonomy (the "even more costing" requirement)

A canonical Soapbox measure taxonomy, each entry mapping to its source rows and carrying a
confidence tier. Target coverage for v1:

- **HVAC heating / electrification:** ASHP (RTU / split / VRF), ground-source heat pump (GSHP),
  condensing boiler, high-efficiency furnace, heat-pump water heating.
- **HVAC cooling:** high-efficiency chiller replacement, **chiller-plant optimization**, RTU
  replacement, economizer.
- **HVAC distribution & controls:** VFDs, demand-controlled ventilation (DCV), BAS / advanced
  controls, ERV / HRV.
- **Ventilation (specialty):** fume-hood VAV / occupancy setback — *flagged bespoke, low
  confidence, no open source*.
- **Envelope:** roof/wall/attic insulation, air sealing, high-performance windows, cool roof.
- **Lighting:** LED retrofit, lighting controls.
- **Domestic hot water:** heat-pump water heaters, condensing DHW.
- **On-site generation / DER:** solar PV, battery storage, GHP (routed to REopt).
- **Electrical:** service-capacity upgrade (parametric).

Each measure carries `source` (scout | deer | trm:<state> | remdb | reopt | pge-parametric |
tuned-base), `base_year`, `confidence` (high | medium | low), and where the source provides it,
native uncertainty. Measures with no open source (fume-hood VAV, commercial electrical) map to the
parametric / tuned-base / low-confidence path and surface that plainly.

## MCP tools

1. **`list_measures()` / `describe_measure(measure)`** — taxonomy discovery; returns each
   measure's source, confidence, unit basis, and coverage caveats.
2. **`get_measure_capex(measure, archetype, region, size)`** → `{ low, base, high, unit_basis,
   cost_breakdown: { material, labour, equipment }, contingency_pct, source, base_year,
   escalation: { index, index_vintage, escalated_to }, labour_factor, confidence, references[] }`
   from the curated store, escalated + regionalized (labour factor applied to the labour share).
3. **`get_energy_prices(region, sector, fuel)`** → EIA retail price series (¢/kWh, $/Mcf) by
   state × sector.
4. **`get_tariff(utility_or_zip, sector)`** → URDB tariff structure incl. demand charges (for a
   proper OpEx delta, not a flat blended rate).
5. **`get_der_economics(system, size, location)`** → REopt capital + O&M + lifecycle economics
   for PV / storage / GHP.
6. **`estimate_service_upgrade(demand_increase_kw | target_amperage, phase, service_type,
   sector, region)`** → `{ low, base, high, flag: "UNVERIFIED" }` parametric model (§ below).
7. **`get_regional_factor(region)`** → **separate labour and material** cost multipliers used to
   regionalize national CapEx (RSMeans City Cost Index substitute); the labour multiplier is
   applied to the labour share of `cost_breakdown`.
8. **`get_references(measure | system_type)`** → the vetted citations backing a measure's cost
   (from the register), so every estimate can surface its evidence.
9. **`add_reference(...)`** (build/ops) → ingest a new market survey into the register + memory
   bank; the growth mechanism, not a portfolio-agent runtime tool.

`get_measure_capex` responses include a `references[]` array of the citations that support the
returned range.

The **costing skill** composes these into the `measure.cost` object (it does not compute
NPV/IRR — that stays in `decarb-plan`). For a fuel-switch it: pulls `get_measure_capex` for the
switch and its efficiency alternative, `estimate_service_upgrade` for the `electrical_capacity`
block, and `get_energy_prices`/`get_tariff` to derive `opex_delta_yr`. Every number carries its
provenance through to the object.

## Supporting layers

- **Freshness / currency policy (≤ 1 year — required):** every cost figure served must reflect
  **current-year dollars, current within one year.** A source with an older base year is only
  admissible after escalation to the current year using an index that is itself **< 1 year old**
  (ENR Construction Cost Index or BLS PPI for construction). Every figure carries an
  **escalation stamp** (`base_year`, `index`, `index_vintage`, `escalated_to`). Sources with an
  annual refresh cadence (utility TRMs, CalNEXT) are preferred over multi-year-cycle surveys for
  measures where both exist. A raw, un-escalated older figure is **non-compliant** and must not be
  surfaced.
- **Base-year escalation:** the escalation layer (above) brings all sources (Scout often 2013$,
  EIA equipment study 2022$, TRMs vary) to the common current-year basis. Escalation factors are
  data, versioned in the curated store with their vintage.
- **Contingency (explicit, never hidden):** each CapEx estimate carries an explicit
  `contingency_pct` uplift reflecting design maturity / estimate class (screening-level estimates
  warrant higher contingency than a designed scope). Contingency is reported **as its own field**
  and its effect on the total is transparent — it is not silently folded into `base`. Default
  contingency by estimate class is a versioned parameter in the curated store, tunable by
  Christopher.
- **Labour factors + cost breakdown:** CapEx is decomposed into **material / labour / equipment**
  where the source supports it, so that:
  - **Regionalization applies a labour-rate factor to the labour portion** (prevailing-wage /
    union / local-market variation) rather than one blanket multiplier on the whole cost — the
    labour share is what actually varies most by region.
  - The material portion takes a separate (smaller) regional/freight factor.
  A `labour_factor(region)` table (seeded from BLS Occupational Employment & Wage Statistics for
  construction trades, or a TRM/RSMeans-substitute regional labour index) drives this. Where a
  source gives only a blended installed cost, apply a default labour-share assumption per measure
  class (versioned, flagged lower-confidence).
- **Regionalization:** without RSMeans City Cost Indexes, use regional-factor tables — **separate
  labour and material factors** (above) at Census-division granularity for v1; DEER values (CA
  baseline) are regionalized before use elsewhere.
- **Uncertainty (low/base/high):** native where the source provides distributions (Scout, REMDB);
  otherwise derived from multiple baselines (DEER), historical volatility (EIA), or applied ±
  factors keyed to the measure's confidence tier. Escalation and regionalization widen the band.
- **Electrical service-capacity parametric model:** `service_upgrade_cost = f(target_amperage or
  demand_kw, phase, overhead/underground, sector, region)`, seeded from the PG&E/NV5 2022 study
  (residential/MF, solid) and contractor ranges (commercial, weak). Always `low/base/high`,
  always `flag: UNVERIFIED` at screening scale; the band is intentionally wide (5–10×).

## Reference library & surfaced references (grows over time)

Beyond the numeric curated store, Soapbox Costing maintains a **reference library** — a corpus of
cost *evidence* (market surveys, cost studies, program datasets, manufacturer/industry reports)
for specific system types (ASHP, VRF, GSHP, chillers, RTUs, boilers, envelope, lighting, DHW,
etc.). Two tiers:

1. **Curated reference register** — vetted, structured references stored alongside the curated
   cost data: `{ system_type, citation, publisher, year, reported_range, unit_basis, url,
   confidence }`. Every `get_measure_capex` response includes the `references[]` that back the
   number, so the persona and reports **surface citations** rather than an unsourced figure. This
   is what makes an estimate defensible.
2. **Growing memory (hindsight `soapbox-costing` bank)** — the accumulating corpus. As new market
   surveys are found, they are **retained** as tagged reference memories (by system type +
   metric); the Costing Specialist **recalls** relevant references at estimate time and can **add**
   new ones. This is the *grows-over-time* mechanism — the library is not frozen at build. (Bank
   parallels the existing `retrofit-library` bank.)

**Ingest flow:** a documented path to add a new survey — parse its reported cost figures + full
citation → add to the register (if vetted) and retain to the memory bank (tagged `costing`,
`reference`, `<system-type>`). New references adjust/tighten uncertainty bands and appear in future
citations. The library is expected to be **fed continuously** as the team encounters new surveys.

**Seeding:** a targeted market-survey research pass (by HVAC system type) seeds the initial
register — likely sources include ACEEE, LBNL, NEEP cold-climate ASHP specification & cost data,
RMI, DOE/BTO, ASHRAE, and industry market reports (each verified against its primary source at
build). This is a research deliverable that feeds the register, not invented content.

## Costing Specialist persona

`agents/subagents/costing-specialist.md` — a provenance-gated specialist (the
retrofit-specialist "runtime tool gates" lesson):

- **Never invents numbers.** Every figure traces to an MCP tool result or the tuned-base layer.
- **Surfaces provenance + confidence** on every estimate; distinguishes sourced (high) vs
  synthesized/parametric (low) vs tuned-base.
- **Never collapses an UNVERIFIED range** to a point estimate.
- **Always pairs a fuel-switch with its efficiency alternative.**
- **Flags coverage gaps** (commercial electrical, lab/fume-hood) rather than presenting a false
  point.
- **Surfaces references.** Every estimate cites the market-survey / study evidence backing it
  (`get_references` + recall from the `soapbox-costing` bank); an uncited number is treated as
  low-confidence.
- **Feeds the library.** When it encounters a new relevant survey, it retains it to the growing
  memory bank so the corpus compounds over time.
- Uses the costing MCP for all cost data — never cached or estimated values.

## Wiring into the decarb pipeline

- `decarb-plan` measure screening calls the (now MCP-backed) costing skill instead of reading
  placeholder `cost-bases.md`. `cost-bases.md` is retained only as the low-confidence **tuned-base
  fallback** for measures with no MCP coverage.
- `quality-review` reads the `measure.cost` objects unchanged (same canonical contract), and its
  gates now see real provenance/confidence to reason about.
- The contract's `electrical_capacity` block is populated from `estimate_service_upgrade`;
  `efficiency_alternative` from a second `get_measure_capex` call.

## Canada

No open Canadian per-measure cost DB (RETScreen data is locked in the desktop app). Canadian
estimates = US curated values × NRCan-informed regional factor, shipped at **lower confidence**
and flagged. Confirm any RETScreen reuse with NRCan before relying on it.

## Verify-at-build (do NOT trust the research doc's specifics blindly)

The research is a **map, not a fact source.** Before the plan hard-codes any of these, verify
against the primary source:
- **NREL → "National Laboratory of the Rockies" / `nlr.gov`** rebrand and the death of
  `nrel.gov` — a surprising, post-cutoff, single-fetch claim. Treat as **unconfirmed**; verify the
  actual live host for the REopt and URDB APIs at plan time.
- **RSMeans ToU redistribution language** — quoted verbatim in the plan only after confirming it
  against the current User Agreement; it justifies the entire "don't wrap RSMeans" architecture.
- EIA v2 / URDB / REopt exact endpoint paths, auth, and rate limits.
- Scout ECM JSON schema fields and current base years; DEER download path; TRM document URLs.

## Testing / acceptance

- **MCP contract tests:** each tool returns a well-formed, schema-valid response for a
  representative query; `get_measure_capex` returns `low ≤ base ≤ high` with a non-null `source`
  and `base_year`; `estimate_service_upgrade` never returns `low === high` and always flags
  `UNVERIFIED` at screening scale.
- **Curated-store integrity:** every taxonomy measure resolves to at least one source row or is
  explicitly marked tuned-base/parametric; escalation applied (no raw 2013$ leaks through);
  regional factor applied.
- **End-to-end:** a fuel-switch measure run through the costing skill yields a `measure.cost`
  object that validates against the canonical `soapbox-agent` schema, carries an
  `electrical_capacity` (UNVERIFIED range) and an `efficiency_alternative`, and passes
  `quality-review`'s decarb gates.
- **Provenance:** no returned cost lacks a `source`; low-confidence/gap measures are labelled.
- **References:** every high/medium-confidence measure resolves to ≥1 register reference, and
  `get_measure_capex` surfaces them; `add_reference` round-trips (ingest → register + bank →
  recall).
- **Freshness/currency:** every CapEx figure carries an escalation stamp with an index vintage
  < 1 year old and `escalated_to` = current year; a fixture with a stale index fails the
  curated-store integrity check; `quality-review` WARNs on a missing stamp.
- **Contingency & labour:** `get_measure_capex` returns an explicit `contingency_pct` and a
  `cost_breakdown` summing to the pre-contingency base; the regional labour factor is applied to
  the labour share only (verify a high-labour region moves labour, not material, and the total
  reflects it).
- **Regression (245 First):** the lab-envelope measure stays excluded; a boiler-vs-ASHP screen
  surfaces both options with sourced capex + opex delta and an honest electrical-capacity range.
- Plugin/skill lint mirrors existing `scripts/lint-skill-*` conventions.

## Rollout / internal build order

Even though it all ships as v1, build in this dependency order so each stage is independently
testable:
1. Plugin scaffold + `.mcp.json`/`plugin.json` + empty MCP service deployed to `soapbox-mcps`.
2. OpEx tools (EIA + URDB) — cleanest, fully redistributable, verifies the MCP plumbing.
3. Electrical service-capacity parametric model + REopt DER tool.
4. Curated CapEx store + ETL (Scout → escalation → regional → DuckDB), then DEER/TRM/REMDB
   enrichment across the measure taxonomy.
5. Costing skill orchestration + Costing Specialist persona.
6. Rewire `decarb-plan`; verify `quality-review` end-to-end.

## Open decisions (for the plan)

- Curated store format: DuckDB file shipped in the image (proposed) vs a small Postgres in
  `soapbox-mcps`. Proposed: DuckDB (simple, fast, deterministic, no extra service).
- MCP server language/stack: match existing `soapbox-mcps` services (confirm at plan time).
- Regional-factor granularity: Census division vs state vs metro (proposed: Census division for
  v1, refine later).
