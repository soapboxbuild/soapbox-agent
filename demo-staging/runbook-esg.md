# Demo Runbook — ESG Profile on Madison (sponsor)

**Status:** ✅ Validated on stage post-`TOOLS_VERSION v14` (thread `39b5efaf`, artifact "Madison — Sponsor ESG Profile (Fund IV, 2025)", ~85s scripted replay).

## Setup (staged)
- Org: **Demo** (`8ebc72a7-…`) → portfolio **Demo** → asset **Madison** (`cece8ad8-…`, Residential/BTR sponsor).
- Files on asset: `extract.xlsx`, `notes_scrubbed.docx`, `bps_cache.json` (ESG Inputs); `example-sponsor.json` (Demo Staging).
- `crrem-skills` MCP attached to the Demo portfolio (row `c02b3008`); physrisk already wired.
- Asset `system_prompt` = `[DEMO MODE — Madison ESG]` (uses a scripted-replay fixture; render via fill_report(esg-profile)).

## On stage (what you do)
1. Open the Demo org → Madison → **new thread**.
2. Type: **"Run the ESG Profile assessment for the Madison sponsor. Inputs are in the asset files. Produce the sponsor ESG profile report."**
3. Watch: begin scripted replay of the verified ESG run (narration + gap-filled crrem + physrisk findings) → reconciles → renders the branded ESG profile.

## Expected beats (~85s target, scripted replay)
- Asset ingestion + files access (scorecard, extract, peer data) — live upstream steps.
- Scripted replay phase (~85s) — deterministic narration of a verified ESG run, including recorded crrem stranding + physrisk findings.
  - **Note:** Live crrem and physrisk calls were intentionally dropped for stage reliability. The narration replays a recorded run's gap-filled stranding year and physical risk; the only live step is the final `fill_report(esg-profile)` re-render.
- Reconcile + regression detection → `fill_report(esg-profile)` → branded artifact (live re-render).

## Hero live calls
- **fill_report(esg-profile)** — the final live render step (re-renders the profile for the current asset).

## Fallback
- Validated artifact `d93af6dc-8fdc-41bd-ae31-5b2ba72cf816` on the Madison asset — open from the artifacts pane.

## Notes
- The `.docx` text-extraction can fail in the agent's `read_file`; the prompt tells it not to retry and to use the spreadsheet + semantic search (harmless).
- Pseudonymous ("Madison"/"Fund IV"); scrub gate: `python3 demo-staging/scrub-check.py`.
