# Per-Skill Pickup Contract (Task 0.3)

How each skill reads staged state today, so Phase 4 can pre-stage exactly the right
store/key/field to make slow phases short-circuit and gates pass honestly. Verified against
`skills/{rsra,decarb-plan,esg-profile}/SKILL.md`, `decarb-plan/state-schema.json`, and live
reads of Supabase project `fplbvanvwvnviczozwhz` (memories/files/artifacts/assets/asset_connectors).
No writes were performed.

---

## RSRA

### 1. OM discovery
Phase 1A, exact order:
1. Files attached to the conversation (in-turn upload).
2. Asset document library via `search_files("offering memorandum")`, `search_files("investment
   summary")`, `search_files("property overview")` — this is the Supabase `files` table (asset
   document library), not a generic web search.
3. If neither: prompt the user to upload.

**Staging lever:** pre-load a `files` row for the demo asset with a name that matches one of
those three search terms (e.g. a doc named `"... Offering Memorandum.pdf"`) so `search_files`
hits on the first call.

### 2. Slow external-call phases — cache hooks

| Phase | Call | Pre-existing cache read BEFORE calling? | Exact hook |
|---|---|---|---|
| 2A Audette (energy/carbon) | `list_buildings` → `get_building_model_details` | **Yes, implicitly** — Audette itself is the "cache": the skill checks `audette_pipeline_state` and uses Audette's stored model instead of a fresh calibration run. No separate memory/file cache layer — the skill always calls the Audette MCP live; there's no "read `memories` key X before calling Audette" step. | N/A — lever is that the asset's `assets.metadata` / Audette building already has a calibrated model (as it does for the Cortland assets), so the *Audette-side* call returns instantly instead of falling through to CBECS. |
| 2C Building Performance Database (BPD) | `get_eui_percentile`, `get_statistics` | **No.** Always called live; no memory/file short-circuit described. | None — no cache hook exists. |
| 4A physrisk (hazard/VaR) | `assess_physical_risk`, `calculate_climate_var` | **No.** Called live every time lat/lon is available; the fabrication gate explicitly forbids reusing a "plausible-looking" cached score from memory instead of a real tool result. | None — no cache hook exists. |
| 7A/7B Incentives (IRA, state/utility rebates) | `brave_web_search` | **No.** Web search every time; no memory/file cache read first. | None — no cache hook exists. |
| 2A fuel-type verification, 2D web research | `brave_web_search` | **No.** | None. |

**Bottom line for RSRA:** there is **no memory-key or file-based cache hook anywhere in the
skill text** for physrisk/BPD/incentives/web-research. The ONLY lever available for a demo
short-circuit on these phases is a per-asset **`[DEMO MODE]` system_prompt directive** instructing
the agent to use pre-staged numeric values instead of calling the live tools (or to treat a
stubbed/fast-responding connector as the live one). The one exception where genuine staged state
helps is **Audette (2A)** — if the demo asset already has a calibrated Audette model (as the
Cortland assets do), Phase 2A's data hierarchy step 1 ("Audette calibrated model — best") resolves
immediately without falling through to slower estimation paths.

### 3. Final render
Confirmed: **`fill_report(template: 'rsra', data)`** (Phase 10) — the skill explicitly prohibits
any hand-written HTML; this is the sole rendering path.

Top-level required fields of `data` (from the Phase 10 pre-flight checklist):
- `property` `{name, address, type, units, year_built, zip}`
- `decarb_plan[]` — ≥1 measure, each with `measure`, `capex_total`, `timing`, `emissions_reduction_pct`
- `decarb_plan_total` `{capex_per_unit, capex_total}`
- `decarb_sensitivity[]` — **REQUIRED, exactly 3 rows**, each `{label, total_spend, spend_per_unit
  (if multifamily), emissions_reduction_pct, noi_impact_annual, value_delta_pct}` — omission makes the
  sensitivity chart/table invisible
- `deal_signal` `{level, narrative}` — `level` ∈ `"Low Risk" | "Moderate Risk — Opportunity" |
  "Moderate Risk — CapEx" | "High Transition Risk"`
- `emissions_profile` `{fuel_profile, utility_structure, baseline_emissions, crrem_pathway,
  regulation}` (+ optional `bpd_chart`)
- `physical_climate_risk` `{hazards[≥3 with risk_2030/risk_2050], insurance_note, climate_var?}`
- `ghg_scoping` `{scopes[Scope 1, 2, 3], offset_note}`
- `certifications_and_debt`, `seller_questions[]`, `sources[]`, `prepared_by`, `prepared_for`,
  `report_date`, `data_quality`, `disposition_mode`

---

## decarb-plan (THE crux)

### 4. Where the engagement `state` object is persisted and read

**Empirically determined — NOT in Supabase `memories`.** Query against the Cortland portfolio
(`8cea3d4f-2387-4f89-beb2-60937dc761e1`) and specifically asset `02848996-666e-41c9-9687-fd70edaf0653`
(Cortland Westminster — a real, far-progressed engagement per file names below) returned:

```sql
select scope, key, left(value,150) from memories where asset_id = '02848996-...'; -- 0 rows
```

The `memories` table is entirely empty for this asset (and for the whole portfolio's asset-id
list). So the engagement `state` (phase/baseline/measures/targets/audette/citations/report) is
**not** written through the `memories`/agent-memory MCP.

**It is also not embedded in the Supabase `files` table content** — `files` only stores
pointers (`name`, `storage_path`, `mime_type`, `size`) into Supabase Storage; there is no
`content` column, so the actual bytes of any registered file (including a would-be
`decarb-plan-state.html` or `decarb-plan.md`) live in Storage, not queryable via SQL. For this
asset the registered files include (confirming SKILL.md's file layout):
- `decarb-plan-state.html`, `measures.md`, `findings.md` (the state/roster companions)
- `2026-07-05 - Helper Files - Decarb Plan.html` (the one growing helper file)
- three `...Decarbonization-Roadmap...html` (rendered report copies)
- source docs: the AEI energy audit PDF, a boundary survey PDF, a PCA PDF

**`assets.metadata` (jsonb)** holds Audette/building-model data (equipment survey, energy
`{units, source, gas_gj_yr, electricity_kwh_yr, ...}`, `audette_building_uids`,
`audette_buildings_rebuilt` note) — this is P2/Audette-model bookkeeping, **not** the decarb-plan
engagement state ledger (no `phase`, `kickoff`, `targets`, `measures.register_ids`, etc. keys
present).

**`artifacts.report_data`** holds the *rendered* report's data object (post-`fill_report`) for
the finished asset — e.g. `{"baseline": {"eui_kwh_m2": 128, ...}, ...}` — this is the OUTPUT of
P5, not the resumable engagement ledger.

**Conclusion:** `projects/<asset-key>/decarb-plan.json` (and its companion `.md`) as described
in the SKILL is a file in the **agent's own session/project working directory** (the sandbox
filesystem the Resume Protocol `cat`s), not a Supabase-backed store at all. It is orthogonal to
the three DB stores investigated. **Staging implication:** Phase 4 seeding for decarb-plan
cannot be done via SQL/memories inserts — it must pre-write the actual
`projects/<asset-key>/decarb-plan.json` file (matching `state-schema.json`) into the demo
agent's working directory/Files registration before the run, with `phase` set past the phase(s)
you want to skip (e.g. `phase: "P4"` with `state.report.verification_status.pass: true` already
recorded, to skip straight to P5 render). The companion `decarb-plan.md` should also be
pre-registered in the asset's Files (matching the `files` table pattern seen above, e.g.
`decarb-plan-state.html`) so the Resume Protocol's `list_files`/`search_files` calls succeed
without triggering a fresh P0 kickoff.

### 5. Render-gate requirements (from SKILL, P4 step 3 + ground rule 3/4)

`fill_report(template:'decarb', data)` passes only when, for **this asset** (`asset_id` always
explicit — never a bare/portfolio-wide call):

- `verifier__verification_status({asset_id})` (or `verifier__list_findings({asset_id})`) returns
  the deployed shape `{pass: boolean, open_high: number, open_total: number}` with **`pass: true`**
  (i.e., zero open-high findings on this asset), **OR**
- every open high-severity finding on this asset has a documented override in
  `state.report.overrides[]`: `{finding_id, override_reason, approved_by}` (schema-required
  fields; `approved_by` is a person, not a self-certifying agent — ground rule 4 explicitly bans
  self-opening-and-confirming a finding in the same turn).

Additional hard pre-render checks the gate enforces (ground rule 5, non-exhaustive but
demo-relevant): non-increasing emissions trajectory, headline % reconciles to tonnage math,
CRREM curve must come from a fresh `crrem__get_pathway` call every render (never rebuilt from
stored state), fine-consistency validator (`validateFineConsistency`) if any BPS fine is claimed.
**Staging these pre-conditions matters as much as the finding-status row** — a stubbed
"verification passes" state with an internally-inconsistent payload will still fail the render
gate's payload-level checks.

### 6. `asset_connectors` row the render gate expects

Confirmed empirically (`select distinct plugin_id from asset_connectors` → `audette, costing,
retrofit, verifier, memory, null`):

- **`plugin_id = 'verifier'`** (NOT `'plugin_verifier'` — that name appears only in prior
  memory-note shorthand/conventions, not the actual column value).
- Every existing verifier row across **all** portfolios (11 rows checked, including the Cortland
  portfolio `8cea3d4f-...` and the Demo portfolio `3b683c32-ea8e-4851-b350-fd7b85a60e2e`) is
  **`scope = 'portfolio'`, `asset_id = NULL`, `portfolio_id = <portfolio>`,
  `url = 'https://verifier-mcp-production.up.railway.app/mcp'`, `enabled = true`.** There is
  **no per-asset connector row** anywhere in the table — asset-level scoping happens purely via
  the `asset_id` argument passed into the verifier tool calls (`verifier__list_findings`,
  `verifier__verification_status`), not via a second connector row keyed by asset.
- **The Demo portfolio already has this row** (id `7c78443d-ade6-4e26-b418-9acde6119cee`,
  `plugin_id='verifier'`, `enabled: true`) — so the connector-row gap described in
  `verifier-connector-row-gap` is **already resolved for this portfolio**; no seeding needed
  there. (It does **not** yet have a `crrem` row — see §7 below.)

**To reach a passing gate for a staged demo asset:** ensure (a) this portfolio-scoped connector
row exists and is enabled (it does, for the Demo portfolio), and (b) the asset's actual finding
ledger in the verifier service has zero open-high findings for that `asset_id` — this requires
either genuinely running `verifier__record_finding` + `verifier__resolve_finding` calls ahead of
time against the live verifier MCP for the demo asset, or (if the verifier service supports it)
directly seeding its own findings store — **UNKNOWN, recommend:** call
`verifier__list_findings({asset_id: <demo-asset>})` once through a real session before the demo
to confirm current state, since this task was scoped to read-only DB access and could not call
the verifier MCP directly (no trusted-header proxy available outside a live agent session).

---

## esg-profile

### 7. Demo pickup pattern (`skills/esg-profile/demo/README.md` + `connectors/registry.json`)

- **Static inputs** are read from files under `skills/esg-profile/demo/`:
  - `static/extract.xlsx` (sheet `30_input_qualitative`) — feeds `questionnaire`, `peer_benchmark`,
    `governance`, `bps`, `investment_info` connectors (all `kind: file`/`kind: api` per registry,
    bound to `static` for the demo).
  - `static/notes_scrubbed.docx` — engagement notes.
  - `static/bps_cache.json` — market regulation / fine exposure.
  - `reference/materiality.json` — feeds the `materiality` connector.
  - `example-sponsor.json` / `example-fund.json` — render-check fixtures, not live run inputs.
- **Connector bindings** are resolved per `source_id` from `skills/esg-profile/connectors/registry.json`
  (`default_live_adapter` shape) and then overridden by `state.config.connectors` (kickoff phase,
  step 3). Each `source_id` entry carries `kind: mcp|file|api|manual`; switching a source from
  static→live is a registry/config edit only (no workflow/schema change) — e.g. flipping
  `green_street` from `static` to `{"kind":"mcp","tool":"green-street get_metrics"}`.
  Per the demo README, for the demo run specifically:
  - `crrem` → **LIVE** (`crrem get_pathway`)
  - `physical_risk` → **LIVE** (`physrisk get_hazard_exposure`)
  - `green_street` → static ("not provided" in source)
  - `questionnaire`, `peer_benchmark`, `governance`, `bps`, `investment_info`, `materiality` → static
  - `energy` → static (EU/EPC extract; ESPM is US-only and the demo sponsor is EU)

### crrem live-beat blocker — confirmed

Queried `asset_connectors` for the Demo portfolio (`3b683c32-ea8e-4851-b350-fd7b85a60e2e`):
rows exist for `audette`, `costing`, `retrofit`, `verifier`, plus two `plugin_id: null` rows
(`energy-star`, `mcp.mila.gg`). **There is no `crrem` connector row for the Demo portfolio.**
This directly confirms the brief's premise: the **live-crrem beat in the ESG-profile demo
choreography (`crrem get_pathway` filling the stranding year live, on stage) is currently
blocked** for the Demo portfolio — the tool isn't attached, so any attempt to resolve the `crrem`
`source_id` via its `default_live_adapter` (`kind: mcp`) will error/return unreachable.

**It must fall back to static** for this portfolio unless a `crrem` connector row is added
(mirroring the portfolio-scoped `verifier` row pattern: `scope='portfolio', asset_id=NULL,
portfolio_id='3b683c32-...', plugin_id='crrem', url=<crrem MCP url>, enabled=true`) before the
demo. Per the registry, `crrem` is explicitly flagged `"gap_filler": true` — the whole point of
the demo beat is turning this specific blank into a live value, so **adding the connector row is
the correct staging fix**, not permanently binding it to static in `config.connectors` (that
would defeat the demo's stated purpose). **Recommend:** insert the missing `crrem`
`asset_connectors` row for the Demo portfolio (same shape as the existing `verifier` row) as a
Phase-4 seed step, then leave the registry's `default_live_adapter` (`mcp`, `crrem get_pathway`)
in effect so kickoff step 3 binds it live automatically — no skill/config override needed once
the row exists.

---

## Summary of stores by skill

| Skill | State store | Key convention |
|---|---|---|
| RSRA | None (stateless per-run); OM via `files` table `search_files` | n/a — no cache hooks for slow phases; lever = `[DEMO MODE]` system_prompt only (except Audette, which benefits from a pre-calibrated model) |
| decarb-plan | Agent session/project filesystem — **NOT Supabase** | `projects/<asset-key>/decarb-plan.json` (+ `.md` companion registered in `files`); `<asset-key>` = lowercased asset name, spaces→hyphens |
| esg-profile | Static files under `skills/esg-profile/demo/` (`static/`, `reference/`) + live MCP connectors resolved via `connectors/registry.json` → `state.config.connectors` | No asset-scoped memory/file state for the run ledger described here beyond `projects/<fund>/<sponsor>/esg-profile.json` (per SKILL "State ledger" section — same filesystem pattern as decarb-plan, not verified against DB in this task since brief scoped verification to decarb) |

## Open UNKNOWNs

1. **Verifier findings seeding mechanism** — could not call the verifier MCP directly (needs the
   trusted portfolio header via proxy, not available to a read-only DB task). Recommend a live
   session call `verifier__list_findings({asset_id: <demo-asset>})` to confirm current state
   before relying on "gate passes" as a staged assumption, and use `verifier__record_finding` /
   `verifier__resolve_finding` through a real agent session (not direct DB writes) to seed a
   clean/overridden state — the verifier's own store is external to this Supabase project.
2. **esg-profile `state-schema.json` and `projects/<fund>/<sponsor>/esg-profile.json` persistence**
   — not empirically verified against the DB in this task (brief scoped the DB dive to decarb-plan/
   Cortland only); by analogy with decarb-plan's confirmed filesystem-only persistence, treat it as
   filesystem-only unless later verified otherwise.

---

## CONTROLLER ADDENDUM (post-spike verification)

**Decarb state channel — corrected & sharpened:**
- The engagement `state` ledger is `projects/<asset-key>/decarb-plan.json` in the agent **workspace**.
- The **Resume Protocol reads ONLY the workspace `.json`** (`cat projects/<asset-key>/decarb-plan.json`; SKILL line 355). Missing file ⇒ new engagement at P0.
- The Files store holds the **companion/exports** (`decarb-plan-state.txt/.html`), NOT what resume reads. Confirmed durable per asset across many real engagements.
- **A real "4th and Madison" decarb engagement already exists**: asset `b577e453-8356-4746-8d75-76b7bf93f072`, `decarb-plan-state.txt` in Files (2026-07-07). Usable as the pseudonymization basis.
- **OPEN PLATFORM FACT (blocks decarb pre-stage):** is the managed-agent `projects/` workspace durable per asset / hydrated from the Files store at session start, and writable out-of-band? 
  - If workspace hydrates from Files ⇒ stage `decarb-plan.json` into Files ⇒ resume picks it up ⇒ decarb-as-approved holds.
  - If workspace ephemeral & separate ⇒ fresh demo thread starts at P0 ⇒ "pre-stage & resume" infeasible ⇒ reshape decarb beat. ESCALATED to Christopher.
- P0 DOES bootstrap from Files: it searches portfolio/asset files for an "engagement reference" doc and pre-fills kickoff (SKILL 373-380). So an engagement-reference doc in Files accelerates a live run regardless.

**RSRA/ESG channel (unblocked, proceed):** both read inputs via `search_files` → Files store. No cache hooks. Stage supporting data as **Files documents the agent reads & cites** (keeps clear of RSRA fabrication gate). physrisk stays a live hero call. crrem MCP absent on Demo portfolio → add `installed_plugins` row (Task 4.2) or fall back to static.

**Verifier gate:** connector row `plugin_id='verifier'`, portfolio-scoped (asset_id NULL) — already present on Demo portfolio. Asset scoping is via tool-call args. Findings store seeded via live verifier MCP calls (needs a session), not SQL.
