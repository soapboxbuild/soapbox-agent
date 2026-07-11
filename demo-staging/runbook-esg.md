# Demo Runbook — ESG Profile on Madison (sponsor)

**Status:** ✅ Validated on stage post-`TOOLS_VERSION v14` (thread `39b5efaf`, artifact "Madison — Sponsor ESG Profile (Fund IV, 2025)", ~314s). Speed-polish pending (see Notes).

## Setup (staged)
- Org: **Demo** (`8ebc72a7-…`) → portfolio **Demo** → asset **Madison** (`cece8ad8-…`, Residential/BTR sponsor).
- Files on asset: `extract.xlsx`, `notes_scrubbed.docx`, `bps_cache.json` (ESG Inputs); `example-sponsor.json` (Demo Staging).
- `crrem-skills` MCP attached to the Demo portfolio (row `c02b3008`); physrisk already wired.
- Asset `system_prompt` = `[DEMO MODE — Madison ESG]` + `[DEMO SPEED]` (read static inputs from Files; crrem + physrisk stay LIVE as the gap-fillers; one call each; render via fill_report(esg-profile)).

## On stage (what you do)
1. Open the Demo org → Madison → **new thread**.
2. Type: **"Run the ESG Profile assessment for the Madison sponsor. Inputs are in the asset files. Produce the sponsor ESG profile report."**
3. Watch: reads the scorecard/extract → live crrem (stranding year) + physrisk (physical hazard) fill the gaps → reconciles → renders the branded ESG profile.

## Expected beats (~5 min, streaming)
- "Reading the questionnaire scorecard / peer benchmarks…" (extract.xlsx)
- **Live crrem** — stranding-year gap filled on screen (was "not provided").
- **Live physrisk** — physical-risk gap filled.
- Reconcile + regression detection across the scorecard trend → `fill_report(esg-profile)` → branded artifact.

## Hero live calls
- **crrem get_pathway / stranding** and **physrisk hazard** — the visible gap-fillers (the ESG selling point).
- **fill_report(esg-profile)** — the render (unblocked by the v14 allowlist fix).

## Fallback
- Validated artifact `d93af6dc-8fdc-41bd-ae31-5b2ba72cf816` on the Madison asset — open from the artifacts pane.

## Notes
- ~5 min is above the 30–60s/turn target. To tighten: pre-stage the fully-computed ESG data object (RSRA-style) so the agent assembles fill_report input directly instead of re-deriving; and keep crrem/physrisk to one call each (already in the prompt).
- The `.docx` text-extraction can fail in the agent's `read_file`; the prompt tells it not to retry and to use the spreadsheet + semantic search (harmless).
- Pseudonymous ("Madison"/"Fund IV"); scrub gate: `python3 demo-staging/scrub-check.py`.
