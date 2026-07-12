-- Idempotent backfill: ensure every existing portfolio has the core Cambium plugin.
-- Mirrors the corePlugins seed in soapbox-platform apps/api/src/services/portfolio.ts.
-- Run via Supabase (project fplbvanvwvnviczozwhz). Safe to re-run (WHERE NOT EXISTS guard).
-- prompt_addition is kept verbatim in sync with CAMBIUM_PROMPT_ADDITION in portfolio.ts;
-- the trailing CAMBIUM_SCENARIO=<id> marker is what the scenario dropdown parses/rewrites.

insert into installed_plugins (portfolio_id, scope, plugin_id, name, description, mcp_url, prompt_addition, enabled)
select p.id, 'portfolio', 'cambium', 'plugin_cambium',
  'NREL Cambium forward grid emission factors (AER/LRMER) — the CRREM carbon basis and measure-impact grid intensity.',
  'https://cambium-mcp-production.up.railway.app/mcp',
  $CAMBIUM$You have access to NREL Cambium electricity grid emission factors via the cambium MCP server (tools: list_scenarios, get_emission_factors).

For ANY CRREM / decarbonization carbon-intensity or stranding analysis you MUST source grid emission factors from Cambium — NOT a static eGRID subregion average and NEVER a flat (non-declining) grid factor.

- Building CRREM carbon intensity and the BAU trajectory: call get_emission_factors(gea_region=<asset US state abbrev, e.g. 'WA'>, scenario=<org default below>, year) and use the returned AER (average rate) for EACH year of the trajectory. AER declines year over year, so BAU must slope down accordingly.
- Per-measure carbon savings: use the LRMER (long-run marginal) rate from the same tool.
- The eGRID/ESPM location-based GHG figure is a labeled SECONDARY disclosure (GRESB/lender) only — never the headline CRREM stranding verdict.

Default Cambium scenario for this org: mid_case (NREL/DOE central estimate).
CAMBIUM_SCENARIO=mid_case$CAMBIUM$,
  true
from portfolios p
where not exists (
  select 1 from installed_plugins ip
  where ip.portfolio_id = p.id and ip.name = 'plugin_cambium'
);

-- Verify: cambium_enabled should equal the portfolio count.
-- select (select count(*) from portfolios) as portfolios,
--        (select count(*) from installed_plugins where name='plugin_cambium' and enabled) as cambium_enabled;
