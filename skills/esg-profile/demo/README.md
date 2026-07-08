# ESG Profile — Demo Runbook (IMN)

The 60-second on-stage transformation: raw, messy sponsor data → a branded, investor-grade
ESG Profile, with connected tools visibly filling gaps the manual process leaves blank.

## Prerequisites
- `esg-profile` is live on `template-mcp` (`templates.mcp.soapbox.build/health` → `esg-profile: available:true`).
- Live MCPs connected in the session: `crrem`, `physrisk` (the gap-fillers). Static inputs
  are pre-loaded here in `demo/static/`.
- **Anonymization:** the demo data in `demo/static/` is already scrubbed and verified clean
  (`node scripts/scrub-demo-data.mjs`). Never stage un-scrubbed source. The real-name denylist
  is untracked at `demo/.scrub-denylist.json`.

## Demo data (pseudonymous)
- `static/extract.xlsx` — sheet `30_input_qualitative` (questionnaire scorecard + qual status,
  peer benchmarks, governance rights, market regulation).
- `static/notes_scrubbed.docx` — engagement notes.
- `static/bps_cache.json` — market regulation / fine exposure.
- `reference/materiality.json` — residential/BTR materiality considerations.
- Fixtures for render checks: `example-sponsor.json`, `example-fund.json`.

## Connector bindings for the demo
| source_id | binding | note |
|-----------|---------|------|
| `crrem` | **LIVE** (`crrem get_pathway`) | fills stranding year — blank in source |
| `physical_risk` | **LIVE** (`physrisk get_hazard_exposure`) | fills physical impact — blank in source |
| `green_street` | static | "not provided" in source |
| `questionnaire`, `peer_benchmark`, `governance`, `bps`, `investment_info` | static (`static/*`) | |
| `energy` | static (EU/EPC) | ESPM is US-only; demo sponsor is EU |
| `materiality` | static (`reference/materiality.json`) | |

## The choreography (Sponsor Profile)
1. **Kickoff** — scope: one sponsor, `anonymize: true`, reporting_year 2025.
2. **Collect** — the visible beat: the agent fans out, calling `crrem` and `physrisk` **live**
   while reading the static extracts. The two live calls turn "not provided / analysis
   underway" into real values on screen.
3. **Reconcile** — normalize units (kWh/m²), apply source-precedence to the seeded
   DISCREPANCY notes (→ Verifier findings), run regression detection across the scorecard trend.
4. **Render** — sponsor-scoped fail-closed gate passes → `fill_report(report_type:'esg-profile')`
   → branded HTML artifact renders (~60s).
5. **Export** — "and here's the PPTX her team actually uses" (+ XLSX companion via
   `scripts/build_xlsx.py --template esg-profile`).

## Fund Overview variant
Run with `scope: fund` over ≥2 sponsors → the Fund ESG Overview layout (sponsor metrics
matrix, ranking vs MIEPPI/MIR, underperformers → risk/mitigation).

## Quick local verification (no live MCPs)
```bash
node scripts/validate-esg-profile.mjs   # schemas + fixtures
node scripts/scrub-demo-data.mjs        # anonymization gate
node scripts/smoke-esg-profile.mjs      # both layouts inject/render
python3 scripts/build_xlsx.py --template esg-profile --data @skills/esg-profile/demo/example-sponsor.json --output /tmp/esg.xlsx
```

## To go live on any data source later
Change the binding in the run config `connectors` block (or the default in
`connectors/registry.json`) from `file` to `mcp`/`api`. No workflow, schema, or template
change. E.g. when Green Street API access lands: `"green_street": {"kind":"mcp","tool":"green-street get_sector_risk"}`.
