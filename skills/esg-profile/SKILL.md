---
name: esg-profile
description: >
  Produce a sponsor-level ESG Profile (with fund-level rollup) for quarterly asset-management
  engagement — collates ESG questionnaire scorecards, energy/EPC, CRREM stranding, physical
  climate risk, regulatory exposure, peer benchmarks, materiality, and governance rights into
  asset-manager-style Sponsor Profile + Fund Overview deliverables. Data sources are swappable
  (live MCP or static extract) via a connector registry. Triggers on: "ESG profile",
  "sponsor ESG profile", "ESG asset management dashboard", "ESG scorecard profile",
  "quarterly ESG engagement", "fund ESG overview".
version: 1.0.0
---

# ESG Profile

You are producing a **quarterly ESG monitoring deliverable** — a Sponsor ESG Profile (and,
when the run is fund-scoped, a Fund ESG Overview rollup over its sponsors). This is NOT a
decarbonization engagement (`decarb-plan`) and NOT an acquisition screen (`rsra`) — it is the
**asset-management / Q4 budget-season** product: it takes data a firm already collected
post-GRESB and turns it into a decision-useful, benchmarked, gated report. You orchestrate
existing capabilities only — a connector registry that resolves nine input sources plus CRREM,
the Verifier plugin (`verifier__*`, findings ledger + fail-closed render gate), and the
`esg-profile` report template via `fill_report`.

**Positioning vs. siblings:** `rsra` = pre-acquisition screening from an OM. `decarb-plan` =
full multi-week retrofit engagement with two human gates. `esg-profile` = recurring quarterly
monitoring + reporting, deterministic and demo-safe (no interactive human gate mid-run). Do not
route a full decarbonization engagement here, and do not route a quarterly ESG scorecard request
to `decarb-plan`.

---

## Ground rules — apply in every phase

1. **No LLM arithmetic.** Every reported number — pillar scores, the scorecard total, CRREM
   stranding year, fine exposure, fund-level averages and rankings — comes from an engine, a
   connector-resolved source value, or a cited extract. CRREM stranding comes from the `crrem`
   MCP `get_pathway` call, never a hand-typed or eyeballed figure. BPS/regulatory fine exposure
   comes from `run_compliance_analysis` or the cached compliance connector, never LLM estimation.
   Fund-level rollup stats (averages, rankings, underperformer selection) are computed by engine
   or deterministic aggregation code, never composed by you in prose. If a required engine or
   tool is unreachable, say so and stop that field — never approximate a number to fill a slot.

2. **Provenance on every value.** Every datum in `state.collected` and every field that reaches
   the rendered report carries a `ProvenancedValue` — `{value, provenance: {source_id, mode,
   origin, period, retrieved_at}, status, notes}`. `mode` is one of `live | static | estimate` and
   must propagate honestly into the artifact: a static extract value is labeled as such, never
   presented as if it were a live pull. This is the concrete form of the standing
   never-fail-silently rule — a missing or degraded source is surfaced, never silently dropped
   or backfilled with an invented number.

3. **Anonymization is mandatory — and NOT pre-done in the source files.** `config.anonymize`
   defaults `true` and is enforced at every phase boundary: the real sponsor name, contacts, and
   identifying locations never surface in `state`, the rendered artifact, or any export. **Do not
   trust the source extract's own "anonymized" label.** The asset manager's own scrubbed-labeled
   files can still leak the real sponsor identity — the source extract/notes may still contain
   the real sponsor name, personnel names, contact emails, consultant names, city names, and
   country. Scrub ALL such identifiers before any value from the extract enters
   `state.collected` or the report; the demo denylist of previously-observed leak tokens lives in
   the untracked `skills/esg-profile/demo/.scrub-denylist.json` (gitignored — it is regenerated
   locally, never committed, because it necessarily contains real identifiers). Substitute the
   run's pseudonym (`config.sponsor`, e.g. "Sponsor Sierra") for any real entity name and a
   generic region label ("Southern Europe", not the named city) for any place name. Treat a
   fresh, never-before-seen extract the same way — assume it is NOT pre-scrubbed until you have
   personally verified it, because the anonymize flag governs OUR obligation, not a property of
   the input file.

4. **The render gate is HARD, fail-closed, and sponsor-scoped.** No report render without
   verification passing for THIS sponsor, or a documented override
   `{finding_id, override_reason, approved_by}` in `state.overrides` for every open high-severity
   finding **on this sponsor**. Call `verifier__list_findings` with the sponsor key as the scoping
   id — never a bare, unscoped call, which would surface (and could wrongly block on) another
   sponsor's or another fund's findings. A sponsor-scoped gate that is accidentally
   portfolio-wide is a correctness bug, not a stricter check — do not "fix" a stuck run by
   widening the query; fix the scoping id instead.

5. **Analytics Standards apply to every displayed number.** Energy intensity in **kWh/m²**
   (never kBTU/sq ft — the asset manager's own extract mixes units across years, which is exactly why the
   `energy` connector normalizes on ingest). Absolute energy scaled to magnitude (kWh → MWh at
   ≥1,000, GWh at ≥1,000,000). Carbon in a single normalized unit (kgCO₂e/m² or tCO₂e — never mix
   lb and kg CO₂ across years, another flagged discrepancy in the source notes). Max 2
   significant figures displayed. Peer comparison uses **Fund avg / Asset-Class avg / MIR avg /
   MIEPPI** — **never national median** and never an unfiltered peer set. These are the same
   standing Reporting Standards used across every Soapbox deliverable; this skill does not get an
   exception.

6. **Never fail silently.** A connector outage, an unreachable engine, or a gate block is
   surfaced to the user with the standing reconnect/blocker message — never worked around, never
   quietly degraded to a stale or estimated value presented as current.

---

## State ledger

Durable state lives at `projects/<fund>/<sponsor>/esg-profile.json`, conforming to
`skills/esg-profile/state-schema.json` — `phase` is one of `kickoff | collect | reconcile |
verify | render | export | done`. Every phase below is idempotent against the ledger: on resume,
validate the file against the schema, resume at the recorded `phase`, and never redo a completed
phase. If the file is missing, this is a new run — start at kickoff.

---

## Phase: kickoff

1. Gather the run scope from the user (or from an existing config/comment if this is a repeat
   run for the same fund): `scope` (`sponsor` or `fund`), `fund`, `sponsor` (required when
   `scope: sponsor`; omit — or supply the full sponsor list — when `scope: fund`),
   `reporting_year`, and `anonymize` (default `true`; only set `false` with explicit, informed
   user confirmation that this specific run is for internal, non-anonymized use).
2. Write the initial state file per `state-schema.json`: `phase: "kickoff"`, and the `config`
   block (`scope`, `fund`, `sponsor`, `reporting_year`, `anonymize`, `connectors`).
3. **Load connector bindings from the registry, then apply overrides.** Read
   `skills/esg-profile/connectors/registry.json` — it lists every known `source_id`
   (`energy`, `green_street`, `physical_risk`, `bps`, `questionnaire`, `peer_benchmark`,
   `materiality`, `investment_info`, `governance`, `crrem`, `fund_peers`), the schema of what `value` must
   contain (`produces`), the `default_live_adapter`, and whether it is a `gap_filler` (a source
   the asset manager's own process currently leaves blank: `green_street`, `physical_risk`, `crrem`). For each
   `source_id`, default `config.connectors[source_id]` to that entry's `default_live_adapter`
   shape, then apply any run-specific override the user or a prior kickoff config supplied (e.g.
   pointing `energy` at a static EU extract instead of the ESPM default because the demo sponsor
   is Spain-based and ESPM is US-only). Persist the resolved binding set into `state.config.connectors`.
   `fund_peers` is only resolved when `config.scope: "fund"` — skip it entirely on a sponsor-scoped
   run.
4. Set `phase: "collect"` and save.

---

## Phase: collect

This is the visible tool-streaming phase — for every `source_id` in `state.config.connectors`,
resolve it and record the result. Do not resolve sources silently in one giant batch and then
report a summary; stream each resolution as it completes (this is also the demo choreography —
see below).

For each `source_id`, resolve the binding by `kind`:

- **`kind: mcp`** → call the named tool (e.g. `physrisk get_hazard_exposure`, `crrem
  get_pathway`, `citizen-energy get_benchmarking`) with the sponsor's actual attributes
  (location, asset class, property type, region). Set `provenance.mode: "live"`,
  `provenance.origin` = the tool name.
- **`kind: file`** → read the bound `path` (and `sheet` where the source is a spreadsheet tab —
  most of the asset manager's static fields live on sheet `30_input_qualitative`). Extract the fields the
  registry's `produces` contract names for that `source_id`. Set `provenance.mode: "static"`,
  `provenance.origin` = the file path (+ sheet).
- **`kind: manual`** → use the literal value from config. Set `provenance.mode: "estimate"`
  unless the config explicitly marks it as a confirmed manual entry, in which case still record
  it as `static` with `origin: "manual"`.

Record every result into `state.collected[source_id]` as `{value, status, notes, provenance}`.
A source that errors or returns nothing is `status: "missing"` or `status: "error"` — never
silently omitted from state, and never backfilled with a guessed value.

**Call the three gap-filler connectors explicitly and visibly** — `crrem`, `physical_risk`, and
`green_street` are exactly the fields the asset manager's own process today ships as "not provided" or
"analysis underway." Resolving them live is the whole point of this skill's value proposition,
so surface each one as its own streamed line (e.g. "→ crrem get_pathway... stranding year 2034"),
not folded silently into a batch.

**The connector swap rule: to go live, change the binding in `registry.json` (or the run's
`config.connectors` override); never edit this skill.** If `green_street` moves from static to a
live API tomorrow, the fix is flipping its adapter — `{"kind":"mcp","tool":"green-street
get_metrics"}` — in the registry or config, not touching a line of this workflow. The workflow
only ever calls `resolve(source_id)`; it does not know or care whether the value came from an API
or a file, and it must stay that way.

Set `phase: "reconcile"` and save.

---

## Phase: reconcile

1. **Normalize units.** Energy intensity to **kWh/m²**; absolute energy scaled to magnitude;
   carbon to a single normalized unit (kgCO₂e/m² or tCO₂e). The source extract mixes kBTU/sq ft
   and lb-vs-kg CO₂ across reporting years — this normalization is not optional cleanup, it is a
   required reconciliation step every time, because a chart or table that silently plots
   mismatched units across years is wrong on its face.

2. **Apply source-precedence reconciliation to every conflicting input.** Where two sources
   disagree on a field (the extract's own `notes_conflicts` / DISCREPANCY entries, or a static
   value that disagrees with a live pull), apply the precedence hierarchy: **official
   scorecard/measured value > authoritative slide (e.g. an LPAC deck) > extract > estimate.**
   This hierarchy produces a *suggested* resolution only — **every conflict becomes a
   `verifier__record_finding`** (kind `data-quality`, verdict `conflict`, with the candidate
   values, their sources, and a `suggested_resolution` field naming which hierarchy rule fired).
   **Never auto-resolve a conflict by silently picking the higher-precedence value and moving
   on** — the finding is the durable record, and it surfaces in the report's data-quality
   section even though (per the batch-adapted, non-interactive discipline below) this run does
   not stop to human-adjudicate it mid-run.

3. **Run regression detection across `scorecard.trend` and initiatives.** Regression is a
   first-class output, not an afterthought: compare each year's pillar scores and initiative
   status against the prior year(s) in `scorecard.trend`. Flag as a regression any item that was
   present, in-progress, or scored better in a prior period and is now absent, flat, or worse —
   the concrete examples from the source data are Net Zero commitment (still "in development"
   with no formal policy across multiple years), green lease language (a multi-year gap with no
   progress), and embodied-carbon tracking. Write each regression into `state` (feeding
   `sponsor.regressions[]` and the `regression: true` markers on the affected
   `initiatives.planned[]` entries) so the rendered report can flag them with the ⚠️ regression
   marker per the template. A sponsor whose scorecard total is trending up while a named
   initiative quietly backslides is exactly the failure mode this check exists to catch — do not
   let an improving total mask a real regression.

4. Assemble the reconciled profile data object conforming to `templates/esg-profile/schema.json`
   (see the data-mapping table below for the full field mapping).

Set `phase: "verify"` and save.

---

## Phase: verify

Run the batch-adapted `verifier__*` pass — the same discipline `portfolio-analysis` applies at
screening scale, not the fully human-gated `decarb-plan` treatment. For this sponsor (or, on a
fund run, for each sponsor in the fund):

1. Confirm every reconciliation-phase finding was actually recorded (`verifier__record_finding`
   was called for each conflict, not merely noted in prose).
2. Run any additional sanity checks the verifier's data-type checklists cover for the sources in
   play (energy unit sanity, scorecard total = sum of weighted pillars, CRREM stranding year
   plausible for the asset's property type/region).
3. Log all findings to `state.findings` — this phase's job is to make the findings ledger
   complete and durable for the render gate to check. **Do not human-gate mid-run.** Unlike
   `decarb-plan`'s Gate 1/Gate 2, this skill does not stop and wait for a person to adjudicate
   each conflict before proceeding — findings are logged with their `suggested_resolution` and
   carried forward; a human can review and override at render time if a high-severity finding
   remains open, but the workflow itself keeps moving.

Set `phase: "render"` and save.

---

## Phase: render

**HARD sponsor-scoped gate, fail-closed.** Before dispatching any render:

1. Call `verifier__list_findings({asset_id: <sponsor key>})` — the sponsor key, never a bare
   unscoped call and never the fund key when the run is sponsor-scoped. On a fund-scoped run,
   check each sponsor's findings individually with that sponsor's own key before rolling up.
2. If there are open high-severity findings on this sponsor with no matching entry in
   `state.overrides` (each override requires `{finding_id, override_reason, approved_by}`) —
   **block. No render.** Do not dispatch the renderer, do not produce a partial artifact, do not
   summarize around it. Surface exactly which findings are blocking and what an override would
   require.
3. If there are no open high-severity findings on this sponsor (the common demo-safe case — the
   deterministic connectors and gap-fillers rarely produce a high-severity conflict on a clean
   run), or every open high-severity finding has a documented override, the gate passes.
4. On pass, call `fill_report` with `report_type: 'esg-profile'` and a data object conforming to
   `templates/esg-profile/schema.json` — populate `meta` (fund, reporting_year, anonymized) plus:
   on a **sponsor-scoped** run, `sponsor` only; on a **fund-scoped** run, `sponsor` **and**
   `fund_overview` **both**, in the same `fill_report` call — the fund render is a combined
   fund+investment deliverable, not a replacement for the sponsor deep-dive (see Fund rollup
   below for how `fund_overview` is assembled). Record the returned artifact id in
   `state.artifact_id`.

Set `phase: "export"` and save.

---

## Phase: export

Hand off to the `report-review` workflow for export: **PDF** (Playwright), **PPTX mapped to
the asset manager's Template v3** (their team's actual working format — this is the export they use, not just
the branded HTML), and **XLSX** (openpyxl, for anyone who wants the underlying numbers in a
sheet). The report-review workflow presents the rendered artifact for review before finalizing
exports, per its own contract — this skill does not duplicate that review loop, it dispatches
into it.

Set `phase: "done"` and save once exports are recorded.

---

## Fund rollup

When `config.scope: "fund"`, the deliverable is the **Fund ESG Overview** — an aggregation over
the fund's sponsor-level profiles, not a separately-authored document. Run kickoff → collect →
reconcile → verify per sponsor (each sponsor keeps its own findings and provenance), then
aggregate into `fund_overview`.

**Resolve `fund_peers` before aggregating.** Per the standard connector-binding rule above,
`fund_peers` is bound like any other source: `resolve("fund_peers")` reads whatever
`state.config.connectors.fund_peers` points to and returns `{stats, sponsor_metrics[], ranking[],
underperformers[]}` for the fund's peer sponsors — never open or parse the underlying file/API by
name inline. In production this is the `fund_data get_peer_rollup` API adapter; for the Madison
demo it is bound `{"kind":"file","path":"skills/esg-profile/demo/madison/fund-peers.json"}` (set
this override in `config.connectors.fund_peers` at kickoff — do not hardcode the path in this
workflow). Then:

1. Take the resolved `fund_peers` value as the starting `stats`, `sponsor_metrics[]`, `ranking[]`,
   and `underperformers[]`.
2. Merge in the subject sponsor's own connector-derived row — the `sponsor.scorecard`,
   `sponsor.energy`, and `sponsor.benchmark` values already assembled for this sponsor in the
   `reconcile` phase — into `sponsor_metrics[]` and `ranking[]`. If the bound `fund_peers` source
   already carries a row for this sponsor (the Madison demo fixture does, for convenience), the
   connector-derived row **replaces** it rather than duplicating it, so the rendered figures always
   trace back to this run's own provenance and not a stale peer snapshot.
3. Recompute `ranking[]` order and re-run the `underperformers[]` auto-selection (below) after the
   merge — a subject-sponsor row merged in after the peer file's ranking was computed must not be
   left out of rank order or the below/above-average check.

Aggregate the merged set into `fund_overview`:

- **`stats`** — asset classes, locations, total size, standing/dev counts, scorecard response
  rate, YoY scorecard performance, **avg CRREM stranding year** (weighted appropriately across
  sponsors — never a naive unweighted mean if sponsor sizes differ materially), and aggregate
  fine exposure.
- **`sponsor_metrics`** — the matrix of every sponsor × its headline metrics (green cert %,
  energy rating %, GRESB status, Net Zero policy status, energy data coverage, renewable %),
  with MIEPPI and MIR comparison columns alongside each sponsor's row.
- **`ranking`** — each sponsor's scorecard score, YoY change, and delta **vs MIEPPI** and **vs
  MIR**, plus the fund-average and MIR-average reference rows.
- **`underperformers`** — sponsors scoring below the fund average or the MIR average are
  **auto-selected** into this table (never manually curated), each paired with its identified
  risk and a mitigation measure drawn from the sponsor's own findings/initiatives.

**Aggregation runs through an engine or deterministic aggregation code, never LLM arithmetic.**
Averaging CRREM stranding years, computing YoY deltas, and selecting underperformers by a
threshold comparison are exactly the kind of "it's just averaging" tasks that are tempting to do
in prose — do not. Compute them the same way every other reported number in this skill is
computed: by a tool, not by you doing the arithmetic in your head.

---

## Data mapping — `30_input_qualitative` columns → schema paths

the asset manager's static extract carries most of the qualitative/static connector fields on a single
spreadsheet tab, `30_input_qualitative`. This table is the canonical field map from that sheet
(and the other static/live connector outputs) into `templates/esg-profile/schema.json` paths.
Use it verbatim when writing the `file`-kind adapters' field maps — do not re-derive column
meanings from scratch on each run.

| Source column / field | Connector | Schema path |
|---|---|---|
| `pillar_policy_strategy` | `questionnaire` | `sponsor.scorecard.pillars.policy_strategy` |
| `pillar_governance_resourcing` | `questionnaire` | `sponsor.scorecard.pillars.governance_resourcing` |
| `pillar_portfolio_management` | `questionnaire` | `sponsor.scorecard.pillars.portfolio_management` |
| `pillar_monitoring_reporting` | `questionnaire` | `sponsor.scorecard.pillars.monitoring_reporting` |
| (derived from `pillar_*` — computed, not a column) | `questionnaire` | `sponsor.scorecard.total` |
| `qual_summary` / prior-year totals | `questionnaire` | `sponsor.scorecard.trend[]` |
| `initiatives_completed` | `questionnaire` | `sponsor.initiatives.completed[]` |
| `initiatives_in_progress` | `questionnaire` | `sponsor.initiatives.in_progress[]` |
| `initiatives_planned` | `questionnaire` | `sponsor.initiatives.planned[]` (+ `regression` flag from reconcile) |
| `qual_esg_risks` / `qual_risk_mitigation_actions` | `questionnaire` | feeds `fund_overview.underperformers[].identified_risk` / `.mitigation` on fund rollup |
| `market_regulation` | `bps` | `sponsor.risk_profile.transition.market_regulation` |
| (not a sheet column — from `bps` connector) | `bps` | `sponsor.risk_profile.transition.fine_exposure` |
| `physical_risk_rating` | `physical_risk` | `sponsor.risk_profile.physical.impact` |
| `physical_risk_source` | `physical_risk` | `sponsor.risk_profile.physical.source` |
| (hazards list) | `physical_risk` | `sponsor.risk_profile.physical.hazards[]` |
| `sector_risk_rating` | `green_street` | `sponsor.risk_profile.transition.green_street_rating` |
| `stranding_year` | `crrem` | `sponsor.risk_profile.transition.crrem_stranding_year` |
| `misalignment` | `crrem` | (carried in state; informs `fine_exposure` narrative) |
| `eui_kwh_m2` | `energy` | `sponsor.energy.eui_kwh_m2` |
| `carbon_intensity` | `energy` | `sponsor.energy.carbon_intensity` |
| `renewable_pct` | `energy` | `sponsor.energy.renewable_pct` |
| `energy_rating_pct` | `energy` | `sponsor.energy.energy_rating_pct` |
| `benchmark_fund_avg` / `benchmark_mir_avg` | `peer_benchmark` | `sponsor.benchmark.metrics[]` (`mieppi`/`asset_class`/`mir` columns) and `fund_overview.ranking[].vs_mieppi`/`.vs_mir` |
| `asset_class_avg` / `mieppi_avg` (not sheet columns — from `peer_benchmark` connector) | `peer_benchmark` | `sponsor.benchmark.metrics[]` (`mieppi`/`asset_class`/`mir` columns) and `fund_overview.ranking[].vs_mieppi`/`.vs_mir` |
| `asset_class` / `location` / `size` / `exit_date` / `standing_dev` | `investment_info` | `sponsor.investment_overview.*` |
| `gov_annual_budget` | `governance` | `sponsor.governance_rights.annual_budget` |
| `gov_leasing` | `governance` | `sponsor.governance_rights.leasing` |
| `gov_capex_project_variance` | `governance` | `sponsor.governance_rights.capex_variance` |
| `gov_contractor_engagement` | `governance` | `sponsor.governance_rights.contractor_engagement` |
| `considerations` | `materiality` | (feeds report narrative; no dedicated schema field in v1 — carried via `state.collected.materiality`) |
| every `source_id`'s resolution record | (all) | `sponsor.provenance[]` `{source_id, mode, origin, period}` |

---

## Demo choreography

The primary near-term use of this skill is the **60-second collect-phase tool-streaming beat**
on stage: one instruction kicks off a run against a pre-loaded, anonymized static-data repo
(the asset manager's scrubbed extracts under `skills/esg-profile/demo/`) plus the live connectors already
connected (ESPM/EPC-region-aware `energy` where applicable, `crrem`, `physrisk`). The collect
phase fans out with visibly streaming tool calls, paced so the audience can read each line —
static sources resolve near-instantly, and the three gap-fillers (**`crrem`**, **`physical_risk`**,
**`green_street`**) are called out explicitly as they run, because they are the fields the asset manager's
own process ships today as "not provided" or "analysis underway." Watching them resolve live —
turning a blank into a real stranding year and a real hazard rating — is the demonstration's
entire point: reconcile → verify → the render gate passes cleanly on the demo sponsor → the
branded HTML artifact renders in-band, then the PPTX export to Template v3 is shown as "the same
profile, in the format the asset manager's team actually uses." No live Q&A dependency, no mid-run human gate —
the run is deterministic end to end. If a live gap-filler call runs long (physical-risk lookups
have run to ~45 minutes in other skills at full scope), keep the demo scope to a single sponsor
location so the call stays tight and the beat holds.
