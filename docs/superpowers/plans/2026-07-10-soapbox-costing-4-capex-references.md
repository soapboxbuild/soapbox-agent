# Soapbox Costing — Plan 4: Curated CapEx store + growing reference library

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Give the MCP a curated, citable CapEx layer across a broad HVAC + building-retrofit taxonomy — `get_measure_capex` (low/base/high with cost_breakdown, contingency, escalation stamp, and surfaced `references[]`), `get_references`, `get_regional_factor` — plus the **growing reference library** (register + hindsight `soapbox-costing` bank + `add_reference` ingest) and an ETL scaffold for ongoing source enrichment.

**Architecture:** Ship the curated data **in-repo as JSON** (`data/*.json`) loaded at startup — the proven `cambium-mcp` pattern (deterministic, no extra service, redistribution-safe). CapEx = a curated seed built **from `soapbox-agent/docs/research/2026-07-10-hvac-cost-market-surveys.md`** (the authoritative gathered figures) escalated to current-year dollars and regionalized on read. The reference **register** is `data/references.json`; the **growing memory** is the hindsight `soapbox-costing` bank. Exhaustive DOE Scout / DEER / TRM ingestion is an ETL scaffold + documented iterative enrichment, NOT a v1 blocker.

**Tech Stack:** same MCP (TS ESM). JSON loaded via `readFileSync`/`import`. hindsight via the MCP's HTTP API (see Task 5).

## Global Constraints

- **Seed from the research doc, cite everything.** Every curated CapEx entry and every register reference traces to a row in `docs/research/2026-07-10-hvac-cost-market-surveys.md` (or a clearly-labelled parametric/tuned-base fallback). **No invented figures** — if the doc has no number for a taxonomy cell, mark it `confidence: "low"` / `source: "tuned-base"` and flag it, do not fabricate.
- **Freshness / ≤1-year currency (required):** every CapEx figure carries an escalation stamp `{ base_year, index, index_vintage, escalated_to }` and is escalated to the current year; the escalation index vintage must be < 1 year old. A figure lacking a stamp is non-compliant.
- **Contingency explicit** (`contingency_pct`, not folded into base) and **cost_breakdown** `{material, labour, equipment}` where known; the regional **labour** factor applies to the labour share only.
- **Provenance + confidence on every response**; `references[]` surfaced on `get_measure_capex`.
- All cost seeds are PLACEHOLDER-grade pending Christopher's tuning — label them.
- The taxonomy is broad (HVAC heating/cooling/distribution/ventilation, envelope, lighting, DHW, DER, electrical) per the design; v1 seeds the measures the research doc actually covers and marks the rest `not_seeded`.
- Loading data must not crash the server if a file is malformed — fail the specific tool with a clear error, keep `/health` up.

## Data shapes (authoritative — later tasks depend on these exact keys)

`data/measures.json`:
```json
{
  "current_year": 2026,
  "measures": [
    {
      "measure_id": "commercial-ashp-rtu",
      "measure_kind": "fuel_switch",
      "category": "hvac_heating",
      "unit_basis": "$/ton",
      "archetypes": ["office","multifamily","logistics"],
      "capex": { "low": 1800, "base": 2600, "high": 3800 },
      "cost_breakdown": { "material": 0.55, "labour": 0.4, "equipment": 0.05 },
      "contingency_pct": 0.2,
      "escalation": { "base_year": 2022, "index": "BLS PPI construction", "index_vintage": "2026-06", "escalated_to": 2026 },
      "confidence": "medium",
      "reference_ids": ["eia-equipment-2022","neep-ccashp-2024"],
      "notes": "..."
    }
  ]
}
```
`data/references.json`:
```json
{
  "references": [
    { "id": "eia-equipment-2022", "system_type": "chillers|boilers|ashp|…",
      "citation": "EIA, Updated Buildings Sector Equipment Cost/Performance, 2022",
      "publisher": "EIA", "year": 2022, "reported_range": "$440–$1,390/ton (chillers)",
      "unit_basis": "$/ton", "url": "https://…", "license": "public domain", "confidence": "high" }
  ]
}
```
`data/regional-factors.json`:
```json
{ "basis": "Census division (BLS PPI/OEWS-informed placeholder)",
  "divisions": { "Pacific": { "labour": 1.25, "material": 1.05 }, "national": { "labour": 1.0, "material": 1.0 }, "…": {} } }
```

---

### Task 1: Curated CapEx store + `get_measure_capex` (escalation applied)

**Files:** Create `data/measures.json`, `src/sources/measures.ts` (loader + escalation + `getMeasureCapex`), `src/tools/measure-capex.ts`; modify `src/index.ts`; test `src/sources/measures.test.ts`.

**Interfaces:** `getMeasureCapex({measure_id, region?, size?}): MeasureCapexResult` returning `{ measure_id, unit_basis, capex:{low,base,high}, cost_breakdown, contingency_pct, escalation, source, confidence, reference_ids, region_applied }` with capex **escalated to `current_year`** and (if `region` given) the regional factors applied (labour factor to labour share — full regional application lands in Task 3; Task 1 escalates + returns national). `registerMeasureCapexTools(server)`.

- [ ] Step 1: failing test — loader returns escalated capex for a known seed measure; `low<base<high`; escalation.escalated_to == current_year; unknown measure_id → clear error listing available ids.
- [ ] Step 2: run → RED.
- [ ] Step 3: seed `data/measures.json` with the priority measures from the research doc's "Priority load order" section (ASHP/HP-RTU, chillers, boilers, HPWH, RTU controls, RCx, GSHP, fume-hood VAV, VRF, envelope, LED) — real figures + base years + reference_ids from the doc; escalate base-year→2026 with a BLS-PPI factor (store the factor + vintage in the escalation stamp). Implement `src/sources/measures.ts` (load, validate, escalate, `getMeasureCapex`).
- [ ] Step 4: run → GREEN.
- [ ] Step 5: `src/tools/measure-capex.ts` (zod: `measure_id` string, `region?` string, `size?` number) wrapping `getMeasureCapex`; register; extend index.test tools/list to include `get_measure_capex`.
- [ ] Step 6: full test → PASS.
- [ ] Step 7: commit (`data/measures.json src/sources/measures.ts src/tools/measure-capex.ts src/index.ts src/sources/measures.test.ts src/index.test.ts`), msg `feat: get_measure_capex + curated escalated CapEx store (seed from HVAC survey research)`.

---

### Task 2: Reference register + `get_references` + surface `references[]`

**Files:** Create `data/references.json`, `src/sources/references.ts`, `src/tools/references.ts`; modify `src/sources/measures.ts` (join `reference_ids`→full refs in the capex result), `src/index.ts`; test `src/sources/references.test.ts`.

- [ ] Step 1: failing test — `getReferences({measure_id})` returns the full citation objects for that measure's `reference_ids`; `getReferences({system_type})` filters by system type; `get_measure_capex` result now includes a `references[]` array of resolved citations (not just ids).
- [ ] Step 2: RED.
- [ ] Step 3: build `data/references.json` from the research doc's 12 system-type sections — one entry per cited source (citation, publisher, year, reported_range, unit_basis, url, license, confidence, system_type). Implement `src/sources/references.ts`; join refs into the capex result in `measures.ts`.
- [ ] Step 4: GREEN.
- [ ] Step 5: `src/tools/references.ts` — `get_references` (zod: `measure_id?`, `system_type?`); register; extend tools/list.
- [ ] Step 6: full test → PASS.
- [ ] Step 7: commit, msg `feat: get_references + reference register; surface citations on get_measure_capex`.

---

### Task 3: Regional factors + `get_regional_factor` (labour factor to labour share)

**Files:** Create `data/regional-factors.json`, `src/sources/regional.ts`, `src/tools/regional.ts`; modify `src/sources/measures.ts` (apply region in `getMeasureCapex`), `src/index.ts`; test `src/sources/regional.test.ts`, extend `measures.test.ts`.

- [ ] Step 1: failing test — `regionalize(capex, cost_breakdown, factors)` multiplies the labour share by `factors.labour` and material share by `factors.material` (equipment national); a high-labour division raises the total via labour only; `get_measure_capex({region})` returns the regionalized capex with `region_applied` set. National (no region) = unchanged.
- [ ] Step 2: RED.
- [ ] Step 3: seed `data/regional-factors.json` (Census divisions, labour+material multipliers — BLS-informed placeholders, labelled). Implement `src/sources/regional.ts`; wire into `getMeasureCapex`.
- [ ] Step 4: GREEN.
- [ ] Step 5: `src/tools/regional.ts` — `get_regional_factor` (zod: `region` string); register; extend tools/list.
- [ ] Step 6: full test → PASS.
- [ ] Step 7: commit, msg `feat: get_regional_factor; apply regional labour/material factors to CapEx`.

---

### Task 4: Real `list_measures` from the taxonomy

**Files:** modify `src/index.ts` (replace the v0 `list_measures` stub with one that returns the curated taxonomy: id, category, unit_basis, confidence, coverage), test in `src/index.test.ts`.

- [ ] Step 1: failing test — `list_measures` returns a non-empty `measures[]` with the seeded ids and their categories (not the v0 empty stub).
- [ ] Step 2–4: RED → implement (read from `src/sources/measures.ts`) → GREEN.
- [ ] Step 5: commit, msg `feat: list_measures returns the curated taxonomy`.

---

### Task 5: Growing reference library — hindsight bank + `add_reference` + ETL scaffold

**Files:** Create `src/sources/library.ts` (hindsight client), `src/tools/add-reference.ts`, `scripts/ingest-scout.mjs` (ETL scaffold), `scripts/README.md`; modify `src/index.ts`; test `src/sources/library.test.ts`.

**Interfaces:** `addReference(ref, opts)` → appends to `data/references.json` AND retains to the hindsight `soapbox-costing` bank (tags `costing`,`reference`,`<system_type>`); `recallReferences(query)` → recalls from the bank. Reads `HINDSIGHT_URL` + `HINDSIGHT_TOKEN` (or the shared hindsight MCP HTTP endpoint) from env; if unset, `add_reference` still updates the register file and returns a clear note that the bank sync was skipped (never crash).

- [ ] Step 1: failing test — `addReference` validates a ref, appends it to an in-memory register, and (with a mocked hindsight `fetchImpl`) posts a retain payload with the right tags; missing hindsight env → returns `{registered:true, bank_synced:false, note:"…"}` (no throw).
- [ ] Step 2: RED.
- [ ] Step 3: implement `src/sources/library.ts` (hindsight retain/recall over HTTP, mockable `fetchImpl`); `addReference` writes the register + retains. Create `scripts/ingest-scout.mjs` — a documented scaffold that reads a DOE Scout ECM JSON path, maps `installed_cost`/`cost_units`/`installed_cost_source` → a `measures.json` entry with base-year escalation TODO, and prints proposed entries (dry-run by default; does NOT overwrite curated data without `--write`). `scripts/README.md` documents the enrichment loop (Scout → DEER → TRM) and that the library grows over time.
- [ ] Step 4: GREEN.
- [ ] Step 5: `src/tools/add-reference.ts` — `add_reference` (ops tool; zod for the ref fields); register. Extend tools/list. (This is a build/ops tool; document it as such in the description.)
- [ ] Step 6: full test → PASS.
- [ ] Step 7: commit, msg `feat: growing reference library (add_reference + hindsight soapbox-costing bank) + Scout ETL scaffold`.

---

### Task 6: Deploy + live smoke ⚠️ OUTWARD-FACING

- [ ] Step 1: If the hindsight bank needs env vars (`HINDSIGHT_URL`/`HINDSIGHT_TOKEN`), set them on `costing-mcp` (controller; values from the shared hindsight service — same one the memory/verifier plugins use). If the shared bank is reachable without per-service creds, note that instead.
- [ ] Step 2: `git push` (auto-deploy); wait Online.
- [ ] Step 3: Live smoke: `get_measure_capex {"measure_id":"<a seeded id>","region":"Pacific"}` → escalated + regionalized capex with `references[]` populated and an escalation stamp; `get_references {"system_type":"chillers"}` → citations; `get_regional_factor {"region":"Pacific"}` → labour+material factors; `list_measures` → the taxonomy. Record outputs.
- [ ] Step 4: (If bank env set) verify `add_reference` round-trips to the `soapbox-costing` bank via a hindsight recall; else note deferred.

---

## Self-Review

- **Spec coverage:** implements the design's curated CapEx layer, contingency+labour breakdown, ≤1-yr escalation, regional factors, and the growing citable reference library (register + hindsight bank + add_reference) + ETL scaffold. Exhaustive Scout/DEER/TRM ingestion is explicitly iterative enrichment (the "grows over time" requirement), not a v1 blocker — the scaffold + docs make the loop real.
- **Placeholder scan:** seed figures are cited to the research doc or labelled tuned-base/low-confidence; regional + PPI factors are labelled placeholders. The Scout ETL is a documented dry-run scaffold, not a stub pretending to be complete.
- **Type consistency:** `get_measure_capex` result shape (capex/cost_breakdown/contingency_pct/escalation/references/confidence) matches the design's `measure.cost` extension and is what Plan 5's skill consumes and Plan 6 maps into the canonical contract.
- **No-fabrication guard:** taxonomy cells without a real figure are marked, never invented; loader failures degrade the specific tool, not `/health`.
