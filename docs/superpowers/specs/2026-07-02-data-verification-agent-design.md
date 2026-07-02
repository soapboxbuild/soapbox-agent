# Data Verification Agent ("Verifier") + Memory Plugin — Design Spec

**Date:** 2026-07-02
**Status:** Approved by Christopher (brainstorm session, Cortland onboarding day)
**Pilot:** Cortland portfolio (helper data explicitly tagged "not client-verified")

---

## Problem

Agent outputs and ingested data carry unverified claims. Helper data arrives tagged
Medium/Low confidence; agent-generated reports can hallucinate numbers; owners carry
fiduciary risk on anything we present as fact. There is no persistent, growing body
of validated knowledge — every session re-learns vendor quirks, jurisdiction gotchas,
and benchmark priors from scratch — and no mechanism guarantees client-identifying
information stays out of any cross-client knowledge.

## Goals

1. Verify data at rest (asset/portfolio data, ingested helper data) and agent
   outputs (reports, analyses) — user decision: both, plus proactive hunting (D).
2. Prevent hallucinations from reaching owners; gate fiduciary deliverables (B).
3. Surface hidden risk AND opportunity (missed incentives, benchmark gaps,
   compliance exposure) proactively.
4. Persistent memory built from validated findings, growing across sessions:
   per-client banks + one shared expertise bank (B), tiered provenance (C),
   zero client-identifying information in the shared bank — enforced in code.
5. Core plugins, auto-installed on every portfolio, tools at asset + portfolio
   scope. Findings recorded in Files; verifier woven into all thread activity.

## Non-goals (v1)

- No Paperclip employee agent (possible later wrapper around the same MCP).
- No new database tables — the ledger lives in Files; memory lives in hindsight.
- No custom-trained verifier models (Haiku-class checks suffice; MiniCheck-style
  models are a later optimization).
- No UI beyond what Files/threads already render.

---

## Research grounding (deep-research run wq125vuqi, 104 agents, all findings 3-0 verified)

- **Palantir AIP**: grounding-first (tenant ontology at inference), deterministic
  registered functions for all computation, human proposal queues for consequential
  actions, citations on every answer. → We ground in per-tenant connectors, route
  math to existing engines, gate exports behind human-resolvable findings, and
  require source citations on every ledger entry.
- **Chain-of-Verification (Meta, ACL 2024)**: decompose into atomic claims; verify
  each **factored** — the verifier must not see the original draft (anchoring).
  ~17%→~70% accuracy improvement on benchmark tasks.
- **Detector ceiling**: best hallucination detectors < 78% balanced accuracy across
  four benchmarks → automated checks are never a sole gate; tiers + human loop
  required.
- **Zep/Graphiti**: facts carry bi-temporal validity windows + provenance.
  **Mem0**: candidate memories reconciled (ADD/UPDATE/DELETE/NOOP) against existing
  ones. → Both patterns adopted in retention.
- **Gap**: no surveyed system combines external-source verification with memory
  writes or documents cross-tenant scrubbing — the anonymization gate is custom
  and must be code-enforced.

---

## Architecture

Two new **core plugins**, auto-installed on every portfolio (added to
`plugin_catalog` + the `createPortfolio` core-plugins list in soapbox-api, plus a
one-time backfill for existing portfolios). Both expose tools at asset AND
portfolio agent scope.

### Plugin 1: `memory` — hindsight MCP, direct

- Connector URL: `https://agent-memory.soapbox.build/mcp` (hindsight 0.5.1,
  already deployed with Railway volume; MCP tools verified: retain, recall,
  reflect, mental models).
- **Bank pinning is server-side**: the connector proxy injects
  `bank_id: org-<org uuid>` on every call — agents cannot choose a bank. This is
  the tenant-isolation guarantee. (Implementation: proxy rewrite in soapbox-api's
  connector proxy, keyed off the portfolio's organization_id; hindsight API key
  stays server-side.)
- Agents get native `retain` / `recall` / `reflect` against their client's bank.
  Hindsight does fact decomposition, 4-strategy recall (semantic/keyword/graph/
  temporal), and entity/timestamp extraction.
- Org-bank facts carry tier + provenance in fact metadata **by convention**
  (single-client blast radius; formal tier state lives in the ledger).
- The shared `soapbox-expertise` bank is NOT reachable through this plugin.

### Plugin 2: `verifier` — governance MCP (new repo `verifier-mcp`, deploys to soapbox-mcps as `verifier.mcp.soapbox.build`)

Owns exactly what must be code-enforced:

**Methodology tools**
- `get_verification_checklist(data_type)` → domain rubric + claims-to-verify in
  **factored** form (no draft reasoning attached). Rubrics v1:
  - energy figures → BPD plausibility bands + audit/ESPM cross-check
  - equipment install years → Shovels permits
  - address/GFA/floors → Overture/ESPM/audit agreement
  - regulatory/compliance claims → BPS rules (bps-compliance skill data)
  - financial figures → must originate from deterministic engines (DCF engine,
    cashflow MCP, CRREM MCP). **Any LLM-computed number = automatic fail.**
  - incentives/opportunity claims → primary-source citation required
- Checklists are versioned data files in the repo — updating methodology is a
  data change, not a code change.

**Ledger tools** (findings live in Files, per user decision)
- `record_finding(scope, finding)` → appends to `Verification/findings.jsonl`
  (structured: id, ts, claim, verdict, severity, evidence[], sources[], status
  open|confirmed|dismissed) and regenerates `Verification/findings.md`
  (human-readable) on the asset or portfolio via the files API. Files are
  therefore client-visible AND RAG-indexed automatically.
- `list_findings(scope, status?)`, `resolve_finding(id, confirm|dismiss, note)`.
  Resolution is the human validation signal: confirm upgrades related memory to
  `validated`; dismiss records negative knowledge (`refuted`).
- `verification_status(scope)` → {pass|fail, open high-severity count, unverified
  critical claims} — consumed by the report gate.

**Shared-expertise tools** (the ONLY path to the shared bank)
- `retain_shared_expertise(fact, evidence[])` — code-enforced gates, in order:
  1. **Tier gate**: requires ≥2 independent sources in evidence, or a
     confirmed-finding reference. Otherwise rejected (org-bank it instead).
  2. **Anonymization gate**: reject or strip client names, org names, asset
     names, street addresses, coordinates, uids/ids, client financial figures,
     and any string matching the platform's org/asset registries (fetched
     server-side). Rejection is loud (error with reason), never silent.
  3. **Reconciliation** (Mem0 pattern): recall similar facts from the shared
     bank; ADD / UPDATE (supersede with validity window) / NOOP; contradictions
     demote the older fact.
  Then retains into `soapbox-expertise` with tier, domain tag (vendor-quirk |
  jurisdiction | benchmark-prior | methodology | source-reliability), validity
  window, and de-identified provenance ("an AEI audit, 2023, CO multifamily").
- `recall_expertise(query, tiers?)` — read-only proxy over the shared bank;
  always returns tier + provenance; defaults to validated-only when the caller
  declares a fiduciary context.

### Platform integration (soapbox-api)

1. **Catalog + core install**: `memory` and `verifier` rows in `plugin_catalog`;
   both appended to the `createPortfolio` core-plugins list; backfill script for
   existing portfolios.
2. **Prompt injection**: verification system-prompt block injected into asset AND
   portfolio agent configs (same mechanism as `AUDETTE_DEGRADED_PROMPT`):
   recall-before-assert, checklist use on data claims, retain-after-verify,
   record findings as they arise, never present `provisional` facts as settled.
3. **Proactive loops** (existing `loops` infra): per portfolio, (a) event loop on
   `file.uploaded` — verify new documents against asset data; (b) weekly cron —
   re-verify `provisional` facts, hunt risk/opportunity, refresh the ledger.
   High-severity risk findings additionally notify via the portfolio's
   `notify_email` (Resend).
4. **Report gate** (fiduciary outputs only): RSRA/report export paths call
   `verification_status` before render/export; block on open high-severity
   findings or unverified critical claims; explicit human override allowed and
   recorded in the ledger (Palantir proposal-queue pattern). Chat remains
   advisory — no gating on ordinary turns.

---

## Data flow (verify one claim, end to end)

1. Agent (thread or loop) has a claim: "DHW heater installed 2014."
2. `get_verification_checklist("equipment")` → factored claim + rubric: check
   Shovels permits, audit text, equipment survey.
3. Agent runs its own tools (Shovels, RAG over audits) — grounding uses the
   tenant's existing connectors.
4. Two sources agree → `record_finding` (verdict: verified, sources) →
   `retain` (org bank, tier validated in metadata). If it generalizes
   ("[vendor] audits state install years matching permit dates ±1yr in CO") →
   `retain_shared_expertise`, which strips identity and gates tier.
5. Sources conflict → finding severity set, status open; surfaces in thread +
   ledger; human `resolve_finding` settles it and updates memory.

## Failure handling

- Hindsight down → verification proceeds stateless; retention calls fail loudly
  in-thread ([[feedback-never-fail-silently]]); loops retry next run.
- Anonymization gate rejection → error with the offending category named; agent
  retains to org bank instead.
- Gate endpoint unavailable → report export fails CLOSED for fiduciary outputs
  (with override), never silently open.

## Testing

- **Unit (verifier-mcp)**: anonymization gate vs adversarial fixtures (addresses
  in prose, uids in URLs, client names possessive-cased); tier gate; reconciliation
  supersede/demote logic; ledger jsonl↔md round-trip.
- **Integration**: retain→recall round-trip on a scratch hindsight bank; bank
  pinning (attempt to address another org's bank must fail); files API ledger
  write on a test asset; gate pass/fail/override on a fixture report.
- **E2E pilot**: Cortland — run the verification sweep over Batch 1 helper data
  (equipment years vs Shovels permits, energy figures vs BPD bands, gas splits
  flagged Medium), confirm ledger files render in the app, confirm at least one
  generalizable fact lands in the shared bank with zero identifying strings.

## Rollout

- **v1.0**: memory plugin (catalog + bank-pinned proxy), verifier MCP (checklists,
  ledger, shared-expertise tools), prompt injection, core-install + backfill.
- **v1.1**: proactive loops + notifications.
- **v1.2**: report gate on RSRA/export paths.
Each stage independently useful; pilot on Cortland before backfilling all orgs.

## Open questions for implementation

1. Hindsight bank auto-creation: create `org-<uuid>` bank at portfolio creation
   or lazily on first retain? (Lean: lazily, creation is idempotent.)
2. Connector-proxy bank pinning: confirm the proxy can rewrite JSON-RPC params
   for hindsight's tool shapes (it already rewrites for Audette refresh).
3. `soapbox-expertise` seeding: import the standing hindsight `soapbox` bank
   habit facts, or start clean? (Lean: start clean; that bank mixes ops notes.)
4. Registry-based scrub list: refresh cadence for org/asset name lists used by
   the anonymization gate (lean: cached 1h server-side).
