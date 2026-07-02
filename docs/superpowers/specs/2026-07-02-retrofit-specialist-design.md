# Soapbox Retrofit Specialist — Design Spec

**Date:** 2026-07-02
**Status:** Approved by Christopher (brainstorm session)
**Pattern precedent:** Data Verification Agent v1.0 (spec 2026-07-02-data-verification-agent-design.md) — this plugin reuses its architecture, security wiring, and memory infrastructure wholesale.
**Pilot:** Cortland Westminster (audit ECMs + PCA capital table on file, open gas-split finding as worked example).

---

## Problem

Retrofit recommendations today come from physics models (Audette), audit ECM
tables, and PCA capital plans — none of which apply asset-management judgment
(hold period, capital events, tenant disruption, contractor reality) or a
consistent value test. Recommendations are prose, not auditable claim-sets, so
they cannot be scrutinized line-by-line or reused by downstream workflows. The
expertise gained on one engagement evaporates.

## What it is

A **worker, not a pipeline**: a multifaceted retrofit-expertise capability that
any workflow calls (decarbonization plan production, RSRA, capex planning,
disposition prep). The calling workflow defines the deliverable; the Specialist
supplies candidate origination, evaluation, screening, and per-asset working
state. Approved decisions:

- **Candidate sources (C):** all of Audette measures, PCA capital tables, audit
  ECMs, PLUS its own origination (RCx/controls, O&M fixes, staging tied to
  equipment end-of-life, utility rate plays) — everything through one screen.
- **Value test (B):** NOI + exit lens. A measure is value-accretive if it lifts
  NOI and defensibly lifts exit value (NOI ÷ cap rate); green premium / brown
  discount priced ONLY with citable evidence. Future-proofing is test 3 on its
  own terms — cited, never silently priced into the gate.
- **Three-test screen:** (1) value-accretive per above; (2) engineering-feasible
  and practical (site conditions, disruption, contractor/permit reality,
  staging vs remaining useful life); (3) future-proofs the asset (BPS
  trajectory, CRREM stranding, investor screens, climate exposure). Labels:
  `recommended` / `defensive` (fails 1, justified by 3 with citations) /
  `screened-out` (with the failing test named) / `needs-data`.
- **Reference materials (C):** curated shared library (client-agnostic
  engineering knowledge — ASHRAE/DOE/PNNL/RMI/ACEEE, cost references, BPS rule
  texts; seeded from public sources, extendable) + live web supplement for
  currency (costs, incentives, code changes). Library-vs-web provenance is a
  required citation field.
- **Architecture (Approach 3, deployed as a plugin):** MCP service for
  everything that must be uniform and enforced + persona prompt injection for
  judgment. Core plugin, auto-installed on every portfolio, asset + portfolio
  scope.

## Architecture

New repo `retrofit-mcp` (clone verifier-mcp's skeleton: TS, express +
StreamableHTTP MCP, bearer auth = MCP_SERVER_SECRET, trusted-header tenancy
behind the connector proxy, vitest). Railway service in soapbox-mcps at
`retrofit.mcp.soapbox.build` (railway service domain until custom-domain cert
issues resolve, per verifier precedent). Catalog row `retrofit` /
`plugin_retrofit`; added to corePlugins in createPortfolio (with the env-gated
seeding + mustUseProxy + reserved-name treatment the verifier got); backfill
for existing portfolios.

### MCP tools (discipline in code)

1. `propose_candidates(asset_id)` — returns (a) the source checklist the
   calling agent must pull (Audette measures, PCA capital table via RAG, audit
   ECMs via RAG) and (b) playbook-driven origination prompts keyed to asset
   attributes (equipment end-of-life, jurisdiction, archetype). Accepts pulled
   source data and normalizes into the candidate schema:
   `{measure_family, name, source: audette|pca|audit|originated, raw_basis}`.
2. `evaluate_measure(asset_id, measure)` — the scrutinized core. Schema-enforced
   evaluation where EVERY economic field carries provenance
   (`engine:<dcf|cashflow-mcp|crrem>` or `source:<doc/citation>`); the tool
   REJECTS evaluations whose economics lack deterministic/cited origin (the
   verifier's financial auto-fail rule, enforced at write time). Fields: cost
   basis, owner-captured savings (LL/TT allocation applied), NOI delta,
   exit-value delta (NOI ÷ cap rate; cap rate source required), green
   premium/brown discount (citation required, else omitted), incentives (with
   eligibility basis), feasibility rubric score (site conditions from PCA,
   tenant disruption class, contractor/permit reality via Shovels, staging vs
   remaining useful life), future-proofing rationale (cited). Returns the
   structured evaluation; does NOT run LLM reasoning server-side — the calling
   agent supplies inputs, the tool validates + computes what is deterministic
   (exit math) + persists.
3. `screen_measures(asset_id, evaluation_ids)` — applies the three tests,
   assigns labels, names the failing test. Pure logic, versioned thresholds.
4. `get_retrofit_playbook(measure_family | phase)` — versioned methodology data
   files (playbooks/*.json, verifier-checklist pattern) for ≥6 families: hvac,
   envelope, dhw, controls-rcx, solar-storage, electrification-staging; plus
   process phases (walk-the-pca, staging, baseline-discipline). Encodes the
   pragmatist doctrine: measured baselines over modeled savings, boring-proven
   over novel, stage with capital events, load-reduction before plant
   replacement, maintainability by on-site staff.
5. `update_measure_state / get_measure_state(asset_id)` — per-asset measure
   register in Files: `Retrofit/measures.jsonl` (source of truth) + rendered
   `measures.md` (client-visible, RAG-indexed via soapbox-api POST
   /internal/index-file). Sanitized rendering (verifier ledger pattern).
   Compounding working state; deliverables stay workflow-owned.
6. `search_reference_library(query)` / `add_reference(doc_meta)` — shared,
   client-agnostic library. Storage: dedicated hindsight bank
   `retrofit-library` for indexed content chunks + a storage prefix for source
   PDFs (implementation may alternatively reuse platform RAG under a reserved
   portfolio-independent scope — pick the simpler; the bank approach needs no
   platform changes). `add_reference` requires an admin flag (env-listed
   principal or MCP-secret-only path); reads open to all tenants. Citations
   carry `provenance: library|web`.

### Persona (judgment in prompt)

`RETROFIT_SPECIALIST_PROMPT` exported from its own module in soapbox-api (verifier
pattern), injected into asset + portfolio agent prompts when the
`plugin_retrofit` connector is enabled: read the PCA before proposing; respect
hold period and capital plan; distrust modeled savings without measured
baselines; name tenant disruption honestly; prefer maintainable measures;
check Shovels for what contractors actually permit in that metro; evaluate
through the MCP tools only; cite everything; record state after evaluation;
retain generalizable lessons via retain_shared_expertise.

### Memory

No new infrastructure. Org banks (client-specific facts) via the memory
plugin; generalizable lessons through the verifier's gated
`retain_shared_expertise` with new domain tags added to its enum:
`measure-performance`, `cost-prior`, `contractor-market`. Reference library as
above (read-mostly third store).

### Scrutiny integration

Evaluations are claim-sets with per-field sources, so the verifier audits
line-items: its `financial` checklist applies verbatim; workflow deliverables
built on the register flow through record_finding / verification_status like
all fiduciary outputs. The register schema exists precisely to make scrutiny
mechanical.

## Failure handling

Loud failures throughout (platform standing rule): schema rejections name the
offending field; hindsight/library outages degrade to stateless evaluation
with an explicit in-result warning; ledger write failures throw. Storage
uploads use text/plain (bucket allowlist, learned from verifier).

## Testing

- Unit: evaluation schema enforcement (economics without provenance rejected),
  screening logic (all four labels + failing-test naming), playbook loading,
  register jsonl↔md round-trip with sanitization, library citation provenance.
- Integration: register write → files row → internal reindex; tenancy
  (asset_id validated against portfolio; cross-tenant register invisible).
- Pilot (Cortland Westminster): pull real audit ECMs + PCA capital items,
  originate at least one non-modeled measure (controls/RCx class), evaluate
  through the DCF engine, screen, confirm register renders in Files and the
  verifier's checklist passes an evaluation and rejects a doctored one
  (LLM-math economics).

## Rollout

v1: repo + 6 playbook families + evaluation/screen/register/library tools +
persona injection + core install/backfill + library seeding (public docs) +
Cortland pilot. Later: OpenStudio/EnergyPlus modeling hooks, portfolio-level
rollup tools, Paperclip worker wrapper.

## Open questions for implementation

1. Library store: hindsight bank `retrofit-library` vs platform RAG reserved
   scope — decide in Task 1 by whichever avoids platform schema changes
   (lean: hindsight bank + storage prefix for source PDFs).
2. Cap-rate source for exit math: asset metadata field vs per-evaluation input
   (lean: per-evaluation input with source, optionally defaulted from asset
   metadata when present).
3. Verifier domain-enum extension (`measure-performance`, `cost-prior`,
   `contractor-market`) ships as a small verifier-mcp change in this project.
4. add_reference authorization: MCP-secret-only endpoint vs admin user list
   (lean: MCP-secret-only; humans add via ops, agents read-only).
