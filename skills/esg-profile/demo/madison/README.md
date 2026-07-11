# ESG Profile — Madison Demo (US BTR sponsor)

Sibling fixture set to `demo/` (the EU/Southern-Europe "Sponsor Sierra" demo), scoped to a
fictional US residential/Build-to-Rent sponsor, **Madison**. Same schemas, same choreography —
different market (US BPS/fine-exposure regime instead of EU EPC) so the demo can be run for a
US-market audience without reusing the Sierra fixtures.

## Demo data (pseudonymous)
- `extract.xlsx` — sheet `30_input_qualitative` (questionnaire scorecard + qual status, peer
  benchmarks, governance rights, market regulation), 3 reporting years (2023–2025).
- `notes_scrubbed.docx` — engagement notes, mirrors `demo/static/notes_scrubbed.docx` structure
  (sponsor overview, engagement history, data gaps).
- `bps_cache.json` — market regulation / fine exposure (US Building Performance Standards, fine
  exposure still `TBD` pending jurisdiction-level compliance mapping — same "not provided" pattern
  as the source questionnaire).
- `example-sponsor.json` — Madison-specific sponsor fixture, same shape as
  `../example-sponsor.json`, validates against `templates/esg-profile/schema.json`.
- `reference/materiality.json` (shared, unchanged) — residential/BTR materiality considerations
  apply equally to the US market; no Madison-specific copy needed.

## Connector bindings for this demo
| source_id | binding | note |
|-----------|---------|------|
| `crrem` | **LIVE** (`crrem get_pathway`) — **see gap below** | fills stranding year — blank in source |
| `physical_risk` | **LIVE** (`physrisk get_hazard_exposure`) | fills physical impact — blank in source |
| `green_street` | static | "not rated" in source |
| `questionnaire`, `peer_benchmark`, `governance`, `bps`, `investment_info` | static (`extract.xlsx` / `bps_cache.json`) | |
| `energy` | static | US market; ESPM/Citizen Energy binding can go live later (see registry) |
| `materiality` | static (`../reference/materiality.json`, shared) | |

## ⚠️ CRREM connector gap (flag for demo runner)
The `crrem` MCP is registered as `gap_filler: true` in `connectors/registry.json` and is CORE on
most portfolios, but as of this writing it is **not confirmed attached to the Demo portfolio**
that this fixture set would run under. Before running the live "Collect" beat on stage:
1. Verify `crrem` is connected on the Demo portfolio (asset_connectors row present), same check
   as the `verifier-connector-row-gap` pattern — a missing row silently degrades the tool to
   unavailable rather than erroring loudly.
2. If it isn't, either (a) attach the connector to the Demo portfolio before the run, or (b) fall
   back to a static value for `crrem_stranding_year` (already seeded in `example-sponsor.json` as
   `2030` with `provenance.mode:"live"` — swap to `"static"` provenance if falling back, so the
   render doesn't misrepresent the source as a live gap-fill).
`physical_risk` (physrisk) has no equivalent gap noted — it is expected to already be live on all
portfolios per `rsra-skill-driven-physrisk` memory.

## Pseudonym mapping (kept out of prose; see denylist)
This demo set is derived from patterns in read-only US residential/BTR ESG due-diligence source
material (multiple sponsors/assets) plus a separate US decarbonization/BPS model workbook — none
reproduced verbatim, no figures copied 1:1. All entity names below are invented:
- Sponsor pseudonym: **Madison** (fictional; not a real sponsor name)
- Fund pseudonym: **Fund IV** (fictional)
- All dollar figures, scores, percentages, and dates are invented and do not correspond to any
  single real source value.

The actual real-world identifiers that must never appear in tracked output (property names,
fund managers, LPs, vendors, contacts) are kept in the **untracked** sidecar
`demo/madison/.scrub-denylist.json` (same pattern as `demo/.scrub-denylist.json`) — never commit
real names there or anywhere else; that file exists only so a future
`scripts/scrub-demo-data.mjs`-style check can grep this directory.

## Quick local verification
```bash
node -e "JSON.parse(require('fs').readFileSync('skills/esg-profile/demo/madison/example-sponsor.json'))" && echo SPONSOR_JSON_VALID
node scripts/validate-esg-profile.mjs   # schema-compiles against templates/esg-profile/schema.json (checks demo/example-sponsor.json directly; Madison fixture shares the same schema and was checked ad hoc — see task-2.2-report.md)
python3 demo-staging/scrub-check.py   # fail-closed real-name scrub gate (denylist is untracked)
```

## To go live later
Same mechanism as the main demo README: flip `connectors` block bindings from `file`/`static` to
`mcp`/`api` in the run config or `connectors/registry.json` default — no schema or template change
required.
