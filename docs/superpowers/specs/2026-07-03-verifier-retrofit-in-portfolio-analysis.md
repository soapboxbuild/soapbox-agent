# Data-Verification & Building-Science Agents — Deep Dive + Portfolio-Analysis Port

_2026-07-03. Companion to the `verifier-mcp` / `retrofit-mcp` designs and the `decarb-plan`
workflow. This document (1) explains what the two agents are and how the decarb-plan skill
wires them, and (2) specifies how they are applied to the `portfolio-analysis` skill._

---

## Part 1 — What the two agents are

Both are **worker-pattern core plugins** (auto-installed on every portfolio, backfilled to all
existing ones). Each is a Railway MCP service cloned from the same auth/tenancy/ledger
skeleton. They are exposed to thread agents two ways at once:

- A **persona prompt** injected into the system prompt of **both asset- and portfolio-scope
  agents** (`agent-config.ts`): `VERIFICATION_PROMPT` and `RETROFIT_SPECIALIST_PROMPT`
  (degraded variants when the tools are unreachable).
- The **tools themselves**, registered as `verifier__*` / `retrofit__*` custom tools and
  self-executed through the runtime's `custom_tool_use` gate.

The portfolio builder (`getOrCreatePortfolioAgentConfig`) injects both prompts and both tool
sets — so a portfolio thread already has every tool the port below needs. The
`portfolio-analysis` skill simply never called any of them; it re-implemented verification and
measure-screening ad-hoc in the LLM.

### 1a. The Data-Verification agent (`verifier-mcp`)

A **findings ledger + reusable verification methodology + shared-expertise gate.** Seven tools:

| Tool | Purpose |
|---|---|
| `get_verification_checklist(data_type)` | Returns a versioned rubric for one of `energy / equipment / physical / regulatory / financial / opportunity`. E.g. energy: sanity-check units before comparing, cross-check ESPM/AEI/BPD bands. financial: every figure originates from a deterministic engine or cited doc. This is the reusable methodology — the same rubric the decarb-plan human uses. |
| `record_finding({asset_id?, claim, verdict, severity, kind, evidence[], sources[]})` | Writes a durable finding to `<scope>/verification/findings.jsonl` (+ RAG-indexed `findings.md`). `verdict ∈ verified/refuted/conflict/unverifiable`; `kind ∈ risk/opportunity/data-quality`. **`asset_id` is optional — omit for a portfolio-level finding.** |
| `list_findings({asset_id?, status?})` | Read the ledger (`open/confirmed/dismissed`). |
| `resolve_finding({asset_id?, id, resolution, note})` | `confirmed`/`dismissed` + rationale. |
| `verification_status({asset_id?})` | Returns `{pass, open_high, open_total}` — the render-gate signal. Per-asset OR portfolio-level. |
| `recall_expertise({query, tiers?, fiduciary?})` | Search the de-identified cross-client `soapbox-expertise` bank. `fiduciary=true` restricts to the validated tier — use it for client deliverables. |
| `retain_shared_expertise({fact, domain, evidence[], confirmed_finding_id?})` | Write a generalizable lesson to the shared bank. Code-enforced: `domain` enum, **≥2 independent sources or a confirmed finding**, and an anonymization gate that refuses client/asset-identifying text. |

Core doctrine: **no number without provenance; two agreeing independent sources ⇒ verified,
one ⇒ provisional, disagreement ⇒ an open finding with both citations; never benchmark against
national medians.**

### 1b. The Building-Science / Retrofit-Specialist agent (`retrofit-mcp`)

A **provenance-enforced measure evaluator + screening engine + measure register + building-science
playbooks.** Eight tools; the load-bearing three:

- `propose_candidates({asset_attributes})` — returns the source checklist and origination prompts
  to build a candidate list (Audette measures, PCA/audit ECMs, equipment-driven, originated).
- `evaluate_measure({asset_id, measure})` — **validates + persists** one measure. Every econ
  field (`cost`, `owner_savings_annual`, `noi_delta_annual`, `cap_rate`) is
  `{value, unit, engine|source}` and is **rejected without engine or source provenance.** It
  then computes `exit_value_delta = noi_delta_annual ÷ cap_rate` server-side
  (`engine: retrofit-mcp/exit-math@1`). `feasibility.score` is an **integer 1–5**;
  `green_premium` needs a source citation; `incentives[]` need program + eligibility basis.
- `screen_measures({asset_id, measure_ids?})` — applies three tests and labels each measure:
  - **needs-data** — missing `exit_value_delta` or empty `feasibility.sources`.
  - **screened-out** — `feasibility.score < 3`, or the value test fails with no future-proofing citation. (`failing_test` names which.)
  - **defensive** — value test fails but `future_proofing.citations` justify keeping it.
  - **recommended** — `feasibility ≥ 3` AND simple payback `≤ 15y` AND `noi_delta > 0`.

Plus `get/update_measure_state` (the register at `<assetId>/retrofit/measures.jsonl`, the
system of record across sessions), `get_retrofit_playbook(key)` (9 versioned playbooks — 6
measure families + 3 process phases: `walk-the-pca`, `staging`, `baseline-discipline` — carrying
boots-on-ground doctrine like combustion-safety-after-air-sealing and A2L refrigerants), and
`search_reference_library / add_reference` (curated ASHRAE/DOE/PNNL/RMI library,
`provenance:'library'`).

---

## Part 2 — How `decarb-plan` wires them (the reference implementation)

`decarb-plan` is the **single-asset, multi-week, human-gated** engagement product. Its use of
the two agents is total:

1. **Ground rules** — "no LLM arithmetic," "hierarchy is suggestion-only, human adjudicates ALL
   conflicts at Gate 1," "the render gate is HARD and fails closed."
2. **P1 evidence** — loads the existing register (`get_measure_state`), open findings
   (`list_findings`), status, and checklist so known data issues carry forward; `recall_expertise`
   for prior lessons; `search_reference_library` FIRST for jurisdiction/incentive claims.
3. **P2 reconciliation** — every disagreeing field becomes a `record_finding` (kind
   `data-quality`, verdict `conflict`) with a hierarchy-derived *suggested* resolution; nothing
   auto-resolves.
4. **GATE 1 (human)** — the user adjudicates each conflict; each gets `resolve_finding`.
5. **P3 measure plan** — `propose_candidates` on adjudicated attributes → Audette physics →
   `evaluate_measure` for every candidate (provenance-enforced) → `screen_measures` → staging via
   `get_retrofit_playbook('staging')`; measures land in the register.
6. **GATE 2 (human)** — roster confirmation; edits applied via `update_measure_state`.
7. **P4 render gate (HARD)** — `verification_status` must pass or carry a documented per-finding
   override, else **no render, fails closed.**
8. **P5** — `retain_shared_expertise` for anonymized lessons.

The defining feature is the **two human gates** and **fail-closed render** — affordable because
it's one asset over weeks.

---

## Part 3 — The port to `portfolio-analysis`

`portfolio-analysis` is the **screening-scale** sibling: N assets (often 30–40) in one batch
run, one interactive gate (parameters). You **cannot** human-adjudicate every conflict on every
asset. So the two agents are applied in a **batch-adapted** form. The adaptations are deliberate
product differences, not a weakening of the discipline — single-asset engagements already route
to `decarb-plan`.

### Decision that shapes everything: who owns the economics

The portfolio DCF engine (`run_dcf` / `run_intervention_irr`) **stays authoritative** for the
report's financial numbers — it carries IRA credits, LL/TT capture, `value_method`
(inclusive/standalone), and utility escalation that the retrofit tool's plain NOI÷cap exit math
does not. The retrofit agent owns **discipline, building science, and the register**, not the
numbers.

Mechanism: feed the **DCF/cashflow engine outputs into `evaluate_measure` as `engine`-provenanced
fields** (`engine: "soapbox-dcf"` / `"cashflow-mcp"`). This is exactly what the `financial.json`
checklist sanctions ("every financial figure must originate from a deterministic engine"), so the
provenance gate passes on real numbers. The register's server-computed `exit_value_delta`
(NOI÷cap) is a **screening proxy** that largely agrees with the report's inclusive value-creation
figure; where a table shows *value creation*, it comes from the DCF engine, not the register.

**Label composition** (stated in the skill so the two screens can't fight):

> A measure is **recommended in the portfolio report** iff `screen_measures` labels it
> `recommended` **AND** its DCF IRR ≥ `irr_hurdle`. Screen-recommended but IRR-missing →
> **below-hurdle**. Screen `defensive` → defensive. Screen `needs-data` → needs-data (never
> reaches the IRR screen). Compliance-required measures are included regardless of IRR, flagged
> mandatory.

### The BPD-only edge case (would otherwise crash the batch)

Assets with no Audette link and no docs run on BPD-benchmark `(est.)` values. `evaluate_measure`
**refuses unprovenanced numbers**, so it would reject every one. Mapping: BPD-only assets →
labelled **`needs-data`**, bypass `evaluate_measure`, stay in the report but are **excluded from
the verified roster and headline aggregates**, clearly marked.

### The four insertion points (surgical — the ~1000 working lines of DCF/IRA/CRREM/XLSX are preserved)

1. **Run start** — a new "Verification & Building-Science Discipline" section stating the batch
   ground rules, plus `recall_expertise(fiduciary=true)` for portfolio-scale prior lessons.
2. **Step 3A Step 5 (reconcile)** — replace the ad-hoc High/Medium/Low confidence ladder with the
   `get_verification_checklist` rubrics; on a material Audette-vs-doc conflict (>25%),
   `record_finding` (kind `data-quality`, verdict `conflict`) instead of "show both and pick."
   Auto-apply the hierarchy suggestion (screening-scale), but **log** every conflict as a finding.
3. **Step 3C (measure economics)** — `propose_candidates` → `evaluate_measure` (DCF-fed,
   provenance-gated) → `screen_measures`; persist via `update_measure_state`; feasibility &
   staging from `get_retrofit_playbook`. The register becomes the shared system-of-record — a
   later `decarb-plan` on any of these assets **inherits** it.
4. **New per-asset render gate + run end** — `verification_status(asset_id)` per asset; assets
   with open high-severity findings are flagged inline and their contribution to headline KPIs is
   **called out** (the batch analog of fail-closed — the whole report is not blocked on one bad
   asset, but the totals never silently absorb unverified data). At the end,
   `retain_shared_expertise` for anonymized portfolio-scale lessons.

### Conventions mirrored from decarb-plan (so an asset touched by both keeps one coherent ledger/register)

- finding `kind: data-quality` for reconciliation conflicts; `verdict: conflict`.
- `asset_id` = the **Soapbox asset UUID** (from `query_portfolio_data`'s `ID:` field) — never the
  Audette property/building uid.
- `feasibility.score` = integer 1–5.
- `recall_expertise(fiduciary=true)` because the portfolio report is a client deliverable.
</content>
