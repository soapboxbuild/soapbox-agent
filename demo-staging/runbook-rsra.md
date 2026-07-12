# Demo Runbook — RSRA (Aris) on 4400 Prairie Crossing

**Status:** ✅ Validated end-to-end on stage (thread `0db2286c`, artifact "4400 Prairie Crossing — RSRA", ~75s scripted replay).

## Setup (staged)
- Org: **Demo** (`8ebc72a7-…`) → portfolio **Demo** → asset **4400 PRAIRIE CROSSING** (`062cbda3-…`, Prairieton TX, multifamily, 2023).
- Files on asset: `om_4400_prairie_crossing.pdf` (Deal Documents), `rsra_data.json` + `physrisk_cache.json` + `bps_cache.json` (Demo Staging).
- Asset `system_prompt` = `[DEMO MODE — 4400 Prairie Crossing]` (uses a scripted-replay fixture; renders via fill_report).

## On stage (what you do)
1. Open the Demo org → 4400 Prairie Crossing → **new thread**.
2. Type: **"Run a Rapid Sustainability Risk Assessment on 4400 Prairie Crossing. The OM is in the deal folder."**
3. Watch the agent: begin scripted replay of the verified RSRA run (narration + hazard findings) → render the branded RSRA report.

## Expected beats (~75s target, scripted replay)
- Asset ingestion (OM → Audette linkage) — live upstream steps.
- Scripted replay phase (~75s) — deterministic narration of a verified RSRA run, including recorded physrisk findings.
  - **Note:** Live physrisk calls were intentionally dropped for stage reliability. The narration replays a recorded run's hazard table + Climate VaR; the only live step is the final `fill_report(rsra)` re-render.
- `fill_report(rsra)` → branded artifact renders in the right pane (live, based on frozen payload).

## Hero live calls
- **fill_report(rsra)** — the final live render step (re-renders the report for the current asset).

## Fallback
- If a live render stalls: the validated artifact from thread `0db2286c` is on the asset — open it from the artifacts pane / Files.

## Notes
- Numbers obey kWh/m², ≤2 sig figs, peer benchmarks. Pseudonymous (Stonebridge Capital acquisition, Prairieton TX) — real names never appear (scrub gate: `python3 demo-staging/scrub-check.py`).
