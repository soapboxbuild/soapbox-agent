# Cambium Grid Factors — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make NREL Cambium the authoritative, forward-looking grid emission-factor source for the decarb/CRREM carbon basis (declining per-year AER/LRMER instead of a static flat eGRID average), expose the scenario as an org-level dropdown, and make the Cambium plugin core to every org.

**Architecture:** The Cambium MCP (`~/cambium-mcp`) deploys to the `soapbox-mcps` Railway project and is seeded as a core plugin in `portfolio.ts`, wired via `installed_plugins.mcp_url` (callable MCP server, per the crrem-skills pattern at agent-config.ts:1345–1356). The org's scenario choice and the "use Cambium for grid factors" directive travel to the **frozen** managed-agent skill bundle via `installed_plugins.prompt_addition`, which is fetched **live per session** (agent-config.ts:322,350) — this is the primary delivery vehicle, since SKILL.md edits only land on re-sync. A scenario dropdown in platform-web PluginsSettings regenerates that `prompt_addition` from a template carrying a `CAMBIUM_SCENARIO=<id>` marker.

**Tech Stack:** TypeScript (MCP: `@modelcontextprotocol/sdk`, zod; API: Hono + Supabase JS; web: Next.js/React), Railway, Cloudflare DNS, Supabase Postgres (project `fplbvanvwvnviczozwhz`).

## Global Constraints

- **Default scenario = `mid_case`** (confirmed by Christopher; NREL/DOE central estimate). Preselected in the dropdown; used when no other scenario is configured.
- **Rate mapping (verbatim):** building CRREM carbon intensity + BAU trajectory use **AER** (average) per year; per-measure carbon savings use **LRMER** (long-run marginal). Per DOE-BTO guidance embedded in the MCP.
- **Cambium plugin is CORE** — auto-provisioned on every org and backfilled onto all existing orgs.
- **MCP domain:** `https://cambium.mcp.soapbox.build/mcp`, deployed to the `soapbox-mcps` Railway project (project id `e5434a34`) — never a new project. Set the Cloudflare CNAME manually after `customDomainCreate`.
- **Region source:** pass the asset's US **state abbreviation** (e.g. `WA`) to `get_emission_factors` `gea_region`; the MCP resolves state → GEA region (WA → `WECCNW`).
- **eGRID/ESPM location-based GHG figure** stays a **labeled secondary disclosure**, never the headline CRREM verdict.
- **Scenario dropdown options (curated CRREM-relevant set):** `mid_case` (default), `mid_case_100_decarb_2035` (most 1.5°C-aligned), `high_re_battery_cost` (upper bound). The dataset holds 8 scenarios; the UI exposes this curated 3 (matching the DOE uncertainty-bound guidance). The MCP still accepts any valid scenario id.
- **Frozen-bundle rule:** the SKILL.md edit (Task 4) only affects new installs / re-syncs. The `prompt_addition` (Tasks 2–3) is what fixes existing orgs (incl. Demo) live. Task 5 verifies the live path.
- **Verified target numbers (WECCNW `mid_case` AER, kg/MWh):** 2026=158.4, 2030=98.4, 2034≈66.6, 2050=11.2. For 4th & Madison (asset `f6e043dd…`, ~all-electric office, EUI 31.1 kBtu/sf ≈ 99 kWh/m²), corrected BAU ≈ 15.7 (2026) → 6.6 (2034), which sits **below** the CRREM pathway (25.5→8.9) across the horizon → **no stranding** (was falsely 2026).

---

### Task 1: Cambium MCP — optional `scenario` param + deploy to soapbox-mcps

**Files:**
- Modify: `~/cambium-mcp/src/index.ts` (the `get_emission_factors` tool input schema, ~line 182)

**Interfaces:**
- Produces: live MCP at `https://cambium.mcp.soapbox.build/mcp` with tools `list_scenarios`, region lookup, `get_emission_factors({ gea_region, scenario?, year })` → `{ aer, lrmer }` kg CO₂e/MWh. `scenario` defaults to `mid_case` when omitted.

- [ ] **Step 1: Make `scenario` optional with a `mid_case` default.**

In `src/index.ts`, change the `get_emission_factors` input schema field from:
```ts
      scenario: z.string().describe("Cambium scenario ID (e.g. 'mid_case'). Use list_scenarios to see options."),
```
to:
```ts
      scenario: z.string().optional().default("mid_case").describe("Cambium scenario ID (e.g. 'mid_case'). Optional — defaults to 'mid_case' (NREL/DOE central estimate). Use list_scenarios to see options."),
```
The existing unknown-scenario guard (`if (!regionRates[scenario])`) already handles a bad id; with the default, an omitted scenario resolves to `mid_case`.

- [ ] **Step 2: Build locally and smoke-test the default.**

Run:
```bash
cd ~/cambium-mcp && npm install && npm run build && node -e '
const {execSync}=require("child_process");
' 2>/dev/null; echo "build exit: $?"
```
Expected: build exit `0`, `dist/` (or configured out dir) produced. If there is a test/smoke script (`package.json` scripts), run it; otherwise verify the built file loads: `node dist/index.js --help 2>&1 | head` should not throw a syntax/import error.

- [ ] **Step 3: Deploy to the `soapbox-mcps` Railway project.**

Deploy as a new service in project `e5434a34` (soapbox-mcps). Set env `CAMBIUM_DATA_URL` only if overriding the default GitHub raw source (`soapboxbuild/cambium-data`); the repo bundles `data/cambium.json`, so the default works. Create the service, deploy the repo, then:
```bash
railway status   # confirm the cambium service is Active in soapbox-mcps
```
Expected: service deployed, healthy.

- [ ] **Step 4: Add the custom domain + Cloudflare CNAME.**

`customDomainCreate` for `cambium.mcp.soapbox.build` on the service, then **manually add the CNAME in Cloudflare** (Railway does not auto-set DNS — see [[feedback-railway-dns-cloudflare]]). Avoid a doubled TXT/CNAME.

- [ ] **Step 5: Verify the live endpoint.**

Run:
```bash
curl -s --max-time 20 https://cambium.mcp.soapbox.build/health; echo
```
Expected: a healthy response (200 / `ok`). Then confirm `get_emission_factors` with **no** scenario returns `mid_case` AER for WA (via an MCP `tools/call` POST, or defer the tool-call assertion to Task 5's agent run). Record the endpoint.

- [ ] **Step 6: Commit.**
```bash
cd ~/cambium-mcp && git add -A && git commit -m "feat: default scenario to mid_case when omitted"
```

---

### Task 2: Core seed — `portfolio.ts` CAMBIUM_PROMPT_ADDITION + corePlugins entry

**Files:**
- Modify: `~/soapbox-platform/apps/api/src/services/portfolio.ts` (prompt const near top; `corePlugins` array ~line 72; connector-seed exclusion filter ~line 103)

**Interfaces:**
- Consumes: live Cambium MCP url from Task 1.
- Produces: every newly created portfolio gets an enabled `installed_plugins` row `plugin_id='cambium'`, `name='plugin_cambium'`, `mcp_url='https://cambium.mcp.soapbox.build/mcp'`, `prompt_addition=CAMBIUM_PROMPT_ADDITION`. No `asset_connectors` row (no-auth, wired via `installed_plugins.mcp_url` like crrem-skills/cashflow).

- [ ] **Step 1: Add the `CAMBIUM_PROMPT_ADDITION` constant** (after `CRREM_PROMPT_ADDITION`).

```ts
// Kept in sync with the platform-web plugin catalog (plugin-registry.ts id 'cambium')
// and the scenario-dropdown template in routes/plugins.ts (buildCambiumPromptAddition).
// The trailing CAMBIUM_SCENARIO marker is parsed by the dropdown to preselect the value.
const CAMBIUM_PROMPT_ADDITION = `You have access to NREL Cambium electricity grid emission factors via the cambium MCP server (tools: list_scenarios, get_emission_factors).

For ANY CRREM / decarbonization carbon-intensity or stranding analysis you MUST source grid emission factors from Cambium — NOT a static eGRID subregion average and NEVER a flat (non-declining) grid factor.

- Building CRREM carbon intensity and the BAU trajectory: call get_emission_factors(gea_region=<asset US state abbrev, e.g. 'WA'>, scenario=<org default below>, year) and use the returned AER (average rate) for EACH year of the trajectory. AER declines year over year, so BAU must slope down accordingly.
- Per-measure carbon savings: use the LRMER (long-run marginal) rate from the same tool.
- The eGRID/ESPM location-based GHG figure is a labeled SECONDARY disclosure (GRESB/lender) only — never the headline CRREM stranding verdict.

Default Cambium scenario for this org: mid_case (NREL/DOE central estimate).
CAMBIUM_SCENARIO=mid_case`
```

- [ ] **Step 2: Add the corePlugins entry** (inside the `corePlugins` array, after the `crrem-skills` entry):

```ts
    { plugin_id: 'cambium',       name: 'plugin_cambium',       description: 'NREL Cambium forward grid emission factors (AER/LRMER) — the CRREM carbon basis and measure-impact grid intensity.', mcp_url: 'https://cambium.mcp.soapbox.build/mcp', prompt_addition: CAMBIUM_PROMPT_ADDITION },
```

- [ ] **Step 3: Exclude cambium from connector seeding** (it is a no-auth `installed_plugins.mcp_url` plugin, like cashflow/crrem-skills).

Change the filter at ~line 103 from:
```ts
  await Promise.all(corePlugins.filter(p => p.mcp_url && p.plugin_id !== 'cashflow' && p.plugin_id !== 'crrem-skills').map(p => {
```
to:
```ts
  await Promise.all(corePlugins.filter(p => p.mcp_url && p.plugin_id !== 'cashflow' && p.plugin_id !== 'crrem-skills' && p.plugin_id !== 'cambium').map(p => {
```

- [ ] **Step 4: Typecheck.**

Run:
```bash
cd ~/soapbox-platform && npx tsc -p apps/api --noEmit 2>&1 | head
```
Expected: no new type errors referencing `portfolio.ts`.

- [ ] **Step 5: Commit.**
```bash
cd ~/soapbox-platform && git add apps/api/src/services/portfolio.ts && git commit -m "feat(cambium): seed Cambium as a core plugin with CRREM grid-factor prompt_addition"
```

---

### Task 3: Backfill existing orgs with the Cambium plugin

**Files:**
- Create: `~/soapbox-agent/demo-staging/backfill-cambium.sql` (idempotent upsert script, run via Supabase MCP `execute_sql`)

**Interfaces:**
- Consumes: `CAMBIUM_PROMPT_ADDITION` text (copy verbatim from Task 2).
- Produces: an enabled `installed_plugins` row `plugin_id='cambium'` on every existing `portfolios` row.

- [ ] **Step 1: Write the idempotent backfill** (`onConflict (portfolio_id,name) do nothing`, matching the seed's conflict target). Insert for every portfolio missing a cambium row:

```sql
insert into installed_plugins (portfolio_id, scope, plugin_id, name, description, mcp_url, prompt_addition, enabled)
select p.id, 'portfolio', 'cambium', 'plugin_cambium',
  'NREL Cambium forward grid emission factors (AER/LRMER) — the CRREM carbon basis and measure-impact grid intensity.',
  'https://cambium.mcp.soapbox.build/mcp',
  $CAMBIUM$<paste CAMBIUM_PROMPT_ADDITION verbatim here>$CAMBIUM$,
  true
from portfolios p
where not exists (
  select 1 from installed_plugins ip
  where ip.portfolio_id = p.id and ip.name = 'plugin_cambium'
);
```

- [ ] **Step 2: Dry-run count first.**

Run (via `execute_sql`, project `fplbvanvwvnviczozwhz`):
```sql
select count(*) as portfolios,
  (select count(*) from installed_plugins where name='plugin_cambium') as cambium_rows
from portfolios;
```
Expected: note the `portfolios` count and current `cambium_rows` (likely 0).

- [ ] **Step 3: Run the backfill.** Execute the Step-1 insert.

- [ ] **Step 4: Verify every portfolio now has an enabled cambium row.**

Run:
```sql
select
  (select count(*) from portfolios) as portfolios,
  (select count(*) from installed_plugins where name='plugin_cambium' and enabled) as cambium_enabled;
```
Expected: `cambium_enabled == portfolios`.

- [ ] **Step 5: Commit the script.**
```bash
cd ~/soapbox-agent && git add demo-staging/backfill-cambium.sql && git commit -m "chore(cambium): idempotent backfill of Cambium core plugin onto existing orgs"
```

---

### Task 4: decarb-plan SKILL.md — name Cambium as THE grid-factor source

**Files:**
- Modify: `~/soapbox-agent/skills/decarb-plan/SKILL.md` (the "Grid emission factor — the CRREM carbon basis (HARD)" rule added in commit dd61f75)

**Interfaces:**
- Consumes: nothing runtime; this is skill text for new installs / re-syncs.
- Produces: the durable methodology rule pointing at the Cambium MCP tools by name (mirrors `CAMBIUM_PROMPT_ADDITION`).

- [ ] **Step 1: Read the current rule** to get exact surrounding text.
```bash
grep -n "Grid emission factor" ~/soapbox-agent/skills/decarb-plan/SKILL.md
```

- [ ] **Step 2: Rewrite the rule body** so it names Cambium as the mechanism (keep the HARD framing). The rule MUST state, verbatim in intent:
  - Source grid factors from the **cambium MCP** (`get_emission_factors(gea_region=<asset US state>, scenario=<org default from the cambium prompt_addition, else mid_case>, year)`); call `list_scenarios` if unsure.
  - Building CRREM intensity + BAU trajectory ← **AER per year** (declining); never a static flat eGRID average, never a flat BAU.
  - Per-measure carbon savings ← **LRMER**.
  - eGRID/ESPM location-based figure = labeled **secondary** disclosure only.
  - Keep the existing Seattle City Light (~0.03) vs NWPPc (~0.29) failure example as the motivating case, noting Cambium's forward WECCNW `mid_case` (0.16→0.01 kg/kWh) is the correct declining basis.

- [ ] **Step 3: Review the diff for internal consistency** (units kgCO₂e/m²/yr; AER/LRMER split matches Global Constraints).
```bash
cd ~/soapbox-agent && git diff skills/decarb-plan/SKILL.md
```
Expected: rule now references Cambium tools; no contradiction with the CRREM-provenance bullet.

- [ ] **Step 4: Commit.**
```bash
cd ~/soapbox-agent && git add skills/decarb-plan/SKILL.md && git commit -m "docs(decarb): grid-factor rule sources Cambium AER/LRMER per year (CRREM carbon basis)"
```

---

### Task 5: Live verification — Demo 4th & Madison re-render un-strands

**Files:**
- None (operational verification). Optional: append results to `~/soapbox-agent/demo-staging/runbook-decarb.md`.

**Interfaces:**
- Consumes: deployed MCP (Task 1), seeded/backfilled cambium row on the Demo org (Task 3), the `prompt_addition` directive.

- [ ] **Step 1: Confirm the Demo org's cambium row is enabled and carries the prompt_addition.**

Run (`execute_sql`):
```sql
select ip.enabled, left(ip.prompt_addition, 60) as pa, ip.mcp_url
from installed_plugins ip
join portfolios p on p.id = ip.portfolio_id
where ip.name='plugin_cambium'
  and p.id = (select portfolio_id from assets where id::text like 'f6e043dd%');
```
Expected: `enabled=true`, `pa` starts with the Cambium directive, `mcp_url` set.

- [ ] **Step 2: If the decarb skill text is load-bearing for this render, re-sync the Demo bundle** (frozen-bundle caveat — the `prompt_addition` alone should suffice, but re-sync guarantees the SKILL rule is present). Trigger the per-portfolio skill re-register for Demo, then restart `soapbox-api` to clear the ~30-min warm cache (per [[building-setup-workflow]]).

- [ ] **Step 3: Start a NEW decarb thread on 4th & Madison** (asset `f6e043dd…`) as the service account and instruct: "Re-run the decarbonization plan carbon basis using Cambium grid factors; render the corrected report." Hold the SSE in a detached run (curl SSE cutoffs cancel managed runs — see prior runbook).

- [ ] **Step 4: Verify the corrected artifact.**

Run (`execute_sql`), newest artifact on the asset:
```sql
select
  (report_data->'targets'->>'crrem_stranding_year') as stranding_year,
  report_data->'targets'->'trajectory'->0->>'bau' as bau_2026,
  report_data->'targets'->'trajectory'->-1->>'bau' as bau_last
from artifacts
where asset_id::text like 'f6e043dd%'
order by created_at desc limit 1;
```
Expected: `bau_2026` ≈ 15–17 (NOT 29.8), `bau_last` < `bau_2026` (declining, ≈6–8), and the BAU series sits below the CRREM pathway → `stranding_year` null / "None" (NOT 2026). If it still shows 29.8/flat, the prompt_addition did not take — re-check Steps 1–2 before proceeding.

- [ ] **Step 5: Record the outcome** in `runbook-decarb.md` (numbers + thread id) and clean up any service-account test threads created during verification (per [[feedback-cleanup-test-data]]).

---

### Task 6: platform-web — Cambium registry entry + scenario dropdown

**Files:**
- Modify: `~/platform-web/src/lib/plugin-registry.ts` (add `cambium` entry + `config_options` field on the `Plugin` type)
- Modify: `~/platform-web/src/components/app/settings/PluginsSettings.tsx` (render the scenario `<select>` + persist)
- Modify: `~/soapbox-platform/apps/api/src/routes/plugins.ts` (accept a scenario in the PATCH and regenerate `prompt_addition`) OR reuse `POST /api/portfolios/plugins`

**Interfaces:**
- Consumes: the `CAMBIUM_SCENARIO=<id>` marker convention from Task 2.
- Produces: an org-level scenario selector that rewrites the cambium `installed_plugins.prompt_addition` (regenerated from the template with the new scenario id + marker).

- [ ] **Step 1: Extend the `Plugin` type** in `plugin-registry.ts` with an optional config-select field:
```ts
  config_options?: {
    key: string;                          // e.g. 'scenario'
    label: string;                        // e.g. 'Default grid scenario'
    default: string;                      // 'mid_case'
    options: { value: string; label: string }[];
  };
```

- [ ] **Step 2: Add the `cambium` registry entry** (curated 3 scenarios per Global Constraints):
```ts
  {
    id: 'cambium',
    name: 'Cambium Grid Factors',
    description: 'NREL Cambium forward grid emission factors (AER/LRMER) — the declining CRREM carbon basis and measure-impact grid intensity.',
    iconUrl: '/icons/soapbox-app-icon.svg',
    category: 'sustainability',
    core: true,
    mcp_url: 'https://cambium.mcp.soapbox.build/mcp',
    mcp_auth_type: 'none',
    config_options: {
      key: 'scenario',
      label: 'Default grid scenario',
      default: 'mid_case',
      options: [
        { value: 'mid_case',                 label: 'Mid Case (NREL central estimate) — default' },
        { value: 'mid_case_100_decarb_2035', label: '100% Decarb by 2035 (most 1.5°C-aligned)' },
        { value: 'high_re_battery_cost',     label: 'High RE/Battery Cost (conservative upper bound)' },
      ],
    },
  },
```

- [ ] **Step 3: Add the API endpoint** to set the scenario. In `routes/plugins.ts`, extend the PATCH (`plugins.patch('/:id')`) to accept `{ scenario }` and, when present for the cambium plugin, set `prompt_addition = buildCambiumPromptAddition(scenario)`. Define `buildCambiumPromptAddition(scenario: string)` in a shared spot (e.g. a small `apps/api/src/lib/cambium-prompt.ts`) that returns the same template as `CAMBIUM_PROMPT_ADDITION` with the scenario substituted in the two places (the "Default Cambium scenario for this org: X" line and the `CAMBIUM_SCENARIO=X` marker). Import that helper in `portfolio.ts` too, replacing the inline const, so seed + dropdown share one source of truth.
  - Guard: reject a `scenario` not in the curated option set (400).

- [ ] **Step 4: Render the dropdown in PluginsSettings.** For a plugin whose registry `meta.config_options` is set (and installed), render a `<select>` (reuse the existing select styling at ~line 796) whose current value is parsed from the installed plugin's `prompt_addition` via `/CAMBIUM_SCENARIO=(\w+)/` (fallback to `config_options.default`). On change, PATCH the plugin id with `{ scenario }` and flash success.

- [ ] **Step 5: Verify locally.**
```bash
cd ~/platform-web && npx next build 2>&1 | tail -20     # or the repo's typecheck script
cd ~/soapbox-platform && npx tsc -p apps/api --noEmit 2>&1 | head
```
Expected: both clean. Manually (or via Playwright) load Settings → Plugins → Cambium: the dropdown renders with `mid_case` preselected; changing it and reloading persists; the cambium `prompt_addition` in the DB reflects the new `CAMBIUM_SCENARIO=` marker.

- [ ] **Step 6: Deploy platform-web + soapbox-api and commit.**
```bash
cd ~/platform-web && git add src/lib/plugin-registry.ts src/components/app/settings/PluginsSettings.tsx && git commit -m "feat(cambium): Cambium plugin registry entry + org scenario dropdown"
cd ~/soapbox-platform && git add apps/api/src/routes/plugins.ts apps/api/src/lib/cambium-prompt.ts apps/api/src/services/portfolio.ts && git commit -m "feat(cambium): scenario PATCH regenerates prompt_addition; shared buildCambiumPromptAddition"
```
Deploy per each repo's standard path (platform-web pushes to `main`; soapbox-api on `main`).

---

## Self-Review

- **Spec coverage:** (1) Cambium as grid source → Tasks 1,2,4,5. (2) scenario dropdown, most-CRREM-aligned option present, `mid_case` default → Task 6 + Global Constraints. (3) core to every org → Tasks 2,3. Testing → Tasks 5,6. All spec sections mapped.
- **Sequencing:** correctness fix (1–5) ships and is verified before the separable dropdown UI (6), per the advisor.
- **Frozen-bundle risk:** addressed — `prompt_addition` (live per session) is the primary channel; Task 5 explicitly checks the live re-render, not stale behavior.
- **Type consistency:** `buildCambiumPromptAddition` is the single source of the prompt template (Task 6 Step 3), shared by seed and dropdown; `CAMBIUM_SCENARIO=<id>` marker convention used consistently in Tasks 2, 3, 6.
- **Placeholder scan:** the only "paste verbatim" is the prompt text (Task 3 Step 1) — deliberate, to keep one source; no TODOs.
- **Scope note:** spec said "3 scenarios"; dataset actually has 8. Resolved in Global Constraints — UI exposes a curated 3, MCP accepts all. Flag to Christopher.
