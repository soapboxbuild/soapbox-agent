# Demo Staging — Environment (Task 0.1 / 0.2)

## Write target (0.1)
- Supabase project: `fplbvanvwvnviczozwhz`, database `postgres`.
- Confirmed the app (prod + stage config) reads this ref; Demo org present here.
- Demo org: `8ebc72a7-dca1-4cb1-be02-eed12f38340f`
- Demo portfolio: `3b683c32-ea8e-4851-b350-fd7b85a60e2e`
- ⚠️ This ref backs BOTH prod and stage — every write MUST be filtered to the Demo org/portfolio.
- Write path: Supabase MCP (`execute_sql` / `apply_migration`) + verifier MCP for findings + service-account app API for threads.

## Service-account thread creation (0.1) — for Phase 5 rehearsals
- Per `drive-soapbox-app-own-login`: authenticate as claude@agents via Supabase auth, then POST conversations+messages to the app API with `x-organization-id: 8ebc72a7-dca1-4cb1-be02-eed12f38340f`.
- Credentials in Vaultwarden (retrieve at rehearsal time). Base URL = stage app host.

## Installed skill bundle (0.2)
- soapbox-agent bundle on the Demo portfolio contains 14 skills including all three needed:
  `rsra`, `esg-profile`, `decarb-plan` ✅ (also construction-costing, helper-files, quality-review, delivery-presentation, capex-analysis, cashflow-model, portfolio-analysis, portfolio-ingest, project-kickoff, sustainability-passport, utility-split-estimation).
- `skills_synced_sha` is NULL → bundle installed but not marked-synced; Task 1.1 re-syncs to guarantee latest version (skills are PRESENT, so this is a currency check, not a gap).
- MCPs wired at portfolio scope (all enabled): audette, bpd, bps-compliance, brave-search, cashflow, costing, energy-star, memory (agent-memory.soapbox.build), mila, overture-maps, physrisk, retrofit, soapbox-agent (templates.mcp.soapbox.build), verifier.
- NOTE: `crrem` is NOT in the installed list — ESG demo needs crrem LIVE. Flag for Task 4.2 (may need crrem MCP attached to the Demo portfolio).
