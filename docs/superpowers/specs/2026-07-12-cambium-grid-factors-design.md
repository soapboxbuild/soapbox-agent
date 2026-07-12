# Cambium Grid Factors for the CRREM Carbon Basis — Design

**Date:** 2026-07-12
**Owner:** Christopher

**Goal:** Make NREL Cambium the authoritative, forward-looking grid emission-factor source for the decarb/CRREM carbon basis — replacing static eGRID regional averages / flat BAU with per-year *declining* factors. Expose the Cambium scenario as an org-level dropdown, and make the Cambium plugin core to every org.

## Decisions (confirmed with Christopher)
- **Default scenario = `mid_case`** (NREL/DOE central estimate). *Flag for review:* the original ask was "most CRREM-aligned as default"; `mid_case_100_decarb_2035` is the most 1.5°C-aligned. `mid_case` chosen as the defensible standard default; the dropdown makes the aggressive scenario one click away. Confirm or flip.
- **Rate type:** **AER** (average) for the building's CRREM carbon intensity + BAU trajectory; **LRMER** (long-run marginal) for per-measure carbon savings. Per DOE-BTO guidance embedded in the MCP.
- **Scenario is an org-level dropdown**, preselected to the default; the decarb flow reads the org's chosen scenario.
- **Cambium plugin is CORE** — auto-provisioned on every org.

## Cambium MCP (already built, `~/cambium-mcp`)
Tools: `list_scenarios` (3: `mid_case`, `high_re_battery_cost`, `mid_case_100_decarb_2035` + DOE guidance), region lookup (GEA region by state/id/name), `get_emission_factors(gea_region, scenario, year) → {aer, lrmer}` kg CO₂e/MWh with linear year interpolation. Data from `CAMBIUM_DATA_URL`. **Not yet deployed.**

## Architecture

### 1. Deploy + provision
- **Deploy `cambium-mcp` to the `soapbox-mcps` Railway project** → `https://cambium.mcp.soapbox.build/mcp`, set `CAMBIUM_DATA_URL`, add the Cloudflare CNAME. (Per [[railway-mcp-project]] / [[feedback-railway-dns-cloudflare]].)
- **Core seed** — add to `soapbox-platform/apps/api/src/services/portfolio.ts` `corePlugins`:
  `{ plugin_id:'cambium', name:'plugin_cambium', description:'NREL Cambium forward grid emission factors (AER/LRMER) for CRREM carbon-basis and measure impact.', mcp_url:'https://cambium.mcp.soapbox.build/mcp' }`. Auto-provisions on every new org; existing orgs get it via the standard provisioning/backfill.
- **`PLUGIN_REGISTRY`** (platform-web `plugin-registry.ts`): add `id:'cambium'`, name "Cambium Grid Factors", `iconUrl:'/icons/soapbox-app-icon.svg'`, `category:'sustainability'`, `core:true`, `mcp_url`, `mcp_auth_type:'none'`.

### 2. Scenario dropdown (org default)
- Cambium plugin carries a **`default_scenario`** config. Rendered as a **dropdown** in `PluginsSettings` with the 3 scenario options (static enum matching `list_scenarios`), preselected to `mid_case`.
- **Implementation detail (resolve in plan):** the connector-config storage/render path. Existing registry supports a plain-text config value (`mcp_auth_secret:false`); this needs a **select** control. Options: (a) add a `config_options?: {key,label,options:[{value,label}],default}` field to the registry + a `<select>` render in PluginsSettings, persisted like the existing config value and passed to the MCP as the connector's config; or (b) if that's heavy, ship a fixed default now (`mid_case`) via the MCP's own default and add the dropdown as a fast-follow. Prefer (a) if the config plumbing is small.
- The decarb flow passes the org's `default_scenario` to `get_emission_factors`; if unset, the MCP default (`mid_case`) applies.

### 3. Wire into the decarb/CRREM carbon basis
Update the decarb-plan CRREM carbon-basis rule (just added in `skills/decarb-plan/SKILL.md`) to name Cambium as THE source:
- Building CRREM intensity + `targets.trajectory[]` BAU and with-plan carbon ← `cambium get_emission_factors(gea_region, scenario, year).aer` **per year** (declining). Region = GEA region mapped from the asset's state/ZIP via the Cambium region tool.
- Per-measure carbon savings ← `.lrmer`.
- The eGRID/ESPM location-based GHG number remains a **labeled secondary disclosure**, never the headline CRREM verdict (unchanged from the rule just encoded).
- Keep the "non-increasing trajectory" + no-flat-BAU guardrails; Cambium's declining AER makes BAU slope down naturally.

## Data flow
```
asset state/ZIP → Cambium region lookup → GEA region
org default_scenario (config) ─┐
                               ├─► cambium get_emission_factors(region, scenario, year)
year (per trajectory point) ───┘        ├─ .aer  → building CRREM intensity + BAU (per year, declining)
                                        └─ .lrmer→ per-measure carbon savings
→ decarb fill_report targets.trajectory[] (declining) vs targets.crrem_pathway (CRREM) → correct stranding verdict
```

## Testing ("make sure it works")
1. **MCP up:** `cambium.mcp.soapbox.build/health` OK; `list_scenarios` returns the 3; region lookup resolves WA → NWPP GEA region.
2. **Declining curve:** `get_emission_factors(NWPP, mid_case, year)` for 2026…2034 returns a **monotonically non-increasing AER** (and steeper under `mid_case_100_decarb_2035`).
3. **Core provisioning:** a fresh/backfilled org shows the Cambium plugin installed + enabled; the scenario dropdown renders with `mid_case` preselected.
4. **End-to-end:** a decarb re-render for 4th & Madison uses Cambium AER → building trajectory declines (not flat 29.8) → 4th & Madison is no longer falsely stranded; eGRID 29.8 shown only as labeled secondary.

## Out of scope
- Utility-specific factors (e.g. Seattle City Light hydro) — Cambium is regional (GEA); the regional declining curve is the standardized fix. A utility-level override is a future enhancement.
- Hourly/8760 Cambium factors — annual AER/LRMER only.
- Backfilling Cambium onto historical rendered reports (only new/re-rendered reports pick it up).
