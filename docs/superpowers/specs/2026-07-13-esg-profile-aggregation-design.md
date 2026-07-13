# ESG Profile Automation — Fund + Investment Aggregation (Madison / Katie) — Design

**Date:** 2026-07-13
**Status:** Design (brainstorming approved; pending spec review → writing-plans)
**Origin:** Katie Cappola (VP ESG, Madison International Realty) — "profile automation" email + attachments (template v3, Azora structured extract, engagement notes).
**Builds on:** the existing `esg-profile` skill, `templates/esg-profile/*`, the RSRA scripted-replay demo pipeline, the verifier agent, the shared hindsight `soapbox` memory bank.

## Goal & business purpose

Reproduce, as an automated backend, the aggregation Madison's ESG team does by hand: collate disparate ESG / climate / building-performance / investment data and transform it into an **ESG Profile at two levels — fund overview and per-sponsor investment profile** (per template v3). Business purpose (Katie's words): move from raw GRESB-style data collection to decision-useful, investment-level insight for asset management — a context-setting and monitoring tool for risk monitoring, budget planning, and asset-management decisions.

**Demo framing:** this is the ESG workflow of the IMN scripted-replay demo. The deliverable is a live, recorded golden run that visibly calls the connectors, reconciles messy inputs, and renders the fund + sponsor profile — then is frozen as the demo's `esg` replay fixture.

## Current state (this is an enhancement, not greenfield)

The `esg-profile` skill is already substantially built and already ingests Katie's Azora data:
- `skills/esg-profile/` — `SKILL.md`, `state-schema.json`, `registry.json`, `connectors/`, `reference/`, `demo/`, `madison/`.
- `templates/esg-profile/schema.json` — already has top-level `meta`, `sponsor`, **`fund_overview`** (`stats`, `sponsor_metrics[]`, `ranking[]`, `underperformers[]`).
- `skills/esg-profile/demo/` + `madison/` already contain the Azora `extract.xlsx`, scrubbed `notes_scrubbed.docx`, `materiality.json`, `bps_cache.json`.
- Existing connectors: `energy-star` (ESPM), `greenstreet` (built), `crrem`, `bps`/fines-&-regs, `physrisk`.

**Empirically-confirmed gap:** the current run (artifact `46326f22`, source of the frozen `esg.json`) produces rich `sponsor` + `meta` but leaves **`fund_overview` empty**. Populating it is the core of this work.

## The data model (what the aggregation reconciles)

- **Grain:** the scorecard is **per sponsor, per reporting year** (Azora/Nestar: 53.66%→58.57%→81.73%→84.96%→90.45% across 2021–2025), with four GRESB pillars (Policy & Strategy, Governance & Resourcing, Portfolio Management, Monitoring & Reporting).
- **Fund context:** the same sponsor sits across **Fund VI and Fund VII**; what varies by fund is the **benchmark** (`benchmark_fund_avg` vs `benchmark_mir_avg`) and the **investment/governance** layer.
- **Deliberately messy:** the extract flags `DISCREPANCY` rows (slide-vs-notes benchmark mismatches, rounding 81.73%↔82%, 61%→60%, 64%→58%) and resolves them ("slide deck used as authoritative source"). **Reconciling conflicting sources is an explicit demonstrated behavior**, not noise to hide.

## Connector architecture

Per the "keep it in the agentic layer; spoof from real API docs where we lack an API" directive. Each of Katie's 9 inputs maps to an agentic plugin/connector; none of this is server-side platform code.

| Input (Katie's 9) | Source connector | Status |
|---|---|---|
| ENERGY STAR | **ESPM** (`energy-star`) | have |
| GreenStreet (transition/sector risk) | **GreenStreet** | have (built) |
| Physical climate risk | **First Street** plugin | **build** — new plugin, spoof-backed to First Street's response shape |
| Building-regulation monitoring (BPS) | **fines & regs** plugin | have |
| Sponsor questionnaire responses | **Microsoft Fabric MCP** | **build** — self-hosted plugin, spoof-backed, shaped to Fabric |
| Fund / asset-class averages | **GRESB** plugin | have |
| Materiality considerations | **shared materiality reference** (see below) | via memory MCP |
| Basic investment info | **Microsoft Fabric MCP** (Madison warehouse) | via Fabric MCP |
| Investment governance rights | Madison deal terms (via Fabric MCP / small fixture) | spoof |
| CRREM stranding | **CRREM** | have |

**Two net-new plugins: First Street and Microsoft Fabric.** Everything else is an existing plugin (ESPM, GreenStreet, GRESB, CRREM, fines & regs) or the memory MCP (materiality).

**First Street MCP (new, spoof-backed):** a physical-climate-risk connector shaped to First Street's response structure (peril-level risk factors/scores). Spoof-backed for the demo sponsor; distinct from our generic `physrisk` because Katie's workflow names First Street specifically as the physical-risk source.

**Microsoft Fabric MCP (new, self-hosted):** deploy our own Fabric MCP in the `soapbox-mcps` Railway project (`fabric.mcp.soapbox.build`). Microsoft ships official Fabric MCP servers we can build on — the open-source **local Fabric MCP** and **`microsoft/fabric-rti-mcp`** are self-hostable, a **Fabric Data Agent** can be exposed as an MCP from a Fabric workspace, and there is a Microsoft-hosted **Fabric Core MCP** (Entra OAuth) for zero-install. Our plugin serves the demo sponsor's **questionnaire responses + investment master data + governance rights** from a fixture, shaped exactly to Fabric's responses; in production the same plugin swaps to the real Core MCP / Data Agent via an Entra service principal. Follows the two-package plugin pattern (MCP server + registration).

**Spoofing standard:** for GRESB, First Street, and Fabric, research the real API's request/response structure and emit **realistic, correctly-shaped** spoofed outputs backed by example files — so the connector calls look and behave like the real thing during the recorded run.

## Materiality (no separate skill; shared reference + verifier gate)

Materiality is a judgment/knowledge layer, split into two roles, both in the agentic layer:
- **Knowledge:** a **shared materiality reference** (SASB/ISSB real-estate materiality map, keyed by asset class + market) stored in the **shared hindsight `soapbox` memory bank**, reached at runtime via the **memory MCP**. Single source of truth, evolvable without redeploy. NOT a static file duplicated per plugin (skill bundles freeze at install → drift), NOT server-side.
- **Enforcement:** a **materiality-coverage gate added to the verifier agent** — for the investment's asset class + market, the profile must address the High-materiality topics and flag material regressions; unaddressed High topic or unflagged material regression → finding. This reuses the verifier's existing evolving-expertise gate pattern and gives a consistent cross-workflow materiality lens (RSRA/decarb/portfolio) without a new skill.
- The esg-profile skill **generates** material considerations from the shared reference; the verifier **enforces** coverage against the same reference → no drift.
- **Demo note:** for the scripted replay the materiality content is baked into the recorded run, so there is no live-recall dependency on stage; the live-recall path matters for real production use.

## Output (template v3)

Two rendered levels (template already schema-specced):
- **Fund overview** — `stats` (asset classes, locations, total sq ft, standing/dev, response rate, YoY performance, avg CRREM stranding year, fine exposure), `sponsor_metrics[]` (multi-sponsor comparison table), `ranking[]` (rank, sponsor, score, YoY, vs-MIEPPI, vs-MIR), `underperformers[]` (sponsor, identified risk, mitigation).
- **Sponsor profile** — investment overview, risk profile (transition: GreenStreet sector rating, CRREM stranding year, market regulation, fine exposure; physical: First Street impact), Completed/In-Progress/Planned initiatives with budget, ESG-governance approval rights.
- Glossary + endnotes (methodology) are static template content.

**The core build:** populate `fund_overview`. Katie's data is single-sponsor (Azora), so the fund view requires **spoofed peer sponsors** (Sponsor A/B/D/E + MIR benchmark) to make the multi-sponsor comparison + ranking real. This spoofed peer set is where the "aggregation" story visibly lives.

## Anonymization

Sponsor identity must be anonymized before anything is shared (Katie's explicit constraint; "Azora"/"Nestar" are real). Reuse the demo scrub gate + pseudonym map pattern. Every frozen artifact passes `scrub-check.py`.

## Demo integration (run → record → freeze)

- **Capture in a NON-demo org.** The deployed scripted-replay now intercepts every Demo-org run of a classified prompt, so a fresh Demo-org ESG run would replay the *stale* `esg.json`, not run live. Capture the new golden run in a non-demo org (or against the source asset directly), exactly the path used for RSRA.
- **Verify** the live run produces a full template-v3 output (populated `fund_overview` + sponsor profile) and passes the verifier (incl. the new materiality gate) + scrub.
- **Freeze** via `build-fixture-from-run.mjs` → replace the current `esg.json` (which only has `meta`+`sponsor`) at `soapbox-platform/apps/api/src/services/demo-fixtures/esg.json`. The build already copies fixtures into `dist` (fixed 2026-07-13).
- Result: the demo's ESG workflow replays the full fund + sponsor aggregation.

## Out of scope / non-goals

- Production/live data integrations for the two new plugins — the **First Street** and **Fabric** MCPs are spoof-backed for the demo sponsor (real First Street / Fabric wiring is a later swap, not this work).
- A standalone materiality skill (rejected — reference + verifier gate instead).
- Any server-side platform-core code for materiality or connectors.
- Multi-fund automation beyond what template v3 shows (Fund VI/VII benchmark context is represented; not a general multi-fund engine).

## Success criteria

- One live (non-demo-org) run visibly calls the connector set, reconciles the discrepant inputs, and renders **both** a populated fund overview (with spoofed peers + ranking) and the Azora sponsor profile, matching template v3.
- The verifier passes, including a new materiality-coverage gate; output is scrub-clean and anonymized.
- The run is frozen as the demo `esg.json` fixture and replays in the scripted-replay demo.

## Open items to resolve in the plan

- Exact Fabric MCP surface (self-host approach — open-source local MCP vs Data Agent vs wrapper; which tools; fixture shape for questionnaire + investment master + governance rights; `soapbox-mcps` deploy + `fabric.mcp.soapbox.build`).
- First Street MCP surface (tools + spoofed peril/risk-factor response shape).
- The spoofed peer-sponsor dataset for `fund_overview` (how many peers, their metrics, the MIR benchmark math).
- Where the materiality reference entry is created in the `soapbox` bank and its key schema (asset class × market → considerations).
- The verifier materiality-gate check definition + how it's added to the verifier's checklist/expertise.
- Which org/asset hosts the golden run capture.
